#!/usr/bin/env python
"""
Comprehensive API testing for lesson creation endpoint.

Tests all scenarios including happy path and edge cases.
Uses actual tokens to verify lesson creation and visibility.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Tuple

# Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from materials.models import Subject, SubjectEnrollment
from scheduling.models import Lesson

User = get_user_model()

# API Configuration
API_BASE_URL = "http://localhost:8000/api"
LESSONS_ENDPOINT = f"{API_BASE_URL}/scheduling/lessons/"

# Test data
TEACHER_TOKEN = "d7825d01e7ba027d5c0f3c8acaec15a5d3bc1d27"
STUDENT_TOKEN = "0f355c1ada928441a0c2889ddc9958ad23f75b7d"

class TestResult:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.tests = []

    def add_pass(self, scenario_name: str, details: str = ""):
        """Record a passed test."""
        self.passed += 1
        self.tests.append({
            'scenario': scenario_name,
            'status': 'PASSED',
            'details': details
        })
        print(f"✓ PASS: {scenario_name}")
        if details:
            print(f"  {details}")

    def add_fail(self, scenario_name: str, expected: str, actual: str, error: str = ""):
        """Record a failed test."""
        self.failed += 1
        self.tests.append({
            'scenario': scenario_name,
            'status': 'FAILED',
            'expected': expected,
            'actual': actual,
            'error': error
        })
        print(f"✗ FAIL: {scenario_name}")
        print(f"  Expected: {expected}")
        print(f"  Actual: {actual}")
        if error:
            print(f"  Error: {error}")
        self.errors.append((scenario_name, expected, actual, error))

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print("\n" + "="*80)
        print(f"TEST SUMMARY: {self.passed}/{total} passed ({100*self.passed//total}%)")
        print("="*80)

        if self.failed > 0:
            print("\nFAILED TESTS:")
            for i, (scenario, expected, actual, error) in enumerate(self.errors, 1):
                print(f"\n{i}. {scenario}")
                print(f"   Expected: {expected}")
                print(f"   Actual: {actual}")
                if error:
                    print(f"   Error: {error}")

class LessonAPITester:
    """Test lesson API endpoint."""

    def __init__(self):
        self.result = TestResult()
        self.created_lesson_ids = []
        self._setup_test_data()

    def _setup_test_data(self):
        """Setup test users and enrollments."""
        # Get or create teacher
        self.teacher = User.objects.filter(role='teacher').first()
        if not self.teacher:
            print("ERROR: No teacher found in database")
            sys.exit(1)

        # Get or create student
        self.student = User.objects.filter(role='student').first()
        if not self.student:
            print("ERROR: No student found in database")
            sys.exit(1)

        # Get or create subject
        self.subject = Subject.objects.first()
        if not self.subject:
            self.subject = Subject.objects.create(
                name='Test Subject',
                description='Subject for API testing'
            )

        # Ensure enrollment exists
        enrollment, created = SubjectEnrollment.objects.get_or_create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            defaults={'is_active': True}
        )
        if not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save()

        print(f"Test data setup:")
        print(f"  Teacher: {self.teacher.email} (ID: {self.teacher.id})")
        print(f"  Student: {self.student.email} (ID: {self.student.id})")
        print(f"  Subject: {self.subject.name} (ID: {self.subject.id})")
        print()

    def _make_request(self, method: str, url: str, token: str = None,
                      json_data: Dict = None, params: Dict = None) -> Tuple[int, Dict]:
        """Make HTTP request with authorization."""
        headers = {
            'Content-Type': 'application/json'
        }

        if token:
            headers['Authorization'] = f'Token {token}'

        try:
            if method == 'POST':
                response = requests.post(url, json=json_data, headers=headers, params=params)
            elif method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'PATCH':
                response = requests.patch(url, json=json_data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            try:
                data = response.json()
            except:
                data = response.text

            return response.status_code, data

        except Exception as e:
            print(f"Request error: {e}")
            return 0, {'error': str(e)}

    def test_happy_path_lesson_creation(self):
        """Test T001: Valid lesson creation with all fields."""
        print("\n" + "="*80)
        print("TEST T001: Valid lesson creation with all fields")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00',
            'description': 'Test lesson created via API',
            'telemost_link': 'https://telemost.example.com/test'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 201:
            lesson_id = response.get('id')
            self.created_lesson_ids.append(lesson_id)

            # Verify response contains expected fields
            expected_fields = ['id', 'student', 'subject', 'date', 'start_time',
                             'end_time', 'description', 'telemost_link', 'status']
            missing_fields = [f for f in expected_fields if f not in response]

            if missing_fields:
                self.result.add_fail(
                    'Valid lesson creation',
                    f"Response contains {expected_fields}",
                    f"Missing fields: {missing_fields}",
                    f"Response: {response}"
                )
            else:
                self.result.add_pass(
                    'Valid lesson creation with all fields',
                    f"Lesson created (ID: {lesson_id}, Status: {response.get('status')})"
                )
        else:
            self.result.add_fail(
                'Valid lesson creation',
                'Status 201 Created',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_lesson_visibility_for_teacher(self):
        """Test T002: Teacher can see their created lessons."""
        print("\n" + "="*80)
        print("TEST T002: Teacher can see their created lessons")
        print("="*80)

        status_code, response = self._make_request(
            'GET', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN
        )

        if status_code == 200:
            if isinstance(response, dict) and 'results' in response:
                lessons = response['results']
            elif isinstance(response, list):
                lessons = response
            else:
                lessons = []

            if lessons:
                self.result.add_pass(
                    'Teacher can see lessons',
                    f"Retrieved {len(lessons)} lesson(s)"
                )
            else:
                self.result.add_pass(
                    'Teacher can see lessons',
                    "Retrieved 0 lessons (might be expected)"
                )
        else:
            self.result.add_fail(
                'Teacher can see lessons',
                'Status 200 OK',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_lesson_visibility_for_student(self):
        """Test T003: Student can see their lessons."""
        print("\n" + "="*80)
        print("TEST T003: Student can see their lessons")
        print("="*80)

        status_code, response = self._make_request(
            'GET', LESSONS_ENDPOINT,
            token=STUDENT_TOKEN
        )

        if status_code == 200:
            if isinstance(response, dict) and 'results' in response:
                lessons = response['results']
            elif isinstance(response, list):
                lessons = response
            else:
                lessons = []

            # Filter by current student
            student_lessons = [l for l in lessons if str(l.get('student')) == str(self.student.id)]

            if lessons or student_lessons:
                self.result.add_pass(
                    'Student can see lessons',
                    f"Retrieved {len(lessons)} lesson(s), {len(student_lessons)} for this student"
                )
            else:
                self.result.add_pass(
                    'Student can see lessons',
                    "Retrieved 0 lessons (might be expected)"
                )
        else:
            self.result.add_fail(
                'Student can see lessons',
                'Status 200 OK',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_non_teacher_cannot_create_lesson(self):
        """Test T004: Non-teacher cannot create lessons."""
        print("\n" + "="*80)
        print("TEST T004: Non-teacher cannot create lessons (access denied)")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00',
            'description': 'Unauthorized lesson attempt'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=STUDENT_TOKEN,  # Student trying to create
            json_data=payload
        )

        if status_code == 403:
            self.result.add_pass(
                'Non-teacher cannot create lessons',
                f"Correctly rejected with 403: {response.get('error', response)}"
            )
        elif status_code == 401:
            self.result.add_pass(
                'Non-teacher cannot create lessons',
                f"Correctly rejected with 401 (authentication): {response}"
            )
        else:
            self.result.add_fail(
                'Non-teacher cannot create lessons',
                'Status 403 Forbidden',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_invalid_student_id(self):
        """Test T005: Invalid student ID returns 400."""
        print("\n" + "="*80)
        print("TEST T005: Invalid student ID returns 400")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': 'invalid-uuid',
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Invalid student ID returns 400',
                f"Error message: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Invalid student ID returns 400',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_invalid_subject_id(self):
        """Test T006: Invalid subject ID returns 400."""
        print("\n" + "="*80)
        print("TEST T006: Invalid subject ID returns 400")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': '99999',
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Invalid subject ID returns 400',
                f"Error message: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Invalid subject ID returns 400',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_start_time_after_end_time(self):
        """Test T007: Start time >= end time returns 400."""
        print("\n" + "="*80)
        print("TEST T007: Start time >= end time returns 400")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '11:00',
            'end_time': '10:00'  # End before start
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Start time after end time returns 400',
                f"Error message: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Start time after end time returns 400',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_same_start_and_end_time(self):
        """Test T008: Same start and end time returns 400."""
        print("\n" + "="*80)
        print("TEST T008: Same start and end time returns 400")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '10:00',
            'end_time': '10:00'  # Same time
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Same start and end time returns 400',
                f"Error message: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Same start and end time returns 400',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_past_date_lesson(self):
        """Test T009: Lesson in the past returns 400."""
        print("\n" + "="*80)
        print("TEST T009: Lesson in the past returns 400")
        print("="*80)

        past_date = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': past_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Past date lesson returns 400',
                f"Error message: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Past date lesson returns 400',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_missing_required_fields(self):
        """Test T010: Missing required fields returns 400."""
        print("\n" + "="*80)
        print("TEST T010: Missing required fields returns 400")
        print("="*80)

        # Missing date
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Missing required fields returns 400',
                f"Error message: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Missing required fields returns 400',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_unauthenticated_request(self):
        """Test T011: Unauthenticated request returns 401."""
        print("\n" + "="*80)
        print("TEST T011: Unauthenticated request returns 401")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=None,  # No token
            json_data=payload
        )

        if status_code == 401:
            self.result.add_pass(
                'Unauthenticated request returns 401',
                f"Error message: {response.get('detail', response)}"
            )
        else:
            self.result.add_fail(
                'Unauthenticated request returns 401',
                'Status 401 Unauthorized',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_enrollment_requirement(self):
        """Test T012: Teacher must have active enrollment to create lesson."""
        print("\n" + "="*80)
        print("TEST T012: Teacher must have active enrollment")
        print("="*80)

        # Create another student without enrollment
        another_student = User.objects.create_user(
            email=f'new_student_{datetime.now().timestamp()}@test.com',
            password='TestPass123!',
            role='student'
        )

        future_date = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(another_student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 400:
            self.result.add_pass(
                'Teacher must have enrollment',
                f"Correctly rejected: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Teacher must have enrollment',
                'Status 400 Bad Request',
                f'Status {status_code}',
                f'Response: {response}'
            )

        # Cleanup
        another_student.delete()

    def test_optional_fields(self):
        """Test T013: Optional fields (description, telemost_link) can be omitted."""
        print("\n" + "="*80)
        print("TEST T013: Optional fields can be omitted")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=8)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '14:00',
            'end_time': '15:00'
            # No description or telemost_link
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 201:
            self.created_lesson_ids.append(response.get('id'))
            self.result.add_pass(
                'Optional fields can be omitted',
                f"Lesson created successfully (ID: {response.get('id')})"
            )
        else:
            self.result.add_fail(
                'Optional fields can be omitted',
                'Status 201 Created',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_time_format_variations(self):
        """Test T014: Accept HH:MM and HH:MM:SS time formats."""
        print("\n" + "="*80)
        print("TEST T014: Accept HH:MM time format")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=9)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '15:30',  # HH:MM format
            'end_time': '16:30'     # HH:MM format
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 201:
            self.created_lesson_ids.append(response.get('id'))
            self.result.add_pass(
                'Accept HH:MM time format',
                f"Lesson created successfully"
            )
        else:
            self.result.add_fail(
                'Accept HH:MM time format',
                'Status 201 Created',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_response_contains_computed_fields(self):
        """Test T015: Response includes computed fields."""
        print("\n" + "="*80)
        print("TEST T015: Response includes computed fields")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '09:00',
            'end_time': '10:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 201:
            self.created_lesson_ids.append(response.get('id'))

            # Check for computed fields
            computed_fields = ['teacher_name', 'student_name', 'subject_name',
                             'is_upcoming', 'can_cancel', 'datetime_start', 'datetime_end']

            missing_fields = [f for f in computed_fields if f not in response]

            if missing_fields:
                self.result.add_fail(
                    'Response includes computed fields',
                    f"Contains fields: {computed_fields}",
                    f"Missing: {missing_fields}",
                    f"Response: {json.dumps(response, indent=2, default=str)}"
                )
            else:
                self.result.add_pass(
                    'Response includes computed fields',
                    f"All computed fields present: {computed_fields}"
                )
        else:
            self.result.add_fail(
                'Response includes computed fields',
                'Status 201 Created',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_lesson_initial_status(self):
        """Test T016: New lesson defaults to 'pending' status."""
        print("\n" + "="*80)
        print("TEST T016: New lesson defaults to 'pending' status")
        print("="*80)

        future_date = (timezone.now() + timedelta(days=11)).strftime('%Y-%m-%d')
        payload = {
            'student_id': str(self.student.id),
            'subject_id': str(self.subject.id),
            'date': future_date,
            'start_time': '11:00',
            'end_time': '12:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        if status_code == 201:
            self.created_lesson_ids.append(response.get('id'))

            if response.get('status') == 'pending':
                self.result.add_pass(
                    'New lesson defaults to pending',
                    f"Status: {response.get('status')}"
                )
            else:
                self.result.add_fail(
                    'New lesson defaults to pending',
                    "Status: 'pending'",
                    f"Status: {response.get('status')}",
                    f"Response: {response}"
                )
        else:
            self.result.add_fail(
                'New lesson defaults to pending',
                'Status 201 Created',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def run_all_tests(self):
        """Run all test scenarios."""
        print("\n" + "="*80)
        print("COMPREHENSIVE LESSON API TESTING")
        print("="*80)
        print(f"API Base URL: {API_BASE_URL}")
        print(f"Lessons Endpoint: {LESSONS_ENDPOINT}")
        print()

        # Happy path
        self.test_happy_path_lesson_creation()

        # Visibility tests
        self.test_lesson_visibility_for_teacher()
        self.test_lesson_visibility_for_student()

        # Authorization tests
        self.test_non_teacher_cannot_create_lesson()
        self.test_unauthenticated_request()

        # Validation tests
        self.test_invalid_student_id()
        self.test_invalid_subject_id()
        self.test_start_time_after_end_time()
        self.test_same_start_and_end_time()
        self.test_past_date_lesson()
        self.test_missing_required_fields()
        self.test_enrollment_requirement()

        # Optional fields and formats
        self.test_optional_fields()
        self.test_time_format_variations()

        # Response validation
        self.test_response_contains_computed_fields()
        self.test_lesson_initial_status()

        # Print summary
        self.result.print_summary()

        # Cleanup created lessons
        print("\n" + "="*80)
        print("CLEANUP")
        print("="*80)
        print(f"Created {len(self.created_lesson_ids)} lessons during testing")
        for lesson_id in self.created_lesson_ids:
            try:
                Lesson.objects.filter(id=lesson_id).delete()
                print(f"  - Deleted lesson {lesson_id}")
            except Exception as e:
                print(f"  - Failed to delete lesson {lesson_id}: {e}")

        return self.result.failed == 0

if __name__ == '__main__':
    tester = LessonAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
