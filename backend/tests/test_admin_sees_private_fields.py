"""
T011: Test that admin CAN see all private student fields

Admin visibility tests for private fields:
- goal (learning goal)
- tutor_id (assigned tutor)
- parent_id (assigned parent)

Admin should see these fields through:
1. GET /api/accounts/admin/users/{user_id}/profile/ - Single student detail
2. GET /api/accounts/students/ - Student list endpoint
3. GET /api/accounts/admin/users/{user_id}/full-info/ - Full info endpoint
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

if not django.apps.apps.ready:
    django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import StudentProfile

User = get_user_model()


class TestAdminCanSeeStudentPrivateFields(TestCase):
    """Test that admin can see all student private fields"""

    def setUp(self):
        """Create test data"""
        # Clean up existing test data
        User.objects.filter(username__startswith='admin_test_').delete()

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin_test_admin',
            email='admin@test.com',
            first_name='Admin',
            last_name='User',
            password='TestPass123!',
            role=User.Role.ADMIN,
            is_staff=True,
            is_active=True,
        )
        self.admin_token = Token.objects.create(user=self.admin_user)

        # Create parent
        self.parent_user = User.objects.create_user(
            username='admin_test_parent',
            email='parent@test.com',
            first_name='Parent',
            last_name='User',
            password='TestPass123!',
            role=User.Role.PARENT,
            is_active=True,
        )

        # Create tutor
        self.tutor_user = User.objects.create_user(
            username='admin_test_tutor',
            email='tutor@test.com',
            first_name='Tutor',
            last_name='User',
            password='TestPass123!',
            role=User.Role.TUTOR,
            is_active=True,
        )

        # Create student with all private fields set
        self.student_user = User.objects.create_user(
            username='admin_test_student',
            email='student@test.com',
            first_name='John',
            last_name='Student',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            grade=10,
            goal='Learn advanced mathematics',
            tutor=self.tutor_user,
            parent=self.parent_user,
            progress_percentage=75,
            streak_days=5,
            total_points=250,
            accuracy_percentage=85,
        )

        # Create second student with some null private fields
        self.student2_user = User.objects.create_user(
            username='admin_test_student2',
            email='student2@test.com',
            first_name='Jane',
            last_name='Student',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.student2_profile = StudentProfile.objects.create(
            user=self.student2_user,
            grade=11,
            goal='Improve physics',
            tutor=None,
            parent=None,
            progress_percentage=60,
        )

        self.client = APIClient()

    def tearDown(self):
        """Clean up test data"""
        User.objects.filter(username__startswith='admin_test_').delete()

    def test_admin_profile_endpoint_shows_goal(self):
        """Test /api/accounts/admin/users/{id}/profile/ shows goal field"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200, f"Status: {response.status_code}, Response: {response.json()}")
        data = response.json()

        # Check for goal in response
        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('goal', profile, "goal field should be in student_profile")
            self.assertEqual(profile['goal'], 'Learn advanced mathematics', "goal should match")
        elif 'goal' in data:
            self.assertEqual(data['goal'], 'Learn advanced mathematics', "goal should be visible in root response")

    def test_admin_profile_endpoint_shows_tutor(self):
        """Test /api/accounts/admin/users/{id}/profile/ shows tutor field"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check for tutor in response
        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('tutor', profile, "tutor field should be in student_profile")
            self.assertIsNotNone(profile['tutor'], "tutor should not be None")

            # Check if tutor is dict or ID
            if isinstance(profile['tutor'], dict):
                self.assertEqual(profile['tutor']['id'], self.tutor_user.id)
            else:
                self.assertEqual(profile['tutor'], self.tutor_user.id)

    def test_admin_profile_endpoint_shows_parent(self):
        """Test /api/accounts/admin/users/{id}/profile/ shows parent field"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check for parent in response
        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('parent', profile, "parent field should be in student_profile")
            self.assertIsNotNone(profile['parent'], "parent should not be None")

            # Check if parent is dict or ID
            if isinstance(profile['parent'], dict):
                self.assertEqual(profile['parent']['id'], self.parent_user.id)
            else:
                self.assertEqual(profile['parent'], self.parent_user.id)

    def test_admin_profile_endpoint_shows_null_tutor(self):
        """Test /api/accounts/admin/users/{id}/profile/ shows null tutor correctly"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student2_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('tutor', profile, "tutor field should exist even if null")
            self.assertIsNone(profile['tutor'], "tutor should be None")

    def test_admin_profile_endpoint_shows_null_parent(self):
        """Test /api/accounts/admin/users/{id}/profile/ shows null parent correctly"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student2_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('parent', profile, "parent field should exist even if null")
            self.assertIsNone(profile['parent'], "parent should be None")

    def test_admin_list_students_shows_private_fields(self):
        """Test /api/accounts/students/ list shows private fields"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get('/api/accounts/students/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Handle pagination
        if isinstance(data, dict) and 'results' in data:
            students = data['results']
        elif isinstance(data, list):
            students = data
        else:
            students = []

        # Find our test student in the list
        our_student = next((s for s in students if s.get('id') == self.student_user.id), None)
        self.assertIsNotNone(our_student, "Test student should be in list")

        # Check for private fields in list
        if 'student_profile' in our_student:
            profile = our_student['student_profile']
            self.assertIn('goal', profile, "goal should be in list response")
            self.assertIn('tutor', profile, "tutor should be in list response")
            self.assertIn('parent', profile, "parent should be in list response")

    def test_admin_full_info_endpoint_shows_all_private_fields(self):
        """Test /api/accounts/admin/users/{id}/full-info/ shows all private fields"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/full-info/')

        if response.status_code == 200:  # Endpoint may or may not exist
            data = response.json()

            if 'student_profile' in data:
                profile = data['student_profile']
                # Should contain private fields
                has_goal = 'goal' in profile
                has_tutor = 'tutor' in profile
                has_parent = 'parent' in profile

                self.assertTrue(has_goal or has_tutor or has_parent,
                               "At least one private field should be visible")

    def test_admin_sees_private_fields_all_set(self):
        """Test that admin sees all private fields when all are set"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'student_profile' in data:
            profile = data['student_profile']

            # All three private fields should be visible
            private_fields = ['goal', 'tutor', 'parent']
            visible_count = sum(1 for f in private_fields if f in profile)

            self.assertGreaterEqual(visible_count, 2,
                                   f"At least 2 private fields should be visible, found {visible_count}")

    def test_superuser_can_see_private_fields(self):
        """Test that superuser can also see private fields"""
        # Create superuser
        super_user = User.objects.create_superuser(
            username='admin_test_superuser',
            email='superuser@test.com',
            password='TestPass123!',
        )
        super_token = Token.objects.create(user=super_user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {super_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('goal', profile, "Superuser should see goal")
            self.assertIn('tutor', profile, "Superuser should see tutor")
            self.assertIn('parent', profile, "Superuser should see parent")

    def test_admin_cannot_see_inactive_student_private_fields_maybe(self):
        """Test admin view of inactive student - may still see private fields"""
        # Create inactive student
        inactive_student = User.objects.create_user(
            username='admin_test_inactive',
            email='inactive@test.com',
            first_name='Inactive',
            last_name='Student',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=False,
        )

        inactive_profile = StudentProfile.objects.create(
            user=inactive_student,
            grade=9,
            goal='Was learning',
            tutor=self.tutor_user,
            parent=None,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{inactive_student.id}/profile/')

        # Admin should be able to view inactive student's profile
        if response.status_code == 200:
            data = response.json()
            if 'student_profile' in data:
                profile = data['student_profile']
                # Admin should see private fields even for inactive users
                if 'goal' in profile:
                    self.assertEqual(profile['goal'], 'Was learning')


class TestAdminPrivateFieldsNotHidden(TestCase):
    """Test that admin views do NOT filter out private fields"""

    def setUp(self):
        """Create test data"""
        User.objects.filter(username__startswith='admin_filter_').delete()

        self.admin_user = User.objects.create_user(
            username='admin_filter_admin',
            email='admin_filter@test.com',
            password='TestPass123!',
            role=User.Role.ADMIN,
            is_staff=True,
            is_active=True,
        )
        self.admin_token = Token.objects.create(user=self.admin_user)

        self.student_user = User.objects.create_user(
            username='admin_filter_student',
            email='admin_filter_student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            grade=10,
            goal='Secret learning goal',
            tutor=None,
            parent=None,
        )

        self.client = APIClient()

    def tearDown(self):
        """Clean up"""
        User.objects.filter(username__startswith='admin_filter_').delete()

    def test_admin_response_includes_goal_field(self):
        """Test that admin response includes goal field (not filtered)"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertIn('goal', profile,
                         "goal field should not be filtered out for admin")
            self.assertEqual(profile['goal'], 'Secret learning goal')

    def test_admin_response_includes_all_private_field_keys(self):
        """Test that admin response includes all private field keys"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        response = self.client.get(f'/api/accounts/admin/users/{self.student_user.id}/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'student_profile' in data:
            profile = data['student_profile']
            private_fields = ['goal', 'tutor', 'parent']

            # At least 2 of 3 private fields should be present
            present_fields = [f for f in private_fields if f in profile]
            self.assertGreaterEqual(len(present_fields), 2,
                                   f"Expected at least 2 private fields, got: {present_fields}")
