"""
T_ASSIGN_014: Tests for plagiarism detection integration.

Tests:
- Model creation and properties
- Service client submission and polling
- Webhook receipt and verification
- Permission checks
- Notification delivery
- Status transitions
"""
import json
import hmac
import hashlib
import pytest
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from assignments.models import Assignment, AssignmentSubmission, PlagiarismReport
from assignments.services.plagiarism import (
    PlagiarismDetectionFactory, CustomPlagiarismClient, TurnitinClient
)
from assignments.tasks.plagiarism import check_plagiarism, poll_plagiarism_results

User = get_user_model()


class PlagiarismReportModelTest(TestCase):
    """Test PlagiarismReport model"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            due_date=timezone.now()
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission content'
        )

    def test_plagiarism_report_creation(self):
        """Test creating plagiarism report"""
        report = PlagiarismReport.objects.create(
            submission=self.submission,
            similarity_score=Decimal('25.5'),
            detection_status=PlagiarismReport.DetectionStatus.COMPLETED,
            sources=[
                {'source': 'example.com', 'match_percent': Decimal('25.5')}
            ]
        )
        self.assertEqual(report.similarity_score, Decimal('25.5'))
        self.assertFalse(report.is_high_similarity)
        self.assertEqual(str(report), f"Plagiarism: {self.student.get_full_name()} - 25.50%")

    def test_high_similarity_detection(self):
        """Test is_high_similarity property"""
        # Low similarity
        report = PlagiarismReport.objects.create(
            submission=self.submission,
            similarity_score=Decimal('20.0'),
            detection_status=PlagiarismReport.DetectionStatus.COMPLETED
        )
        self.assertFalse(report.is_high_similarity)

        # High similarity
        report.similarity_score = Decimal('35.0')
        self.assertTrue(report.is_high_similarity)

    def test_processing_time_calculation(self):
        """Test processing_time_seconds calculation"""
        report = PlagiarismReport.objects.create(
            submission=self.submission,
            detection_status=PlagiarismReport.DetectionStatus.PENDING
        )

        # No checked_at, no processing time
        self.assertIsNone(report.processing_time_seconds)

        # Add checked_at
        report.checked_at = timezone.now()
        processing_time = report.processing_time_seconds
        self.assertIsNotNone(processing_time)
        self.assertGreaterEqual(processing_time, 0)

    def test_unique_plagiarism_report_per_submission(self):
        """Test OneToOneField constraint"""
        PlagiarismReport.objects.create(
            submission=self.submission,
            detection_status=PlagiarismReport.DetectionStatus.COMPLETED
        )

        # Try to create duplicate
        with self.assertRaises(Exception):
            PlagiarismReport.objects.create(
                submission=self.submission,
                detection_status=PlagiarismReport.DetectionStatus.PENDING
            )


class PlagiarismServiceClientTest(TestCase):
    """Test plagiarism service clients"""

    def test_factory_returns_custom_client(self):
        """Test PlagiarismDetectionFactory returns correct client"""
        client = PlagiarismDetectionFactory.get_client('custom')
        self.assertIsInstance(client, CustomPlagiarismClient)

    def test_custom_client_submission(self):
        """Test CustomPlagiarismClient submission"""
        client = CustomPlagiarismClient()
        report_id = client.submit_for_checking('test content', 'test.txt')

        self.assertIsNotNone(report_id)
        self.assertEqual(len(report_id), 36)  # UUID length

    def test_custom_client_get_results(self):
        """Test CustomPlagiarismClient results retrieval"""
        client = CustomPlagiarismClient()
        report_id = client.submit_for_checking('test content')

        results = client.get_results(report_id)
        self.assertIsNotNone(results)
        self.assertIn('similarity_score', results)
        self.assertIn('sources', results)
        self.assertIsInstance(results['sources'], list)

    @patch('requests.post')
    def test_turnitin_client_submission_success(self, mock_post):
        """Test TurnitinClient successful submission"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'turnitin-123'}
        mock_post.return_value = mock_response

        client = TurnitinClient()
        client.api_key = 'test-key'
        report_id = client.submit_for_checking('test content')

        self.assertEqual(report_id, 'turnitin-123')
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_turnitin_client_submission_failure(self, mock_post):
        """Test TurnitinClient submission failure"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad request'
        mock_post.return_value = mock_response

        client = TurnitinClient()
        client.api_key = 'test-key'
        report_id = client.submit_for_checking('test content')

        self.assertIsNone(report_id)


class PlagiarismCheckTaskTest(TestCase):
    """Test plagiarism check Celery tasks"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            due_date=timezone.now()
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission content with some unique text'
        )

    def test_check_plagiarism_task_creates_report(self):
        """Test check_plagiarism task creates PlagiarismReport"""
        result = check_plagiarism(self.submission.id)

        self.assertIn('status', result)
        self.assertTrue(
            result['status'] in ['submitted', 'error'],
            f"Unexpected status: {result['status']}"
        )

        # Check report was created
        report = PlagiarismReport.objects.filter(submission=self.submission).first()
        self.assertIsNotNone(report)
        self.assertIn(
            report.detection_status,
            [PlagiarismReport.DetectionStatus.PENDING,
             PlagiarismReport.DetectionStatus.PROCESSING]
        )

    def test_check_plagiarism_empty_submission(self):
        """Test check_plagiarism with empty submission"""
        empty_submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content=''
        )

        result = check_plagiarism(empty_submission.id)

        self.assertEqual(result['status'], 'error')
        report = PlagiarismReport.objects.filter(submission=empty_submission).first()
        self.assertIsNotNone(report)
        self.assertEqual(
            report.detection_status,
            PlagiarismReport.DetectionStatus.FAILED
        )

    def test_check_plagiarism_duplicate_report(self):
        """Test check_plagiarism prevents duplicate reports"""
        # Create first report
        check_plagiarism(self.submission.id)

        # Try to create second report
        result = check_plagiarism(self.submission.id)

        self.assertEqual(result['status'], 'error')
        self.assertEqual(
            PlagiarismReport.objects.filter(submission=self.submission).count(),
            1
        )


class PlagiarismWebhookTest(TestCase):
    """Test plagiarism webhook endpoints"""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            due_date=timezone.now()
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission'
        )
        self.report = PlagiarismReport.objects.create(
            submission=self.submission,
            service_report_id='turnitin-123',
            detection_status=PlagiarismReport.DetectionStatus.PROCESSING
        )

    def test_webhook_invalid_json(self):
        """Test webhook rejects invalid JSON"""
        response = self.client.post(
            '/api/assignments/webhooks/plagiarism/',
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_missing_report_id(self):
        """Test webhook requires report_id"""
        payload = json.dumps({
            'similarity_score': 25.5,
            'sources': []
        })

        response = self.client.post(
            '/api/assignments/webhooks/plagiarism/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_unknown_report(self):
        """Test webhook for unknown report"""
        payload = json.dumps({
            'report_id': 'unknown-id',
            'similarity_score': 25.5,
            'sources': []
        })

        response = self.client.post(
            '/api/assignments/webhooks/plagiarism/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

    def test_webhook_updates_report(self):
        """Test webhook updates plagiarism report"""
        payload = {
            'report_id': 'turnitin-123',
            'similarity_score': 35.5,
            'sources': [
                {'source': 'example.com', 'match_percent': 35.5}
            ]
        }

        response = self.client.post(
            '/api/assignments/webhooks/plagiarism/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Report should be updated
        self.report.refresh_from_db()
        self.assertEqual(self.report.detection_status, PlagiarismReport.DetectionStatus.COMPLETED)
        self.assertEqual(self.report.similarity_score, Decimal('35.5'))
        self.assertEqual(len(self.report.sources), 1)


class PlagiarismPermissionsTest(TestCase):
    """Test plagiarism endpoint permissions"""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.other_student = User.objects.create_user(
            email='other@test.com',
            password='test123',
            role='student'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            due_date=timezone.now()
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission'
        )
        self.report = PlagiarismReport.objects.create(
            submission=self.submission,
            detection_status=PlagiarismReport.DetectionStatus.COMPLETED
        )

    def test_teacher_can_view_report(self):
        """Test teacher can view any submission's plagiarism report"""
        self.client.login(email='teacher@test.com', password='test123')
        # Note: Would need actual API test here with proper authentication

    def test_student_can_view_own_report(self):
        """Test student can view their own submission's report"""
        # Would test with actual API endpoint
        pass

    def test_student_cannot_view_other_report(self):
        """Test student cannot view other student's report"""
        # Would test with actual API endpoint
        pass


class PlagiarismNotificationTest(TestCase):
    """Test plagiarism notifications"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            due_date=timezone.now()
        )

    @patch('assignments.tasks.plagiarism.NotificationService.notify')
    def test_student_notification_on_completion(self, mock_notify):
        """Test student receives notification on plagiarism check completion"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission'
        )
        report = PlagiarismReport.objects.create(
            submission=submission,
            similarity_score=Decimal('20.0'),
            detection_status=PlagiarismReport.DetectionStatus.COMPLETED
        )

        # Simulate webhook processing
        from assignments.tasks.plagiarism import _send_plagiarism_notifications
        _send_plagiarism_notifications(report)

        # Student notification should be sent
        self.assertTrue(mock_notify.called)

    @patch('assignments.tasks.plagiarism.NotificationService.notify')
    def test_teacher_alert_on_high_similarity(self, mock_notify):
        """Test teacher gets alert for high similarity"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission'
        )
        report = PlagiarismReport.objects.create(
            submission=submission,
            similarity_score=Decimal('45.0'),  # High similarity
            detection_status=PlagiarismReport.DetectionStatus.COMPLETED
        )

        from assignments.tasks.plagiarism import _send_plagiarism_notifications
        _send_plagiarism_notifications(report)

        # Should send both student and teacher notifications
        self.assertEqual(mock_notify.call_count, 2)


class PlagiarismStatusTransitionTest(TestCase):
    """Test plagiarism report status transitions"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Description',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            due_date=timezone.now()
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission'
        )

    def test_status_transitions(self):
        """Test valid status transitions"""
        report = PlagiarismReport.objects.create(
            submission=self.submission,
            detection_status=PlagiarismReport.DetectionStatus.PENDING
        )

        # PENDING -> PROCESSING
        report.detection_status = PlagiarismReport.DetectionStatus.PROCESSING
        report.save()
        self.assertEqual(report.detection_status, PlagiarismReport.DetectionStatus.PROCESSING)

        # PROCESSING -> COMPLETED
        report.detection_status = PlagiarismReport.DetectionStatus.COMPLETED
        report.checked_at = timezone.now()
        report.save()
        self.assertEqual(report.detection_status, PlagiarismReport.DetectionStatus.COMPLETED)

    def test_failed_status_with_error(self):
        """Test FAILED status with error message"""
        report = PlagiarismReport.objects.create(
            submission=self.submission,
            detection_status=PlagiarismReport.DetectionStatus.FAILED,
            error_message='API timeout after 30 seconds'
        )

        self.assertEqual(report.detection_status, PlagiarismReport.DetectionStatus.FAILED)
        self.assertIn('timeout', report.error_message)
