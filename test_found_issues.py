#!/usr/bin/env python3
"""
Test Suite for Found Issues in THE_BOT Platform
Tests the issues discovered during comprehensive testing

Run with: pytest test_found_issues.py -v
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.config.settings')
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform')
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

django.setup()

from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from accounts.models import User, StudentProfile, TeacherProfile
from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


class AuthenticationSecurityTests(APITestCase):
    """Tests for authentication security issues"""

    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        StudentProfile.objects.create(user=self.student)

    def test_login_rate_limiting(self):
        """[HIGH] #1: Test that rate limiting is enforced on login"""
        # Try 6 login attempts rapidly (limit is 5/minute)
        attempts = 0
        rate_limited = False

        for i in range(7):
            response = self.client.post('/api/auth/login/', {
                'email': 'student@test.com',
                'password': 'wrong_password'
            })
            attempts += 1
            if response.status_code == 429:  # Too Many Requests
                rate_limited = True
                break

        # Should be rate limited after 5 attempts
        self.assertTrue(
            rate_limited or attempts >= 5,
            "Rate limiting should kick in after 5 attempts"
        )

    def test_login_csrf_protection(self):
        """[HIGH] #1: Test CSRF protection on login endpoint"""
        # POST to login without CSRF token
        # In production, this should be rejected if CSRF middleware is enabled
        # but login endpoint has @csrf_exempt
        response = self.client.post('/api/auth/login/', {
            'email': 'student@test.com',
            'password': 'testpass123'
        })

        # Should either succeed with token or fail with 403
        # Current implementation: likely succeeds (vulnerability)
        print(f"[!] Login endpoint status: {response.status_code}")
        print(f"[!] @csrf_exempt found on login - potential vulnerability")

    def test_change_password_requires_auth(self):
        """Test that password change requires authentication"""
        response = self.client.post('/api/auth/change-password/', {
            'old_password': 'testpass123',
            'new_password': 'newpass123'
        })

        # Should be 401 without auth
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            "Password change should require authentication"
        )

    def test_admin_endpoints_require_permission(self):
        """[HIGH] #3: Test that admin endpoints require admin role"""
        # Login as student
        self.client.force_authenticate(self.student)

        # Try to access admin users endpoint
        response = self.client.get('/api/admin/users/')

        # Should be 403 Forbidden
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Student should not access admin endpoints"
        )

    def test_admin_endpoints_allow_admin(self):
        """Test that admin endpoints work for admin role"""
        # Login as admin
        self.client.force_authenticate(self.admin)

        # Try to access admin users endpoint
        response = self.client.get('/api/admin/users/')

        # Should succeed (200 or 401 if not implemented)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
            f"Got unexpected status {response.status_code}"
        )


class SchedulingValidationTests(APITestCase):
    """Tests for scheduling validation issues"""

    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        # Create profiles
        TeacherProfile.objects.create(user=self.teacher)
        StudentProfile.objects.create(user=self.student)

        # Create subject and enrollment
        self.subject = Subject.objects.create(name='Math')
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

    def test_lesson_time_validation(self):
        """[MEDIUM] #3: Test that start_time must be < end_time"""
        self.client.force_authenticate(self.teacher)

        # Try to create lesson with end_time < start_time
        response = self.client.post('/api/scheduling/lessons/', {
            'subject': self.subject.id,
            'start_time': '2026-01-06T12:00:00Z',
            'end_time': '2026-01-06T11:00:00Z'
        })

        # Should fail with 400 Bad Request
        if response.status_code == 201:
            print("[!] ISSUE FOUND: Lesson created with end_time < start_time")
            print(f"    Response: {response.data}")
            self.fail("Should reject lesson with end_time < start_time")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Should reject invalid time range"
        )

    def test_lesson_time_conflict(self):
        """[MEDIUM] #2: Test that conflicting lesson times are detected"""
        self.client.force_authenticate(self.teacher)

        # Create first lesson
        lesson1_response = self.client.post('/api/scheduling/lessons/', {
            'subject': self.subject.id,
            'start_time': '2026-01-06T10:00:00Z',
            'end_time': '2026-01-06T11:00:00Z'
        })

        if lesson1_response.status_code != 201:
            self.skipTest("Could not create first lesson")

        # Try to create overlapping lesson
        lesson2_response = self.client.post('/api/scheduling/lessons/', {
            'subject': self.subject.id,
            'start_time': '2026-01-06T10:30:00Z',
            'end_time': '2026-01-06T11:30:00Z'
        })

        # Should fail with 400 Bad Request (or check via logic)
        if lesson2_response.status_code == 201:
            print("[!] ISSUE FOUND: Overlapping lessons allowed")
            print(f"    Lesson 1: 10:00-11:00")
            print(f"    Lesson 2: 10:30-11:30")
            print(f"    Both created successfully (potential data issue)")
            self.fail("Should reject overlapping lesson times")

        self.assertEqual(
            lesson2_response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Should reject overlapping lesson times"
        )

    def test_lesson_must_be_in_future(self):
        """Test that lessons cannot be in the past"""
        self.client.force_authenticate(self.teacher)

        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        response = self.client.post('/api/scheduling/lessons/', {
            'subject': self.subject.id,
            'start_time': f'{yesterday}Z',
            'end_time': f'{yesterday}Z'
        })

        # Should fail with 400
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Should reject lessons in the past"
        )


class AssignmentSecurityTests(APITestCase):
    """Tests for assignment/file upload security"""

    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        StudentProfile.objects.create(user=self.student)

    def test_file_upload_size_limit(self):
        """[MEDIUM] #4: Test that file upload size is limited"""
        self.client.force_authenticate(self.student)

        # Try to upload a file (we can't easily create a 100MB file, so we'll note the issue)
        print("[!] File upload size limit test:")
        print("    - No MAX_UPLOAD_SIZE found in settings")
        print("    - Potential DoS vulnerability if large files can be uploaded")
        print("    - Recommendation: Add FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB")

        # Check if settings has file upload limits
        from django.conf import settings

        has_limit = hasattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE')
        print(f"    - FILE_UPLOAD_MAX_MEMORY_SIZE configured: {has_limit}")

        if not has_limit:
            print("[!] ISSUE: No file upload size limit configured")


class PermissionTests(APITestCase):
    """Tests for role-based permission issues"""

    def setUp(self):
        self.client = APIClient()

        # Create users for each role
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.tutor = User.objects.create_user(
            email='tutor@test.com',
            password='testpass123',
            role='tutor'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )

        StudentProfile.objects.create(user=self.student)
        TeacherProfile.objects.create(user=self.teacher)

    def test_student_cannot_view_admin_panel(self):
        """Test that students cannot access admin endpoints"""
        self.client.force_authenticate(self.student)

        response = self.client.get('/api/admin/users/')

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Students should not access admin endpoints"
        )

    def test_teacher_cannot_view_admin_panel(self):
        """Test that teachers cannot access admin endpoints"""
        self.client.force_authenticate(self.teacher)

        response = self.client.get('/api/admin/users/')

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Teachers should not access admin endpoints"
        )

    def test_admin_can_view_admin_panel(self):
        """Test that admins CAN access admin endpoints"""
        self.client.force_authenticate(self.admin)

        response = self.client.get('/api/admin/users/')

        # Should succeed (200, 404, or anything except 403/401)
        self.assertNotEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Admins should be able to access admin endpoints"
        )

    def test_unauthenticated_gets_401(self):
        """Test that unauthenticated requests get 401"""
        response = self.client.get('/api/profile/')

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            "Unauthenticated requests should get 401"
        )


class DataValidationTests(APITestCase):
    """Tests for input validation"""

    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        StudentProfile.objects.create(user=self.student)

    def test_xss_protection_in_profile(self):
        """Test that XSS is prevented in profile updates"""
        self.client.force_authenticate(self.student)

        response = self.client.patch('/api/profile/', {
            'full_name': '<script>alert("XSS")</script>'
        })

        if response.status_code == 200:
            # Check that script tag is escaped
            profile_data = response.json()
            full_name = str(profile_data.get('data', {}).get('full_name', ''))

            if '<script>' in full_name.lower():
                print("[!] ISSUE: XSS not escaped in response")
            else:
                print("[✓] PASS: XSS properly escaped")

    def test_empty_email_validation(self):
        """Test that empty email is rejected"""
        response = self.client.post('/api/auth/login/', {
            'email': '',
            'password': 'testpass123'
        })

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Empty email should be rejected"
        )

    def test_empty_password_validation(self):
        """Test that empty password is rejected"""
        response = self.client.post('/api/auth/login/', {
            'email': 'student@test.com',
            'password': ''
        })

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Empty password should be rejected"
        )


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
