"""
T_ASN_007: Late Submission Handling Tests

Tests for:
- Late submission detection
- Penalty calculation
- Teacher override/exemption
- Deadline extensions
- Late submission reporting
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase

from assignments.models import (
    Assignment, AssignmentSubmission, SubmissionExemption,
    StudentDeadlineExtension
)
from assignments.services.late_policy import LatePolicyService

User = get_user_model()


class LateSubmissionDetectionTests(TestCase):
    """Test late submission detection and calculation."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass',
            role='student'
        )

        # Create assignment that ends now
        self.now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            late_penalty_type='percentage',
            late_penalty_value=Decimal('10'),  # 10% per day
            penalty_frequency='per_day',
            max_penalty=Decimal('50'),
            allow_late_submission=True
        )

    def test_on_time_submission(self):
        """Test that on-time submission is not marked as late."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now - timedelta(hours=1)
        )

        service = LatePolicyService(submission)
        assert service.is_late() is False
        assert service.calculate_days_late() == Decimal('0')

    def test_late_submission_same_day(self):
        """Test late submission same day."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(hours=2)
        )

        service = LatePolicyService(submission)
        assert service.is_late() is True
        # Should be rounded up to 1 day
        assert service.calculate_days_late() == Decimal('1')

    def test_late_submission_multiple_days(self):
        """Test late submission after multiple days."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=3)
        )

        service = LatePolicyService(submission)
        assert service.is_late() is True
        assert service.calculate_days_late() == Decimal('3')

    def test_late_submission_hours_frequency(self):
        """Test late submission with hourly penalty frequency."""
        # Create assignment with hourly penalties
        assignment = Assignment.objects.create(
            title='Hourly Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            late_penalty_type='percentage',
            late_penalty_value=Decimal('5'),
            penalty_frequency='per_hour',
            max_penalty=Decimal('50'),
            allow_late_submission=True
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(hours=3.5)
        )

        service = LatePolicyService(submission)
        assert service.is_late() is True
        # Should be rounded up to 4 hours
        assert service.calculate_days_late() == Decimal('4')


class PenaltyCalculationTests(TestCase):
    """Test penalty calculation logic."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass',
            role='student'
        )

        self.now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            late_penalty_type='percentage',
            late_penalty_value=Decimal('10'),  # 10% per day
            penalty_frequency='per_day',
            max_penalty=Decimal('50'),
            allow_late_submission=True
        )

    def test_percentage_penalty_calculation(self):
        """Test penalty calculation with percentage type."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=2)
        )

        service = LatePolicyService(submission)
        penalty = service.calculate_penalty(original_score=100)

        # 100 * 10% * 2 days = 20 points
        assert penalty == Decimal('20')

    def test_fixed_points_penalty_calculation(self):
        """Test penalty calculation with fixed points type."""
        assignment = Assignment.objects.create(
            title='Fixed Points Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            late_penalty_type='fixed_points',
            late_penalty_value=Decimal('5'),  # 5 points per day
            penalty_frequency='per_day',
            max_penalty=Decimal('50'),
            allow_late_submission=True
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=3)
        )

        service = LatePolicyService(submission)
        penalty = service.calculate_penalty(original_score=100)

        # 5 points * 3 days = 15 points
        assert penalty == Decimal('15')

    def test_penalty_capped_at_max_penalty(self):
        """Test that penalty is capped at max_penalty percentage."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=10)  # Very late
        )

        service = LatePolicyService(submission)
        penalty = service.calculate_penalty(original_score=100)

        # Max penalty is 50%, so penalty should be capped at 50
        assert penalty == Decimal('50')

    def test_penalty_not_exceeding_score(self):
        """Test that final score doesn't go below zero."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=10)
        )

        service = LatePolicyService(submission)
        result = service.apply_penalty(original_score=100)

        # Final score should not be negative
        assert result['final_score'] >= 0


class ExemptionTests(TestCase):
    """Test exemption functionality."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass',
            role='student'
        )

        self.now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            late_penalty_type='percentage',
            late_penalty_value=Decimal('10'),
            penalty_frequency='per_day',
            max_penalty=Decimal('50'),
            allow_late_submission=True
        )

    def test_full_exemption(self):
        """Test full exemption from penalty."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=2)
        )

        service = LatePolicyService(submission)

        # Create exemption
        service.create_exemption(
            exemption_type='full',
            reason='Medical excuse',
            created_by=self.teacher
        )

        # Penalty should be zero with exemption
        penalty = service.calculate_penalty(original_score=100)
        assert penalty == Decimal('0')

    def test_custom_penalty_rate(self):
        """Test custom penalty rate exemption."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=2)
        )

        service = LatePolicyService(submission)

        # Create custom exemption with 5% rate
        service.create_exemption(
            exemption_type='custom_rate',
            reason='Partial forgiveness',
            created_by=self.teacher,
            custom_penalty_rate=Decimal('5')
        )

        # Penalty should be calculated at custom rate
        penalty = service.calculate_penalty(original_score=100)
        # 100 * 5% * 2 days = 10 points
        assert penalty == Decimal('10')

    def test_remove_exemption(self):
        """Test removing exemption."""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=2)
        )

        service = LatePolicyService(submission)

        # Create and remove exemption
        service.create_exemption(
            exemption_type='full',
            reason='Medical excuse',
            created_by=self.teacher
        )
        assert service.is_exempt() is True

        service.remove_exemption()
        assert service.is_exempt() is False

        # Penalty should now apply
        penalty = service.calculate_penalty(original_score=100)
        assert penalty == Decimal('20')  # 10% * 2 days


class StudentDeadlineExtensionTests(TestCase):
    """Test student deadline extension functionality."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass',
            role='student'
        )

        self.now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            allow_late_submission=True
        )

    def test_create_deadline_extension(self):
        """Test creating deadline extension."""
        new_deadline = self.now + timedelta(days=7)

        extension = StudentDeadlineExtension.objects.create(
            assignment=self.assignment,
            student=self.student,
            extended_deadline=new_deadline,
            reason='Medical excuse',
            extended_by=self.teacher
        )

        assert extension.student == self.student
        assert extension.assignment == self.assignment
        assert extension.extended_deadline == new_deadline

    def test_extension_uniqueness(self):
        """Test that only one extension per student per assignment."""
        new_deadline1 = self.now + timedelta(days=7)
        new_deadline2 = self.now + timedelta(days=14)

        StudentDeadlineExtension.objects.create(
            assignment=self.assignment,
            student=self.student,
            extended_deadline=new_deadline1,
            reason='First extension',
            extended_by=self.teacher
        )

        # Second extension should replace first
        extension2 = StudentDeadlineExtension.objects.create(
            assignment=self.assignment,
            student=self.student,
            extended_deadline=new_deadline2,
            reason='Updated extension',
            extended_by=self.teacher
        )

        # Should only have one extension
        count = StudentDeadlineExtension.objects.filter(
            assignment=self.assignment,
            student=self.student
        ).count()
        assert count == 1
        assert extension2.extended_deadline == new_deadline2


class LateSubmissionAcceptanceTests(TestCase):
    """Test acceptance of late submissions."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass',
            role='student'
        )

        self.now = timezone.now()

    def test_accept_late_submission_when_allowed(self):
        """Test that late submission is accepted when allowed."""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            allow_late_submission=True
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=2)
        )

        service = LatePolicyService(submission)
        can_accept, error = service.can_accept_late_submission()

        assert can_accept is True
        assert error is None

    def test_reject_late_submission_when_not_allowed(self):
        """Test that late submission is rejected when not allowed."""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            allow_late_submission=False
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=2)
        )

        service = LatePolicyService(submission)
        can_accept, error = service.can_accept_late_submission()

        assert can_accept is False
        assert error is not None

    def test_reject_late_submission_after_late_deadline(self):
        """Test that late submission is rejected after late deadline."""
        late_deadline = self.now + timedelta(days=3)
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            start_date=self.now - timedelta(days=7),
            due_date=self.now,
            max_score=100,
            allow_late_submission=True,
            late_submission_deadline=late_deadline
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Test answer',
            submitted_at=self.now + timedelta(days=5)
        )

        service = LatePolicyService(submission)
        can_accept, error = service.can_accept_late_submission()

        assert can_accept is False
        assert error is not None
