"""
T_ASN_003: Tests for Assignment Attempt Tracking

Tests the creation, validation, and management of assignment attempts
with support for retakes and attempt limiting.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import Assignment, AssignmentSubmission, AssignmentAttempt
from .services.attempts import (
    AttemptValidationService,
    AttemptCreationService,
    AttemptStatisticsService
)

User = get_user_model()


@pytest.mark.django_db
class TestAttemptValidationService:
    """Test attempt validation logic"""

    def setup_method(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

    def test_can_create_first_attempt(self):
        """Test that a student can create their first attempt"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        can_create, message = AttemptValidationService.can_create_attempt(
            assignment,
            self.student.id
        )

        assert can_create is True
        assert 'Ready' in message

    def test_cannot_exceed_attempt_limit(self):
        """Test that students cannot exceed attempt limit"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            attempts_limit=2,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        # Create two attempts
        for i in range(2):
            AssignmentAttempt.objects.create(
                submission=submission,
                assignment=assignment,
                student=self.student,
                attempt_number=i + 1,
                content=f'Attempt {i + 1}'
            )

        # Try to create a third attempt
        can_create, message = AttemptValidationService.can_create_attempt(
            assignment,
            self.student.id
        )

        assert can_create is False
        assert 'Maximum attempts' in message

    def test_cannot_submit_after_deadline(self):
        """Test that submissions after deadline are rejected"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            attempts_limit=3,
            due_date=timezone.now() - timedelta(days=1),
            allow_late_submission=False
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        can_create, message = AttemptValidationService.can_create_attempt(
            assignment,
            self.student.id
        )

        assert can_create is False
        assert 'closed' in message.lower()

    def test_allow_late_submission(self):
        """Test that late submissions are allowed when enabled"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            attempts_limit=3,
            due_date=timezone.now() - timedelta(days=1),
            allow_late_submission=True
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        can_create, message = AttemptValidationService.can_create_attempt(
            assignment,
            self.student.id
        )

        assert can_create is True

    def test_get_attempt_number(self):
        """Test correct attempt numbering"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            attempts_limit=5,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        # First attempt should be numbered 1
        assert AttemptValidationService.get_current_attempt_number(submission) == 1

        # Create first attempt
        AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student,
            attempt_number=1,
            content='Attempt 1'
        )

        # Next should be 2
        assert AttemptValidationService.get_current_attempt_number(submission) == 2


@pytest.mark.django_db
class TestAttemptCreationService:
    """Test attempt creation and grading"""

    def setup_method(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

    def test_create_attempt(self):
        """Test creating an assignment attempt"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        attempt = AttemptCreationService.create_attempt(
            submission=submission,
            content='My answer to the assignment'
        )

        assert attempt.id is not None
        assert attempt.attempt_number == 1
        assert attempt.content == 'My answer to the assignment'
        assert attempt.status == AssignmentAttempt.Status.SUBMITTED
        assert attempt.max_score == 100

    def test_grade_attempt(self):
        """Test grading an assignment attempt"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        attempt = AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student,
            attempt_number=1,
            content='My answer',
            max_score=100
        )

        # Grade the attempt
        graded_attempt = AttemptCreationService.grade_attempt(
            attempt=attempt,
            score=85,
            feedback='Good work!',
            status=AssignmentAttempt.Status.GRADED
        )

        assert graded_attempt.score == 85
        assert graded_attempt.feedback == 'Good work!'
        assert graded_attempt.status == AssignmentAttempt.Status.GRADED
        assert graded_attempt.graded_at is not None

    def test_get_best_attempt(self):
        """Test retrieving the best-scoring attempt"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        # Create and grade multiple attempts
        attempt1 = AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student,
            attempt_number=1,
            content='First attempt',
            score=75,
            status=AssignmentAttempt.Status.GRADED,
            max_score=100
        )

        attempt2 = AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student,
            attempt_number=2,
            content='Second attempt',
            score=90,
            status=AssignmentAttempt.Status.GRADED,
            max_score=100
        )

        best = AttemptCreationService.get_best_attempt(submission)
        assert best.id == attempt2.id
        assert best.score == 90

    def test_get_latest_attempt(self):
        """Test retrieving the most recent attempt"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Initial submission'
        )

        # Create multiple attempts
        for i in range(1, 4):
            AssignmentAttempt.objects.create(
                submission=submission,
                assignment=assignment,
                student=self.student,
                attempt_number=i,
                content=f'Attempt {i}',
                max_score=100
            )

        latest = AttemptCreationService.get_latest_attempt(submission)
        assert latest.attempt_number == 3


@pytest.mark.django_db
class TestAttemptStatistics:
    """Test attempt statistics gathering"""

    def setup_method(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student1 = User.objects.create_user(
            email='student1@test.com',
            password='testpass123',
            role='student'
        )
        self.student2 = User.objects.create_user(
            email='student2@test.com',
            password='testpass123',
            role='student'
        )

    def test_assignment_stats(self):
        """Test getting assignment-wide statistics"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student1, self.student2)

        # Create submissions
        submission1 = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            content='Answer 1'
        )
        submission2 = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student2,
            content='Answer 2'
        )

        # Student 1: 2 attempts, graded first
        AssignmentAttempt.objects.create(
            submission=submission1,
            assignment=assignment,
            student=self.student1,
            attempt_number=1,
            content='Attempt 1',
            score=75,
            status=AssignmentAttempt.Status.GRADED,
            max_score=100
        )
        AssignmentAttempt.objects.create(
            submission=submission1,
            assignment=assignment,
            student=self.student1,
            attempt_number=2,
            content='Attempt 2',
            max_score=100
        )

        # Student 2: 1 attempt, graded
        AssignmentAttempt.objects.create(
            submission=submission2,
            assignment=assignment,
            student=self.student2,
            attempt_number=1,
            content='Attempt 1',
            score=90,
            status=AssignmentAttempt.Status.GRADED,
            max_score=100
        )

        stats = AttemptStatisticsService.get_attempt_stats(assignment)

        assert stats['total_students'] == 2
        assert stats['students_with_attempts'] == 2
        assert stats['total_attempts'] == 3
        assert stats['graded_attempts'] == 2
        assert stats['average_score'] == 82.5  # (75 + 90) / 2
        assert stats['average_attempts_per_student'] == 1.5  # (2 + 1) / 2

    def test_student_stats(self):
        """Test getting student-specific statistics"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student1)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            content='Answer'
        )

        # Create attempts
        AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student1,
            attempt_number=1,
            content='Attempt 1',
            score=75,
            status=AssignmentAttempt.Status.GRADED,
            max_score=100
        )
        AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student1,
            attempt_number=2,
            content='Attempt 2',
            max_score=100
        )

        stats = AttemptStatisticsService.get_student_stats(submission)

        assert stats['total_attempts'] == 2
        assert stats['graded_attempts'] == 1
        assert stats['best_score'] == 75
        assert stats['completion_status'] == 'in_progress'
        assert stats['latest_attempt_number'] == 2

    def test_empty_stats(self):
        """Test statistics for submission with no attempts"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student1)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            content='Answer'
        )

        stats = AttemptStatisticsService.get_student_stats(submission)

        assert stats['total_attempts'] == 0
        assert stats['graded_attempts'] == 0
        assert stats['best_score'] is None
        assert stats['completion_status'] == 'not_started'


@pytest.mark.django_db
class TestAssignmentAttemptModel:
    """Test AssignmentAttempt model functionality"""

    def setup_method(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

    def test_attempt_percentage(self):
        """Test percentage score calculation"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Answer'
        )

        attempt = AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student,
            attempt_number=1,
            content='My answer',
            score=85,
            max_score=100
        )

        assert attempt.percentage == 85.0

    def test_is_graded_property(self):
        """Test is_graded property"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Do this',
            author=self.teacher,
            start_date=timezone.now(),
            start_date=timezone.now(),
            max_score=100,
            attempts_limit=3,
            due_date=timezone.now() + timedelta(days=1)
        )
        assignment.assigned_to.add(self.student)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Answer'
        )

        # Not graded
        attempt = AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=self.student,
            attempt_number=1,
            content='My answer',
            status=AssignmentAttempt.Status.SUBMITTED,
            max_score=100
        )
        assert attempt.is_graded is False

        # Graded
        attempt.status = AssignmentAttempt.Status.GRADED
        attempt.score = 85
        assert attempt.is_graded is True

        # Returned for revision (still considered graded)
        attempt.status = AssignmentAttempt.Status.RETURNED
        assert attempt.is_graded is True
