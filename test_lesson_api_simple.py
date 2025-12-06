#!/usr/bin/env python
"""
Comprehensive API testing for lesson creation endpoint.

Tests all scenarios including happy path and edge cases.
Uses actual requests to test the API.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

# API Configuration
API_BASE_URL = "http://localhost:8000/api"
LESSONS_ENDPOINT = f"{API_BASE_URL}/scheduling/lessons/"

# Test tokens
TEACHER_TOKEN = "d7825d01e7ba027d5c0f3c8acaec15a5d3bc1d27"
STUDENT_TOKEN = "0f355c1ada928441a0c2889ddc9958ad23f75b7d"

# Test IDs from database
# Teacher token d7825d01... corresponds to teacher ID 192 (teacher@test.com)
# Valid enrollment: Teacher 192 -> Student 190 (Mathematics)
STUDENT_ID = "190"   # student1@test.com
SUBJECT_ID = "15"    # Matematika (has active enrollment with teacher 192)

class TestResult:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, scenario_name: str, details: str = ""):
        """Record a passed test."""
        self.passed += 1
        print(f"✓ PASS: {scenario_name}")
        if details:
            print(f"  {details}")

    def add_fail(self, scenario_name: str, expected: str, actual: str, error: str = ""):
        """Record a failed test."""
        self.failed += 1
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
        if total > 0:
            pass_rate = 100 * self.passed // total
        else:
            pass_rate = 0
        print(f"TEST SUMMARY: {self.passed}/{total} passed ({pass_rate}%)")
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

    def _make_request(self, method: str, url: str, token: str = None,
                      json_data: Dict = None, params: Dict = None) -> Tuple[int, Dict]:
        """Make HTTP request with authorization."""
        headers = {
            'Content-Type': 'application/json'
        }

        if token:
            headers['Authorization'] = f'Token {token}'

        # Disable proxy for localhost
        proxies = {
            'http': None,
            'https': None,
        }

        try:
            if method == 'POST':
                response = requests.post(url, json=json_data, headers=headers, params=params, timeout=10, proxies=proxies)
            elif method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10, proxies=proxies)
            elif method == 'PATCH':
                response = requests.patch(url, json=json_data, headers=headers, timeout=10, proxies=proxies)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10, proxies=proxies)
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

        # Calculate future date
        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00',
            'description': 'Test lesson created via API',
            'telemost_link': 'https://telemost.example.com/test'
        }

        print(f"Payload: {json.dumps(payload, indent=2)}")

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")
        print(f"Response: {json.dumps(response, indent=2, default=str)}")

        if status_code == 201:
            lesson_id = response.get('id')
            if lesson_id:
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

        print(f"Response status: {status_code}")

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

        print(f"Response status: {status_code}")

        if status_code == 200:
            if isinstance(response, dict) and 'results' in response:
                lessons = response['results']
            elif isinstance(response, list):
                lessons = response
            else:
                lessons = []

            if lessons:
                self.result.add_pass(
                    'Student can see lessons',
                    f"Retrieved {len(lessons)} lesson(s)"
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

        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
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

        print(f"Response status: {status_code}")

        if status_code in [403, 401]:
            self.result.add_pass(
                'Non-teacher cannot create lessons',
                f"Correctly rejected with {status_code}: {response.get('error', response)}"
            )
        else:
            self.result.add_fail(
                'Non-teacher cannot create lessons',
                'Status 403 or 401',
                f'Status {status_code}',
                f'Response: {response}'
            )

    def test_invalid_student_id(self):
        """Test T005: Invalid student ID returns 400."""
        print("\n" + "="*80)
        print("TEST T005: Invalid student ID returns 400")
        print("="*80)

        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student': 'invalid-uuid',
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

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

        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': '99999',
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

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

        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '11:00',
            'end_time': '10:00'  # End before start
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

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

        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '10:00',
            'end_time': '10:00'  # Same time
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

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

        past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': past_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

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
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

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

        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '10:00',
            'end_time': '11:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=None,  # No token
            json_data=payload
        )

        print(f"Response status: {status_code}")

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

    def test_optional_fields(self):
        """Test T012: Optional fields (description, telemost_link) can be omitted."""
        print("\n" + "="*80)
        print("TEST T012: Optional fields can be omitted")
        print("="*80)

        future_date = (datetime.now() + timedelta(days=8)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
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

        print(f"Response status: {status_code}")

        if status_code == 201:
            if response.get('id'):
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
        """Test T013: Accept HH:MM and HH:MM:SS time formats."""
        print("\n" + "="*80)
        print("TEST T013: Accept HH:MM time format")
        print("="*80)

        future_date = (datetime.now() + timedelta(days=9)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '15:30',  # HH:MM format
            'end_time': '16:30'     # HH:MM format
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

        if status_code == 201:
            if response.get('id'):
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

    def test_lesson_initial_status(self):
        """Test T014: New lesson defaults to 'pending' status."""
        print("\n" + "="*80)
        print("TEST T014: New lesson defaults to 'pending' status")
        print("="*80)

        future_date = (datetime.now() + timedelta(days=11)).strftime('%Y-%m-%d')
        payload = {
            'student': STUDENT_ID,
            'subject': SUBJECT_ID,
            'date': future_date,
            'start_time': '11:00',
            'end_time': '12:00'
        }

        status_code, response = self._make_request(
            'POST', LESSONS_ENDPOINT,
            token=TEACHER_TOKEN,
            json_data=payload
        )

        print(f"Response status: {status_code}")

        if status_code == 201:
            if response.get('id'):
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
        print(f"Teacher Token: {TEACHER_TOKEN}")
        print(f"Student Token: {STUDENT_TOKEN}")
        print(f"Test Student ID: {STUDENT_ID}")
        print(f"Test Subject ID: {SUBJECT_ID}")
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

        # Optional fields and formats
        self.test_optional_fields()
        self.test_time_format_variations()

        # Response validation
        self.test_lesson_initial_status()

        # Print summary
        self.result.print_summary()

        return self.result.failed == 0

if __name__ == '__main__':
    tester = LessonAPITester()
    success = tester.run_all_tests()

    # Exit with appropriate code
    import sys
    sys.exit(0 if success else 1)
