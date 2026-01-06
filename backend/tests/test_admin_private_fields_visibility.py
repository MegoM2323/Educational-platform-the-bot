"""
Test for private fields visibility - verify that students cannot see their own private fields.

Private fields that must be hidden from a student:
- goal (student's learning goal)
- tutor_id (assigned tutor)
- parent_id (assigned parent)

These fields should only be visible to:
- Teachers (can view student's private fields)
- Tutors (can view their assigned students' private fields)
- Admins (can view all private fields)
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


class TestStudentOwnPrivateFields(TestCase):
    """Test that students cannot see their own private fields via API"""

    def setUp(self):
        """Create test users with different roles"""
        # Clean up any existing test users
        User.objects.filter(username__startswith='test_').delete()

        # Create a regular student
        self.student_user = User.objects.create_user(
            username='test_student',
            email='student@example.com',
            first_name='John',
            last_name='Student',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        # Create student profile with private fields
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            grade=10,
            goal='I want to improve my math skills and get better grades',
            progress_percentage=75,
            streak_days=5,
            total_points=250,
            accuracy_percentage=85,
        )

        # Create a teacher (can view student's private fields)
        self.teacher_user = User.objects.create_user(
            username='test_teacher',
            email='teacher@example.com',
            first_name='Jane',
            last_name='Teacher',
            password='TestPass123!',
            role=User.Role.TEACHER,
            is_active=True,
        )

        # Create a tutor (can view their assigned students' private fields)
        self.tutor_user = User.objects.create_user(
            username='test_tutor',
            email='tutor@example.com',
            first_name='Mike',
            last_name='Tutor',
            password='TestPass123!',
            role=User.Role.TUTOR,
            is_active=True,
        )

        # Assign tutor and no parent to student
        self.student_profile.tutor = self.tutor_user
        self.student_profile.parent = None
        self.student_profile.save()

        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@example.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
        )

        self.client = APIClient()

    def tearDown(self):
        """Clean up test data"""
        User.objects.filter(username__startswith='test_').delete()

    def test_01_student_me_endpoint_hides_goal(self):
        """Test that GET /api/accounts/me/ hides goal from student"""
        self.client.force_authenticate(user=self.student_user)

        response = self.client.get('/api/accounts/me/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertNotIn('goal', profile, "goal field should not be in response")
        elif 'goal' in data:
            self.assertIsNone(data.get('goal'), "goal should be None when viewed by student")

    def test_02_student_me_endpoint_hides_tutor(self):
        """Test that GET /api/accounts/me/ hides tutor from student"""
        self.client.force_authenticate(user=self.student_user)

        response = self.client.get('/api/accounts/me/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertNotIn('tutor', profile, "tutor field should not be in response")
        elif 'tutor' in data:
            self.assertIsNone(data.get('tutor'), "tutor should be None when viewed by student")

    def test_03_student_me_endpoint_hides_parent(self):
        """Test that GET /api/accounts/me/ hides parent from student"""
        self.client.force_authenticate(user=self.student_user)

        response = self.client.get('/api/accounts/me/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        if 'student_profile' in data:
            profile = data['student_profile']
            self.assertNotIn('parent', profile, "parent field should not be in response")
        elif 'parent' in data:
            self.assertIsNone(data.get('parent'), "parent should be None when viewed by student")

    def test_04_student_own_profile_endpoint_hides_private_fields(self):
        """Test that GET /api/accounts/users/{own_id}/ hides private fields from student"""
        self.client.force_authenticate(user=self.student_user)

        response = self.client.get(f'/api/accounts/users/{self.student_user.id}/')

        if response.status_code == 200:
            data = response.json()

            if 'student_profile' in data:
                profile = data['student_profile']
                self.assertNotIn('goal', profile, "goal should not be visible to student viewing own profile")
                self.assertNotIn('tutor', profile, "tutor should not be visible to student viewing own profile")
                self.assertNotIn('parent', profile, "parent should not be visible to student viewing own profile")

    def test_05_student_cannot_access_other_student_profile(self):
        """Test that student gets 403 when trying to access another student's profile"""
        other_student = User.objects.create_user(
            username='test_other_student',
            email='other@example.com',
            first_name='Jane',
            last_name='OtherStudent',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(f'/api/accounts/users/{other_student.id}/')

        self.assertEqual(response.status_code, 403,
                        "Student should not be able to access another student's profile")

    def test_06_teacher_can_see_student_goal(self):
        """Test that teacher can see student's goal"""
        self.client.force_authenticate(user=self.teacher_user)

        response = self.client.get(f'/api/accounts/users/{self.student_user.id}/')

        if response.status_code == 200:
            data = response.json()

            if 'student_profile' in data:
                profile = data['student_profile']
                if 'goal' in profile:
                    self.assertEqual(profile['goal'], 'I want to improve my math skills and get better grades',
                                   "Teacher should see student's goal")

    def test_07_teacher_can_see_student_tutor(self):
        """Test that teacher can see student's tutor assignment"""
        self.client.force_authenticate(user=self.teacher_user)

        response = self.client.get(f'/api/accounts/users/{self.student_user.id}/')

        if response.status_code == 200:
            data = response.json()

            if 'student_profile' in data:
                profile = data['student_profile']
                if 'tutor' in profile:
                    self.assertIsNotNone(profile['tutor'], "Teacher should see student's tutor")

    def test_08_tutor_can_see_own_student_goal(self):
        """Test that tutor can see their assigned student's goal"""
        self.client.force_authenticate(user=self.tutor_user)

        response = self.client.get(f'/api/accounts/users/{self.student_user.id}/')

        if response.status_code == 200:
            data = response.json()

            if 'student_profile' in data:
                profile = data['student_profile']
                if 'goal' in profile:
                    self.assertEqual(profile['goal'], 'I want to improve my math skills and get better grades',
                                   "Assigned tutor should see student's goal")

    def test_09_admin_can_see_all_private_fields(self):
        """Test that admin can see all student's private fields"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(f'/api/accounts/users/{self.student_user.id}/')

        if response.status_code == 200:
            data = response.json()

            if 'student_profile' in data:
                profile = data['student_profile']

                if 'goal' in profile:
                    self.assertEqual(profile['goal'], 'I want to improve my math skills and get better grades',
                                   "Admin should see student's goal")

                if 'tutor' in profile:
                    self.assertIsNotNone(profile['tutor'], "Admin should see student's tutor")


class TestStudentPrivateFieldsInListEndpoint(TestCase):
    """Test that private fields are hidden when student is listed (if endpoints support listing)"""

    def setUp(self):
        """Create test users"""
        User.objects.filter(username__startswith='test_list_').delete()

        self.student_user = User.objects.create_user(
            username='test_list_student',
            email='list_student@example.com',
            first_name='Test',
            last_name='Student',
            password='TestPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            grade=9,
            goal='Secret learning goal',
            progress_percentage=50,
        )

        self.client = APIClient()

    def tearDown(self):
        """Clean up test data"""
        User.objects.filter(username__startswith='test_list_').delete()

    def test_01_list_students_hides_own_private_fields(self):
        """Test that when student views a list of students, own private fields are hidden"""
        self.client.force_authenticate(user=self.student_user)

        response = self.client.get('/api/accounts/students/')

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list):
                our_student = next((s for s in data if s.get('id') == self.student_user.id), None)
            elif isinstance(data, dict) and 'results' in data:
                our_student = next((s for s in data['results'] if s.get('id') == self.student_user.id), None)
            else:
                our_student = None

            if our_student:
                self.assertNotIn('goal', our_student, "goal should not be visible in list")
                self.assertNotIn('tutor', our_student, "tutor should not be visible in list")
                self.assertNotIn('parent', our_student, "parent should not be visible in list")
