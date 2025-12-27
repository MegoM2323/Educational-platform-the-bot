"""
Tests for notification archival system
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Notification
from .archive import NotificationArchiveService

User = get_user_model()


class NotificationArchiveServiceTests(TransactionTestCase):
    """Tests for NotificationArchiveService"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            email='test1@test.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User1'
        )
        self.user2 = User.objects.create_user(
            email='test2@test.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User2'
        )

    def test_archive_old_notifications(self):
        """Test archiving notifications older than 30 days"""
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        old_date = thirty_days_ago - timedelta(days=1)

        # Create old notifications (should be archived)
        old_notif1 = Notification.objects.create(
            recipient=self.user1,
            title='Old notification 1',
            message='This is old',
            type=Notification.Type.SYSTEM,
            created_at=old_date
        )
        old_notif2 = Notification.objects.create(
            recipient=self.user1,
            title='Old notification 2',
            message='This is also old',
            type=Notification.Type.MESSAGE_NEW,
            created_at=old_date
        )

        # Create recent notifications (should NOT be archived)
        recent_notif = Notification.objects.create(
            recipient=self.user1,
            title='Recent notification',
            message='This is recent',
            type=Notification.Type.SYSTEM
        )

        # Archive old notifications
        result = NotificationArchiveService.archive_old_notifications(days=30)

        # Verify results
        assert result['archived_count'] >= 2, f"Expected at least 2 archived, got {result['archived_count']}"
        assert len(result['errors']) == 0, f"Expected no errors, got {result['errors']}"

        # Verify notifications
        old_notif1.refresh_from_db()
        old_notif2.refresh_from_db()
        recent_notif.refresh_from_db()

        assert old_notif1.is_archived is True, "Old notification 1 should be archived"
        assert old_notif1.archived_at is not None, "Archived notification should have archived_at timestamp"
        assert old_notif2.is_archived is True, "Old notification 2 should be archived"
        assert recent_notif.is_archived is False, "Recent notification should NOT be archived"

    def test_archive_notifications_batch_processing(self):
        """Test that archiving handles batch processing correctly"""
        now = timezone.now()
        old_date = now - timedelta(days=31)

        # Create many notifications to test batching
        notifications = []
        for i in range(150):
            notif = Notification.objects.create(
                recipient=self.user1,
                title=f'Notification {i}',
                message=f'Message {i}',
                type=Notification.Type.SYSTEM,
                created_at=old_date
            )
            notifications.append(notif)

        # Archive with small batch size
        result = NotificationArchiveService.archive_old_notifications(
            days=30,
            batch_size=50
        )

        # Verify all were archived
        assert result['archived_count'] == 150, f"Expected 150 archived, got {result['archived_count']}"

        # Verify no errors
        assert len(result['errors']) == 0, f"Expected no errors, got {result['errors']}"

    def test_get_archive_statistics(self):
        """Test archive statistics"""
        now = timezone.now()
        old_date = now - timedelta(days=31)

        # Create archived notifications
        notif1 = Notification.objects.create(
            recipient=self.user1,
            title='Old notif 1',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now,
            created_at=old_date
        )
        notif2 = Notification.objects.create(
            recipient=self.user1,
            title='Old notif 2',
            message='msg',
            type=Notification.Type.MESSAGE_NEW,
            is_archived=True,
            archived_at=now,
            created_at=old_date
        )
        notif3 = Notification.objects.create(
            recipient=self.user2,
            title='Old notif 3',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now,
            created_at=old_date
        )

        # Get statistics for user1
        stats = NotificationArchiveService.get_archive_statistics(user=self.user1)

        assert stats['total_archived'] == 2, "User1 should have 2 archived notifications"
        assert Notification.Type.SYSTEM in stats['archived_by_type'], "Should have SYSTEM type"
        assert stats['archived_by_type'][Notification.Type.SYSTEM] == 1, "Should have 1 SYSTEM notification"
        assert Notification.Type.MESSAGE_NEW in stats['archived_by_type'], "Should have MESSAGE_NEW type"

        # Get statistics for all users
        stats_all = NotificationArchiveService.get_archive_statistics()
        assert stats_all['total_archived'] == 3, "Should have 3 total archived notifications"

    def test_restore_notification(self):
        """Test restoring a single notification"""
        now = timezone.now()

        # Create archived notification
        notif = Notification.objects.create(
            recipient=self.user1,
            title='Archived notification',
            message='This is archived',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )

        # Restore
        restored = NotificationArchiveService.restore_notification(notif.id, user=self.user1)

        # Verify
        assert restored.is_archived is False, "Notification should be restored"
        assert restored.archived_at is None, "Archived_at should be cleared"

    def test_restore_notification_not_found(self):
        """Test restoring non-existent notification"""
        with pytest.raises(ValueError):
            NotificationArchiveService.restore_notification(9999, user=self.user1)

    def test_restore_non_archived_notification(self):
        """Test restoring non-archived notification"""
        # Create non-archived notification
        notif = Notification.objects.create(
            recipient=self.user1,
            title='Not archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=False
        )

        with pytest.raises(ValueError):
            NotificationArchiveService.restore_notification(notif.id, user=self.user1)

    def test_bulk_restore_notifications(self):
        """Test restoring multiple notifications"""
        now = timezone.now()

        # Create archived notifications
        notif1 = Notification.objects.create(
            recipient=self.user1,
            title='Archived 1',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )
        notif2 = Notification.objects.create(
            recipient=self.user1,
            title='Archived 2',
            message='msg',
            type=Notification.Type.MESSAGE_NEW,
            is_archived=True,
            archived_at=now
        )
        notif3 = Notification.objects.create(
            recipient=self.user1,
            title='Not archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=False
        )

        # Restore multiple
        result = NotificationArchiveService.bulk_restore_notifications(
            [notif1.id, notif2.id, notif3.id],
            user=self.user1
        )

        # Verify
        assert result['restored_count'] == 2, f"Should restore 2, got {result['restored_count']}"
        assert result['not_found'] == 1, f"Should have 1 not restored, got {result['not_found']}"

        # Verify notifications
        notif1.refresh_from_db()
        notif2.refresh_from_db()
        assert notif1.is_archived is False, "Notification 1 should be restored"
        assert notif2.is_archived is False, "Notification 2 should be restored"

    def test_bulk_delete_archived(self):
        """Test deleting old archived notifications"""
        now = timezone.now()
        old_archived = now - timedelta(days=91)
        recent_archived = now - timedelta(days=50)

        # Create old archived notification (should be deleted)
        old_notif = Notification.objects.create(
            recipient=self.user1,
            title='Old archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=old_archived
        )

        # Create recent archived notification (should NOT be deleted)
        recent_notif = Notification.objects.create(
            recipient=self.user1,
            title='Recent archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=recent_archived
        )

        # Delete old archived
        result = NotificationArchiveService.bulk_delete_archived(days=90)

        # Verify
        assert result['deleted_count'] >= 1, f"Should delete at least 1, got {result['deleted_count']}"
        assert len(result['errors']) == 0, f"Should have no errors, got {result['errors']}"

        # Verify old notification is deleted
        assert not Notification.objects.filter(id=old_notif.id).exists(), "Old notification should be deleted"

        # Verify recent notification still exists
        assert Notification.objects.filter(id=recent_notif.id).exists(), "Recent notification should still exist"


class NotificationArchiveAPITests(APITestCase):
    """Tests for notification archive API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@test.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_archive_endpoint_returns_archived_notifications(self):
        """Test GET /api/notifications/archive/"""
        now = timezone.now()
        old_date = now - timedelta(days=31)

        # Create archived notifications
        notif1 = Notification.objects.create(
            recipient=self.user,
            title='Archived 1',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )
        notif2 = Notification.objects.create(
            recipient=self.user,
            title='Archived 2',
            message='msg',
            type=Notification.Type.MESSAGE_NEW,
            is_archived=True,
            archived_at=now
        )

        # Create non-archived notification (should NOT appear)
        Notification.objects.create(
            recipient=self.user,
            title='Not archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=False
        )

        # Get archive
        response = self.client.get('/api/notifications/archive/')

        # Verify
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2, f"Should return 2 archived, got {len(response.data['results'])}"

    def test_archive_endpoint_with_type_filter(self):
        """Test archive endpoint with type filter"""
        now = timezone.now()

        # Create archived notifications of different types
        Notification.objects.create(
            recipient=self.user,
            title='System notification',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )
        Notification.objects.create(
            recipient=self.user,
            title='Message notification',
            message='msg',
            type=Notification.Type.MESSAGE_NEW,
            is_archived=True,
            archived_at=now
        )

        # Filter by type
        response = self.client.get('/api/notifications/archive/?type=system')

        # Verify
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1, "Should return only SYSTEM notifications"
        assert response.data['results'][0]['type'] == 'system'

    def test_archive_endpoint_with_date_filter(self):
        """Test archive endpoint with date filters"""
        now = timezone.now()
        old_date = now - timedelta(days=10)
        very_old_date = now - timedelta(days=30)

        # Create archived notifications at different times
        Notification.objects.create(
            recipient=self.user,
            title='Very old',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now,
            created_at=very_old_date
        )
        Notification.objects.create(
            recipient=self.user,
            title='Old',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now,
            created_at=old_date
        )

        # Filter by date
        date_from = (now - timedelta(days=15)).isoformat()
        response = self.client.get(f'/api/notifications/archive/?date_from={date_from}')

        # Verify
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1, "Should return only recent notifications"

    def test_restore_endpoint(self):
        """Test PATCH /api/notifications/{id}/restore/"""
        now = timezone.now()

        # Create archived notification
        notif = Notification.objects.create(
            recipient=self.user,
            title='Archived notification',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )

        # Restore
        response = self.client.patch(f'/api/notifications/{notif.id}/restore/')

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_archived'] is False
        assert response.data['archived_at'] is None

        # Verify in database
        notif.refresh_from_db()
        assert notif.is_archived is False

    def test_restore_non_archived_notification_fails(self):
        """Test that restoring non-archived notification fails"""
        # Create non-archived notification
        notif = Notification.objects.create(
            recipient=self.user,
            title='Not archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=False
        )

        # Try to restore
        response = self.client.patch(f'/api/notifications/{notif.id}/restore/')

        # Verify error
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_list_excludes_archived_by_default(self):
        """Test that list endpoint excludes archived notifications by default"""
        now = timezone.now()

        # Create archived notification
        Notification.objects.create(
            recipient=self.user,
            title='Archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )

        # Create non-archived notification
        Notification.objects.create(
            recipient=self.user,
            title='Active',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=False
        )

        # List notifications
        response = self.client.get('/api/notifications/')

        # Verify only non-archived is returned
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1, "Should only return non-archived notifications"
        assert response.data['results'][0]['title'] == 'Active'

    def test_other_users_cannot_access_archived(self):
        """Test that users cannot access other users' archived notifications"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='TestPass123!',
            first_name='Other',
            last_name='User'
        )
        now = timezone.now()

        # Create archived notification for other user
        notif = Notification.objects.create(
            recipient=other_user,
            title='Other user archived',
            message='msg',
            type=Notification.Type.SYSTEM,
            is_archived=True,
            archived_at=now
        )

        # Try to restore as different user
        response = self.client.patch(f'/api/notifications/{notif.id}/restore/')

        # Verify not found
        assert response.status_code == status.HTTP_404_NOT_FOUND
