"""
T_ASSIGN_006: Tests for assignment scheduling.

Tests cover:
- Model field validation
- State transitions
- Late submission policy
- Student assignment
"""
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase

from assignments.models import Assignment

User = get_user_model()


class AssignmentSchedulingTestCase(TestCase):
    """Tests for assignment scheduling feature."""

    def setUp(self):
        """Set up test data."""
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

        self.now = timezone.now()
        self.future = self.now + timedelta(hours=1)

    def test_assignment_creation_with_dates(self):
        """Test basic assignment creation with start and due dates."""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            status=Assignment.Status.DRAFT,
        )

        self.assertEqual(assignment.title, 'Test Assignment')
        self.assertEqual(assignment.status, Assignment.Status.DRAFT)
        self.assertIsNotNone(assignment.start_date)
        self.assertIsNotNone(assignment.due_date)

    def test_assignment_status_transitions(self):
        """Test assignment status can transition between states."""
        assignment = Assignment.objects.create(
            title='Status Transition Test',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            status=Assignment.Status.DRAFT,
        )

        self.assertEqual(assignment.status, Assignment.Status.DRAFT)
        assignment.status = Assignment.Status.PUBLISHED
        assignment.save()
        self.assertEqual(assignment.status, Assignment.Status.PUBLISHED)

    def test_assignment_with_late_submission_settings(self):
        """Test assignment with late submission policy."""
        assignment = Assignment.objects.create(
            title='Late Submission Test',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            allow_late_submission=True,
            late_penalty_type='percentage',
            late_penalty_value=10,
            status=Assignment.Status.PUBLISHED,
        )

        self.assertTrue(assignment.allow_late_submission)
        self.assertEqual(assignment.late_penalty_type, 'percentage')

    def test_assignment_can_be_assigned_to_students(self):
        """Test assigning assignment to specific students."""
        assignment = Assignment.objects.create(
            title='Assignment for Students',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            start_date=self.now,
            due_date=self.now + timedelta(days=7),
            status=Assignment.Status.PUBLISHED,
        )

        assignment.assigned_to.add(self.student1, self.student2)
        self.assertEqual(assignment.assigned_to.count(), 2)
        self.assertIn(self.student1, assignment.assigned_to.all())
