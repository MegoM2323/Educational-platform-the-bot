"""
GDPR-compliant user data export service.

Handles data collection, export generation, and secure downloads.
"""
import json
import csv
import os
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from io import StringIO, BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings

User = get_user_model()


class UserDataExporter:
    """
    Collects and exports user data in GDPR-compliant manner.
    """

    def __init__(self, user: User):
        """
        Initialize exporter for a specific user.

        Args:
            user: User instance to export data for
        """
        self.user = user
        self.export_data = {}

    def collect_all_data(self) -> Dict[str, Any]:
        """
        Collect all user data from various sources.

        Returns:
            dict: Complete user data structure
        """
        self.export_data = {
            'user': self._export_user_profile(),
            'profile': self._export_role_profiles(),
            'notifications': self._export_notifications(),
            'messages': self._export_messages(),
            'assignments': self._export_assignments(),
            'payments': self._export_payments(),
            'activity': self._export_activity(),
            'export_timestamp': timezone.now().isoformat(),
        }
        return self.export_data

    def _export_user_profile(self) -> Dict[str, Any]:
        """
        Export base user profile information.

        Returns:
            dict: User profile data
        """
        return {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'full_name': self.user.get_full_name(),
            'role': self.user.role,
            'phone': self.user.phone,
            'is_verified': self.user.is_verified,
            'is_active': self.user.is_active,
            'created_at': self.user.created_at.isoformat(),
            'updated_at': self.user.updated_at.isoformat(),
        }

    def _export_role_profiles(self) -> Dict[str, Any]:
        """
        Export role-specific profile information.

        Returns:
            dict: Profile data by role
        """
        profiles = {}

        # Student profile
        if hasattr(self.user, 'student_profile'):
            sp = self.user.student_profile
            profiles['student'] = {
                'grade': sp.grade,
                'goal': sp.goal,
                'progress_percentage': sp.progress_percentage,
                'streak_days': sp.streak_days,
                'total_points': sp.total_points,
                'accuracy_percentage': sp.accuracy_percentage,
                'telegram': sp.telegram,
            }

        # Teacher profile
        if hasattr(self.user, 'teacher_profile'):
            tp = self.user.teacher_profile
            profiles['teacher'] = {
                'subject': tp.subject,
                'experience_years': tp.experience_years,
                'bio': tp.bio,
                'telegram': tp.telegram,
            }

        # Tutor profile
        if hasattr(self.user, 'tutor_profile'):
            tp = self.user.tutor_profile
            profiles['tutor'] = {
                'specialization': tp.specialization,
                'experience_years': tp.experience_years,
                'bio': tp.bio,
                'telegram': tp.telegram,
            }

        # Parent profile
        if hasattr(self.user, 'parent_profile'):
            pp = self.user.parent_profile
            profiles['parent'] = {
                'relationship': pp.relationship,
                'telegram': pp.telegram,
                'children_count': pp.children_students.count(),
            }

        return profiles

    def _export_notifications(self) -> List[Dict[str, Any]]:
        """
        Export notifications sent to user.

        Returns:
            list: User's notifications
        """
        from notifications.models import Notification

        notifications = Notification.objects.filter(
            user=self.user
        ).values(
            'id', 'type', 'title', 'message', 'is_read',
            'created_at', 'read_at'
        ).order_by('-created_at')

        return list(notifications)

    def _export_messages(self) -> List[Dict[str, Any]]:
        """
        Export user's chat messages (only their own side).

        Returns:
            list: User's messages
        """
        from chat.models import Message

        messages = Message.objects.filter(
            sender=self.user
        ).values(
            'id', 'content', 'created_at', 'is_edited',
            'edited_at', 'room_id'
        ).order_by('created_at')

        return list(messages)

    def _export_assignments(self) -> Dict[str, Any]:
        """
        Export user's assignments and submissions.

        Returns:
            dict: Assignments and submissions data
        """
        from assignments.models import Assignment, AssignmentSubmission

        assignments_data = {
            'assigned': [],
            'submissions': []
        }

        # Assignments assigned to user
        assigned = Assignment.objects.filter(
            assigned_to=self.user
        ).values(
            'id', 'title', 'description', 'type', 'status',
            'max_score', 'start_date', 'due_date'
        ).order_by('-due_date')

        assignments_data['assigned'] = list(assigned)

        # Submissions made by user
        submissions = AssignmentSubmission.objects.filter(
            student=self.user
        ).values(
            'id', 'assignment_id', 'status', 'score',
            'feedback', 'submitted_at', 'graded_at'
        ).order_by('-submitted_at')

        assignments_data['submissions'] = list(submissions)

        return assignments_data

    def _export_payments(self) -> Dict[str, Any]:
        """
        Export user's payment history.

        Returns:
            dict: Payments and invoices data
        """
        from payments.models import Payment, Invoice

        payments_data = {
            'payments': [],
            'invoices': []
        }

        # Payments
        payments = Payment.objects.filter(
            customer_id=self.user.id
        ).values(
            'id', 'amount', 'status', 'service_name',
            'created', 'paid_at'
        ).order_by('-created')

        payments_data['payments'] = list(payments)

        # Invoices
        invoices = Invoice.objects.filter(
            user=self.user
        ).values(
            'id', 'invoice_number', 'amount', 'status',
            'created_at', 'due_date'
        ).order_by('-created_at')

        payments_data['invoices'] = list(invoices)

        return payments_data

    def _export_activity(self) -> List[Dict[str, Any]]:
        """
        Export user's activity log.

        Returns:
            list: Recent activity events
        """
        from core.models import ActivityLog

        activity = ActivityLog.objects.filter(
            user=self.user
        ).values(
            'id', 'action', 'resource_type', 'resource_id',
            'ip_address', 'user_agent', 'timestamp'
        ).order_by('-timestamp')[:1000]  # Last 1000 events

        return list(activity)

    def to_json(self) -> str:
        """
        Export data as JSON.

        Returns:
            str: JSON-formatted user data
        """
        # Convert datetime objects to ISO format strings
        return json.dumps(
            self.export_data,
            default=str,
            indent=2,
            ensure_ascii=False
        )

    def to_csv(self) -> Dict[str, str]:
        """
        Export data as CSV (multiple files).

        Returns:
            dict: File names mapped to CSV content
        """
        csv_files = {}

        # User profile CSV
        user_csv = StringIO()
        writer = csv.DictWriter(user_csv, fieldnames=self.export_data['user'].keys())
        writer.writeheader()
        writer.writerow(self.export_data['user'])
        csv_files['user.csv'] = user_csv.getvalue()

        # Notifications CSV
        if self.export_data['notifications']:
            notif_csv = StringIO()
            writer = csv.DictWriter(
                notif_csv,
                fieldnames=self.export_data['notifications'][0].keys()
            )
            writer.writeheader()
            writer.writerows(self.export_data['notifications'])
            csv_files['notifications.csv'] = notif_csv.getvalue()

        # Messages CSV
        if self.export_data['messages']:
            msg_csv = StringIO()
            writer = csv.DictWriter(
                msg_csv,
                fieldnames=self.export_data['messages'][0].keys()
            )
            writer.writeheader()
            writer.writerows(self.export_data['messages'])
            csv_files['messages.csv'] = msg_csv.getvalue()

        # Assignments CSV
        if self.export_data['assignments']['assigned']:
            assign_csv = StringIO()
            writer = csv.DictWriter(
                assign_csv,
                fieldnames=self.export_data['assignments']['assigned'][0].keys()
            )
            writer.writeheader()
            writer.writerows(self.export_data['assignments']['assigned'])
            csv_files['assignments.csv'] = assign_csv.getvalue()

        # Submissions CSV
        if self.export_data['assignments']['submissions']:
            subm_csv = StringIO()
            writer = csv.DictWriter(
                subm_csv,
                fieldnames=self.export_data['assignments']['submissions'][0].keys()
            )
            writer.writeheader()
            writer.writerows(self.export_data['assignments']['submissions'])
            csv_files['submissions.csv'] = subm_csv.getvalue()

        # Payments CSV
        if self.export_data['payments']['payments']:
            pay_csv = StringIO()
            writer = csv.DictWriter(
                pay_csv,
                fieldnames=self.export_data['payments']['payments'][0].keys()
            )
            writer.writeheader()
            writer.writerows(self.export_data['payments']['payments'])
            csv_files['payments.csv'] = pay_csv.getvalue()

        return csv_files


class ExportTokenGenerator:
    """
    Generate and verify secure download tokens.
    """

    TOKEN_VALIDITY_DAYS = 7

    @classmethod
    def generate(cls, user_id: int, filename: str) -> str:
        """
        Generate a secure HMAC token for file download.

        Args:
            user_id: User ID
            filename: Export filename

        Returns:
            str: Secure token
        """
        secret = settings.SECRET_KEY
        timestamp = timezone.now().isoformat()
        message = f"{user_id}:{filename}:{timestamp}".encode()
        token = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        return token

    @classmethod
    def verify(cls, user_id: int, filename: str, token: str, timestamp: str) -> bool:
        """
        Verify token and check expiration.

        Args:
            user_id: User ID
            filename: Export filename
            token: Provided token
            timestamp: ISO format timestamp

        Returns:
            bool: Token is valid and not expired
        """
        # Verify token signature
        secret = settings.SECRET_KEY
        message = f"{user_id}:{filename}:{timestamp}".encode()
        expected_token = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(token, expected_token):
            return False

        # Check expiration
        try:
            token_time = datetime.fromisoformat(timestamp)
            expiry_time = token_time + timedelta(days=cls.TOKEN_VALIDITY_DAYS)
            return timezone.now() <= expiry_time
        except (ValueError, TypeError):
            return False


class ExportFileManager:
    """
    Manage export file storage and cleanup.
    """

    EXPORT_DIR = 'user_exports'
    CLEANUP_AFTER_DAYS = 7

    @classmethod
    def get_export_path(cls, user_id: int, export_format: str) -> str:
        """
        Get standardized export file path.

        Args:
            user_id: User ID
            export_format: 'json' or 'csv'

        Returns:
            str: File path
        """
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        extension = 'json' if export_format == 'json' else 'zip'
        filename = f"export_user_{user_id}_{timestamp}.{extension}"
        return f"{cls.EXPORT_DIR}/{filename}"

    @classmethod
    def save_export(cls, user_id: int, content: str, export_format: str) -> str:
        """
        Save export file to storage.

        Args:
            user_id: User ID
            content: File content
            export_format: 'json' or 'csv'

        Returns:
            str: File path
        """
        filepath = cls.get_export_path(user_id, export_format)
        default_storage.save(filepath, content)
        return filepath

    @classmethod
    def cleanup_old_exports(cls, days: int = CLEANUP_AFTER_DAYS) -> int:
        """
        Delete expired export files.

        Args:
            days: Files older than this many days are deleted

        Returns:
            int: Number of files deleted
        """
        from django.core.management.base import CommandError

        try:
            cutoff_time = timezone.now() - timedelta(days=days)
            deleted_count = 0

            for filename in default_storage.listdir(cls.EXPORT_DIR)[1]:
                file_path = f"{cls.EXPORT_DIR}/{filename}"
                file_time = default_storage.get_created_time(file_path)

                if file_time < cutoff_time:
                    default_storage.delete(file_path)
                    deleted_count += 1

            return deleted_count
        except Exception:
            return 0
