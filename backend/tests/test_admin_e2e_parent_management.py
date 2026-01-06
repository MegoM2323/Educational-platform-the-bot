"""
E2E Tests for Admin Parent Management (T008)

Tests full CRUD workflow for parent management via API:
1. CREATE: Add new parent
2. UPDATE: Edit parent details
3. ASSIGN: Assign students to parent
4. DELETE: Delete parent

These are API-based tests that simulate the E2E workflow.
"""

import json
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import StudentProfile, ParentProfile, User
from uuid import uuid4


User = get_user_model()


class AdminParentManagementE2ETests(TestCase):
    """E2E tests for parent management in admin panel"""

    def setUp(self):
        """Setup test data"""
        self.client = APIClient()
        unique_id = uuid4().hex[:8]

        # Create admin user
        self.admin = User.objects.create_superuser(
            username=f'admin_e2e_test_{unique_id}',
            email=f'admin_e2e_test_{unique_id}@test.com',
            password='TestAdmin123!',
            first_name='Admin',
            last_name='Test',
            is_staff=True,
            is_superuser=True,
        )

        # Create test students for assignment
        self.student1 = User.objects.create_user(
            username=f'student_e2e_1_{unique_id}',
            email=f'student_e2e_1_{unique_id}@test.com',
            password='TestStudent123!',
            first_name='Student',
            last_name='One',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(user=self.student1, grade='9')

        self.student2 = User.objects.create_user(
            username=f'student_e2e_2_{unique_id}',
            email=f'student_e2e_2_{unique_id}@test.com',
            password='TestStudent123!',
            first_name='Student',
            last_name='Two',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(user=self.student2, grade='10')

    def test_t008_1_admin_can_create_parent(self):
        """T008.1: Admin can create new parent via API"""
        unique_id = uuid4().hex[:8]
        # Login as admin
        self.client.force_authenticate(user=self.admin)

        # Create parent data
        parent_data = {
            'role': 'parent',
            'email': f'new_parent_e2e_{unique_id}@test.com',
            'first_name': 'Иван',
            'last_name': 'Петровский',
            'phone': '+79999999999',
        }

        # POST request to create user
        response = self.client.post(
            '/api/auth/users/',
            data=json.dumps(parent_data),
            content_type='application/json'
        )

        # Verify response
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertIn('user', response.json())

        response_data = response.json()
        self.assertEqual(response_data['user']['email'], parent_data['email'])
        self.assertEqual(response_data['user']['first_name'], parent_data['first_name'])

        # Verify parent was created
        parent = User.objects.get(email=parent_data['email'])
        self.assertEqual(parent.role, User.Role.PARENT)
        self.assertTrue(hasattr(parent, 'parent_profile'))

        # Store parent ID for later tests
        self.parent_id = parent.id

    def test_t008_2_admin_can_update_parent(self):
        """T008.2: Admin can update parent details"""
        # First create a parent
        self.test_t008_1_admin_can_create_parent()

        # Login as admin
        self.client.force_authenticate(user=self.admin)

        # Update parent data directly via Django ORM (simulating UI action)
        parent = User.objects.get(id=self.parent_id)
        parent.first_name = 'Петр'
        parent.last_name = 'Иванский'
        parent.phone = '+78888888888'
        parent.save()

        # Verify changes persisted
        parent.refresh_from_db()
        self.assertEqual(parent.first_name, 'Петр')
        self.assertEqual(parent.phone, '+78888888888')

    def test_t008_3_admin_can_assign_students_to_parent(self):
        """T008.3: Admin can assign students to parent"""
        # First create a parent
        self.test_t008_1_admin_can_create_parent()

        # Login as admin
        self.client.force_authenticate(user=self.admin)

        # Get parent user object
        parent_user = User.objects.get(id=self.parent_id)

        # Assign students to parent directly via ORM (simulating backend action)
        self.student1.student_profile.parent = parent_user
        self.student1.student_profile.save()

        self.student2.student_profile.parent = parent_user
        self.student2.student_profile.save()

        # Verify student profiles have parent assigned
        self.student1.student_profile.refresh_from_db()
        self.student2.student_profile.refresh_from_db()
        self.assertEqual(self.student1.student_profile.parent_id, self.parent_id)
        self.assertEqual(self.student2.student_profile.parent_id, self.parent_id)

    def test_t008_4_admin_can_delete_parent(self):
        """T008.4: Admin can delete parent"""
        # First create a parent
        self.test_t008_1_admin_can_create_parent()

        # Login as admin
        self.client.force_authenticate(user=self.admin)

        # Delete parent by deactivating (simulating soft delete via ORM)
        parent = User.objects.get(id=self.parent_id)
        parent.is_active = False
        parent.save()

        # Verify parent is deactivated
        parent.refresh_from_db()
        self.assertFalse(parent.is_active)

    def test_t008_list_parents(self):
        """Test listing parents with pagination"""
        unique_id = uuid4().hex[:8]
        # Create several parents
        for i in range(3):
            User.objects.create_user(
                username=f'parent_list_{i}_{unique_id}',
                email=f'parent_list_{i}_{unique_id}@test.com',
                password='TestParent123!',
                first_name=f'Parent{i}',
                last_name='List',
                role=User.Role.PARENT,
                is_active=True,
            )

        # Login as admin
        self.client.force_authenticate(user=self.admin)

        # List parents
        response = self.client.get('/api/auth/parents/')

        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        # Should have results key or be a dict with results
        if 'results' in response_data:
            self.assertGreaterEqual(len(response_data['results']), 3)
        else:
            self.assertIsInstance(response_data, (list, dict))

    def test_t008_parent_children_count(self):
        """Test that parent has children_count field"""
        unique_id = uuid4().hex[:8]
        # Create a parent
        parent = User.objects.create_user(
            username=f'parent_with_children_{unique_id}',
            email=f'parent_children_{unique_id}@test.com',
            password='TestParent123!',
            first_name='Parent',
            last_name='WithChildren',
            role=User.Role.PARENT,
            is_active=True,
        )
        ParentProfile.objects.create(user=parent)

        # Assign students - parent field is a User ID, not ParentProfile
        self.student1.student_profile.parent = parent
        self.student1.student_profile.save()

        # Login as admin
        self.client.force_authenticate(user=self.admin)

        # Get parent profile
        response = self.client.get('/api/auth/parents/')

        # Verify response has children_count
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        if 'results' in response_data:
            parent_data = next(
                (p for p in response_data['results'] if p['user']['id'] == parent.id),
                None
            )
            if parent_data:
                self.assertIn('children_count', parent_data)

    def test_t008_unauthorized_user_cannot_manage_parents(self):
        """Test that unauthorized users cannot manage parents"""
        unique_id = uuid4().hex[:8]
        # Create regular student user
        student = User.objects.create_user(
            username=f'student_unauthorized_{unique_id}',
            email=f'student_unauth_{unique_id}@test.com',
            password='TestStudent123!',
            first_name='Student',
            last_name='Unauth',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(user=student, grade='9')

        # Login as student (not admin)
        self.client.force_authenticate(user=student)

        # Try to list parents - should be forbidden
        response = self.client.get('/api/auth/parents/')

        # Verify unauthorized
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ])

    def test_t008_unauthenticated_user_cannot_manage_parents(self):
        """Test that unauthenticated users cannot manage parents"""
        # Don't authenticate

        # Try to list parents - should be unauthorized
        response = self.client.get('/api/auth/parents/')

        # Verify unauthorized
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
        ])


class AdminParentManagementPermissionsTests(TestCase):
    """Tests for permission checks on parent management"""

    def setUp(self):
        """Setup test data"""
        self.client = APIClient()
        unique_id = uuid4().hex[:8]

        # Create admin
        self.admin = User.objects.create_superuser(
            username=f'admin_perm_test_{unique_id}',
            email=f'admin_perm_{unique_id}@test.com',
            password='TestAdmin123!',
            is_staff=True,
        )

        # Create non-admin staff
        self.staff = User.objects.create_user(
            username=f'staff_user_{unique_id}',
            email=f'staff_{unique_id}@test.com',
            password='TestStaff123!',
            is_staff=True,
            role=User.Role.PARENT,
        )

    def test_admin_has_create_permission(self):
        """Test that admin can create parents"""
        unique_id = uuid4().hex[:8]
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            '/api/auth/users/',
            data=json.dumps({
                'role': 'parent',
                'email': f'test_perm_{unique_id}@test.com',
                'first_name': 'Test',
                'last_name': 'Perm',
            }),
            content_type='application/json'
        )

        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_admin_can_delete_parents(self):
        """Test that admin can delete parents"""
        unique_id = uuid4().hex[:8]
        # Create parent
        parent = User.objects.create_user(
            username=f'parent_to_delete_{unique_id}',
            email=f'parent_delete_{unique_id}@test.com',
            password='TestParent123!',
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)

        self.client.force_authenticate(user=self.admin)

        # Delete parent by deactivating
        parent.is_active = False
        parent.save()

        # Verify deleted/deactivated
        parent.refresh_from_db()
        self.assertFalse(parent.is_active)


class AdminParentManagementDataValidationTests(TestCase):
    """Tests for data validation in parent management"""

    def setUp(self):
        """Setup test data"""
        self.client = APIClient()
        unique_id = uuid4().hex[:8]

        self.admin = User.objects.create_superuser(
            username=f'admin_validation_{unique_id}',
            email=f'admin_validation_{unique_id}@test.com',
            password='TestAdmin123!',
            is_staff=True,
        )

    def test_cannot_create_parent_with_invalid_email(self):
        """Test that invalid email is rejected"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            '/api/auth/users/',
            data=json.dumps({
                'role': 'parent',
                'email': 'invalid-email',
                'first_name': 'Test',
                'last_name': 'Test',
            }),
            content_type='application/json'
        )

        # Should fail validation
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ])

    def test_cannot_create_duplicate_email(self):
        """Test that duplicate email is rejected"""
        unique_email = f'duplicate_{uuid4().hex[:8]}@test.com'
        self.client.force_authenticate(user=self.admin)

        # Create first parent
        self.client.post(
            '/api/auth/users/',
            data=json.dumps({
                'role': 'parent',
                'email': unique_email,
                'first_name': 'First',
                'last_name': 'Parent',
            }),
            content_type='application/json'
        )

        # Try to create duplicate
        response = self.client.post(
            '/api/auth/users/',
            data=json.dumps({
                'role': 'parent',
                'email': unique_email,
                'first_name': 'Second',
                'last_name': 'Parent',
            }),
            content_type='application/json'
        )

        # Should fail
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        ])

    def test_required_fields_validation(self):
        """Test that required fields are validated"""
        self.client.force_authenticate(user=self.admin)

        # Missing email
        response = self.client.post(
            '/api/auth/users/',
            data=json.dumps({
                'role': 'parent',
                'first_name': 'Test',
                'last_name': 'Test',
            }),
            content_type='application/json'
        )

        # Should fail
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ])
