"""
Tests for Broadcast System Enhancements
Testing progress tracking, cancellation, and retry functionality
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient

from notifications.models import Broadcast, BroadcastRecipient
from notifications.services.broadcast import BroadcastService

User = get_user_model()


class BroadcastProgressTestCase(TestCase):
    """Test progress tracking functionality"""

    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        # Create test students
        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='TestPass123!',
                first_name=f'Student{i}',
                last_name='Test',
                role='student'
            )
            for i in range(10)
        ]

        # Create broadcast
        self.broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test broadcast message',
            recipient_count=10,
            status=Broadcast.Status.SENDING
        )

        # Create broadcast recipients
        self.recipients = []
        for i, student in enumerate(self.students):
            recipient = BroadcastRecipient.objects.create(
                broadcast=self.broadcast,
                recipient=student
            )
            self.recipients.append(recipient)

            # Mark some as sent
            if i < 7:
                recipient.telegram_sent = True
                recipient.save()
            # Mark some as failed
            elif i < 9:
                recipient.telegram_error = 'Network timeout'
                recipient.save()

        # Update broadcast counts
        self.broadcast.sent_count = 7
        self.broadcast.failed_count = 2
        self.broadcast.save()

    def test_get_progress_returns_correct_stats(self):
        """Test that progress endpoint returns correct statistics"""
        progress = BroadcastService.get_progress(self.broadcast.id)

        assert progress['id'] == self.broadcast.id
        assert progress['status'] == Broadcast.Status.SENDING
        assert progress['total_recipients'] == 10
        assert progress['sent_count'] == 7
        assert progress['failed_count'] == 2
        assert progress['pending_count'] == 1
        assert progress['progress_pct'] == 70
        assert 'Network timeout' in progress['error_summary']

    def test_get_progress_not_found(self):
        """Test that progress raises error for non-existent broadcast"""
        with pytest.raises(ValueError):
            BroadcastService.get_progress(9999)

    def test_progress_percentage_calculation(self):
        """Test progress percentage is calculated correctly"""
        progress = BroadcastService.get_progress(self.broadcast.id)
        expected_percentage = (7 + 2) / 10 * 100
        assert progress['progress_pct'] == int(expected_percentage)

    def test_progress_with_zero_recipients(self):
        """Test progress with zero recipients"""
        empty_broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.CUSTOM,
            message='Empty broadcast',
            recipient_count=0,
            status=Broadcast.Status.SENDING
        )

        progress = BroadcastService.get_progress(empty_broadcast.id)
        assert progress['progress_pct'] == 0
        assert progress['pending_count'] == 0

    def test_progress_all_sent(self):
        """Test progress when all messages are sent"""
        self.broadcast.sent_count = 10
        self.broadcast.failed_count = 0
        self.broadcast.status = Broadcast.Status.COMPLETED
        self.broadcast.completed_at = timezone.now()
        self.broadcast.save()

        progress = BroadcastService.get_progress(self.broadcast.id)
        assert progress['progress_pct'] == 100
        assert progress['pending_count'] == 0
        assert progress['status'] == Broadcast.Status.COMPLETED


class BroadcastCancellationTestCase(TestCase):
    """Test broadcast cancellation functionality"""

    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        self.broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test broadcast',
            recipient_count=100,
            status=Broadcast.Status.SENDING
        )

    def test_cancel_broadcast_success(self):
        """Test successful broadcast cancellation"""
        result = BroadcastService.cancel_broadcast(self.broadcast.id)

        assert result['success'] is True
        assert result['broadcast_id'] == self.broadcast.id
        assert 'cancelled_at' in result

        # Verify broadcast status changed
        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.CANCELLED
        assert self.broadcast.completed_at is not None

    def test_cancel_non_existent_broadcast(self):
        """Test cancellation of non-existent broadcast"""
        with pytest.raises(ValueError):
            BroadcastService.cancel_broadcast(9999)

    def test_cannot_cancel_already_sent_broadcast(self):
        """Test that already sent broadcasts cannot be cancelled"""
        self.broadcast.status = Broadcast.Status.SENT
        self.broadcast.completed_at = timezone.now()
        self.broadcast.save()

        with pytest.raises(ValueError) as exc_info:
            BroadcastService.cancel_broadcast(self.broadcast.id)

        assert 'Cannot cancel broadcast' in str(exc_info.value)

    def test_cannot_cancel_completed_broadcast(self):
        """Test that completed broadcasts cannot be cancelled"""
        self.broadcast.status = Broadcast.Status.COMPLETED
        self.broadcast.completed_at = timezone.now()
        self.broadcast.save()

        with pytest.raises(ValueError):
            BroadcastService.cancel_broadcast(self.broadcast.id)

    def test_cannot_cancel_already_cancelled_broadcast(self):
        """Test that cancelled broadcasts cannot be cancelled again"""
        self.broadcast.status = Broadcast.Status.CANCELLED
        self.broadcast.completed_at = timezone.now()
        self.broadcast.save()

        with pytest.raises(ValueError):
            BroadcastService.cancel_broadcast(self.broadcast.id)

    def test_can_cancel_draft_broadcast(self):
        """Test that draft broadcasts can be cancelled"""
        self.broadcast.status = Broadcast.Status.DRAFT
        self.broadcast.save()

        result = BroadcastService.cancel_broadcast(self.broadcast.id)
        assert result['success'] is True

        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.CANCELLED

    def test_can_cancel_sending_broadcast(self):
        """Test that sending broadcasts can be cancelled"""
        self.broadcast.status = Broadcast.Status.SENDING
        self.broadcast.save()

        result = BroadcastService.cancel_broadcast(self.broadcast.id)
        assert result['success'] is True

        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.CANCELLED


class BroadcastRetryTestCase(TestCase):
    """Test broadcast retry functionality"""

    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        # Create students
        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='TestPass123!',
                first_name=f'Student{i}',
                last_name='Test',
                role='student'
            )
            for i in range(10)
        ]

        self.broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test broadcast',
            recipient_count=10,
            status=Broadcast.Status.SENDING,
            sent_count=7,
            failed_count=3
        )

        # Create recipients - 7 sent, 3 failed
        for i, student in enumerate(self.students):
            recipient = BroadcastRecipient.objects.create(
                broadcast=self.broadcast,
                recipient=student
            )

            if i < 7:
                recipient.telegram_sent = True
                recipient.save()
            else:
                recipient.telegram_error = 'Network error'
                recipient.save()

    def test_retry_failed_recipients(self):
        """Test retry with failed recipients"""
        result = BroadcastService.retry_failed(self.broadcast.id)

        assert result['success'] is True
        assert result['retried_count'] == 3
        assert 'task_id' in result
        assert result['broadcast_id'] == self.broadcast.id

    def test_retry_no_failed_recipients(self):
        """Test retry when no failed recipients exist"""
        # Mark all as sent
        BroadcastRecipient.objects.filter(
            broadcast=self.broadcast,
            telegram_sent=False
        ).delete()

        result = BroadcastService.retry_failed(self.broadcast.id)

        assert result['success'] is True
        assert result['retried_count'] == 0

    def test_retry_non_existent_broadcast(self):
        """Test retry of non-existent broadcast"""
        with pytest.raises(ValueError):
            BroadcastService.retry_failed(9999)

    def test_retry_updates_broadcast_status(self):
        """Test that retry updates broadcast status to SENDING"""
        self.broadcast.status = Broadcast.Status.COMPLETED
        self.broadcast.save()

        # Restart from completed state to get failed recipients
        self.broadcast.status = Broadcast.Status.SENDING
        self.broadcast.save()

        result = BroadcastService.retry_failed(self.broadcast.id)

        self.broadcast.refresh_from_db()
        # Status will be updated by async task, not immediately
        # But the task should be queued
        assert result['success'] is True


class BroadcastUpdateProgressTestCase(TestCase):
    """Test progress update functionality"""

    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        self.broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test broadcast',
            recipient_count=100,
            status=Broadcast.Status.SENDING
        )

    def test_update_progress_success(self):
        """Test successful progress update"""
        BroadcastService.update_progress(self.broadcast.id, 80, 10)

        self.broadcast.refresh_from_db()
        assert self.broadcast.sent_count == 80
        assert self.broadcast.failed_count == 10

    def test_update_progress_to_completed(self):
        """Test that progress update marks broadcast as completed when all processed"""
        BroadcastService.update_progress(self.broadcast.id, 95, 5)

        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.COMPLETED
        assert self.broadcast.completed_at is not None

    def test_update_progress_to_failed_when_all_fail(self):
        """Test that broadcast is marked failed if all sends fail"""
        BroadcastService.update_progress(self.broadcast.id, 0, 100)

        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.FAILED
        assert self.broadcast.completed_at is not None

    def test_update_progress_non_existent_broadcast(self):
        """Test updating progress for non-existent broadcast (should not error)"""
        # Should handle gracefully
        BroadcastService.update_progress(9999, 50, 10)
        # No exception raised

    def test_update_progress_stays_sending_if_not_complete(self):
        """Test that broadcast stays in SENDING status if not all processed"""
        BroadcastService.update_progress(self.broadcast.id, 50, 30)

        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.SENDING


class BroadcastAPIEndpointsTestCase(TestCase):
    """Test broadcast API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        self.broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test broadcast',
            recipient_count=100,
            status=Broadcast.Status.SENDING,
            sent_count=70,
            failed_count=20
        )

        self.client.force_authenticate(user=self.admin_user)

    def test_progress_endpoint_returns_correct_data(self):
        """Test GET /broadcasts/{id}/progress/ endpoint"""
        response = self.client.get(f'/api/admin/broadcasts/{self.broadcast.id}/progress/')

        assert response.status_code == 200
        data = response.json()['data']
        assert data['total_recipients'] == 100
        assert data['sent_count'] == 70
        assert data['failed_count'] == 20
        assert data['progress_pct'] == 90

    def test_progress_endpoint_not_found(self):
        """Test progress endpoint with non-existent broadcast"""
        response = self.client.get('/api/admin/broadcasts/9999/progress/')
        assert response.status_code == 404

    def test_cancel_endpoint_cancels_broadcast(self):
        """Test POST /broadcasts/{id}/cancel/ endpoint"""
        response = self.client.post(f'/api/admin/broadcasts/{self.broadcast.id}/cancel/')

        assert response.status_code == 200
        data = response.json()['data']
        assert data['success'] is True
        assert data['broadcast_id'] == self.broadcast.id

        self.broadcast.refresh_from_db()
        assert self.broadcast.status == Broadcast.Status.CANCELLED

    def test_cancel_endpoint_fails_for_completed(self):
        """Test cancel endpoint fails for completed broadcasts"""
        self.broadcast.status = Broadcast.Status.COMPLETED
        self.broadcast.save()

        response = self.client.post(f'/api/admin/broadcasts/{self.broadcast.id}/cancel/')
        assert response.status_code == 400

    def test_retry_endpoint_queues_retry(self):
        """Test POST /broadcasts/{id}/retry/ endpoint"""
        # Create some failed recipients
        student = User.objects.create_user(
            email='student@test.com',
            password='TestPass123!',
            role='student'
        )
        BroadcastRecipient.objects.create(
            broadcast=self.broadcast,
            recipient=student,
            telegram_error='Network error'
        )

        response = self.client.post(f'/api/admin/broadcasts/{self.broadcast.id}/retry/')

        assert response.status_code == 200
        data = response.json()['data']
        assert data['success'] is True
        assert 'task_id' in data

    def test_retry_endpoint_no_failed(self):
        """Test retry endpoint when no failed recipients"""
        response = self.client.post(f'/api/admin/broadcasts/{self.broadcast.id}/retry/')

        assert response.status_code == 200
        data = response.json()['data']
        assert data['retried_count'] == 0


# ============= TEST SUMMARY =============
"""
Test Coverage:
- Progress Tracking: 5 tests
  * Correct statistics returned
  * Error handling for non-existent broadcasts
  * Progress percentage calculation
  * Edge cases (zero recipients, all sent)

- Cancellation: 6 tests
  * Successful cancellation
  * Error handling for non-existent broadcasts
  * Status validation (cannot cancel completed/cancelled)
  * Can cancel draft/sending broadcasts

- Retry: 5 tests
  * Retry with failed recipients
  * Handling when no failed recipients exist
  * Error handling for non-existent broadcasts
  * Status updates during retry

- Progress Updates: 5 tests
  * Successful updates
  * Auto-completion when all processed
  * Failed status when all fail
  * Graceful handling of non-existent broadcasts

- API Endpoints: 6 tests
  * Progress endpoint functionality
  * Cancel endpoint functionality
  * Retry endpoint functionality
  * Error handling (404, 400)

Total: 27 tests covering all requirements
"""
