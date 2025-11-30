"""
Integration tests for admin user creation endpoints.

Tests:
- POST /api/auth/students/create/ - Create student with profile
- POST /api/auth/parents/create/ - Create parent with profile
- POST /api/auth/assign-parent/ - Assign parent to students
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User, StudentProfile, ParentProfile


@pytest.fixture
def api_client():
    """REST API client"""
    return APIClient()


@pytest.mark.django_db
class TestAdminStudentCreation:
    """Test POST /api/auth/students/create/ endpoint."""

    def test_create_student_minimal_data(self, admin_user, api_client):
        """Test creating student with minimal required data."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_create_student')

        data = {
            'email': 'newstudent@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'grade': '10',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert 'credentials' in response.data
        assert 'login' in response.data['credentials']
        assert 'password' in response.data['credentials']
        assert response.data['credentials']['login'] == data['email']

        # Verify user created in database
        user = User.objects.get(email=data['email'])
        assert user.first_name == data['first_name']
        assert user.last_name == data['last_name']
        assert user.role == User.Role.STUDENT
        assert user.is_active is True

        # Verify profile created
        assert hasattr(user, 'student_profile')
        profile = user.student_profile
        assert profile.grade == data['grade']

    def test_create_student_with_optional_data(self, admin_user, tutor_user, parent_user, api_client):
        """Test creating student with optional fields (tutor, parent, goal, phone)."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_create_student')

        data = {
            'email': 'fullstudent@test.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'grade': '11',
            'phone': '+79991234567',
            'goal': 'Prepare for university entrance exam',
            'tutor_id': tutor_user.id,
            'parent_id': parent_user.id,
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        # Verify profile fields
        user = User.objects.get(email=data['email'])
        profile = user.student_profile
        assert profile.grade == data['grade']
        assert profile.goal == data['goal']
        assert profile.tutor_id == tutor_user.id
        assert profile.parent_id == parent_user.id
        assert user.phone == data['phone']

    def test_create_student_duplicate_email(self, admin_user, student_user, api_client):
        """Test creating student with existing email returns error."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_create_student')

        data = {
            'email': student_user.email,  # Already exists
            'first_name': 'Duplicate',
            'last_name': 'User',
            'grade': '9',
        }

        response = api_client.post(url, data, format='json')

        # Should fail with validation error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]

    def test_create_student_requires_authentication(self, api_client):
        """Test creating student without authentication fails."""
        url = reverse('admin_create_student')

        data = {
            'email': 'unauthorized@test.com',
            'first_name': 'Test',
            'last_name': 'User',
            'grade': '10',
        }

        response = api_client.post(url, data, format='json')

        # DRF returns 401 for unauthenticated, 403 for authenticated but unauthorized
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_student_requires_admin(self, student_user, api_client):
        """Test creating student as non-admin user fails."""
        api_client.force_authenticate(user=student_user)
        url = reverse('admin_create_student')

        data = {
            'email': 'nonadmin@test.com',
            'first_name': 'Test',
            'last_name': 'User',
            'grade': '10',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminParentCreation:
    """Test POST /api/auth/parents/create/ endpoint."""

    def test_create_parent_minimal_data(self, admin_user, api_client):
        """Test creating parent with minimal required data."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_create_parent')

        data = {
            'email': 'newparent@test.com',
            'first_name': 'Parent',
            'last_name': 'Smith',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert 'credentials' in response.data
        assert 'login' in response.data['credentials']
        assert 'password' in response.data['credentials']
        assert response.data['credentials']['login'] == data['email']

        # Verify user created in database
        user = User.objects.get(email=data['email'])
        assert user.first_name == data['first_name']
        assert user.last_name == data['last_name']
        assert user.role == User.Role.PARENT
        assert user.is_active is True

        # Verify profile created
        assert hasattr(user, 'parent_profile')

    def test_create_parent_with_phone(self, admin_user, api_client):
        """Test creating parent with phone number."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_create_parent')

        data = {
            'email': 'parentphone@test.com',
            'first_name': 'Parent',
            'last_name': 'WithPhone',
            'phone': '+79991234567',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        user = User.objects.get(email=data['email'])
        assert user.phone == data['phone']

    def test_create_parent_duplicate_email(self, admin_user, parent_user, api_client):
        """Test creating parent with existing email returns error."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_create_parent')

        data = {
            'email': parent_user.email,  # Already exists
            'first_name': 'Duplicate',
            'last_name': 'Parent',
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
class TestParentAssignment:
    """Test POST /api/auth/assign-parent/ endpoint."""

    def test_assign_parent_to_single_student(self, admin_user, parent_user, student_user, api_client):
        """Test assigning parent to one student."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_assign_parent')

        data = {
            'parent_id': parent_user.id,
            'student_ids': [student_user.id],
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['parent_id'] == parent_user.id
        assert response.data['assigned_students'] == [student_user.id]

        # Verify in database
        student_user.student_profile.refresh_from_db()
        assert student_user.student_profile.parent_id == parent_user.id

    def test_assign_parent_to_multiple_students(self, admin_user, parent_user, api_client):
        """Test assigning parent to multiple students (bulk assignment)."""
        api_client.force_authenticate(user=admin_user)

        # Create multiple students
        student1 = User.objects.create(
            username='student1@bulk.com',
            email='student1@bulk.com',
            first_name='Student',
            last_name='One',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(user=student1, grade='10')

        student2 = User.objects.create(
            username='student2@bulk.com',
            email='student2@bulk.com',
            first_name='Student',
            last_name='Two',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(user=student2, grade='11')

        url = reverse('admin_assign_parent')
        data = {
            'parent_id': parent_user.id,
            'student_ids': [student1.id, student2.id],
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['assigned_students']) == 2

        # Verify both students have parent assigned
        student1.student_profile.refresh_from_db()
        student2.student_profile.refresh_from_db()
        assert student1.student_profile.parent_id == parent_user.id
        assert student2.student_profile.parent_id == parent_user.id

    def test_assign_parent_idempotent(self, admin_user, parent_user, student_user, api_client):
        """Test assigning parent multiple times is idempotent."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_assign_parent')

        data = {
            'parent_id': parent_user.id,
            'student_ids': [student_user.id],
        }

        # Assign first time
        response1 = api_client.post(url, data, format='json')
        assert response1.status_code == status.HTTP_200_OK

        # Assign again (should succeed, no error)
        response2 = api_client.post(url, data, format='json')
        assert response2.status_code == status.HTTP_200_OK

        # Verify still assigned correctly
        student_user.student_profile.refresh_from_db()
        assert student_user.student_profile.parent_id == parent_user.id

    def test_assign_parent_invalid_parent_id(self, admin_user, student_user, api_client):
        """Test assigning non-existent parent returns error."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_assign_parent')

        data = {
            'parent_id': 99999,  # Non-existent ID
            'student_ids': [student_user.id],
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_parent_invalid_student_ids(self, admin_user, parent_user, api_client):
        """Test assigning parent to non-existent students returns error."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_assign_parent')

        data = {
            'parent_id': parent_user.id,
            'student_ids': [99999, 99998],  # Non-existent IDs
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_parent_missing_fields(self, admin_user, api_client):
        """Test assignment without required fields returns error."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin_assign_parent')

        # Missing parent_id
        response1 = api_client.post(url, {'student_ids': [1]}, format='json')
        assert response1.status_code == status.HTTP_400_BAD_REQUEST

        # Missing student_ids
        response2 = api_client.post(url, {'parent_id': 1}, format='json')
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

        # Empty student_ids
        response3 = api_client.post(url, {'parent_id': 1, 'student_ids': []}, format='json')
        assert response3.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAdminWorkflowIntegration:
    """Test complete workflow: create student → create parent → assign parent."""

    def test_complete_workflow(self, admin_user, api_client):
        """Test full workflow of creating users and assigning relationships."""
        api_client.force_authenticate(user=admin_user)

        # Step 1: Create student
        student_url = reverse('admin_create_student')
        student_data = {
            'email': 'workflow.student@test.com',
            'first_name': 'Workflow',
            'last_name': 'Student',
            'grade': '10',
        }
        student_response = api_client.post(student_url, student_data, format='json')
        assert student_response.status_code == status.HTTP_201_CREATED
        student_id = student_response.data['user']['id']

        # Step 2: Create parent
        parent_url = reverse('admin_create_parent')
        parent_data = {
            'email': 'workflow.parent@test.com',
            'first_name': 'Workflow',
            'last_name': 'Parent',
        }
        parent_response = api_client.post(parent_url, parent_data, format='json')
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.data['user']['id']

        # Step 3: Assign parent to student
        assign_url = reverse('admin_assign_parent')
        assign_data = {
            'parent_id': parent_id,
            'student_ids': [student_id],
        }
        assign_response = api_client.post(assign_url, assign_data, format='json')
        assert assign_response.status_code == status.HTTP_200_OK

        # Verify complete relationship in database
        student = User.objects.get(id=student_id)
        parent = User.objects.get(id=parent_id)

        assert student.student_profile.parent_id == parent.id
        assert student.role == User.Role.STUDENT
        assert parent.role == User.Role.PARENT
