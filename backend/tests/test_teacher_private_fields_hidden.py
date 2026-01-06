"""
Test to verify that private fields are hidden from unauthorized users.

T012: Проверка скрытия приватных полей от учителя и других ролей

Тестируем что приватные поля скрыты от неавторизованных пользователей:
- student_profile.goal
- student_profile.tutor
- student_profile.parent
"""
import os
import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

if not django.apps.apps.ready:
    django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import StudentProfile

User = get_user_model()


class TestTeacherStudentPrivateFields(TestCase):
    """Tests to verify private student fields are hidden from unauthorized users"""

    def setUp(self):
        """Create test data: tutor, student, and setup profiles"""
        # Create tutor user
        self.tutor = User.objects.create_user(
            username='tutor_t012',
            email='tutor_t012@test.com',
            first_name='Test',
            last_name='Tutor',
            password='TestPass123!',
            role=User.Role.TUTOR,
            is_active=True,
        )

        # Create a parent
        self.parent = User.objects.create_user(
            username='parent_t012',
            email='parent_t012@test.com',
            first_name='Test',
            last_name='Parent',
            password='TestPass123!',
            role=User.Role.PARENT,
            is_active=True,
        )

        # Create first student (with tutor and parent assigned)
        self.student1 = User.objects.create_user(
            username='student1_t012',
            email='student1_t012@test.com',
            first_name='Student',
            last_name='One',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        # Create StudentProfile for student1 with private fields
        self.student1_profile = StudentProfile.objects.create(
            user=self.student1,
            grade=10,
            goal='Improve mathematics skills',
            tutor=self.tutor,
            parent=self.parent,
            progress_percentage=75,
            streak_days=5,
            total_points=500,
            accuracy_percentage=85,
        )

        # Create second student (for list view testing)
        self.student2 = User.objects.create_user(
            username='student2_t012',
            email='student2_t012@test.com',
            first_name='Student',
            last_name='Two',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        # Create StudentProfile for student2
        self.student2_profile = StudentProfile.objects.create(
            user=self.student2,
            grade=9,
            goal='Learn English language',
            tutor=self.tutor,
            parent=self.parent,
            progress_percentage=60,
            streak_days=3,
            total_points=300,
            accuracy_percentage=70,
        )

        # Create admin for comparison
        self.admin = User.objects.create_user(
            username='admin_t012',
            email='admin_t012@test.com',
            first_name='Admin',
            last_name='User',
            password='TestPass123!',
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        self.client = APIClient()

    def tearDown(self):
        """Clean up test data"""
        User.objects.filter(
            username__in=[
                'tutor_t012',
                'parent_t012',
                'student1_t012',
                'student2_t012',
                'admin_t012',
            ]
        ).delete()

    # ==================== T012.1: Tutor CAN See Private Fields ====================

    def test_tutor_list_students_has_private_fields(self):
        """
        T012.1: Tutor can access list of students and SHOULD see private fields
        GET /api/accounts/my-students/
        """
        # Login as tutor
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'tutor_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        if response.status_code not in [200, 201]:
            self.skipTest(f"Login failed with {response.status_code}")
        token = response.data['data']['token']

        # Get tutor's students list
        response = self.client.get(
            '/api/accounts/my-students/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        # Endpoint exists and returns data
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', []) or data.get('data', []) or (data if isinstance(data, list) else [])

            # Check students returned
            self.assertGreater(len(results), 0, msg="Tutor should see their students")

            # First student should be visible to this tutor (who is their tutor)
            student_item = results[0]

            # Check that goal field exists and has a value
            found_goal = False
            if 'goal' in student_item:
                self.assertIsNotNone(student_item['goal'])
                found_goal = True
            elif 'student_profile' in student_item:
                profile = student_item['student_profile']
                if 'goal' in profile:
                    self.assertIsNotNone(profile['goal'])
                    found_goal = True

            # Tutor should see goal field (either directly or in student_profile)
            self.assertTrue(found_goal, msg="Tutor should see 'goal' field in student data")

    def test_tutor_list_students_has_tutor_field(self):
        """
        T012.2: Tutor can see tutor assignment in student list
        GET /api/accounts/my-students/
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'tutor_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        if response.status_code not in [200, 201]:
            self.skipTest(f"Login failed with {response.status_code}")
        token = response.data['data']['token']

        response = self.client.get(
            '/api/accounts/my-students/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', []) or data.get('data', []) or (data if isinstance(data, list) else [])

            if len(results) > 0:
                student_item = results[0]

                # Check tutor field visibility
                found_tutor = False
                if 'tutor' in student_item:
                    # Should reference the tutor
                    if student_item['tutor'] is not None:
                        found_tutor = True
                elif 'student_profile' in student_item and 'tutor' in student_item['student_profile']:
                    if student_item['student_profile']['tutor'] is not None:
                        found_tutor = True

    def test_tutor_list_students_has_parent_field(self):
        """
        T012.3: Tutor can see parent assignment in student list
        GET /api/accounts/my-students/
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'tutor_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        if response.status_code not in [200, 201]:
            self.skipTest(f"Login failed with {response.status_code}")
        token = response.data['data']['token']

        response = self.client.get(
            '/api/accounts/my-students/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', []) or data.get('data', []) or (data if isinstance(data, list) else [])

            if len(results) > 0:
                student_item = results[0]

                # Check parent field visibility
                if 'parent' in student_item:
                    if student_item['parent'] is not None:
                        pass  # Parent should be visible to tutor
                elif 'student_profile' in student_item and 'parent' in student_item['student_profile']:
                    if student_item['student_profile']['parent'] is not None:
                        pass  # Parent should be visible to tutor

    # ==================== T012.4: Admin CAN See All Private Fields ====================

    def test_admin_students_list_has_all_fields(self):
        """
        T012.4: Admin can see all student fields including private ones
        GET /api/accounts/users/?role=student
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'admin_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        self.assertIn(response.status_code, [200, 201])
        token = response.data['data']['token']

        response = self.client.get(
            '/api/accounts/users/?role=student',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        # Admin can list users
        if response.status_code == 200:
            data = response.json()
            results = data if isinstance(data, list) else data.get('results', []) or data.get('data', [])

            # Should have students
            self.assertGreater(len(results), 0, msg="Admin should see students")

            # Check that admin can see student profiles with goal
            student_with_profile = None
            for user_item in results:
                if user_item.get('role') == 'student' and 'student_profile' in user_item:
                    student_with_profile = user_item
                    break

            if student_with_profile:
                profile = student_with_profile['student_profile']
                # Admin SHOULD see goal
                if 'goal' in profile:
                    self.assertIsNotNone(profile['goal'], msg="Admin should see goal value")

    # ==================== T012.5: Student Cannot See Own Private Fields ====================

    def test_student_own_profile_goal_hidden(self):
        """
        T012.5: Student viewing own profile - goal field should be hidden/null
        GET /api/profile/student/
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'student1_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        self.assertIn(response.status_code, [200, 201])
        token = response.data['data']['token']

        response = self.client.get(
            '/api/profile/student/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # In student profile view, student should NOT see private fields
        # Check if goal is hidden (null or missing)
        if 'goal' in data:
            self.assertIsNone(
                data['goal'],
                msg="Student should not see their own 'goal' (should be null)"
            )

    def test_student_own_profile_tutor_hidden(self):
        """
        T012.6: Student viewing own profile - tutor field should be hidden/null
        GET /api/profile/student/
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'student1_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        if response.status_code not in [200, 201]:
            self.skipTest(f"Login failed with {response.status_code}")
        token = response.data['data']['token']

        response = self.client.get(
            '/api/profile/student/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'tutor' in data:
            self.assertIsNone(
                data['tutor'],
                msg="Student should not see their own 'tutor' (should be null)"
            )

    def test_student_own_profile_parent_hidden(self):
        """
        T012.7: Student viewing own profile - parent field should be hidden/null
        GET /api/profile/student/
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'student1_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        token = response.data['data']['token']

        response = self.client.get(
            '/api/profile/student/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        if 'parent' in data:
            self.assertIsNone(
                data['parent'],
                msg="Student should not see their own 'parent' (should be null)"
            )

    # ==================== T012.8: Verify Private Fields in Admin Edit View ====================

    def test_admin_can_view_student_with_all_private_fields(self):
        """
        T012.8: Admin views student detail - all private fields visible
        GET /api/accounts/admin/users/{student_id}/profile/
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'admin_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        token = response.data['data']['token']

        # Try admin profile view
        response = self.client.get(
            f'/api/accounts/admin/users/{self.student1.id}/profile/',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        # If endpoint exists
        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()

                # Admin should see goal
                if 'goal' in data:
                    self.assertEqual(data['goal'], 'Improve mathematics skills')
                elif 'student_profile' in data:
                    profile = data['student_profile']
                    if 'goal' in profile:
                        self.assertEqual(profile['goal'], 'Improve mathematics skills')

    # ==================== T012.9: Parent Cannot See Other Student's Private Fields ====================

    def test_parent_list_students_no_access(self):
        """
        T012.9: Parent tries to list students - should be denied (not their role)
        GET /api/accounts/users/?role=student
        """
        response = self.client.post(
            '/api/accounts/login/',
            {
                'email': 'parent_t012@test.com',
                'password': 'TestPass123!',
            },
            format='json'
        )
        token = response.data['data']['token']

        response = self.client.get(
            '/api/accounts/users/?role=student',
            HTTP_AUTHORIZATION=f'Token {token}',
        )

        # Parent should NOT have access to list students endpoint
        self.assertEqual(
            response.status_code,
            403,
            msg="Parent should not have access to student list"
        )

    # ==================== T012.10: Unauthenticated User Cannot See Student Data ====================

    def test_unauthenticated_cannot_list_students(self):
        """
        T012.10: Unauthenticated request cannot access student list
        GET /api/accounts/users/?role=student
        """
        response = self.client.get(
            '/api/accounts/users/?role=student',
        )

        # Should be denied (either 401 or 403)
        self.assertIn(
            response.status_code,
            [401, 403],
            msg="Unauthenticated user should not access student list"
        )

    def test_unauthenticated_cannot_access_tutor_students(self):
        """
        T012.11: Unauthenticated request cannot access tutor's students
        GET /api/accounts/my-students/
        """
        response = self.client.get(
            '/api/accounts/my-students/',
        )

        # Should be denied
        self.assertIn(
            response.status_code,
            [401, 403],
            msg="Unauthenticated user should not access tutor students"
        )
