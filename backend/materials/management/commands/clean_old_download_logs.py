"""
Management command to clean up old material download logs.

Usage:
    python manage.py clean_old_download_logs [--days 180]

Example:
    python manage.py clean_old_download_logs --days 90
"""

from django.core.management.base import BaseCommand
from materials.models import MaterialDownloadLog
from materials.services.download_logger import DownloadLogger


class Command(BaseCommand):
    help = "Clean up material download logs older than specified days (default 180)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=180,
            help="Delete logs older than N days (default: 180)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options.get("dry_run", False)

        if days < 1:
            self.stdout.write(
                self.style.ERROR("Days must be greater than 0")
            )
            return

        if dry_run:
            # Count how many would be deleted
            from django.utils import timezone
            from datetime import timedelta

            cutoff_date = timezone.now() - timedelta(days=days)
            count = MaterialDownloadLog.objects.filter(
                timestamp__lt=cutoff_date
            ).count()

            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} download logs older than {days} days"
                )
            )
            return

        # Actually delete
        deleted_count, details = DownloadLogger.cleanup_old_logs(days=days)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_count} download logs older than {days} days"
            )
        )

        if details:
            for model, count in details.items():
                self.stdout.write(f"  {model}: {count} items")
