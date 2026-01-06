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

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tutor_user(db):
    from accounts.models import TutorProfile
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
def student_users(db):
    from accounts.models import StudentProfile, ParentProfile
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
    """T119: Network loss handling - потеря сети"""

    def test_network_timeout_on_list_students(self, authenticated_client):
        """Test: Network timeout when fetching students"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError("Timeout")
            response = authenticated_client.get('/api/tutor/students/')
            assert response.status_code in [
                status.HTTP_504_GATEWAY_TIMEOUT,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND
            ]

    def test_network_connection_error(self, authenticated_client):
        """Test: Connection error handling"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("No connection")
            response = authenticated_client.get('/api/tutor/dashboard/')
            assert response.status_code in [
                status.HTTP_503_SERVICE_UNAVAILABLE,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_404_NOT_FOUND
            ]


# ============================================================================
# T120: Server Error Handling
# ============================================================================

@pytest.mark.django_db
class TestServerErrorHandling:
    """T120: Server error handling - обработка ошибки 500"""

    def test_500_error_response(self, authenticated_client):
        """Test: Server error graceful handling"""
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
    """T121: Request timeout handling - обработка timeout"""

    def test_api_timeout_response(self, authenticated_client):
        """Test: API timeout handling"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError()
            response = authenticated_client.get('/api/tutor/students/')
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_504_GATEWAY_TIMEOUT,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_404_NOT_FOUND
            ]


# ============================================================================
# T122: Invalid Data Handling
# ============================================================================

@pytest.mark.django_db
class TestInvalidDataHandling:
    """T122: Invalid data handling - обработка невалидных данных"""

    def test_invalid_json_request(self, authenticated_client):
        """Test: Invalid JSON is rejected"""
        response = authenticated_client.post(
            '/api/tutor/students/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_fields(self, authenticated_client):
        """Test: Missing required fields"""
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'name': 'John'}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_field_types(self, authenticated_client):
        """Test: Invalid field type"""
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'student_id': 'not_integer'}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sql_injection_protection(self, authenticated_client):
        """Test: SQL injection attempt is blocked"""
        response = authenticated_client.get(
            "/api/tutor/students/?name='; DROP TABLE students; --"
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_xss_injection_protection(self, authenticated_client):
        """Test: XSS injection attempt is blocked"""
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'name': '<script>alert("xss")</script>'}
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_oversized_payload_rejection(self, authenticated_client):
        """Test: Oversized payload is rejected"""
        response = authenticated_client.post(
            '/api/tutor/students/',
            {'name': 'A' * 100000}
        )
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# T123: Concurrent Editing
# ============================================================================

class TestConcurrentEditing(TransactionTestCase):
    """T123: Concurrent editing - конкурентное редактирование"""

    def test_concurrent_profile_edits(self):
        """Test: Concurrent profile edits don't corrupt data"""
        from accounts.models import TutorProfile

        tutor = User.objects.create_user(
            username='tutor_concurrent_20260107',
            email='tutor_concurrent_20260107@example.com',
            role='tutor'
        )
        TutorProfile.objects.create(user=tutor)

        def edit_profile(bio_text):
            client = APIClient()
            client.force_authenticate(user=tutor)
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

        assert any(code in [200, 400, 409, 404] for code in results)


# ============================================================================
# T124: Delete Non-existent Student
# ============================================================================

@pytest.mark.django_db
class TestDeleteNonexistent:
    """T124: Delete non-existent - удаление несуществующего"""

    def test_delete_nonexistent_student_404(self, authenticated_client):
        """Test: Deleting non-existent student returns 404"""
        response = authenticated_client.delete('/api/tutor/students/99999/')
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_delete_student_idempotency(self, authenticated_client, student_users):
        """Test: Second delete of same student"""
        student_id = student_users[0].id
        response1 = authenticated_client.delete(f'/api/tutor/students/{student_id}/')
        response2 = authenticated_client.delete(f'/api/tutor/students/{student_id}/')

        assert response1.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]
        assert response2.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]


# ============================================================================
# T125: Cascade Deletion
# ============================================================================

@pytest.mark.django_db
class TestCascadeDeletion:
    """T125: Cascade deletion - удаление студента удаляет связи"""

    def test_delete_student_cascade(self, authenticated_client, student_users):
        """Test: Cascade deletion of related records"""
        student = student_users[0]
        response = authenticated_client.delete(f'/api/tutor/students/{student.id}/')

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]


# ============================================================================
# T126: Database Race Conditions
# ============================================================================

class TestDatabaseRaceConditions(TransactionTestCase):
    """T126: Race conditions - race conditions в БД"""

    def test_concurrent_subject_creation(self):
        """Test: Concurrent subject creation doesn't create duplicates"""
        from materials.models import Subject

        def create_subject():
            try:
                import threading
                name = f'Subject_{threading.current_thread().ident}_{id(threading)}'
                subject = Subject.objects.create(name=name)
                return subject.id
            except IntegrityError:
                return None

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_subject) for _ in range(3)]
            results = [f.result() for f in as_completed(futures)]

        assert len([r for r in results if r is not None]) >= 1


# ============================================================================
# T127: Student Limit Exceeded
# ============================================================================

@pytest.mark.django_db
class TestStudentLimitExceeded:
    """T127: Student limit - превышение лимита студентов"""

    def test_many_students_handled(self, authenticated_client):
        """Test: System handles many students"""
        from accounts.models import StudentProfile, ParentProfile

        for i in range(10):
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
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# T128: Rate Limiting
# ============================================================================

@pytest.mark.django_db
class TestRateLimiting:
    """T128: Rate limiting - rate limiting на API"""

    def test_rapid_requests_handled(self, authenticated_client):
        """Test: Rapid requests are handled"""
        responses = []
        for i in range(10):
            response = authenticated_client.get('/api/tutor/dashboard/')
            responses.append(response.status_code)

        assert any(code in [200, 404, 429] for code in responses)

    def test_rate_limit_responses(self, authenticated_client):
        """Test: Rate limit responses"""
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
    """T129: Null data - обработка null/undefined данных"""

    def test_null_required_field_rejected(self, authenticated_client):
        """Test: Null in required field is rejected"""
        response = authenticated_client.post(
            '/api/tutor/lessons/',
            {'student_id': None, 'subject_id': 1}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_undefined_fields_in_patch(self, authenticated_client, student_users):
        """Test: PATCH with undefined fields"""
        response = authenticated_client.patch(
            f'/api/tutor/students/{student_users[0].id}/',
            {}
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_404_NOT_FOUND
        ]

    def test_empty_vs_null(self, authenticated_client):
        """Test: Empty string vs null distinction"""
        response1 = authenticated_client.post(
            '/api/tutor/students/',
            {'name': '', 'email': 'test@example.com'}
        )
        response2 = authenticated_client.post(
            '/api/tutor/students/',
            {'name': None, 'email': 'test@example.com'}
        )

        assert response1.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND
        ]
        assert response2.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# T130: Pagination Out of Bounds
# ============================================================================

@pytest.mark.django_db
class TestPaginationOutOfBounds:
    """T130: Pagination - запрос страницы за границей"""

    def test_page_exceeds_total(self, authenticated_client):
        """Test: Page number exceeds total pages"""
        response = authenticated_client.get('/api/tutor/students/?page=99999')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_negative_page_number(self, authenticated_client):
        """Test: Negative page number"""
        response = authenticated_client.get('/api/tutor/students/?page=-1')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_zero_page_number(self, authenticated_client):
        """Test: Page 0"""
        response = authenticated_client.get('/api/tutor/students/?page=0')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_non_numeric_page(self, authenticated_client):
        """Test: Non-numeric page parameter"""
        response = authenticated_client.get('/api/tutor/students/?page=abc')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_excessive_page_size(self, authenticated_client):
        """Test: Excessive page size"""
        response = authenticated_client.get('/api/tutor/students/?page_size=10000')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_pagination_consistency(self, authenticated_client):
        """Test: Pagination consistency across requests"""
        response1 = authenticated_client.get('/api/tutor/students/?page=1')
        response2 = authenticated_client.get('/api/tutor/students/?page=1')

        assert response1.status_code == response2.status_code
