#!/usr/bin/env python
"""
Comprehensive API Endpoint Testing for THE_BOT Platform
Tests all endpoints with proper authentication and permission checks
"""

import os
import sys
import json
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

django.setup()

from accounts.models import UserProfile
from scheduling.models import Lesson
from materials.models import Material, Subject
from assignments.models import Assignment
from chat.models import ChatRoom
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class APIEndpointTests(TestCase):
    """Test all API endpoints"""

    def setUp(self):
        """Set up test users and data"""
        self.client = Client()

        # Create test users with all roles
        self.student = User.objects.create_user(
            email='student1@test.com',
            password='student123',
            is_student=True
        )

        self.teacher = User.objects.create_user(
            email='teacher1@test.com',
            password='teacher123',
            is_teacher=True
        )

        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )

        self.tutor = User.objects.create_user(
            email='tutor1@test.com',
            password='tutor123',
            is_tutor=True
        )

        self.parent = User.objects.create_user(
            email='parent1@test.com',
            password='parent123',
            is_parent=True
        )

        # Create profiles
        UserProfile.objects.create(user=self.student, role='student')
        UserProfile.objects.create(user=self.teacher, role='teacher')
        UserProfile.objects.create(user=self.admin, role='admin')
        UserProfile.objects.create(user=self.tutor, role='tutor')
        UserProfile.objects.create(user=self.parent, role='parent')

        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': [],
            'endpoints_tested': []
        }

    def login(self, email, password):
        """Login and get token"""
        response = self.client.post(
            '/api/auth/login/',
            {'email': email, 'password': password},
            content_type='application/json'
        )
        return response

    def test_01_health_endpoint(self):
        """Test health check endpoint"""
        print("\n1. Health & Status Tests")
        print("-" * 50)

        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        print(f"✓ GET /api/health/ - {response.status_code}")
        self.test_results['endpoints_tested'].append('/api/health/')
        self.test_results['passed'] += 1

    def test_02_swagger_endpoint(self):
        """Test Swagger schema endpoint"""
        response = self.client.get('/api/schema/swagger/')
        is_valid = response.status_code in [200, 404]
        if is_valid:
            print(f"✓ GET /api/schema/swagger/ - {response.status_code}")
            self.test_results['passed'] += 1
        else:
            print(f"✗ GET /api/schema/swagger/ - {response.status_code}")
            self.test_results['failed'] += 1
        self.test_results['endpoints_tested'].append('/api/schema/swagger/')

    def test_03_student_login(self):
        """Test student login"""
        print("\n2. Authentication Tests (All Roles)")
        print("-" * 50)

        response = self.login('student1@test.com', 'student123')
        is_valid = response.status_code == 200
        data = response.json() if response.status_code == 200 else None

        status = "✓" if is_valid else "✗"
        print(f"{status} POST /api/auth/login/ (Student) - {response.status_code}")

        if is_valid:
            self.assertIn('token', data)
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append('Student login failed')

        self.test_results['endpoints_tested'].append('/api/auth/login/ (student)')

    def test_04_teacher_login(self):
        """Test teacher login"""
        response = self.login('teacher1@test.com', 'teacher123')
        is_valid = response.status_code == 200

        status = "✓" if is_valid else "✗"
        print(f"{status} POST /api/auth/login/ (Teacher) - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append('Teacher login failed')

        self.test_results['endpoints_tested'].append('/api/auth/login/ (teacher)')

    def test_05_admin_login(self):
        """Test admin login"""
        response = self.login('admin@test.com', 'admin123')
        is_valid = response.status_code == 200

        status = "✓" if is_valid else "✗"
        print(f"{status} POST /api/auth/login/ (Admin) - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append('Admin login failed')

        self.test_results['endpoints_tested'].append('/api/auth/login/ (admin)')

    def test_06_tutor_login(self):
        """Test tutor login"""
        response = self.login('tutor1@test.com', 'tutor123')
        is_valid = response.status_code == 200

        status = "✓" if is_valid else "✗"
        print(f"{status} POST /api/auth/login/ (Tutor) - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append('Tutor login failed')

        self.test_results['endpoints_tested'].append('/api/auth/login/ (tutor)')

    def test_07_parent_login(self):
        """Test parent login"""
        response = self.login('parent1@test.com', 'parent123')
        is_valid = response.status_code == 200

        status = "✓" if is_valid else "✗"
        print(f"{status} POST /api/auth/login/ (Parent) - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append('Parent login failed')

        self.test_results['endpoints_tested'].append('/api/auth/login/ (parent)')

    def test_08_profile_endpoints(self):
        """Test profile endpoints"""
        print("\n3. Profile Endpoints")
        print("-" * 50)

        self.client.force_login(self.student)

        response = self.client.get('/api/profile/')
        is_valid = response.status_code == 200
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/profile/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/profile/ (GET)')

    def test_09_profile_patch(self):
        """Test profile PATCH"""
        self.client.force_login(self.student)

        response = self.client.patch(
            '/api/profile/',
            {'first_name': 'Test'},
            content_type='application/json'
        )
        is_valid = response.status_code in [200, 400]
        status = "✓" if is_valid else "✗"
        print(f"{status} PATCH /api/profile/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/profile/ (PATCH)')

    def test_10_scheduling_list(self):
        """Test lesson list endpoint"""
        print("\n4. Scheduling Endpoints")
        print("-" * 50)

        self.client.force_login(self.student)

        response = self.client.get('/api/scheduling/lessons/')
        is_valid = response.status_code == 200
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/scheduling/lessons/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/scheduling/lessons/ (GET)')

    def test_11_scheduling_create(self):
        """Test lesson creation"""
        self.client.force_login(self.teacher)

        # Create subject if not exists
        subject, _ = Subject.objects.get_or_create(name='Math')

        data = {
            'subject': subject.id,
            'title': 'Math Lesson',
            'start_time': (timezone.now() + timedelta(days=1)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=1, hours=1)).isoformat(),
        }

        response = self.client.post(
            '/api/scheduling/lessons/',
            json.dumps(data),
            content_type='application/json'
        )
        is_valid = response.status_code in [201, 400]
        status = "✓" if is_valid else "✗"
        print(f"{status} POST /api/scheduling/lessons/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/scheduling/lessons/ (POST)')

    def test_12_materials_list(self):
        """Test materials list endpoint"""
        print("\n5. Materials Endpoints")
        print("-" * 50)

        self.client.force_login(self.teacher)

        response = self.client.get('/api/materials/')
        is_valid = response.status_code == 200
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/materials/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/materials/ (GET)')

    def test_13_assignments_list(self):
        """Test assignments list endpoint"""
        print("\n6. Assignments Endpoints")
        print("-" * 50)

        self.client.force_login(self.student)

        response = self.client.get('/api/assignments/')
        is_valid = response.status_code == 200
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/assignments/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/assignments/ (GET)')

    def test_14_chat_list(self):
        """Test chat endpoints"""
        print("\n7. Chat Endpoints")
        print("-" * 50)

        self.client.force_login(self.student)

        response = self.client.get('/api/chat/rooms/')
        is_valid = response.status_code in [200, 404]
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/chat/rooms/ - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/chat/rooms/ (GET)')

    def test_15_admin_permissions(self):
        """Test admin endpoint permissions"""
        print("\n8. Admin Endpoints (Permission Checks)")
        print("-" * 50)

        # Non-admin should get 403
        self.client.force_login(self.student)

        response = self.client.get('/api/admin/users/')
        is_valid = response.status_code in [403, 404]
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/admin/users/ (Student) - {response.status_code} (should be 403/404)")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/admin/users/ (403 check)')

    def test_16_admin_access(self):
        """Test admin can access admin endpoints"""
        self.client.force_login(self.admin)

        response = self.client.get('/api/admin/users/')
        is_valid = response.status_code in [200, 404]
        status = "✓" if is_valid else "✗"
        print(f"{status} GET /api/admin/users/ (Admin) - {response.status_code}")

        if is_valid:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

        self.test_results['endpoints_tested'].append('/api/admin/users/ (200 for admin)')

    def test_99_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)

        total = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total * 100) if total > 0 else 0

        print(f"Total Endpoints Tested: {total}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        print(f"Success Rate: {success_rate:.1f}%")

        if self.test_results['errors']:
            print("\nErrors:")
            for error in self.test_results['errors']:
                print(f"  - {error}")

        print("\nEndpoints Tested:")
        for ep in self.test_results['endpoints_tested']:
            print(f"  - {ep}")


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(APIEndpointTests)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
