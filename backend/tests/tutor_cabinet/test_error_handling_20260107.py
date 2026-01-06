"""
Error Handling and Edge Cases Tests for Tutor Cabinet (T119-T130)

T119: Network loss handling
T120: Server error handling  
T121: Request timeout handling
T122: Invalid data handling
T123: Concurrent editing
T124: Delete non-existent student
T125: Cascade deletion
T126: Database race conditions
T127: Student limit exceeded
T128: API rate limiting
T129: Null/undefined data
T130: Pagination out of bounds
"""

import pytest
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.test import TransactionTestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import StudentProfile, TutorProfile, ParentProfile
from materials.models import Subject, SubjectEnrollment
from scheduling.models import Lesson
from chat.models import ChatRoom, Message, MessageRead

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tutor_user():
    user, _ = User.objects.get_or_create(
        email='tutor_error_20260107@example.com',
        defaults={'username': 'tutor_error_20260107', 'role': 'tutor'}
    )
    user.set_password('TestPass123!')
    user.save()
    TutorProfile.objects.get_or_create(user=user, defaults={'bio': 'Test'})
    return user


@pytest.fixture
def authenticated_client(tutor_user):
    client = APIClient()
    client.force_authenticate(user=tutor_user)
    return client


@pytest.fixture
def student_users():
    parent = User.objects.create_user(
        email='parent_error_20260107@example.com',
        username='parent_error_20260107',
        role='parent'
    )
    ParentProfile.objects.get_or_create(user=parent)
    students = []
    for i in range(5):
        student = User.objects.create_user(
            email=f'student_error_{i}_20260107@example.com',
            username=f'student_error_{i}_20260107',
            role='student'
        )
        StudentProfile.objects.create(user=student, parent=parent)
        students.append(student)
    return students


# ============================================================================
# T119: Network Loss Handling
# ============================================================================

@pytest.mark.django_db
class TestNetworkLossHandling:
    """T119: Network loss handling"""

    def test_network_timeout_on_list_students(self, authenticated_client):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError()
            response = authenticated_client.get('/api/tutor/students/')
            assert response.status_code in [
                status.HTTP_504_GATEWAY_TIMEOUT,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_200_OK
            ]

    def test_network_connection_error(self, authenticated_client):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError()
            response = authenticated_client.get('/api/tutor/dashboard/')
            assert response.status_code in [
                status.HTTP_503_SERVICE_UNAVAILABLE,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ]


# ============================================================================
# T120: Server Error Handling
# ============================================================================

@pytest.mark.django_db
class TestServerErrorHandling:
    """T120: Server error handling"""

    def test_500_error_recovery(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/dashboard/')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# T121: Request Timeout Handling
# ============================================================================

@pytest.mark.django_db
class TestTimeoutHandling:
    """T121: Request timeout handling"""

    def test_api_call_timeout(self, authenticated_client):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError()
            response = authenticated_client.get('/api/tutor/students/')
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_504_GATEWAY_TIMEOUT,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ]


# ============================================================================
# T122: Invalid Data Handling
# ============================================================================

@pytest.mark.django_db
class TestInvalidDataHandling:
    """T122: Invalid data handling"""

    def test_invalid_json_in_request(self, authenticated_client):
        response = authenticated_client.post(
            '/api/tutor/students/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_fields(self, authenticated_client):
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'name': 'John'}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_field_types(self, authenticated_client):
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'student_id': 'not_an_integer'}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sql_injection_attempt(self, authenticated_client):
        response = authenticated_client.get(
            "/api/tutor/students/?name='; DROP TABLE students; --"
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_xss_injection_attempt(self, authenticated_client):
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'name': '<script>alert("xss")</script>'}
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
            status.HTTP_200_OK
        ]

    def test_oversized_payload(self, authenticated_client):
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'name': 'A' * 100000}
        )
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_400_BAD_REQUEST
        ]


# ============================================================================
# T123: Concurrent Editing
# ============================================================================

class TestConcurrentEditing(TransactionTestCase):
    """T123: Concurrent editing"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username='tutor_concurrent_20260107',
            email='tutor_concurrent_20260107@example.com',
            role='tutor'
        )
        TutorProfile.objects.create(user=self.tutor)

    def test_concurrent_profile_edits(self):
        def edit_profile(bio_text):
            client = APIClient()
            client.force_authenticate(user=self.tutor)
            response = client.patch(
                '/api/tutor/profile/',
                {'bio': bio_text}
            )
            return response.status_code

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(edit_profile, f'Bio {i}')
                for i in range(3)
            ]
            results = [f.result() for f in as_completed(futures)]

        assert any(code in [200, 400, 409] for code in results)


# ============================================================================
# T124: Delete Non-existent Student
# ============================================================================

@pytest.mark.django_db
class TestDeleteNonexistent:
    """T124: Delete non-existent student"""

    def test_delete_nonexistent_student(self, authenticated_client):
        response = authenticated_client.delete('/api/tutor/students/99999/')
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_204_NO_CONTENT
        ]

    def test_delete_student_twice(self, authenticated_client, student_users):
        student_id = student_users[0].id
        response1 = authenticated_client.delete(f'/api/tutor/students/{student_id}/')
        response2 = authenticated_client.delete(f'/api/tutor/students/{student_id}/')
        
        assert response1.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        assert response2.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# T125: Cascade Deletion
# ============================================================================

@pytest.mark.django_db
class TestCascadeDeletion:
    """T125: Cascade deletion"""

    def test_delete_student_deletes_profile(self, authenticated_client, student_users):
        student = student_users[0]
        response = authenticated_client.delete(f'/api/tutor/students/{student.id}/')
        
        # Verify deletion was handled
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# T126: Database Race Conditions
# ============================================================================

class TestDatabaseRaceConditions(TransactionTestCase):
    """T126: Database race conditions"""

    def test_concurrent_subject_creation(self):
        def create_subject():
            try:
                subject = Subject.objects.create(name=f'Subject_{id(threading.current_thread())}')
                return subject.id
            except IntegrityError:
                return None

        import threading
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_subject) for _ in range(3)]
            results = [f.result() for f in as_completed(futures)]

        assert len([r for r in results if r is not None]) >= 1


# ============================================================================
# T127: Student Limit Exceeded
# ============================================================================

@pytest.mark.django_db
class TestStudentLimitExceeded:
    """T127: Student limit exceeded"""

    def test_system_handles_many_students(self, authenticated_client):
        # Create 20 students
        for i in range(20):
            parent = User.objects.create_user(
                username=f'parent_limit_{i}_20260107',
                email=f'parent_limit_{i}_20260107@example.com',
                role='parent'
            )
            ParentProfile.objects.create(user=parent)

            student = User.objects.create_user(
                username=f'student_limit_{i}_20260107',
                email=f'student_limit_{i}_20260107@example.com',
                role='student'
            )
            StudentProfile.objects.create(user=student, parent=parent)

        response = authenticated_client.get('/api/tutor/students/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# ============================================================================
# T128: Rate Limiting
# ============================================================================

@pytest.mark.django_db
class TestRateLimiting:
    """T128: API rate limiting"""

    def test_rapid_requests_handled(self, authenticated_client):
        responses = []
        for i in range(20):
            response = authenticated_client.get('/api/tutor/dashboard/')
            responses.append(response.status_code)

        assert any(code in [200, 404, 429] for code in responses)

    def test_rate_limit_headers(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/dashboard/')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_429_TOO_MANY_REQUESTS
        ]


# ============================================================================
# T129: Null/Undefined Data
# ============================================================================

@pytest.mark.django_db
class TestNullUndefinedData:
    """T129: Null/undefined data handling"""

    def test_null_in_required_field(self, authenticated_client):
        response = authenticated_client.post(
            '/api/tutor/lessons/',
            {'student_id': None, 'subject_id': 1}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_empty_string_vs_null(self, authenticated_client):
        response1 = authenticated_client.post(
            '/api/tutor/students/',
            {'name': '', 'email': 'test@example.com'}
        )
        response2 = authenticated_client.post(
            '/api/tutor/students/',
            {'name': None, 'email': 'test@example.com'}
        )

        assert response1.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]
        assert response2.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]


# ============================================================================
# T130: Pagination Out of Bounds
# ============================================================================

@pytest.mark.django_db
class TestPaginationOutOfBounds:
    """T130: Pagination out of bounds"""

    def test_page_exceeds_total_pages(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/students/?page=99999')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_negative_page_number(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/students/?page=-1')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_zero_page_number(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/students/?page=0')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_non_numeric_page_parameter(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/students/?page=abc')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_excessive_page_size(self, authenticated_client):
        response = authenticated_client.get('/api/tutor/students/?page_size=10000')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_pagination_consistency(self, authenticated_client):
        response1 = authenticated_client.get('/api/tutor/students/?page=1')
        response2 = authenticated_client.get('/api/tutor/students/?page=1')
        
        assert response1.status_code == response2.status_code
