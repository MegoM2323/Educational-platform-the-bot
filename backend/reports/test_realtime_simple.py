"""
Simple synchronous tests for real-time dashboard services.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from reports.services.realtime import DashboardEventService

User = get_user_model()


class DashboardEventServiceSimpleTests(TestCase):
    """Simple tests for DashboardEventService without WebSocket"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Teacher',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Student',
            role='student'
        )

    def test_broadcast_submission_event_no_crash(self):
        """Test that broadcast_submission doesn't crash"""
        from assignments.models import Assignment, AssignmentSubmission

        # Create assignment
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )

        # Create submission
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            submitted_at=timezone.now()
        )

        # Should not raise exception
        DashboardEventService.broadcast_submission(submission, assignment, self.student)

    def test_broadcast_grade_event_no_crash(self):
        """Test that broadcast_grade doesn't crash"""
        from assignments.models import Assignment, AssignmentSubmission

        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            submitted_at=timezone.now(),
            grade=85
        )

        # Should not raise exception
        DashboardEventService.broadcast_grade(submission, assignment, self.student, 85)

    def test_broadcast_assignment_created_no_crash(self):
        """Test that broadcast_assignment_created doesn't crash"""
        from assignments.models import Assignment

        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )

        # Should not raise exception
        DashboardEventService.broadcast_assignment_created(assignment)

    def test_broadcast_assignment_closed_no_crash(self):
        """Test that broadcast_assignment_closed doesn't crash"""
        from assignments.models import Assignment

        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )

        # Should not raise exception
        DashboardEventService.broadcast_assignment_closed(assignment)

    def test_broadcast_to_user_no_crash(self):
        """Test that broadcast_to_user doesn't crash"""
        data = {'message': 'Test event'}

        # Should not raise exception
        DashboardEventService.broadcast_to_user(self.teacher.id, 'custom_event', data)

    def test_broadcast_to_group_no_crash(self):
        """Test that broadcast_to_group doesn't crash"""
        data = {'message': 'Test event'}

        # Should not raise exception
        DashboardEventService.broadcast_to_group('dashboard_metrics', 'custom_event', data)


class DashboardConsumerImportTests(TestCase):
    """Test that consumer can be imported without errors"""

    def test_consumer_import(self):
        """Test that DashboardConsumer can be imported"""
        from reports.consumers import DashboardConsumer
        self.assertIsNotNone(DashboardConsumer)

    def test_routing_import(self):
        """Test that routing can be imported"""
        from reports.routing import websocket_urlpatterns
        self.assertIsNotNone(websocket_urlpatterns)
        self.assertTrue(len(websocket_urlpatterns) > 0)

    def test_event_service_import(self):
        """Test that DashboardEventService can be imported"""
        from reports.services.realtime import DashboardEventService
        self.assertIsNotNone(DashboardEventService)
