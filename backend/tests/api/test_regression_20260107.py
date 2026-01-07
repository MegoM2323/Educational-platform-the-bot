"""
Regression Tests for Fixed Endpoints (tutor_cabinet_final_test_regression_20260107)

Verifies all fixed endpoints work correctly after critical issues resolution:
- Chat: Fixed duplicate created_by parameter (500 error)
- Accounts: Fixed URL routing priority (403 error on students list)
- Invoices/Payments: Verified routing (404 error)
- Assignments: Verified routing (404 error)

Test Coverage:
- Chat endpoints: 4 tests (create, list, retrieve, delete)
- Accounts endpoints: 5 tests (list_students, create, retrieve, update, profile)
- Payments endpoints: 3 tests (list, create, retrieve)
- Assignments endpoints: 3 tests (list, create, retrieve)
Total: 15 endpoints, 16 tests

Created: 2026-01-07
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, date, timedelta

from accounts.models import User, TutorProfile, StudentProfile
from chat.models import ChatRoom
from materials.models import Subject
from payments.models import Payment
from assignments.models import Assignment


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database"""
    pass


@pytest.fixture
def api_client():
    """Provide API client"""
    return APIClient()


@pytest.fixture
def test_data(db):
    """Create test data"""
    # Create admin user for list endpoints (requires IsStaffOrAdmin permission)
    admin = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='TestPass123!',
        role=User.Role.ADMIN,
        first_name='Admin',
        last_name='User',
        is_staff=True,
        is_superuser=True
    )

    # Create tutor
    tutor = User.objects.create_user(
        username='tutor_test',
        email='tutor@test.com',
        password='TestPass123!',
        role=User.Role.TEACHER,
        first_name='Test',
        last_name='Tutor'
    )
    TutorProfile.objects.create(user=tutor)

    # Create students
    student1 = User.objects.create_user(
        username='student1_test',
        email='student1@test.com',
        password='TestPass123!',
        role=User.Role.STUDENT,
        first_name='John',
        last_name='Student'
    )
    StudentProfile.objects.create(user=student1)

    student2 = User.objects.create_user(
        username='student2_test',
        email='student2@test.com',
        password='TestPass123!',
        role=User.Role.STUDENT,
        first_name='Jane',
        last_name='Student'
    )
    StudentProfile.objects.create(user=student2)

    # Create subject
    subject = Subject.objects.create(
        name='Math',
        description='Mathematics'
    )

    return {
        'admin': admin,
        'tutor': tutor,
        'student1': student1,
        'student2': student2,
        'subject': subject
    }


# ================================================================================
# GROUP 1: CHAT ENDPOINTS (Issue #1 Fix - duplicate created_by parameter)
# ================================================================================

class TestChatEndpoints:
    """Test Chat endpoints - Fixed duplicate created_by parameter"""

    @pytest.mark.django_db
    def test_create_chat_room(self, api_client, test_data):
        """Test: POST /api/chat/rooms/ - should return 201 (not 500)"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        payload = {
            'name': 'Test Room',
            'room_type': ChatRoom.Type.GROUP
        }

        response = api_client.post('/api/chat/rooms/', payload, format='json')

        # Expected: 201 Created (not 500)
        assert response.status_code == status.HTTP_201_CREATED, \
            f"Expected 201, got {response.status_code}: {response.data}"
        assert 'id' in response.data

    @pytest.mark.django_db
    def test_list_chat_rooms(self, api_client, test_data):
        """Test: GET /api/chat/rooms/ - should return 200"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        # Create a room first
        ChatRoom.objects.create(
            name='Existing Room',
            created_by=tutor,
            room_type=ChatRoom.Type.GROUP,
            is_active=True
        )

        response = api_client.get('/api/chat/rooms/', format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_retrieve_chat_room(self, api_client, test_data):
        """Test: GET /api/chat/rooms/{id}/ - should return 200"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=tutor,
            room_type=ChatRoom.Type.GROUP,
            is_active=True
        )

        response = api_client.get(f'/api/chat/rooms/{room.id}/', format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_delete_chat_room(self, api_client, test_data):
        """Test: DELETE /api/chat/rooms/{id}/ - should return 204"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=tutor,
            room_type=ChatRoom.Type.GROUP,
            is_active=True
        )

        response = api_client.delete(f'/api/chat/rooms/{room.id}/', format='json')

        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK], \
            f"Expected 204 or 200, got {response.status_code}: {response.data}"


# ================================================================================
# GROUP 2: ACCOUNTS ENDPOINTS (Issue #2 Fix - URL routing priority)
# ================================================================================

class TestAccountsEndpoints:
    """Test Accounts endpoints - Fixed URL routing priority"""

    @pytest.mark.django_db
    def test_list_students(self, api_client, test_data):
        """Test: GET /api/accounts/students/ - should return 200 (not 403)"""
        admin = test_data['admin']
        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/accounts/students/', format='json')

        # Expected: 200 OK (not 403 Forbidden)
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"
        # Verify students are returned (should have at least 2 created in test_data)
        assert 'results' in response.data or isinstance(response.data, list), \
            f"Expected results in response, got: {response.data}"

    @pytest.mark.django_db
    def test_create_student(self, api_client, test_data):
        """Test: POST /api/accounts/students/ - should return 201"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        payload = {
            'username': 'new_student',
            'email': 'new_student@test.com',
            'password': 'TestPass123!',
            'first_name': 'New',
            'last_name': 'Student',
            'role': 'student'
        }

        response = api_client.post('/api/accounts/students/', payload, format='json')

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK], \
            f"Expected 201/200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_retrieve_student(self, api_client, test_data):
        """Test: GET /api/accounts/students/{id}/ - should return 200"""
        tutor = test_data['tutor']
        student = test_data['student1']
        api_client.force_authenticate(user=tutor)

        response = api_client.get(f'/api/accounts/students/{student.id}/', format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_update_user(self, api_client, test_data):
        """Test: PATCH /api/accounts/users/{id}/ - should return 200"""
        student = test_data['student1']
        api_client.force_authenticate(user=student)

        payload = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }

        response = api_client.patch(f'/api/accounts/users/{student.id}/', payload, format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_get_tutor_profile(self, api_client, test_data):
        """Test: GET /api/profile/tutor/ - should return 200"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        response = api_client.get('/api/profile/tutor/', format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"


# ================================================================================
# GROUP 3: PAYMENTS ENDPOINTS (Issue #3 Fix - verify routing)
# ================================================================================

class TestPaymentsEndpoints:
    """Test Payments endpoints - Verified routing"""

    @pytest.mark.django_db
    def test_list_payments(self, api_client, test_data):
        """Test: GET /api/invoices/ - should return 200 (not 404)"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        response = api_client.get('/api/invoices/', format='json')

        # Expected: 200 OK (not 404)
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_create_payment(self, api_client, test_data):
        """Test: POST /api/invoices/ - should return 201"""
        tutor = test_data['tutor']
        student = test_data['student1']
        api_client.force_authenticate(user=tutor)

        payload = {
            'student': student.id,
            'amount': '150.00',
            'description': 'Test Payment',
            'status': 'pending'
        }

        response = api_client.post('/api/invoices/', payload, format='json')

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK], \
            f"Expected 201/200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_retrieve_payment(self, api_client, test_data):
        """Test: GET /api/invoices/{id}/ - should return 200"""
        tutor = test_data['tutor']
        student = test_data['student1']
        api_client.force_authenticate(user=tutor)

        payment = Payment.objects.create(
            tutor=tutor,
            student=student,
            amount=150.00,
            status='pending'
        )

        response = api_client.get(f'/api/invoices/{payment.id}/', format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"


# ================================================================================
# GROUP 4: ASSIGNMENTS ENDPOINTS (Issue #4 Fix - verify routing)
# ================================================================================

class TestAssignmentsEndpoints:
    """Test Assignments endpoints - Verified routing"""

    @pytest.mark.django_db
    def test_list_assignments(self, api_client, test_data):
        """Test: GET /api/assignments/ - should return 200 (not 404)"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        response = api_client.get('/api/assignments/', format='json')

        # Expected: 200 OK (not 404)
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_create_assignment(self, api_client, test_data):
        """Test: POST /api/assignments/ - should return 201"""
        tutor = test_data['tutor']
        student = test_data['student1']
        api_client.force_authenticate(user=tutor)

        payload = {
            'student': student.id,
            'title': 'Test Assignment',
            'description': 'Do this assignment',
            'due_date': (date.today() + timedelta(days=7)).isoformat()
        }

        response = api_client.post('/api/assignments/', payload, format='json')

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK], \
            f"Expected 201/200, got {response.status_code}: {response.data}"

    @pytest.mark.django_db
    def test_retrieve_assignment(self, api_client, test_data):
        """Test: GET /api/assignments/{id}/ - should return 200"""
        tutor = test_data['tutor']
        student = test_data['student1']
        api_client.force_authenticate(user=tutor)

        assignment = Assignment.objects.create(
            tutor=tutor,
            student=student,
            title='Test Assignment',
            description='Do this'
        )

        response = api_client.get(f'/api/assignments/{assignment.id}/', format='json')

        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"


# ================================================================================
# SUMMARY TESTS
# ================================================================================

class TestRegressionSummary:
    """Summary tests to verify no regressions"""

    @pytest.mark.django_db
    def test_all_fixed_endpoints_accessible(self, api_client, test_data):
        """Verify all fixed endpoints are accessible"""
        tutor = test_data['tutor']
        api_client.force_authenticate(user=tutor)

        # Critical endpoints that were fixed
        endpoints = [
            ('/api/chat/rooms/', 'GET'),
            ('/api/accounts/students/', 'GET'),
            ('/api/invoices/', 'GET'),
            ('/api/assignments/', 'GET'),
        ]

        results = {}
        for endpoint, method in endpoints:
            response = api_client.get(endpoint, format='json')
            results[endpoint] = response.status_code
            assert response.status_code == status.HTTP_200_OK, \
                f"Endpoint {endpoint} returned {response.status_code}"

        # All should be 200
        assert all(code == 200 for code in results.values()), \
            f"Some endpoints failed: {results}"
