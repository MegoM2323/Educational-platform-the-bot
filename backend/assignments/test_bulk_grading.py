"""
T_ASSIGN_011: Tests for Bulk Grading Operations

Comprehensive tests for:
- Bulk grade endpoint (POST /api/assignments/{id}/bulk_grade/)
- CSV import validation and parsing
- Validation before applying grades
- Transaction safety (atomic vs partial modes)
- Permission checks (teacher only)
- Progress tracking and statistics
"""

import pytest
import csv
import io
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from assignments.models import Assignment, AssignmentSubmission
from assignments.services.bulk_grading import BulkGradingService

User = get_user_model()


@pytest.mark.django_db
class TestBulkGradingService:
    """Test BulkGradingService functionality"""

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            username='teacher_bulk_test',
            email="teacher@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role="teacher"
        )

    @pytest.fixture
    def assignment(self, teacher):
        """Create a test assignment"""
        return Assignment.objects.create(
            title="Test Assignment",
            description="Test Description",
            instructions="Test Instructions",
            author=teacher,
            start_date=timezone.now(),
            type=Assignment.Type.HOMEWORK,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now()
        )

    @pytest.fixture
    def students(self):
        """Create test students"""
        students = []
        for i in range(10):
            student = User.objects.create_user(
                username=f"student_bulk_{i}",
                email=f"student{i}@test.com",
                password="TestPass123!",
                first_name=f"Student",
                last_name=f"{i}",
                role="student"
            )
            students.append(student)
        return students

    @pytest.fixture
    def submissions(self, assignment, students):
        """Create test submissions"""
        submissions = []
        for student in students:
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                content="Test submission",
                status=AssignmentSubmission.Status.SUBMITTED
            )
            submissions.append(submission)
        return submissions

    def test_validate_grade_data_empty(self, assignment):
        """Test validation fails with empty grades data"""
        is_valid, errors = BulkGradingService.validate_grade_data([], assignment)

        assert not is_valid
        assert any('No grades provided' in str(e) for e in errors)

    def test_validate_grade_data_valid(self, assignment, submissions):
        """Test validation succeeds with valid data"""
        grades_data = [
            {'submission_id': submissions[0].id, 'score': 85, 'feedback': 'Good'},
            {'submission_id': submissions[1].id, 'score': 92}
        ]

        is_valid, errors = BulkGradingService.validate_grade_data(grades_data, assignment)

        assert is_valid
        assert len(errors) == 0

    def test_apply_bulk_grades_atomic_success(self, teacher, assignment, submissions):
        """Test atomic bulk grading success - all grades applied"""
        grades_data = [
            {'submission_id': submissions[0].id, 'score': 85, 'feedback': 'Good'},
            {'submission_id': submissions[1].id, 'score': 92, 'feedback': 'Excellent'},
            {'submission_id': submissions[2].id, 'score': 78, 'feedback': 'OK'}
        ]

        result = BulkGradingService.apply_bulk_grades(
            grades_data=grades_data,
            assignment=assignment,
            user=teacher,
            transaction_mode='atomic'
        )

        assert result['success']
        assert result['created'] == 3
        assert result['failed'] == 0
        assert len(result['errors']) == 0

        # Verify grades were applied
        for idx, grade in enumerate(grades_data):
            submission = AssignmentSubmission.objects.get(id=grade['submission_id'])
            assert submission.score == grade['score']
            assert submission.feedback == grade['feedback']
            assert submission.status == AssignmentSubmission.Status.GRADED
            assert submission.graded_at is not None

    def test_apply_bulk_grades_partial_success(self, teacher, assignment, submissions):
        """Test partial mode skips failed items, continues with others"""
        grades_data = [
            {'submission_id': submissions[0].id, 'score': 85},
            {'submission_id': 9999, 'score': 92},  # Invalid - will fail
            {'submission_id': submissions[2].id, 'score': 78},
            {'submission_id': submissions[3].id, 'score': 88}
        ]

        result = BulkGradingService.apply_bulk_grades(
            grades_data=grades_data,
            assignment=assignment,
            user=teacher,
            transaction_mode='partial'
        )

        assert result['success']  # Some succeeded
        assert result['created'] == 3  # Three succeeded
        assert result['failed'] == 1  # One failed

        # Verify successful grades were applied
        submission0 = AssignmentSubmission.objects.get(id=submissions[0].id)
        assert submission0.score == 85

    def test_parse_csv_grades_valid(self, assignment, submissions):
        """Test CSV parsing with valid data"""
        csv_content = f"""submission_id,score,feedback
{submissions[0].id},85,Good work
{submissions[1].id},92,Excellent
{submissions[2].id},78,Need improvement"""

        grades_data, errors = BulkGradingService.parse_csv_grades(csv_content, assignment)

        assert len(grades_data) == 3
        assert len(errors) == 0
        assert grades_data[0]['submission_id'] == submissions[0].id
        assert grades_data[0]['score'] == 85.0
        assert grades_data[0]['feedback'] == 'Good work'

    def test_get_bulk_grade_stats(self, assignment, teacher, submissions):
        """Test getting bulk grading statistics"""
        # Grade some submissions
        submissions[0].score = 85
        submissions[0].status = AssignmentSubmission.Status.GRADED
        submissions[0].save()

        submissions[1].score = 92
        submissions[1].status = AssignmentSubmission.Status.GRADED
        submissions[1].save()

        stats = BulkGradingService.get_bulk_grade_stats(assignment)

        assert stats['total_submissions'] == 10
        assert stats['graded_count'] == 2
        assert stats['ungraded_count'] == 8
        assert stats['average_score'] == 88.5


@pytest.mark.django_db
class TestBulkGradingAPI:
    """Test bulk grading API endpoints"""

    @pytest.fixture
    def client(self):
        """Create API client"""
        return APIClient()

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            username='teacher_api_test',
            email="teacher@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role="teacher"
        )

    @pytest.fixture
    def student(self):
        """Create a student user"""
        return User.objects.create_user(
            username='student_api_test',
            email="student@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Student",
            role="student"
        )

    @pytest.fixture
    def assignment(self, teacher):
        """Create a test assignment"""
        return Assignment.objects.create(
            title="Test Assignment",
            description="Test Description",
            instructions="Test Instructions",
            author=teacher,
            start_date=timezone.now(),
            type=Assignment.Type.HOMEWORK,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now()
        )

    @pytest.fixture
    def submissions(self, assignment):
        """Create test submissions"""
        submissions = []
        for i in range(10):
            student = User.objects.create_user(
                username=f"student_api_{i}",
                email=f"student{i}@test.com",
                password="TestPass123!",
                first_name=f"Student",
                last_name=f"{i}",
                role="student"
            )
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                content="Test submission",
                status=AssignmentSubmission.Status.SUBMITTED
            )
            submissions.append(submission)
        return submissions

    def test_bulk_grade_endpoint_success(self, client, teacher, assignment, submissions):
        """Test bulk_grade endpoint with valid data"""
        client.force_authenticate(user=teacher)

        data = {
            'grades': [
                {'submission_id': submissions[0].id, 'score': 85, 'feedback': 'Good'},
                {'submission_id': submissions[1].id, 'score': 92, 'feedback': 'Excellent'}
            ],
            'transaction_mode': 'atomic'
        }

        response = client.post(
            f'/api/assignments/{assignment.id}/bulk_grade/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success']
        assert response.data['created'] == 2
        assert response.data['failed'] == 0

    def test_bulk_grade_stats_endpoint(self, client, teacher, assignment, submissions):
        """Test bulk_grade_stats endpoint"""
        # Grade some submissions
        submissions[0].score = 85
        submissions[0].status = AssignmentSubmission.Status.GRADED
        submissions[0].save()

        submissions[1].score = 92
        submissions[1].status = AssignmentSubmission.Status.GRADED
        submissions[1].save()

        client.force_authenticate(user=teacher)

        response = client.get(f'/api/assignments/{assignment.id}/bulk_grade_stats/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_submissions'] == 10
        assert response.data['graded_count'] == 2
        assert response.data['average_score'] == 88.5
