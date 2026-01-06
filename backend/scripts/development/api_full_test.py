#!/usr/bin/env python
"""
THE_BOT Platform - Полное API тестирование через curl/httpx
Тестирует все группы функционала для всех 5 ролей
"""

import os
import sys
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../..')

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


class Role(Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    TUTOR = "tutor"
    ADMIN = "admin"


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASS = "✅"
    FAIL = "❌"
    ERROR = "⚠️"


@dataclass
class TestResult:
    test_id: str
    name: str
    role: Role
    status: TestStatus = TestStatus.PENDING
    response_status: Optional[int] = None
    response_body: Dict = field(default_factory=dict)
    error_message: str = ""
    checks: List[Tuple[str, bool]] = field(default_factory=list)
    duration: float = 0.0

    def add_check(self, check_name: str, passed: bool):
        self.checks.append((check_name, passed))

    def all_checks_passed(self) -> bool:
        return all(passed for _, passed in self.checks)


class TheBottestRunner:
    def __init__(self):
        self.api_client = APIClient()
        self.test_users = {}
        self.test_results: List[TestResult] = []
        self.test_tokens = {}

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def create_test_users(self) -> bool:
        self.log("Creating test users for all roles...")

        test_data = {
            Role.STUDENT: {
                "username": "test_student",
                "email": "student@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Student"
            },
            Role.PARENT: {
                "username": "test_parent",
                "email": "parent@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Parent"
            },
            Role.TEACHER: {
                "username": "test_teacher",
                "email": "teacher@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Teacher"
            },
            Role.TUTOR: {
                "username": "test_tutor",
                "email": "tutor@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Tutor"
            },
            Role.ADMIN: {
                "username": "test_admin",
                "email": "admin@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Admin"
            }
        }

        try:
            for role, data in test_data.items():
                user = User.objects.filter(username=data["username"]).first()
                if not user:
                    user = User.objects.create_user(**data)
                    self.log(f"Created user {role.value}: {user.username}", "OK")
                else:
                    self.log(f"User {role.value} already exists", "SKIP")

                if role == Role.ADMIN:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()

                self.test_users[role] = {
                    "user": user,
                    "credentials": {
                        "username": data["username"],
                        "password": data["password"]
                    }
                }

            return True
        except Exception as e:
            self.log(f"Failed to create test users: {str(e)}", "ERROR")
            return False

    def login(self, role: Role) -> Tuple[bool, str]:
        try:
            credentials = self.test_users[role]["credentials"]
            response = self.api_client.post('/api/auth/login/', {
                'username': credentials['username'],
                'password': credentials['password']
            }, format='json')

            if response.status_code == 200:
                data = response.json()
                token = data.get('access') or data.get('token')
                self.test_tokens[role] = token
                self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
                return True, token
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def run_test(self, test_id: str, test_name: str, role: Role,
                 endpoint: str, method: str = "GET", data: Dict = None,
                 expected_status: int = 200) -> TestResult:

        result = TestResult(test_id=test_id, name=test_name, role=role)
        result.status = TestStatus.RUNNING
        start_time = time.time()

        try:
            if role not in self.test_tokens:
                login_ok, token = self.login(role)
                if not login_ok:
                    result.status = TestStatus.FAIL
                    result.error_message = f"Login failed: {token}"
                    result.duration = time.time() - start_time
                    return result

            token = self.test_tokens.get(role)
            if token:
                self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

            if method.upper() == "GET":
                response = self.api_client.get(endpoint, format='json')
            elif method.upper() == "POST":
                response = self.api_client.post(endpoint, data=data, format='json')
            elif method.upper() == "PUT":
                response = self.api_client.put(endpoint, data=data, format='json')
            elif method.upper() == "DELETE":
                response = self.api_client.delete(endpoint, format='json')
            else:
                raise ValueError(f"Unknown method: {method}")

            result.response_status = response.status_code
            try:
                result.response_body = response.json()
            except:
                result.response_body = {"raw": str(response.content)[:200]}

            result.add_check(f"HTTP Status {expected_status}", response.status_code == expected_status)
            result.add_check("Response has data", bool(result.response_body))

            if response.status_code == expected_status and result.all_checks_passed():
                result.status = TestStatus.PASS
            else:
                result.status = TestStatus.FAIL

        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)

        result.duration = time.time() - start_time
        return result

    def test_group_1_authentication(self) -> List[TestResult]:
        """T1-T10: Authentication"""
        self.log("\n" + "="*60)
        self.log("GROUP 1: AUTHENTICATION (T1-T10)")
        self.log("="*60)

        results = []
        for idx, role in enumerate(Role, 1):
            result = self.run_test(
                test_id=f"T{idx}",
                test_name=f"Login {role.value.capitalize()}",
                role=role,
                endpoint="/api/auth/login/",
                method="POST",
                data={
                    "username": self.test_users[role]["credentials"]["username"],
                    "password": self.test_users[role]["credentials"]["password"]
                },
                expected_status=200
            )
            result.add_check("Token present", 'access' in result.response_body or 'token' in result.response_body)
            results.append(result)
            self.print_test(result)

        for idx, role in enumerate(Role, 6):
            if idx > 10:
                break
            result = self.run_test(
                test_id=f"T{idx}",
                test_name=f"Protected Endpoint - {role.value.capitalize()}",
                role=role,
                endpoint="/api/accounts/profile/",
                method="GET",
                expected_status=200
            )
            results.append(result)
            self.print_test(result)

        return results

    def test_group_2_chat(self) -> List[TestResult]:
        """T11-T15: Chat"""
        self.log("\n" + "="*60)
        self.log("GROUP 2: CHAT (T11-T15)")
        self.log("="*60)

        results = []
        endpoints = [
            ("T11", "Get Chat Rooms", "/api/chat/chatrooms/", "GET", None),
            ("T12", "Get Messages", "/api/chat/messages/", "GET", None),
            ("T13", "Send Message", "/api/chat/messages/", "POST", {"content": "Test"}),
            ("T14", "Get History", "/api/chat/messages/", "GET", None),
            ("T15", "Get Forum", "/api/chat/forum/", "GET", None),
        ]

        for test_id, name, endpoint, method, data in endpoints:
            result = self.run_test(test_id, name, Role.STUDENT, endpoint, method, data, 200)
            results.append(result)
            self.print_test(result)

        return results

    def test_group_3_scheduling(self) -> List[TestResult]:
        """T16-T20: Scheduling"""
        self.log("\n" + "="*60)
        self.log("GROUP 3: SCHEDULING (T16-T20)")
        self.log("="*60)

        results = []
        tests = [
            ("T16", "Get Schedule", Role.STUDENT, "/api/scheduling/schedule/", "GET", None, 200),
            ("T17", "Get Lessons", Role.STUDENT, "/api/scheduling/lessons/", "GET", None, 200),
            ("T18", "Create Lesson", Role.TEACHER, "/api/scheduling/lessons/", "POST", {"title": "Test", "scheduled_at": "2024-01-15T10:00:00Z"}, 201),
            ("T19", "Get Lesson Details", Role.STUDENT, "/api/scheduling/lessons/1/", "GET", None, 200),
            ("T20", "Update Schedule", Role.ADMIN, "/api/scheduling/schedule/1/", "PUT", {"status": "active"}, 200),
        ]

        for test_id, name, role, endpoint, method, data, status in tests:
            result = self.run_test(test_id, name, role, endpoint, method, data, status)
            results.append(result)
            self.print_test(result)

        return results

    def test_group_4_materials(self) -> List[TestResult]:
        """T21-T27: Materials"""
        self.log("\n" + "="*60)
        self.log("GROUP 4: MATERIALS (T21-T27)")
        self.log("="*60)

        results = []
        tests = [
            ("T21", "Get Subjects", Role.STUDENT, "/api/materials/subjects/", "GET", None, 200),
            ("T22", "Get Materials", Role.STUDENT, "/api/materials/", "GET", None, 200),
            ("T23", "Get Progress", Role.STUDENT, "/api/materials/progress/", "GET", None, 200),
            ("T24", "Upload Material", Role.TEACHER, "/api/materials/", "POST", {"title": "Test", "content": "Test"}, 201),
            ("T25", "Assign Material", Role.TEACHER, "/api/materials/assignments/", "POST", {"material_id": 1, "student_id": 1}, 201),
            ("T26", "Submit Feedback", Role.TEACHER, "/api/materials/feedback/", "POST", {"material_id": 1, "student_id": 1, "feedback": "Good"}, 201),
            ("T27", "Mark as Read", Role.STUDENT, "/api/materials/progress/1/", "PUT", {"completed": True}, 200),
        ]

        for test_id, name, role, endpoint, method, data, status in tests:
            result = self.run_test(test_id, name, role, endpoint, method, data, status)
            results.append(result)
            self.print_test(result)

        return results

    def test_group_5_assignments(self) -> List[TestResult]:
        """T28-T34: Assignments"""
        self.log("\n" + "="*60)
        self.log("GROUP 5: ASSIGNMENTS (T28-T34)")
        self.log("="*60)

        results = []
        tests = [
            ("T28", "Get Assignments", Role.STUDENT, "/api/assignments/", "GET", None, 200),
            ("T29", "Create Assignment", Role.TEACHER, "/api/assignments/", "POST", {"title": "Test", "due_date": "2024-01-20T23:59:59Z"}, 201),
            ("T30", "Get Details", Role.STUDENT, "/api/assignments/1/", "GET", None, 200),
            ("T31", "Submit Answer", Role.STUDENT, "/api/assignments/1/submit/", "POST", {"answer": "Test"}, 201),
            ("T32", "Get Submission", Role.STUDENT, "/api/assignments/submissions/", "GET", None, 200),
            ("T33", "Grade Assignment", Role.TEACHER, "/api/assignments/submissions/1/grade/", "POST", {"grade": 85, "feedback": "Well!"}, 200),
            ("T34", "Check Plagiarism", Role.TEACHER, "/api/assignments/plagiarism/check/", "POST", {"submission_id": 1}, 200),
        ]

        for test_id, name, role, endpoint, method, data, status in tests:
            result = self.run_test(test_id, name, role, endpoint, method, data, status)
            results.append(result)
            self.print_test(result)

        return results

    def test_group_6_reports(self) -> List[TestResult]:
        """T35-T40: Reports"""
        self.log("\n" + "="*60)
        self.log("GROUP 6: REPORTS (T35-T40)")
        self.log("="*60)

        results = []
        tests = [
            ("T35", "Student Report", Role.STUDENT, "/api/reports/student/", "GET", None, 200),
            ("T36", "Teacher Report", Role.TEACHER, "/api/reports/teacher/", "GET", None, 200),
            ("T37", "Parent Report", Role.PARENT, "/api/reports/parent/", "GET", None, 200),
            ("T38", "Export Data", Role.ADMIN, "/api/reports/export/", "POST", {"format": "csv", "type": "users"}, 201),
            ("T39", "Get Analytics", Role.ADMIN, "/api/reports/analytics/", "GET", None, 200),
            ("T40", "Get Statistics", Role.TEACHER, "/api/reports/statistics/", "GET", None, 200),
        ]

        for test_id, name, role, endpoint, method, data, status in tests:
            result = self.run_test(test_id, name, role, endpoint, method, data, status)
            results.append(result)
            self.print_test(result)

        return results

    def test_group_7_permissions(self) -> List[TestResult]:
        """T46-T50: Permissions"""
        self.log("\n" + "="*60)
        self.log("GROUP 7: PERMISSIONS & ACCESS CONTROL (T46-T50)")
        self.log("="*60)

        results = []
        tests = [
            ("T46", "Student Cannot Create Lessons", Role.STUDENT, "/api/scheduling/lessons/", "POST", {"title": "Unauth"}, 403),
            ("T47", "Student Cannot Grade", Role.STUDENT, "/api/assignments/submissions/1/grade/", "POST", {"grade": 100}, 403),
            ("T48", "Parent Cannot Upload", Role.PARENT, "/api/materials/", "POST", {"title": "Unauth"}, 403),
            ("T49", "Tutor Cannot Delete", Role.TUTOR, "/api/scheduling/lessons/1/", "DELETE", None, 403),
            ("T50", "Admin Can Access", Role.ADMIN, "/api/accounts/users/", "GET", None, 200),
        ]

        for test_id, name, role, endpoint, method, data, status in tests:
            result = self.run_test(test_id, name, role, endpoint, method, data, status)
            results.append(result)
            self.print_test(result)

        return results

    def print_test(self, result: TestResult):
        status_icon = result.status.value
        print(f"\n{result.test_id}_{result.name.upper().replace(' ', '_')}")
        print(f"  Role: {result.role.value.upper()}")
        print(f"  Status: {status_icon}")
        if result.response_status:
            print(f"  HTTP: {result.response_status}")
        if result.error_message:
            print(f"  Error: {result.error_message}")

    def run_all_tests(self):
        self.log("="*60)
        self.log("THE_BOT PLATFORM - FULL API TEST SUITE")
        self.log("="*60)
        self.log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.create_test_users():
            self.log("Failed to create test users", "ERROR")
            return False

        test_groups = [
            self.test_group_1_authentication(),
            self.test_group_2_chat(),
            self.test_group_3_scheduling(),
            self.test_group_4_materials(),
            self.test_group_5_assignments(),
            self.test_group_6_reports(),
            self.test_group_7_permissions(),
        ]

        for group_results in test_groups:
            self.test_results.extend(group_results)

        self.print_summary()
        return True

    def print_summary(self):
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
        self.log("="*60)

        passed = sum(1 for r in self.test_results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.test_results if r.status == TestStatus.FAIL)
        errors = sum(1 for r in self.test_results if r.status == TestStatus.ERROR)
        total = len(self.test_results)

        print(f"""
RESULTS:
  Total: {total}
  Passed: {passed} ✅
  Failed: {failed} ❌
  Errors: {errors} ⚠️
  Rate: {(passed/total*100):.1f}%
""")

        print("\nDETAILED:")
        print("-" * 80)
        print(f"{'Test':<8} {'Name':<35} {'Role':<10} {'Status':<8} {'HTTP':<6}")
        print("-" * 80)

        for result in self.test_results:
            status = result.status.value
            http = str(result.response_status) if result.response_status else "N/A"
            print(f"{result.test_id:<8} {result.name:<35} {result.role.value:<10} {status:<8} {http:<6}")

        print("-" * 80)

        problems = [r for r in self.test_results if r.status != TestStatus.PASS]
        if problems:
            print(f"\nFOUND {len(problems)} ISSUES:")
            for result in problems:
                print(f"\n{result.test_id} - {result.name}")
                if result.error_message:
                    print(f"  Error: {result.error_message}")

        self.log(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    runner = TheBottestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()
