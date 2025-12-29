"""
Management command to seed admin and system notifications for testing.

Usage:
    python manage.py seed_admin_notifications
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from notifications.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed admin and system notifications for testing admin dashboard'

    def handle(self, *args, **options):
        # Get or create an admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )

        # Create sample admin notifications
        admin_notifications = [
            {
                'title': 'System Alert: High Memory Usage',
                'message': 'System memory usage exceeded 85% threshold. Current usage: 87%',
                'type': Notification.Type.SYSTEM,
                'scope': Notification.Scope.ADMIN,
                'priority': Notification.Priority.HIGH,
            },
            {
                'title': 'Database Backup Completed',
                'message': 'Daily database backup completed successfully at 02:00 UTC',
                'type': Notification.Type.SYSTEM,
                'scope': Notification.Scope.SYSTEM,
                'priority': Notification.Priority.NORMAL,
            },
            {
                'title': 'User Activity Report',
                'message': 'Daily user activity report is ready for review',
                'type': Notification.Type.REPORT_READY,
                'scope': Notification.Scope.ADMIN,
                'priority': Notification.Priority.NORMAL,
            },
            {
                'title': 'New User Registration',
                'message': 'A new user has registered. Email: user@example.com',
                'type': Notification.Type.SYSTEM,
                'scope': Notification.Scope.ADMIN,
                'priority': Notification.Priority.NORMAL,
            },
            {
                'title': 'System Maintenance Alert',
                'message': 'Scheduled system maintenance is planned for tomorrow at 22:00 UTC',
                'type': Notification.Type.REMINDER,
                'scope': Notification.Scope.ADMIN,
                'priority': Notification.Priority.HIGH,
            },
        ]

        # Create notifications
        created_count = 0
        for i, notif_data in enumerate(admin_notifications):
            # Vary the created_at time so they appear to have been created over time
            created_at = timezone.now() - timedelta(days=len(admin_notifications) - i)

            notification, created = Notification.objects.get_or_create(
                recipient=admin_user,
                title=notif_data['title'],
                message=notif_data['message'],
                defaults={
                    'type': notif_data['type'],
                    'scope': notif_data['scope'],
                    'priority': notif_data['priority'],
                    'is_sent': True,
                    'is_read': i > 2,  # First 2 unread, rest read
                    'created_at': created_at,
                    'sent_at': created_at,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {notification.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Already exists: {notification.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} admin/system notifications'
            )
        )

        # Print statistics
        admin_count = Notification.objects.filter(
            scope__in=[Notification.Scope.ADMIN, Notification.Scope.SYSTEM]
        ).count()

        self.stdout.write(f'Total admin/system notifications: {admin_count}')
