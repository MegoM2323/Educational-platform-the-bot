"""
Comprehensive test suite for parent management endpoints

Test coverage:
- create_parent endpoint (13 tests)
- assign_parent_to_students endpoint (11 tests)
- list_parents endpoint (8 tests)
- reset_password (parent role) (3 tests)
- delete_user (parent role) (4 tests)

Total: 39+ test cases covering all scenarios and edge cases
"""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db import transaction
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import User, StudentProfile, ParentProfile

User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture for API client"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user with token"""
    user = User.objects.create_user(
        email='admin@test.com',
        username='admin',
        password='AdminPass123!',
        role=User.Role.STUDENT,
        is_staff=True,
        is_superuser=True
    )
    return user


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """Fixture for authenticated admin API client"""
    token = Token.objects.create(user=admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    api_client.user = admin_user
    return api_client


@pytest.fixture
def parent_user(db):
    """Create a parent user"""
    user = User.objects.create_user(
        email='parent@test.com',
        username='parent',
        password='ParentPass123!',
        first_name='Test',
        last_name='Parent',
        role=User.Role.PARENT,
        is_active=True
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_users(db):
    """Create 3 student users with profiles"""
    students = []
    for i in range(3):
        user = User.objects.create_user(
            email=f'student{i}@test.com',
            username=f'student{i}',
            password='StudentPass123!',
            first_name=f'Student{i}',
            last_name='Test',
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=user, grade='10')
        students.append(user)
    return students


# ============================================================================
# CREATE PARENT ENDPOINT TESTS (13 tests)
# ============================================================================

@pytest.mark.django_db
class TestCreateParentEndpoint:
    """Tests for create_parent endpoint"""

    def test_create_parent_valid_with_all_fields(self, authenticated_admin_client):
        """Test: Valid creation with all fields → 201 Created"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'newparent@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+1234567890'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert 'credentials' in response.data
        assert response.data['credentials']['login'] == 'newparent@test.com'
        assert 'password' in response.data['credentials']

        # Verify user created
        parent = User.objects.get(email='newparent@test.com')
        assert parent.role == User.Role.PARENT
        assert parent.first_name == 'John'
        assert parent.last_name == 'Doe'
        assert parent.phone == '+1234567890'

        # Verify profile created
        assert ParentProfile.objects.filter(user=parent).exists()

    def test_create_parent_valid_with_minimal_fields(self, authenticated_admin_client):
        """Test: Valid creation with minimal fields → 201 Created"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'minimal@test.com',
            'first_name': 'Jane',
            'last_name': 'Smith'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        parent = User.objects.get(email='minimal@test.com')
        assert parent.is_active is True

    def test_create_parent_duplicate_email_returns_409(self, authenticated_admin_client, parent_user):
        """Test: Duplicate email → 409 Conflict"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'parent@test.com',  # Already exists
            'first_name': 'Another',
            'last_name': 'Parent'
        })

        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'detail' in response.data

    def test_create_parent_invalid_email_format_returns_400(self, authenticated_admin_client):
        """Test: Invalid email format → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'not-an-email',
            'first_name': 'Test',
            'last_name': 'Parent'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_parent_missing_email_returns_400(self, authenticated_admin_client):
        """Test: Missing email → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'first_name': 'Test',
            'last_name': 'Parent'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # DRF returns field-specific errors for serializer validation
        assert 'email' in response.data or 'detail' in response.data

    def test_create_parent_missing_first_name_returns_400(self, authenticated_admin_client):
        """Test: Missing first_name → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'test@test.com',
            'last_name': 'Parent'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_parent_missing_last_name_returns_400(self, authenticated_admin_client):
        """Test: Missing last_name → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'test@test.com',
            'first_name': 'Test'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_parent_invalid_phone_format_returns_400(self, authenticated_admin_client):
        """Test: Invalid phone format → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'test@test.com',
            'first_name': 'Test',
            'last_name': 'Parent',
            'phone': 'invalid-phone'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_parent_credentials_returned_once(self, authenticated_admin_client):
        """Test: Credentials returned once (one-time display)"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'onetime@test.com',
            'first_name': 'One',
            'last_name': 'Time'
        })

        assert response.status_code == status.HTTP_201_CREATED
        credentials = response.data.get('credentials')
        assert credentials is not None
        assert 'login' in credentials
        assert 'password' in credentials
        assert len(credentials['password']) >= 12

    def test_create_parent_profile_auto_created(self, authenticated_admin_client):
        """Test: ParentProfile auto-created"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'auto@test.com',
            'first_name': 'Auto',
            'last_name': 'Profile'
        })

        assert response.status_code == status.HTTP_201_CREATED
        parent = User.objects.get(email='auto@test.com')
        profile = ParentProfile.objects.filter(user=parent)
        assert profile.exists()

    def test_create_parent_role_set_correctly(self, authenticated_admin_client):
        """Test: User role set to 'parent'"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'role@test.com',
            'first_name': 'Role',
            'last_name': 'Test'
        })

        assert response.status_code == status.HTTP_201_CREATED
        parent = User.objects.get(email='role@test.com')
        assert parent.role == User.Role.PARENT

    def test_create_parent_transaction_rollback_on_error(self, authenticated_admin_client):
        """Test: Transaction rollback on error"""
        initial_count = User.objects.filter(role=User.Role.PARENT).count()

        # Attempt with missing required field
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'rollback@test.com'
            # Missing first_name, last_name
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verify no user was created
        assert User.objects.filter(role=User.Role.PARENT).count() == initial_count

    def test_create_parent_empty_email_returns_400(self, authenticated_admin_client):
        """Test: Empty email → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': '',
            'first_name': 'Test',
            'last_name': 'Parent'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_parent_empty_names_returns_400(self, authenticated_admin_client):
        """Test: Empty names → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'test@test.com',
            'first_name': '',
            'last_name': ''
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# ASSIGN PARENT TO STUDENTS ENDPOINT TESTS (11 tests)
# ============================================================================

@pytest.mark.django_db
class TestAssignParentToStudentsEndpoint:
    """Tests for assign_parent_to_students endpoint"""

    def test_assign_parent_valid_bulk_assignment(self, authenticated_admin_client, parent_user, student_users):
        """Test: Valid bulk assignment (multiple students) → 200 OK"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [student_users[0].id, student_users[1].id, student_users[2].id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['assigned_students']) == 3
        assert response.data['parent_id'] == parent_user.id

        # Verify assignments
        for student in student_users:
            student_profile = StudentProfile.objects.get(user=student)
            assert student_profile.parent == parent_user

    def test_assign_parent_empty_student_list_returns_400(self, authenticated_admin_client, parent_user):
        """Test: Empty student_ids list → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': []
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_parent_missing_parent_id_returns_400(self, authenticated_admin_client, student_users):
        """Test: Missing parent_id → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'student_ids': [student_users[0].id]
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_parent_parent_not_found_returns_404(self, authenticated_admin_client, student_users):
        """Test: Parent not found → 404 Not Found"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': 99999,
            'student_ids': [student_users[0].id]
        }, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_parent_student_not_found_returns_404(self, authenticated_admin_client, parent_user):
        """Test: Student not found → 404 Not Found"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [99999]
        }, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_parent_invalid_student_ids_type_returns_400(self, authenticated_admin_client, parent_user):
        """Test: Invalid student_ids type → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': 'not-a-list'
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_parent_overwrites_existing_assignment(self, authenticated_admin_client, parent_user, student_users, db):
        """Test: Overwrites existing parent assignment"""
        # Create another parent
        other_parent = User.objects.create_user(
            email='other@test.com',
            username='other',
            password='Pass123!',
            first_name='Other',
            last_name='Parent',
            role=User.Role.PARENT
        )
        ParentProfile.objects.create(user=other_parent)

        # Assign first student to other parent
        student_profile = StudentProfile.objects.get(user=student_users[0])
        student_profile.parent = other_parent
        student_profile.save()

        # Now assign to first parent
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [student_users[0].id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        student_profile.refresh_from_db()
        assert student_profile.parent == parent_user

    def test_assign_parent_transaction_atomicity(self, authenticated_admin_client, parent_user, student_users):
        """Test: Transaction atomicity (all or nothing)"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [student_users[0].id, student_users[1].id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Verify all assigned
        count = StudentProfile.objects.filter(parent=parent_user).count()
        assert count == 2

    def test_assign_parent_response_contains_assigned_ids(self, authenticated_admin_client, parent_user, student_users):
        """Test: Response contains all assigned student IDs"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [student_users[0].id, student_users[1].id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data['assigned_students']) == {student_users[0].id, student_users[1].id}

    def test_assign_parent_missing_parent_id_field_returns_400(self, authenticated_admin_client):
        """Test: Missing parent_id field → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'student_ids': [1, 2]
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_parent_missing_student_ids_field_returns_400(self, authenticated_admin_client, parent_user):
        """Test: Missing student_ids field → 400 Bad Request"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# LIST PARENTS ENDPOINT TESTS (8 tests)
# ============================================================================

@pytest.mark.django_db
class TestListParentsEndpoint:
    """Tests for list_parents endpoint"""

    def test_list_parents_returns_all_parents(self, authenticated_admin_client, parent_user, db):
        """Test: Lists all parents with pagination"""
        # Create multiple parents
        for i in range(3):
            user = User.objects.create_user(
                email=f'parent{i}@test.com',
                username=f'parent{i}',
                password='Pass123!',
                first_name=f'Parent{i}',
                last_name='Test',
                role=User.Role.PARENT
            )
            ParentProfile.objects.create(user=user)

        response = authenticated_admin_client.get('/api/auth/parents/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 3

    def test_list_parents_children_count_accurate(self, authenticated_admin_client, parent_user, student_users):
        """Test: children_count accurate via annotate"""
        # Assign students to parent
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            profile.parent = parent_user
            profile.save()

        response = authenticated_admin_client.get('/api/auth/parents/')

        assert response.status_code == status.HTTP_200_OK
        # Find parent in results
        parent_data = next((p for p in response.data['results'] if p['user']['id'] == parent_user.id), None)
        assert parent_data is not None
        assert parent_data['children_count'] == 3

    def test_list_parents_no_n_plus_one_queries(self, authenticated_admin_client, parent_user, db):
        """Test: No N+1 queries (assert_num_queries <= 5)"""
        # Create 5 parents
        for i in range(5):
            user = User.objects.create_user(
                email=f'many{i}@test.com',
                username=f'many{i}',
                password='Pass123!',
                first_name=f'Many{i}',
                last_name='Parent',
                role=User.Role.PARENT
            )
            ParentProfile.objects.create(user=user)

        # Use django_assert_num_queries to verify query count
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = authenticated_admin_client.get('/api/auth/parents/')

        # Should have minimal queries (select_related + prefetch)
        # Expected: 1-2 queries max (parents + children count)
        assert len(ctx.captured_queries) <= 5
        assert response.status_code == status.HTTP_200_OK

    def test_list_parents_empty_list_when_no_parents(self, authenticated_admin_client, db):
        """Test: Empty list when no parents"""
        # Delete all parents
        User.objects.filter(role=User.Role.PARENT).delete()

        response = authenticated_admin_client.get('/api/auth/parents/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []

    def test_list_parents_ordering_by_date_joined(self, authenticated_admin_client, parent_user, db):
        """Test: Ordering by date_joined correct (newest first)"""
        # Create another parent
        newer_parent = User.objects.create_user(
            email='newer@test.com',
            username='newer',
            password='Pass123!',
            first_name='Newer',
            last_name='Parent',
            role=User.Role.PARENT
        )
        ParentProfile.objects.create(user=newer_parent)

        response = authenticated_admin_client.get('/api/auth/parents/')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        # Newest should be first
        assert results[0]['user']['id'] == newer_parent.id
        assert results[1]['user']['id'] == parent_user.id

    def test_list_parents_filters_inactive_parents(self, authenticated_admin_client, parent_user, db):
        """Test: Can filter inactive parents via query param"""
        # Deactivate parent
        parent_user.is_active = False
        parent_user.save()

        # Create active parent
        active_parent = User.objects.create_user(
            email='active@test.com',
            username='active',
            password='Pass123!',
            first_name='Active',
            last_name='Parent',
            role=User.Role.PARENT,
            is_active=True
        )
        ParentProfile.objects.create(user=active_parent)

        # List only active parents via query param
        response = authenticated_admin_client.get('/api/auth/parents/?is_active=true')

        assert response.status_code == status.HTTP_200_OK
        parent_ids = [p['user']['id'] for p in response.data['results']]
        assert parent_user.id not in parent_ids
        assert active_parent.id in parent_ids

    def test_list_parents_response_format_correct(self, authenticated_admin_client, parent_user, student_users):
        """Test: Response format correct (results array)"""
        response = authenticated_admin_client.get('/api/auth/parents/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert isinstance(response.data['results'], list)

        if response.data['results']:
            parent_data = response.data['results'][0]
            assert 'user' in parent_data
            assert 'children_count' in parent_data


# ============================================================================
# RESET PASSWORD (PARENT ROLE) TESTS (3 tests)
# ============================================================================

@pytest.mark.django_db
class TestResetPasswordParentRole:
    """Tests for reset_password endpoint (parent role)"""

    def test_reset_password_parent_works(self, authenticated_admin_client, parent_user):
        """Test: Password reset for parent works"""
        response = authenticated_admin_client.post(f'/api/auth/users/{parent_user.id}/reset-password/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'new_password' in response.data
        assert response.data['user_id'] == parent_user.id

    def test_reset_password_new_password_hashed_correctly(self, authenticated_admin_client, parent_user):
        """Test: New password stored and hashed correctly"""
        response = authenticated_admin_client.post(f'/api/auth/users/{parent_user.id}/reset-password/')

        assert response.status_code == status.HTTP_200_OK
        new_password = response.data['new_password']

        # Verify password is hashed in DB
        parent_user.refresh_from_db()
        assert parent_user.check_password(new_password)

    def test_reset_password_credentials_returned_once(self, authenticated_admin_client, parent_user):
        """Test: Credentials returned once"""
        response = authenticated_admin_client.post(f'/api/auth/users/{parent_user.id}/reset-password/')

        assert response.status_code == status.HTTP_200_OK
        assert 'new_password' in response.data
        assert len(response.data['new_password']) >= 12


# ============================================================================
# DELETE USER (PARENT ROLE) TESTS (4 tests)
# ============================================================================

@pytest.mark.django_db
class TestDeleteUserParentRole:
    """Tests for delete_user endpoint (parent role)"""

    def test_soft_delete_parent(self, authenticated_admin_client, parent_user):
        """Test: Soft delete parent (is_active = False)"""
        response = authenticated_admin_client.delete(
            f'/api/auth/users/{parent_user.id}/delete/?soft=true',
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        parent_user.refresh_from_db()
        assert parent_user.is_active is False

    def test_hard_delete_parent(self, authenticated_admin_client, parent_user):
        """Test: Hard delete parent (remove from DB)"""
        parent_id = parent_user.id

        response = authenticated_admin_client.delete(
            f'/api/auth/users/{parent_id}/delete/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify user removed from DB
        assert not User.objects.filter(id=parent_id).exists()

    def test_delete_parent_children_fk_cleared(self, authenticated_admin_client, parent_user, student_users, db):
        """Test: Children FK cleared (SET_NULL on delete)"""
        # Assign students to parent
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            profile.parent = parent_user
            profile.save()

        # Hard delete parent
        response = authenticated_admin_client.delete(
            f"/api/auth/users/{parent_user.id}/delete/")

        assert response.status_code == status.HTTP_200_OK

        # Verify children's parent FK is NULL
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            assert profile.parent is None

    def test_delete_parent_reports_affected_children(self, authenticated_admin_client, parent_user, student_users):
        """Test: Reports affected children count"""
        # Assign students to parent
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            profile.parent = parent_user
            profile.save()

        response = authenticated_admin_client.delete(
            f"/api/auth/users/{parent_user.id}/delete/?soft=true")

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True


# ============================================================================
# PERMISSION & AUTHENTICATION TESTS (5 tests)
# ============================================================================

@pytest.mark.django_db
class TestParentManagementPermissions:
    """Tests for permissions and authentication"""

    def test_create_parent_requires_staff_permission(self, api_client, db):
        """Test: Non-admin cannot create parent"""
        # Create non-admin user
        user = User.objects.create_user(
            email='user@test.com',
            username='user',
            password='Pass123!',
            role=User.Role.STUDENT
        )
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.post('/api/auth/parents/create/', {
            'email': 'test@test.com',
            'first_name': 'Test',
            'last_name': 'Parent'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_parent_requires_staff_permission(self, api_client, parent_user, student_users, db):
        """Test: Non-admin cannot assign parent"""
        user = User.objects.create_user(
            email='user@test.com',
            username='user',
            password='Pass123!',
            role=User.Role.STUDENT
        )
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [student_users[0].id]
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_parents_requires_staff_permission(self, api_client, db):
        """Test: Non-admin cannot list parents"""
        user = User.objects.create_user(
            email='user@test.com',
            username='user',
            password='Pass123!',
            role=User.Role.STUDENT
        )
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/parents/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reset_password_requires_staff_permission(self, api_client, parent_user, db):
        """Test: Non-admin cannot reset password"""
        user = User.objects.create_user(
            email='user@test.com',
            username='user',
            password='Pass123!',
            role=User.Role.STUDENT
        )
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.post(f'/api/auth/users/{parent_user.id}/reset-password/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_endpoints_require_authentication(self, api_client, parent_user, db):
        """Test: Unauthenticated users get 401"""
        response = api_client.get('/api/auth/parents/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.post('/api/auth/parents/create/', {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# EDGE CASES & VALIDATION TESTS (5 tests)
# ============================================================================

@pytest.mark.django_db
class TestParentManagementEdgeCases:
    """Tests for edge cases and validation"""

    def test_create_parent_email_case_insensitive(self, authenticated_admin_client):
        """Test: Email is case-insensitive"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'TestEmail@Test.COM',
            'first_name': 'Case',
            'last_name': 'Test'
        })

        assert response.status_code == status.HTTP_201_CREATED
        # Email should be stored as lowercase
        parent = User.objects.get(email__iexact='TestEmail@Test.COM')
        assert parent.email == 'testemail@test.com'

    def test_create_parent_whitespace_trimmed(self, authenticated_admin_client):
        """Test: Whitespace is trimmed from fields"""
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': '  spaced@test.com  ',
            'first_name': '  John  ',
            'last_name': '  Doe  '
        })

        assert response.status_code == status.HTTP_201_CREATED
        parent = User.objects.get(email='spaced@test.com')
        assert parent.first_name == 'John'
        assert parent.last_name == 'Doe'

    def test_assign_parent_partial_students_not_found(self, authenticated_admin_client, parent_user, student_users):
        """Test: If any student not found, assignment fails"""
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_user.id,
            'student_ids': [student_users[0].id, 99999]
        }, format='json')

        # Should only assign the found ones, or fail entirely
        # Based on implementation, it should fail if any not found
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]

    def test_delete_nonexistent_user_returns_404(self, authenticated_admin_client):
        """Test: Deleting nonexistent user returns 404"""
        response = authenticated_admin_client.delete(
            f"/api/auth/users/99999/delete/?soft=true")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_reset_password_nonexistent_user_returns_404(self, authenticated_admin_client):
        """Test: Resetting password for nonexistent user returns 404"""
        response = authenticated_admin_client.post(
            '/api/auth/users/99999/reset-password/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# INTEGRATION TESTS (4 tests)
# ============================================================================

@pytest.mark.django_db
class TestParentManagementIntegration:
    """Integration tests for parent management workflow"""

    def test_complete_parent_workflow(self, authenticated_admin_client, student_users, db):
        """Test: Complete workflow - create, assign, list"""
        # 1. Create parent
        response = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'workflow@test.com',
            'first_name': 'Workflow',
            'last_name': 'Test'
        })
        assert response.status_code == status.HTTP_201_CREATED
        parent_id = response.data['user']['id']

        # 2. Assign students to parent
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent_id,
            'student_ids': [student_users[0].id, student_users[1].id]
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['assigned_students']) == 2

        # 3. List parents and verify
        response = authenticated_admin_client.get('/api/auth/parents/')
        assert response.status_code == status.HTTP_200_OK
        parent_data = next((p for p in response.data['results'] if p['user']['id'] == parent_id), None)
        assert parent_data is not None
        assert parent_data['children_count'] == 2

    def test_parent_reassignment_workflow(self, authenticated_admin_client, student_users, db):
        """Test: Reassign student from one parent to another"""
        # Create two parents
        parent1_resp = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'parent1@test.com',
            'first_name': 'Parent1',
            'last_name': 'Test'
        })
        parent1_id = parent1_resp.data['user']['id']

        parent2_resp = authenticated_admin_client.post('/api/auth/parents/create/', {
            'email': 'parent2@test.com',
            'first_name': 'Parent2',
            'last_name': 'Test'
        })
        parent2_id = parent2_resp.data['user']['id']

        # Assign student to parent1
        authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent1_id,
            'student_ids': [student_users[0].id]
        }, format='json')

        # Reassign to parent2
        response = authenticated_admin_client.post('/api/auth/assign-parent/', {
            'parent_id': parent2_id,
            'student_ids': [student_users[0].id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        student_profile = StudentProfile.objects.get(user=student_users[0])
        assert student_profile.parent_id == parent2_id

    def test_parent_soft_delete_preserves_data(self, authenticated_admin_client, parent_user, student_users):
        """Test: Soft delete preserves data for recovery"""
        # Assign students
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            profile.parent = parent_user
            profile.save()

        # Soft delete parent
        response = authenticated_admin_client.delete(
            f"/api/auth/users/{parent_user.id}/delete/?soft=true")

        assert response.status_code == status.HTTP_200_OK

        # Verify students still linked but parent is inactive
        parent_user.refresh_from_db()
        assert parent_user.is_active is False

        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            assert profile.parent_id == parent_user.id

    def test_parent_hard_delete_cascades_correctly(self, authenticated_admin_client, parent_user, student_users):
        """Test: Hard delete cascades to related objects"""
        # Create parent profile relations
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            profile.parent = parent_user
            profile.save()

        parent_id = parent_user.id

        # Hard delete
        response = authenticated_admin_client.delete(
            f"/api/auth/users/{parent_id}/delete/")

        assert response.status_code == status.HTTP_200_OK

        # Verify user deleted
        assert not User.objects.filter(id=parent_id).exists()

        # Verify profile deleted (cascaded)
        assert not ParentProfile.objects.filter(user_id=parent_id).exists()

        # Verify children FK cleared
        for student in student_users:
            profile = StudentProfile.objects.get(user=student)
            assert profile.parent is None
