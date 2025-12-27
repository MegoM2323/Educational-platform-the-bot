"""
Celery tasks for user data export.

Handles asynchronous export generation and file management.
"""
import logging
import zipfile
from io import BytesIO
from pathlib import Path

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from accounts.export import UserDataExporter, ExportFileManager
from core.monitoring import log_system_event

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def generate_user_export(self, user_id: int, export_format: str = 'json') -> dict:
    """
    Asynchronously generate user data export.

    Collects data from all relevant models and saves to file.
    Supports both JSON and CSV formats.

    Args:
        user_id: ID of user to export
        export_format: 'json' or 'csv'

    Returns:
        dict: {
            'success': bool,
            'file_path': str (if successful),
            'file_size': int,
            'format': str,
            'message': str
        }

    Raises:
        User.DoesNotExist: User not found
    """
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"Starting export for user {user.username} (ID: {user_id})")

        # Collect all user data
        exporter = UserDataExporter(user)
        exporter.collect_all_data()

        if export_format == 'csv':
            file_path = _save_csv_export(user_id, exporter)
        else:
            file_path = _save_json_export(user_id, exporter)

        # Get file size
        file_size = default_storage.size(file_path)

        log_system_event(
            user=user,
            action='DATA_EXPORT_GENERATED',
            resource_type='user_export',
            details={
                'format': export_format,
                'file_path': file_path,
                'file_size': file_size
            }
        )

        logger.info(
            f"Export completed for user {user.username}: "
            f"{file_path} ({file_size} bytes)"
        )

        return {
            'success': True,
            'file_path': file_path,
            'file_size': file_size,
            'format': export_format,
            'message': 'Export generated successfully'
        }

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for export")
        return {
            'success': False,
            'message': 'User not found',
            'format': export_format
        }
    except Exception as exc:
        logger.exception(f"Error generating export for user {user_id}")
        self.retry(exc=exc)


def _save_json_export(user_id: int, exporter: UserDataExporter) -> str:
    """
    Save export as JSON file.

    Args:
        user_id: User ID
        exporter: UserDataExporter instance

    Returns:
        str: File path
    """
    json_content = exporter.to_json()
    file_path = ExportFileManager.get_export_path(user_id, 'json')
    default_storage.save(file_path, ContentFile(json_content.encode('utf-8')))
    return file_path


def _save_csv_export(user_id: int, exporter: UserDataExporter) -> str:
    """
    Save export as ZIP with multiple CSV files.

    Args:
        user_id: User ID
        exporter: UserDataExporter instance

    Returns:
        str: File path
    """
    csv_files = exporter.to_csv()

    # Create ZIP archive in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in csv_files.items():
            zip_file.writestr(filename, content.encode('utf-8'))

    zip_buffer.seek(0)
    file_path = ExportFileManager.get_export_path(user_id, 'csv')
    default_storage.save(file_path, ContentFile(zip_buffer.read()))
    return file_path


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    autoretry_for=(Exception,),
)
def cleanup_expired_exports(self) -> dict:
    """
    Scheduled task to remove expired export files.

    Runs daily and removes exports older than CLEANUP_AFTER_DAYS.

    Returns:
        dict: {
            'success': bool,
            'deleted_count': int,
            'message': str
        }
    """
    try:
        deleted_count = ExportFileManager.cleanup_old_exports()
        logger.info(f"Cleaned up {deleted_count} expired export files")
        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} expired exports'
        }
    except Exception as exc:
        logger.exception("Error cleaning up exports")
        self.retry(exc=exc)
