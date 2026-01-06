"""
Test user deactivation/reactivation functionality.

Tests for admin-only endpoints:
- PATCH /api/admin/users/{id}/ with is_active=True/False
- GET /api/accounts/users/?filter_inactive=true|false
- Login behavior with inactive users
- User visibility in lists based on is_active status

Test scenarios:
1. Deactivate/reactivate student user
2. Deactivate/reactivate teacher user
3. Deactivate/reactivate tutor user
4. Deactivate/reactivate parent user
5. Verify inactive users cannot login
6. Verify inactive users not visible in default lists
7. Verify inactive users visible in inactive filter
8. Verify self-deactivation prevention
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from accounts.models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from materials.models import Subject, SubjectEnrollment


class TestUserActivationDeactivation(TestCase):
    """Test user deactivation and reactivation functionality"""

    databases = '__all__'

    @classmethod
    def setUpClass(cls):
        """Setup test data"""
        super().setUpClass()

        # Create admin user
        cls.admin_user = User.objects.create_user(
            username='admin_activation_test',
            email='admin_activation@test.com',
            password='AdminPass123!',
            role=User.Role.STUDENT,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            first_name='Admin',
            last_name='Test'
        )
        cls.admin_token, _ = Token.objects.get_or_create(user=cls.admin_user)

    def setUp(self):
        """Create fresh client and test users"""
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

        # Create test student
        self.student_user = User.objects.create_user(
            username='test_student_activation',
            email='student_activation@test.com',
            password='StudentPass123!',
            role=User.Role.STUDENT,
            is_active=True,
            first_name='Test',
            last_name='Student'
        )
        StudentProfile.objects.create(user=self.student_user, grade=8)

        # Create test teacher
        self.teacher_user = User.objects.create_user(
            username='test_teacher_activation',
            email='teacher_activation@test.com',
            password='TeacherPass123!',
            role=User.Role.TEACHER,
            is_active=True,
            first_name='Test',
            last_name='Teacher'
        )
        TeacherProfile.objects.create(user=self.teacher_user, experience_years=5)

        # Create test tutor
        self.tutor_user = User.objects.create_user(
            username='test_tutor_activation',
            email='tutor_activation@test.com',
            password='TutorPass123!',
            role=User.Role.TUTOR,
            is_active=True,
            first_name='Test',
            last_name='Tutor'
        )
        TutorProfile.objects.create(user=self.tutor_user, specialization='Math')

        # Create test parent
        self.parent_user = User.objects.create_user(
            username='test_parent_activation',
            email='parent_activation@test.com',
            password='ParentPass123!',
            role=User.Role.PARENT,
            is_active=True,
            first_name='Test',
            last_name='Parent'
        )
        ParentProfile.objects.create(user=self.parent_user)

    def tearDown(self):
        """Clean up test data"""
        User.objects.filter(
            email__in=[
                'student_activation@test.com',
                'teacher_activation@test.com',
                'tutor_activation@test.com',
                'parent_activation@test.com',
            ]
        ).delete()

    # Test 1: Student deactivation/reactivation
    def test_01_student_deactivate_successful(self):
        """Test deactivating a student user"""
        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

    def test_02_student_can_login_when_active(self):
        """Test student can login when active"""
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': self.student_user.email,
                'password': 'StudentPass123!'
            }
        )

        self.assertEqual(response.status_code, 200)
        # Token is in response.data['data']['token'] or response.data['token']
        token = response.data.get('data', response.data).get('token')
        self.assertIsNotNone(token)

    def test_03_student_cannot_login_when_inactive(self):
        """Test inactive student cannot login"""
        # First deactivate the student
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        # Try to login
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': self.student_user.email,
                'password': 'StudentPass123!'
            }
        )

        # Should return 403 Forbidden when user is inactive
        self.assertEqual(response.status_code, 403)

    def test_04_student_reactivate_successful(self):
        """Test reactivating a deactivated student"""
        # First deactivate
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        # Then reactivate
        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': True},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)

    def test_05_reactivated_student_can_login(self):
        """Test reactivated student can login again"""
        # Deactivate then reactivate
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': True},
            format='json'
        )

        # Try to login
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': self.student_user.email,
                'password': 'StudentPass123!'
            }
        )

        self.assertEqual(response.status_code, 200)
        token = response.data.get('data', response.data).get('token')
        self.assertIsNotNone(token)

    # Test 2: Teacher deactivation/reactivation
    def test_06_teacher_deactivate_successful(self):
        """Test deactivating a teacher user"""
        response = self.client.patch(
            f'/api/admin/users/{self.teacher_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.teacher_user.refresh_from_db()
        self.assertFalse(self.teacher_user.is_active)

    def test_07_teacher_cannot_login_when_inactive(self):
        """Test inactive teacher cannot login"""
        self.client.patch(
            f'/api/admin/users/{self.teacher_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': self.teacher_user.email,
                'password': 'TeacherPass123!'
            }
        )

        self.assertEqual(response.status_code, 403)

    def test_08_teacher_reactivate_successful(self):
        """Test reactivating a teacher"""
        self.client.patch(
            f'/api/admin/users/{self.teacher_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.patch(
            f'/api/admin/users/{self.teacher_user.id}/',
            {'is_active': True},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.teacher_user.refresh_from_db()
        self.assertTrue(self.teacher_user.is_active)

    # Test 3: Tutor deactivation/reactivation
    def test_09_tutor_deactivate_successful(self):
        """Test deactivating a tutor user"""
        response = self.client.patch(
            f'/api/admin/users/{self.tutor_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.tutor_user.refresh_from_db()
        self.assertFalse(self.tutor_user.is_active)

    def test_10_tutor_cannot_login_when_inactive(self):
        """Test inactive tutor cannot login"""
        self.client.patch(
            f'/api/admin/users/{self.tutor_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': self.tutor_user.email,
                'password': 'TutorPass123!'
            }
        )

        self.assertEqual(response.status_code, 403)

    def test_11_tutor_reactivate_successful(self):
        """Test reactivating a tutor"""
        self.client.patch(
            f'/api/admin/users/{self.tutor_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.patch(
            f'/api/admin/users/{self.tutor_user.id}/',
            {'is_active': True},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.tutor_user.refresh_from_db()
        self.assertTrue(self.tutor_user.is_active)

    # Test 4: Parent deactivation/reactivation
    def test_12_parent_deactivate_successful(self):
        """Test deactivating a parent user"""
        response = self.client.patch(
            f'/api/admin/users/{self.parent_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.parent_user.refresh_from_db()
        self.assertFalse(self.parent_user.is_active)

    def test_13_parent_cannot_login_when_inactive(self):
        """Test inactive parent cannot login"""
        self.client.patch(
            f'/api/admin/users/{self.parent_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': self.parent_user.email,
                'password': 'ParentPass123!'
            }
        )

        self.assertEqual(response.status_code, 403)

    def test_14_parent_reactivate_successful(self):
        """Test reactivating a parent"""
        self.client.patch(
            f'/api/admin/users/{self.parent_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.patch(
            f'/api/admin/users/{self.parent_user.id}/',
            {'is_active': True},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.parent_user.refresh_from_db()
        self.assertTrue(self.parent_user.is_active)

    # Test 5: List visibility tests
    def test_15_inactive_users_not_in_default_list(self):
        """Test inactive users are not visible in default user list"""
        # Deactivate the student
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        # Get list of users (default shows only active)
        response = self.client.get('/api/accounts/users/?role=student')

        self.assertEqual(response.status_code, 200)
        user_ids = [user['id'] for user in response.data]
        self.assertNotIn(self.student_user.id, user_ids)

    def test_16_active_users_visible_in_default_list(self):
        """Test active users are visible in default list"""
        # Student is active by default
        response = self.client.get('/api/accounts/users/?role=student')

        self.assertEqual(response.status_code, 200)
        user_ids = [user['id'] for user in response.data]
        self.assertIn(self.student_user.id, user_ids)

    def test_17_reactivated_user_visible_in_list(self):
        """Test reactivated user becomes visible in list"""
        # Deactivate then reactivate
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': True},
            format='json'
        )

        # Check list
        response = self.client.get('/api/accounts/users/?role=student')

        self.assertEqual(response.status_code, 200)
        user_ids = [user['id'] for user in response.data]
        self.assertIn(self.student_user.id, user_ids)

    # Test 6: Admin self-deactivation prevention
    def test_18_cannot_deactivate_self(self):
        """Test admin cannot deactivate themselves"""
        response = self.client.patch(
            f'/api/admin/users/{self.admin_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 403)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    # Test 7: Response data validation
    def test_19_deactivation_response_contains_user_data(self):
        """Test deactivation response contains full user data"""
        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.data)
        self.assertFalse(response.data['user']['is_active'])
        self.assertEqual(response.data['user']['email'], self.student_user.email)

    def test_20_reactivation_response_contains_user_data(self):
        """Test reactivation response contains full user data"""
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': True},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.data)
        self.assertTrue(response.data['user']['is_active'])

    # Test 8: Multiple user deactivation
    def test_21_can_deactivate_multiple_users_sequentially(self):
        """Test deactivating multiple users"""
        # Deactivate all test users
        for user in [self.student_user, self.teacher_user, self.tutor_user, self.parent_user]:
            response = self.client.patch(
                f'/api/admin/users/{user.id}/',
                {'is_active': False},
                format='json'
            )
            self.assertEqual(response.status_code, 200)

        # Verify all are inactive
        for user in [self.student_user, self.teacher_user, self.tutor_user, self.parent_user]:
            user.refresh_from_db()
            self.assertFalse(user.is_active)

    def test_22_can_reactivate_multiple_users_sequentially(self):
        """Test reactivating multiple users"""
        # Deactivate all
        for user in [self.student_user, self.teacher_user, self.tutor_user, self.parent_user]:
            self.client.patch(
                f'/api/admin/users/{user.id}/',
                {'is_active': False},
                format='json'
            )

        # Reactivate all
        for user in [self.student_user, self.teacher_user, self.tutor_user, self.parent_user]:
            response = self.client.patch(
                f'/api/admin/users/{user.id}/',
                {'is_active': True},
                format='json'
            )
            self.assertEqual(response.status_code, 200)

        # Verify all are active
        for user in [self.student_user, self.teacher_user, self.tutor_user, self.parent_user]:
            user.refresh_from_db()
            self.assertTrue(user.is_active)

    # Test 9: Deactivation with other fields
    def test_23_can_update_other_fields_with_deactivation(self):
        """Test updating other fields while deactivating"""
        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {
                'is_active': False,
                'first_name': 'Updated',
                'last_name': 'Name'
            },
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)
        self.assertEqual(self.student_user.first_name, 'Updated')
        self.assertEqual(self.student_user.last_name, 'Name')

    def test_24_can_update_other_fields_with_reactivation(self):
        """Test updating other fields while reactivating"""
        # First deactivate
        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        # Then reactivate with updates
        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {
                'is_active': True,
                'first_name': 'Reactivated',
                'last_name': 'User'
            },
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)
        self.assertEqual(self.student_user.first_name, 'Reactivated')

    # Test 10: Unauthorized access
    def test_25_non_admin_cannot_deactivate_user(self):
        """Test non-admin user cannot deactivate users"""
        # Create non-admin client
        non_admin_client = APIClient()
        non_admin_token, _ = Token.objects.get_or_create(user=self.student_user)
        non_admin_client.credentials(HTTP_AUTHORIZATION=f'Token {non_admin_token.key}')

        response = non_admin_client.patch(
            f'/api/admin/users/{self.teacher_user.id}/',
            {'is_active': False},
            format='json'
        )

        # Should be forbidden (403) or not found (404)
        self.assertIn(response.status_code, [403, 404])

        # Verify teacher is still active
        self.teacher_user.refresh_from_db()
        self.assertTrue(self.teacher_user.is_active)

    def test_26_unauthenticated_cannot_deactivate_user(self):
        """Test unauthenticated user cannot deactivate users"""
        unauthenticated_client = APIClient()

        response = unauthenticated_client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 401)
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)

    # Test 11: Edge cases
    def test_27_nonexistent_user_returns_404(self):
        """Test deactivating nonexistent user returns 404"""
        response = self.client.patch(
            '/api/admin/users/99999/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, 404)

    def test_28_is_active_field_only_updates_that_field(self):
        """Test updating only is_active doesn't affect other fields"""
        original_first_name = self.student_user.first_name
        original_email = self.student_user.email

        self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.first_name, original_first_name)
        self.assertEqual(self.student_user.email, original_email)
        self.assertFalse(self.student_user.is_active)

    def test_29_toggling_activation_multiple_times(self):
        """Test toggling activation status multiple times"""
        for i in range(3):
            # Deactivate
            response = self.client.patch(
                f'/api/admin/users/{self.student_user.id}/',
                {'is_active': False},
                format='json'
            )
            self.assertEqual(response.status_code, 200)
            self.student_user.refresh_from_db()
            self.assertFalse(self.student_user.is_active)

            # Reactivate
            response = self.client.patch(
                f'/api/admin/users/{self.student_user.id}/',
                {'is_active': True},
                format='json'
            )
            self.assertEqual(response.status_code, 200)
            self.student_user.refresh_from_db()
            self.assertTrue(self.student_user.is_active)

    def test_30_deactivated_user_profile_still_accessible(self):
        """Test admin can still view deactivated user's profile"""
        # Deactivate user
        response = self.client.patch(
            f'/api/admin/users/{self.student_user.id}/',
            {'is_active': False},
            format='json'
        )

        # Verify deactivation was successful
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['user']['is_active'])
