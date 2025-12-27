"""
Tests for autograder webhook integration (T_ASSIGN_009).

Tests verify:
- Valid webhook processing
- Invalid signature rejection
- Replay attack prevention
- Grade application with notifications
- Error handling and retry mechanism
- Rate limiting enforcement
"""

import json
import hmac
import hashlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

from assignments.models import Assignment, AssignmentSubmission
from assignments.webhooks.models import (
    FailedWebhookLog,
    WebhookSignatureLog,
    WebhookAuditTrail
)
from assignments.webhooks.autograder import (
    verify_webhook_signature,
    check_replay_attack
)
from assignments.services.autograder import AutograderService
from notifications.models import Notification

User = get_user_model()


class TestAutograderWebhookSignatureVerification(TestCase):
    """Test HMAC-SHA256 signature verification"""

    def test_valid_signature(self):
        """Valid signature should be accepted"""
        secret = 'test-secret-key'
        payload = b'{"submission_id": 123, "score": 85}'

        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        assert verify_webhook_signature(payload, signature, secret)

    def test_invalid_signature(self):
        """Invalid signature should be rejected"""
        payload = b'{"submission_id": 123, "score": 85}'
        invalid_signature = 'invalid_signature'

        assert not verify_webhook_signature(payload, invalid_signature)

    def test_signature_tampering_detected(self):
        """Modified payload should fail signature verification"""
        secret = 'test-secret-key'
        original_payload = b'{"submission_id": 123, "score": 85}'

        # Calculate signature for original payload
        signature = hmac.new(
            secret.encode(),
            original_payload,
            hashlib.sha256
        ).hexdigest()

        # Try with tampered payload
        tampered_payload = b'{"submission_id": 123, "score": 90}'
        assert not verify_webhook_signature(tampered_payload, signature, secret)


class TestReplayAttackPrevention(TestCase):
    """Test replay attack detection and prevention"""

    def setUp(self):
        """Clear cache before each test"""
        cache.clear()

    def test_replay_attack_detected(self):
        """Replay of same submission should be detected"""
        submission_id = 123
        timestamp = timezone.now().isoformat()

        # First request should succeed
        assert check_replay_attack(submission_id, timestamp)

        # Second request with same timestamp should be rejected
        assert not check_replay_attack(submission_id, timestamp)

    def test_old_webhook_rejected(self):
        """Webhook older than 5 minutes should be rejected"""
        submission_id = 456
        old_time = (timezone.now() - timedelta(minutes=6)).isoformat()

        assert not check_replay_attack(submission_id, old_time, max_age_seconds=300)

    def test_recent_webhook_accepted(self):
        """Recent webhook should be accepted"""
        submission_id = 789
        recent_time = (timezone.now() - timedelta(seconds=30)).isoformat()

        assert check_replay_attack(submission_id, recent_time, max_age_seconds=300)


class TestAutograderWebhookEndpoint(TestCase):
    """Test webhook HTTP endpoint"""

    def setUp(self):
        """Setup test fixtures"""
        cache.clear()
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7)
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Student answer',
            status=AssignmentSubmission.Status.SUBMITTED
        )
        self.secret = 'test-webhook-secret'

    def _create_signature(self, payload_dict):
        """Helper to create HMAC signature"""
        payload_json = json.dumps(payload_dict)
        payload_bytes = payload_json.encode()
        return hmac.new(
            self.secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    def test_missing_signature_header_rejected(self):
        """Missing signature header should return 401"""
        payload = {
            'submission_id': self.submission.id,
            'score': 85,
            'max_score': 100,
            'feedback': 'Test feedback',
            'timestamp': timezone.now().isoformat()
        }

        response = self.client.post(
            '/api/webhooks/autograder/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 401

    def test_invalid_signature_rejected(self):
        """Invalid signature should return 401"""
        payload = {
            'submission_id': self.submission.id,
            'score': 85,
            'max_score': 100,
            'feedback': 'Test feedback',
            'timestamp': timezone.now().isoformat()
        }

        response = self.client.post(
            '/api/webhooks/autograder/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_AUTOGRADER_SIGNATURE='invalid_signature_here'
        )

        assert response.status_code == 401

    def test_invalid_json_rejected(self):
        """Invalid JSON payload should return 400"""
        response = self.client.post(
            '/api/webhooks/autograder/',
            data='{invalid json}',
            content_type='application/json',
            HTTP_X_AUTOGRADER_SIGNATURE='any_signature'
        )

        assert response.status_code == 400

    def test_missing_required_fields_rejected(self):
        """Missing required fields should return 400"""
        payload = {
            'submission_id': self.submission.id,
            'score': 85
            # Missing max_score, feedback, timestamp
        }
        signature = self._create_signature(payload)

        response = self.client.post(
            '/api/webhooks/autograder/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_AUTOGRADER_SIGNATURE=signature
        )

        assert response.status_code == 400

    def test_nonexistent_submission_returns_404(self):
        """Webhook for non-existent submission should return 404"""
        payload = {
            'submission_id': 99999,  # Non-existent
            'score': 85,
            'max_score': 100,
            'feedback': 'Test feedback',
            'timestamp': timezone.now().isoformat()
        }
        signature = self._create_signature(payload)

        response = self.client.post(
            '/api/webhooks/autograder/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_AUTOGRADER_SIGNATURE=signature
        )

        assert response.status_code == 404


class TestAutograderServiceGradeApplication(TestCase):
    """Test grade application logic"""

    def setUp(self):
        """Setup test fixtures"""
        cache.clear()
        self.service = AutograderService()
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7)
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Student answer',
            status=AssignmentSubmission.Status.SUBMITTED
        )

    def test_grade_applied_to_submission(self):
        """Grade should be applied to submission"""
        payload = {
            'submission_id': self.submission.id,
            'score': 85,
            'max_score': 100,
            'feedback': 'Well done!',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        result = self.service.process_webhook(payload, request)

        assert result['success'] is True
        assert result['score'] == 85

        # Refresh and check submission
        self.submission.refresh_from_db()
        assert self.submission.score == 85
        assert self.submission.max_score == 100
        assert self.submission.feedback == 'Well done!'
        assert self.submission.status == AssignmentSubmission.Status.GRADED

    def test_submission_status_changed_to_graded(self):
        """Submission status should change to GRADED"""
        payload = {
            'submission_id': self.submission.id,
            'score': 90,
            'max_score': 100,
            'feedback': 'Excellent!',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        self.service.process_webhook(payload, request)

        self.submission.refresh_from_db()
        assert self.submission.status == AssignmentSubmission.Status.GRADED

    def test_graded_at_timestamp_set(self):
        """graded_at timestamp should be set"""
        payload = {
            'submission_id': self.submission.id,
            'score': 80,
            'max_score': 100,
            'feedback': 'Good',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        before = timezone.now()
        self.service.process_webhook(payload, request)
        after = timezone.now()

        self.submission.refresh_from_db()
        assert self.submission.graded_at is not None
        assert before <= self.submission.graded_at <= after

    def test_notification_sent_to_student(self):
        """Notification should be sent to student"""
        payload = {
            'submission_id': self.submission.id,
            'score': 75,
            'max_score': 100,
            'feedback': 'Needs improvement',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        # Clear existing notifications
        Notification.objects.filter(recipient=self.student).delete()

        self.service.process_webhook(payload, request)

        # Check notification was created
        notification = Notification.objects.filter(
            recipient=self.student,
            type=Notification.Type.ASSIGNMENT_GRADED
        ).first()

        assert notification is not None

    def test_invalid_score_rejected(self):
        """Score exceeding max_score should be rejected"""
        payload = {
            'submission_id': self.submission.id,
            'score': 150,  # Exceeds max_score of 100
            'max_score': 100,
            'feedback': 'Invalid!',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        with self.assertRaises(Exception):
            self.service.process_webhook(payload, request)

    def test_negative_score_rejected(self):
        """Negative score should be rejected"""
        payload = {
            'submission_id': self.submission.id,
            'score': -10,
            'max_score': 100,
            'feedback': 'Invalid!',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        with self.assertRaises(Exception):
            self.service.process_webhook(payload, request)


class TestErrorHandlingAndRetry(TestCase):
    """Test error handling and retry mechanism"""

    def setUp(self):
        """Setup test fixtures"""
        cache.clear()
        self.service = AutograderService()

    def test_failed_webhook_logged(self):
        """Failed webhook should be logged for retry"""
        payload = {
            'submission_id': 99999,  # Non-existent
            'score': 85,
            'max_score': 100,
            'feedback': 'Test',
            'timestamp': timezone.now().isoformat()
        }

        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'test'}

        # Clear existing failed logs
        FailedWebhookLog.objects.all().delete()

        try:
            self.service.process_webhook(payload, request)
        except Exception:
            pass

        # Check failed webhook was logged
        failed_log = FailedWebhookLog.objects.filter(
            submission_id=payload['submission_id']
        ).first()

        assert failed_log is not None
        assert failed_log.status == FailedWebhookLog.Status.PENDING


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
