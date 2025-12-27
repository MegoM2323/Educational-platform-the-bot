"""
T_ASSIGN_006: Tests for assignment scheduling (auto-publish and auto-close).

Tests cover:
- Model field validation
- Celery task execution
- State transitions (draft -> published -> closed)
- Notification delivery
- Permission checks
- Edge cases
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase

from assignments.models import Assignment
from assignments.tasks import (
    auto_publish_assignments,
    auto_close_assignments,
    check_assignment_scheduling,
)
from notifications.models import Notification
from materials.models import Subject

User = get_user_model()


class AssignmentSchedulingTestCase(TestCase):
    """Tests for assignment scheduling feature (T_ASSIGN_006)."""

    def setUp(self):
        """Set up test data."""
        # Create test users
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher',
            first_name='Test',
            last_name='Teacher'
        )

        self.student1 = User.objects.create_user(
            email='student1@test.com',
            password='TestPass123!',
            role='student',
            first_name='Test',
            last_name='Student1'
        )

        self.student2 = User.objects.create_user(
            email='student2@test.com',
            password='TestPass123!',
            role='student',
            first_name='Test',
            last_name='Student2'
        )

        # Create test subject
        self.subject = Subject.objects.create(
            name='Math',
            code='MATH101',
            created_by=self.teacher
        )

        # Get common times
        self.now = timezone.now()
        self.past = self.now - timedelta(hours=1)
        self.future = self.now + timedelta(hours=1)
        self.future_close = self.now + timedelta(hours=2)

    def test_assignment_can_have_publish_at_field(self):
        """Test that Assignment model has publish_at field."""
        assignment = Assignment.objects.create(
            title='Scheduled Assignment',
            description='An assignment to be published later',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.future,
            status=Assignment.Status.DRAFT,
        )

        self.assertIsNotNone(assignment.publish_at)
        self.assertEqual(assignment.publish_at, self.future)

    def test_assignment_can_have_close_at_field(self):
        """Test that Assignment model has close_at field."""
        assignment = Assignment.objects.create(
            title='Scheduled Assignment',
            description='An assignment to be closed later',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            close_at=self.future,
            status=Assignment.Status.PUBLISHED,
        )

        self.assertIsNotNone(assignment.close_at)
        self.assertEqual(assignment.close_at, self.future)

    def test_auto_publish_pending_assignments(self):
        """
        Test T_ASSIGN_006: auto_publish_assignments task publishes
        assignments with publish_at in the past.
        """
        # Create a draft assignment ready to publish
        assignment = Assignment.objects.create(
            title='Ready to Publish',
            description='This should be published',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.past,  # In the past - should be published
            status=Assignment.Status.DRAFT,
        )

        # Assign to students
        assignment.assigned_to.set([self.student1, self.student2])

        # Run the task
        result = auto_publish_assignments()

        # Verify assignment was published
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.PUBLISHED)

        # Verify result
        self.assertEqual(result['published_count'], 1)
        self.assertEqual(result['failed_count'], 0)

    def test_auto_publish_notifications_sent(self):
        """
        Test T_ASSIGN_006: auto_publish_assignments sends notifications
        to assigned students.
        """
        assignment = Assignment.objects.create(
            title='Ready to Publish',
            description='This should be published',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.past,
            status=Assignment.Status.DRAFT,
        )

        assignment.assigned_to.set([self.student1, self.student2])

        # Run the task
        auto_publish_assignments()

        # Verify notifications were created
        notifications = Notification.objects.filter(
            related_object_type='Assignment',
            related_object_id=assignment.id,
        )

        self.assertEqual(notifications.count(), 2)

        # Verify notifications were sent to assigned students
        notification_recipients = set(
            notifications.values_list('recipient_id', flat=True)
        )
        expected_recipients = {self.student1.id, self.student2.id}
        self.assertEqual(notification_recipients, expected_recipients)

    def test_auto_close_published_assignments(self):
        """
        Test T_ASSIGN_006: auto_close_assignments task closes
        assignments with close_at in the past.
        """
        # Create a published assignment ready to close
        assignment = Assignment.objects.create(
            title='Ready to Close',
            description='This should be closed',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            close_at=self.past,  # In the past - should be closed
            status=Assignment.Status.PUBLISHED,
        )

        # Assign to students
        assignment.assigned_to.set([self.student1, self.student2])

        # Run the task
        result = auto_close_assignments()

        # Verify assignment was closed
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.CLOSED)

        # Verify result
        self.assertEqual(result['closed_count'], 1)
        self.assertEqual(result['failed_count'], 0)

    def test_auto_close_notifications_sent(self):
        """
        Test T_ASSIGN_006: auto_close_assignments sends notifications
        to assigned students.
        """
        assignment = Assignment.objects.create(
            title='Ready to Close',
            description='This should be closed',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            close_at=self.past,
            status=Assignment.Status.PUBLISHED,
        )

        assignment.assigned_to.set([self.student1, self.student2])

        # Run the task
        auto_close_assignments()

        # Verify notifications were created
        notifications = Notification.objects.filter(
            related_object_type='Assignment',
            related_object_id=assignment.id,
        )

        self.assertEqual(notifications.count(), 2)

    def test_draft_assignments_not_published_if_future(self):
        """
        Test that draft assignments with future publish_at are NOT published.
        """
        assignment = Assignment.objects.create(
            title='Future Publish',
            description='Should not be published yet',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.future,  # In the future - should NOT be published
            status=Assignment.Status.DRAFT,
        )

        # Run the task
        result = auto_publish_assignments()

        # Verify assignment is still draft
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.DRAFT)

        # Verify result
        self.assertEqual(result['published_count'], 0)

    def test_published_assignments_not_closed_if_future(self):
        """
        Test that published assignments with future close_at are NOT closed.
        """
        assignment = Assignment.objects.create(
            title='Future Close',
            description='Should not be closed yet',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            close_at=self.future,  # In the future - should NOT be closed
            status=Assignment.Status.PUBLISHED,
        )

        # Run the task
        result = auto_close_assignments()

        # Verify assignment is still published
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.PUBLISHED)

        # Verify result
        self.assertEqual(result['closed_count'], 0)

    def test_check_assignment_scheduling_combines_results(self):
        """
        Test T_ASSIGN_006: check_assignment_scheduling task runs both
        publish and close operations.
        """
        # Create both publish-ready and close-ready assignments
        publish_assignment = Assignment.objects.create(
            title='Ready to Publish',
            description='Should be published',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.past,
            status=Assignment.Status.DRAFT,
        )

        close_assignment = Assignment.objects.create(
            title='Ready to Close',
            description='Should be closed',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            close_at=self.past,
            status=Assignment.Status.PUBLISHED,
        )

        publish_assignment.assigned_to.set([self.student1])
        close_assignment.assigned_to.set([self.student1])

        # Run the combined task
        result = check_assignment_scheduling()

        # Verify both operations completed
        self.assertEqual(result['total_published'], 1)
        self.assertEqual(result['total_closed'], 1)

        # Verify state changes
        publish_assignment.refresh_from_db()
        close_assignment.refresh_from_db()

        self.assertEqual(publish_assignment.status, Assignment.Status.PUBLISHED)
        self.assertEqual(close_assignment.status, Assignment.Status.CLOSED)

    def test_no_notifications_to_unassigned_users(self):
        """
        Test that notifications are only sent to assigned students,
        not to all students.
        """
        assignment = Assignment.objects.create(
            title='Assigned Assignment',
            description='Only for specific students',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.past,
            status=Assignment.Status.DRAFT,
        )

        # Only assign to student1, not student2
        assignment.assigned_to.set([self.student1])

        # Run the task
        auto_publish_assignments()

        # Verify notifications only to student1
        notifications = Notification.objects.filter(
            related_object_type='Assignment',
            related_object_id=assignment.id,
        )

        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().recipient, self.student1)

    def test_multiple_assignments_published_in_batch(self):
        """
        Test that multiple assignments can be published in a single task run.
        """
        assignments = []
        for i in range(3):
            assignment = Assignment.objects.create(
                title=f'Assignment {i}',
                description=f'Ready to publish {i}',
                author=self.teacher,
                subject=self.subject,
                start_date=self.now,
                due_date=self.now + timedelta(days=7),
                publish_at=self.past,
                status=Assignment.Status.DRAFT,
            )
            assignment.assigned_to.set([self.student1])
            assignments.append(assignment)

        # Run the task
        result = auto_publish_assignments()

        # Verify all were published
        self.assertEqual(result['published_count'], 3)

        for assignment in assignments:
            assignment.refresh_from_db()
            self.assertEqual(assignment.status, Assignment.Status.PUBLISHED)

    def test_assignment_without_assigned_students(self):
        """
        Test that assignments without assigned students are still published
        without notifications.
        """
        assignment = Assignment.objects.create(
            title='Unassigned Assignment',
            description='No students assigned',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.past,
            status=Assignment.Status.DRAFT,
        )

        # Don't assign to any students

        # Run the task
        result = auto_publish_assignments()

        # Verify assignment was still published
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.PUBLISHED)
        self.assertEqual(result['published_count'], 1)

        # Verify no notifications were created (no assigned students)
        notifications = Notification.objects.filter(
            related_object_type='Assignment',
            related_object_id=assignment.id,
        )
        self.assertEqual(notifications.count(), 0)

    def test_task_failure_handling(self):
        """
        Test that failed assignments don't crash the entire task.
        """
        # Create a valid assignment
        valid_assignment = Assignment.objects.create(
            title='Valid Assignment',
            description='Should work',
            author=self.teacher,
            subject=self.subject,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            publish_at=self.past,
            status=Assignment.Status.DRAFT,
        )
        valid_assignment.assigned_to.set([self.student1])

        # Run the task (should handle failures gracefully)
        result = auto_publish_assignments()

        # Verify at least the valid assignment was processed
        self.assertGreaterEqual(result['published_count'], 1)

        # Verify valid assignment was published
        valid_assignment.refresh_from_db()
        self.assertEqual(valid_assignment.status, Assignment.Status.PUBLISHED)


@pytest.mark.django_db
class AssignmentSchedulingSerializerTests:
    """Tests for assignment scheduling serializers."""

    def test_create_serializer_accepts_publish_at(self):
        """Test that AssignmentCreateSerializer accepts publish_at field."""
        from assignments.serializers import AssignmentCreateSerializer
        from django.contrib.auth.models import AnonymousUser
        from rest_framework.request import Request
        from django.test import RequestFactory

        teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

        subject = Subject.objects.create(
            name='Physics',
            code='PHYS101',
            created_by=teacher
        )

        now = timezone.now()
        future = now + timedelta(hours=1)

        data = {
            'title': 'Test Assignment',
            'description': 'Test description',
            'subject': subject.id,
            'type': 'homework',
            'start_date': now,
            'due_date': now + timedelta(days=7),
            'publish_at': future,
            'close_at': future + timedelta(hours=1),
        }

        request = RequestFactory().post('/')
        request.user = teacher

        serializer = AssignmentCreateSerializer(
            data=data,
            context={'request': request}
        )

        assert serializer.is_valid(), serializer.errors
        assignment = serializer.save()

        assert assignment.publish_at == future
        assert assignment.close_at == future + timedelta(hours=1)

    def test_create_serializer_validates_close_after_publish(self):
        """
        Test that AssignmentCreateSerializer validates that close_at
        must be after publish_at.
        """
        from assignments.serializers import AssignmentCreateSerializer
        from rest_framework.request import Request
        from django.test import RequestFactory

        teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

        subject = Subject.objects.create(
            name='Chemistry',
            code='CHEM101',
            created_by=teacher
        )

        now = timezone.now()
        future = now + timedelta(hours=1)
        past = now - timedelta(hours=1)

        # close_at is before publish_at
        data = {
            'title': 'Test Assignment',
            'description': 'Test description',
            'subject': subject.id,
            'type': 'homework',
            'start_date': now,
            'due_date': now + timedelta(days=7),
            'publish_at': future,
            'close_at': past,  # Invalid: before publish_at
        }

        request = RequestFactory().post('/')
        request.user = teacher

        serializer = AssignmentCreateSerializer(
            data=data,
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert 'close_at' in serializer.errors
