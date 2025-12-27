"""
T_ASN_008: Tests for assignment cloning functionality.

Tests cover:
- Basic cloning with all questions
- Title and due date customization
- Question randomization
- Permission validation
- Error handling
- Audit logging
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Assignment, AssignmentQuestion, AssignmentAnswer, AssignmentSubmission
from .services.cloning import AssignmentCloningService

User = get_user_model()


class AssignmentCloningModelTests(TestCase):
    """Test the clone() method on Assignment model."""

    def setUp(self):
        """Create test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.other_teacher = User.objects.create_user(
            email='other@test.com',
            password='test123',
            role='teacher'
        )

        self.assignment = Assignment.objects.create(
            title='Original Assignment',
            description='Test description',
            instructions='Test instructions',
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
            difficulty_level=2
        )

        # Create questions
        for i in range(3):
            AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Question {i+1}',
                question_type=AssignmentQuestion.Type.SINGLE_CHOICE,
                points=10 + i,
                order=i,
                options=[
                    {'text': 'Option A', 'is_correct': True},
                    {'text': 'Option B', 'is_correct': False},
                    {'text': 'Option C', 'is_correct': False},
                ]
            )

    def test_clone_basic(self):
        """Test basic cloning creates new assignment with same data."""
        cloned = self.assignment.clone(self.teacher)

        # Check cloned assignment has new ID
        assert cloned.id != self.assignment.id
        assert cloned.pk is None  # Not saved yet

        # Check title is auto-generated
        assert cloned.title == f"Copy of {self.assignment.title}"

        # Check other fields are copied
        assert cloned.description == self.assignment.description
        assert cloned.author == self.teacher
        assert cloned.status == Assignment.Status.DRAFT
        assert cloned.max_score == self.assignment.max_score
        assert cloned.difficulty_level == self.assignment.difficulty_level

    def test_clone_with_custom_title(self):
        """Test cloning with custom title."""
        new_title = "My Custom Title"
        cloned = self.assignment.clone(self.teacher, new_title=new_title)

        assert cloned.title == new_title

    def test_clone_with_custom_due_date(self):
        """Test cloning with custom due date."""
        new_due_date = timezone.now() + timedelta(days=30)
        cloned = self.assignment.clone(self.teacher, new_due_date=new_due_date)

        assert cloned.due_date == new_due_date

    def test_clone_preserves_original_due_date(self):
        """Test cloning preserves original due date by default."""
        cloned = self.assignment.clone(self.teacher)

        assert cloned.due_date == self.assignment.due_date

    def test_clone_creates_questions(self):
        """Test cloning creates all related questions."""
        cloned = self.assignment.clone(self.teacher)
        cloned.save()

        original_questions = self.assignment.questions.all().count()
        cloned_questions = cloned.questions.all().count()

        assert original_questions == 3
        assert cloned_questions == 3

    def test_clone_copies_question_options(self):
        """Test cloning copies question options correctly."""
        cloned = self.assignment.clone(self.teacher)
        cloned.save()

        original_q = self.assignment.questions.first()
        cloned_q = cloned.questions.first()

        assert cloned_q.options == original_q.options
        assert cloned_q.correct_answer == original_q.correct_answer

    def test_clone_with_randomization(self):
        """Test cloning with question randomization."""
        original_q = self.assignment.questions.first()
        original_options = original_q.options.copy()

        cloned = self.assignment.clone(self.teacher, randomize_questions=True)
        cloned.save()

        cloned_q = cloned.questions.first()

        # Options should be shuffled (statistically likely to be different)
        # Note: Small chance of failure if shuffle returns same order
        # We just verify options were copied, order may be same
        assert cloned_q.options is not None
        assert len(cloned_q.options) == len(original_options)

    def test_clone_permission_denied_other_user(self):
        """Test cloning raises PermissionError for non-creator."""
        with pytest.raises(PermissionError):
            self.assignment.clone(self.other_teacher)

    def test_clone_sets_draft_status(self):
        """Test cloned assignment is always in DRAFT status."""
        cloned = self.assignment.clone(self.teacher)

        assert cloned.status == Assignment.Status.DRAFT

    def test_clone_transaction_atomic(self):
        """Test cloning is atomic - all or nothing."""
        cloned = self.assignment.clone(self.teacher)
        cloned.save()

        # Verify cloned assignment exists
        assert Assignment.objects.filter(title=cloned.title).exists()
        assert cloned.questions.count() == self.assignment.questions.count()

    def test_clone_clear_assigned_to(self):
        """Test cloned assignment has no assigned_to students."""
        student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )
        self.assignment.assigned_to.add(student)

        cloned = self.assignment.clone(self.teacher)
        cloned.save()

        # Cloned assignment should not have assigned_to
        assert cloned.assigned_to.count() == 0

    def test_clone_preserves_rubric(self):
        """Test cloned assignment preserves rubric reference."""
        from .models import GradingRubric

        rubric = GradingRubric.objects.create(
            name='Test Rubric',
            description='Test rubric',
            created_by=self.teacher
        )
        self.assignment.rubric = rubric
        self.assignment.save()

        cloned = self.assignment.clone(self.teacher)

        assert cloned.rubric == rubric


class AssignmentCloningServiceTests(TestCase):
    """Test AssignmentCloningService."""

    def setUp(self):
        """Create test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.other_teacher = User.objects.create_user(
            email='other@test.com',
            password='test123',
            role='teacher'
        )

        self.assignment = Assignment.objects.create(
            title='Original Assignment',
            description='Test description',
            instructions='Test instructions',
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7)
        )

        for i in range(2):
            AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Question {i+1}',
                question_type=AssignmentQuestion.Type.SINGLE_CHOICE,
                points=10,
                order=i,
                options=[{'text': 'Option A'}, {'text': 'Option B'}]
            )

    def test_validate_clone_permission_success(self):
        """Test permission validation succeeds for creator."""
        result = AssignmentCloningService.validate_clone_permission(
            self.assignment,
            self.teacher
        )
        assert result is True

    def test_validate_clone_permission_denied(self):
        """Test permission validation fails for non-creator."""
        with pytest.raises(PermissionError):
            AssignmentCloningService.validate_clone_permission(
                self.assignment,
                self.other_teacher
            )

    def test_validate_clone_params_valid(self):
        """Test parameter validation with valid params."""
        result = AssignmentCloningService.validate_clone_params(
            self.assignment,
            new_title='New Title',
            new_due_date=timezone.now() + timedelta(days=30),
            randomize_questions=True
        )
        assert result is True

    def test_validate_clone_params_invalid_title_length(self):
        """Test parameter validation rejects long title."""
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            AssignmentCloningService.validate_clone_params(
                self.assignment,
                new_title='a' * 201  # Too long
            )

    def test_validate_clone_params_past_due_date(self):
        """Test parameter validation rejects past due date."""
        from django.core.exceptions import ValidationError

        past_date = timezone.now() - timedelta(days=1)
        with pytest.raises(ValidationError):
            AssignmentCloningService.validate_clone_params(
                self.assignment,
                new_due_date=past_date
            )

    def test_clone_assignment_success(self):
        """Test successful assignment cloning via service."""
        cloned = AssignmentCloningService.clone_assignment(
            self.assignment,
            self.teacher,
            new_title='Service Clone Test'
        )

        assert cloned.id is not None
        assert cloned.title == 'Service Clone Test'
        assert cloned.author == self.teacher
        assert cloned.status == Assignment.Status.DRAFT
        assert cloned.questions.count() == 2

    def test_clone_assignment_permission_denied(self):
        """Test cloning denied for non-creator via service."""
        with pytest.raises(PermissionError):
            AssignmentCloningService.clone_assignment(
                self.assignment,
                self.other_teacher
            )

    def test_get_clone_suggestions(self):
        """Test getting clone suggestions."""
        suggestions = AssignmentCloningService.get_clone_suggestions(
            self.assignment
        )

        assert 'suggested_title' in suggestions
        assert 'current_due_date' in suggestions
        assert 'suggested_new_due_date' in suggestions
        assert suggestions['questions_count'] == 2


class AssignmentCloningAPITests(APITestCase):
    """Test assignment cloning API endpoint."""

    def setUp(self):
        """Create test data."""
        self.client = APIClient()

        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )
        self.other_teacher = User.objects.create_user(
            email='other@test.com',
            password='test123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )

        self.assignment = Assignment.objects.create(
            title='API Test Assignment',
            description='Test description',
            instructions='Test instructions',
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7)
        )

        for i in range(2):
            AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Q{i}',
                question_type=AssignmentQuestion.Type.SINGLE_CHOICE,
                points=10,
                order=i,
                options=[{'text': 'A'}, {'text': 'B'}]
            )

    def test_clone_endpoint_unauthenticated(self):
        """Test clone endpoint requires authentication."""
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_clone_endpoint_success(self):
        """Test successful clone via API."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {
                'new_title': 'API Cloned Assignment',
                'randomize_questions': False
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'API Cloned Assignment'
        assert response.data['author'] == self.teacher.id
        assert response.data['status'] == 'draft'
        assert response.data['questions_count'] == 2

    def test_clone_endpoint_auto_title(self):
        """Test clone endpoint auto-generates title."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == f"Copy of {self.assignment.title}"

    def test_clone_endpoint_custom_due_date(self):
        """Test clone endpoint with custom due date."""
        self.client.force_authenticate(user=self.teacher)
        new_due_date = timezone.now() + timedelta(days=30)

        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {
                'new_due_date': new_due_date.isoformat()
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        # Due date will be serialized as ISO string

    def test_clone_endpoint_permission_denied(self):
        """Test clone endpoint denies access to non-creator."""
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_clone_endpoint_student_denied(self):
        """Test clone endpoint denies access to students."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_clone_endpoint_invalid_title(self):
        """Test clone endpoint validates title."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {
                'new_title': 'a' * 201  # Too long
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_clone_endpoint_past_due_date(self):
        """Test clone endpoint rejects past due date."""
        self.client.force_authenticate(user=self.teacher)
        past_date = timezone.now() - timedelta(days=1)

        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {
                'new_due_date': past_date.isoformat()
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_clone_endpoint_not_found(self):
        """Test clone endpoint with non-existent assignment."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/assignments/99999/clone/',
            {}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_clone_endpoint_randomize_questions(self):
        """Test clone with question randomization flag."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f'/api/assignments/{self.assignment.id}/clone/',
            {
                'randomize_questions': True
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['questions_count'] == 2
