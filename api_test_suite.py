#!/usr/bin/env python3
"""
API Testing Suite for THE_BOT Platform
Tests all endpoints for each role
"""

import requests
import json
import time
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
from urllib.parse import urljoin

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_users = {
            "admin": {"email": "admin@test.com", "password": "admin@test.com"},
            "teacher": {"email": "teacher1@test.com", "password": "teacher1@test.com"},
            "tutor": {"email": "tutor1@test.com", "password": "tutor1@test.com"},
            "student": {"email": "student1@test.com", "password": "student1@test.com"},
            "parent": {"email": "parent1@test.com", "password": "parent1@test.com"},
        }
        self.tokens = {}
        self.issues = []
        self.results = []

    def log_issue(self, issue_type: str, severity: str, endpoint: str, status: int,
                  error: str, reproduce: str, expected: str, actual: str):
        """Log a found issue"""
        issue = {
            "type": issue_type,
            "severity": severity,
            "endpoint": endpoint,
            "status": status,
            "error_text": error,
            "how_to_reproduce": reproduce,
            "expected_behavior": expected,
            "actual_behavior": actual,
            "timestamp": datetime.now().isoformat()
        }
        self.issues.append(issue)

    def log_result(self, test_name: str, method: str, endpoint: str, status: int,
                   success: bool, details: str = ""):
        """Log a test result"""
        result = {
            "test": test_name,
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

    def login(self, role: str) -> bool:
        """Login a user and get token"""
        if role not in self.test_users:
            print(f"Unknown role: {role}")
            return False

        user = self.test_users[role]
        endpoint = f"{self.base_url}/auth/login/"

        try:
            response = requests.post(endpoint, json={
                "email": user["email"],
                "password": user["password"]
            })

            if response.status_code == 200:
                data = response.json()
                if "access" in data:
                    self.tokens[role] = data["access"]
                    self.session.headers.update({"Authorization": f"Bearer {data['access']}"})
                    self.log_result(f"login_{role}", "POST", endpoint, 200, True)
                    return True
                else:
                    self.log_issue("LOGIN_MISSING_TOKEN", "HIGH", endpoint, 200,
                                 "No access token in response",
                                 f"Login as {role} with correct credentials",
                                 "Should return access token",
                                 f"Response has no 'access' field: {data.keys()}")
                    return False
            else:
                error = response.text[:200]
                self.log_issue("LOGIN_FAILED", "HIGH", endpoint, response.status_code,
                             error,
                             f"Login as {role} with email {user['email']} and password {user['password']}",
                             "Should return 200 with access token",
                             f"Got {response.status_code}: {error}")
                return False
        except Exception as e:
            self.log_issue("LOGIN_ERROR", "HIGH", endpoint, 0,
                         str(e),
                         f"Login as {role}",
                         "Should successfully authenticate",
                         f"Exception: {str(e)}")
            return False

    def get_endpoint(self, role: str, method: str, path: str, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Make a GET request"""
        if role not in self.tokens:
            self.login(role)

        url = urljoin(self.base_url, path.lstrip('/'))
        headers = {"Authorization": f"Bearer {self.tokens.get(role, '')}"}

        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json={})
            else:
                response = requests.request(method, url, headers=headers)

            self.log_result(f"{method.lower()}_{path}", method, path, response.status_code,
                          response.status_code == expected_status or response.status_code in [200, 201, 204])

            try:
                return response.status_code, response.json() if response.text else {}
            except:
                return response.status_code, {"raw": response.text[:200]}
        except Exception as e:
            self.log_result(f"{method.lower()}_{path}", method, path, 0, False, str(e))
            return 0, {"error": str(e)}

    def test_auth_failures(self):
        """Test authentication edge cases"""
        print("\n=== TESTING AUTHENTICATION FAILURES ===")

        # Test 1: Non-existent user
        endpoint = f"{self.base_url}/auth/login/"
        response = requests.post(endpoint, json={
            "email": "nonexistent@test.com",
            "password": "anypassword"
        })
        if response.status_code == 401 or response.status_code == 400:
            self.log_result("auth_nonexistent_user", "POST", endpoint, response.status_code, True)
        else:
            self.log_issue("AUTH_NONEXISTENT_USER", "HIGH", endpoint, response.status_code,
                         response.text[:200],
                         "Try to login with non-existent email",
                         "Should return 401 or 400",
                         f"Got {response.status_code}")

        # Test 2: Empty password
        response = requests.post(endpoint, json={
            "email": "student1@test.com",
            "password": ""
        })
        if response.status_code != 200:
            self.log_result("auth_empty_password", "POST", endpoint, response.status_code, True)
        else:
            self.log_issue("AUTH_EMPTY_PASSWORD", "HIGH", endpoint, response.status_code,
                         "Accepted empty password",
                         "Login with empty password",
                         "Should reject with 401 or 400",
                         "Got 200 - password accepted")

        # Test 3: No email field
        response = requests.post(endpoint, json={
            "password": "somepassword"
        })
        if response.status_code != 200:
            self.log_result("auth_missing_email", "POST", endpoint, response.status_code, True)
        else:
            self.log_issue("AUTH_MISSING_EMAIL", "MEDIUM", endpoint, response.status_code,
                         "No validation for missing email",
                         "POST without email field",
                         "Should return 400 Bad Request",
                         "Got 200")

    def test_admin_endpoints(self):
        """Test admin role endpoints"""
        print("\n=== TESTING ADMIN ENDPOINTS ===")

        if not self.login("admin"):
            print("Failed to login as admin")
            return

        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}

        # Test: Get users list
        status, data = self.get_endpoint("admin", "GET", "/v1/admin/users/")
        if status == 200:
            print("✓ GET /admin/users/ - OK")
            if isinstance(data, dict) and ("results" in data or "data" in data):
                print(f"  - Response format OK, got data")
            else:
                print(f"  - Response format may be wrong: {type(data)}")
        else:
            self.log_issue("ADMIN_USERS_LIST", "MEDIUM", "/v1/admin/users/", status,
                         str(data),
                         "GET /api/v1/admin/users/",
                         "Should return 200 with user list",
                         f"Got {status}")

    def test_teacher_endpoints(self):
        """Test teacher role endpoints"""
        print("\n=== TESTING TEACHER ENDPOINTS ===")

        if not self.login("teacher"):
            print("Failed to login as teacher")
            return

        # Get students
        status, data = self.get_endpoint("teacher", "GET", "/v1/teacher/students/")
        print(f"GET /teacher/students/ - Status: {status}")
        if status == 404:
            # Check if endpoint exists
            self.log_issue("TEACHER_STUDENTS_404", "HIGH", "/v1/teacher/students/", status,
                         "Endpoint not found",
                         "GET /api/v1/teacher/students/",
                         "Should return list of students or 401 if not authorized",
                         f"Got 404")
        elif status == 401:
            print("  - Unauthorized (expected if no students assigned)")

    def test_student_endpoints(self):
        """Test student role endpoints"""
        print("\n=== TESTING STUDENT ENDPOINTS ===")

        if not self.login("student"):
            print("Failed to login as student")
            return

        # Get lessons
        status, data = self.get_endpoint("student", "GET", "/v1/student/lessons/")
        print(f"GET /student/lessons/ - Status: {status}")

    def test_tutor_endpoints(self):
        """Test tutor role endpoints"""
        print("\n=== TESTING TUTOR ENDPOINTS ===")

        if not self.login("tutor"):
            print("Failed to login as tutor")
            return

        # Get students
        status, data = self.get_endpoint("tutor", "GET", "/v1/tutor/students/")
        print(f"GET /tutor/students/ - Status: {status}")

    def test_parent_endpoints(self):
        """Test parent role endpoints"""
        print("\n=== TESTING PARENT ENDPOINTS ===")

        if not self.login("parent"):
            print("Failed to login as parent")
            return

        # Get children
        status, data = self.get_endpoint("parent", "GET", "/v1/parent/children/")
        print(f"GET /parent/children/ - Status: {status}")

    def test_profile_endpoints(self):
        """Test profile endpoints across roles"""
        print("\n=== TESTING PROFILE ENDPOINTS ===")

        for role in ["student", "teacher", "tutor", "parent"]:
            if not self.login(role):
                continue

            status, data = self.get_endpoint(role, "GET", "/auth/profile/")
            print(f"GET /auth/profile/ ({role}) - Status: {status}")
            if status == 200:
                if isinstance(data, dict):
                    print(f"  - OK, keys: {list(data.keys())[:5]}")
                else:
                    self.log_issue("PROFILE_INVALID_FORMAT", "MEDIUM", "/auth/profile/", status,
                                 f"Type is {type(data)} not dict",
                                 f"GET /auth/profile/ as {role}",
                                 "Should return JSON object",
                                 f"Got {type(data)}")

    def test_materials_endpoints(self):
        """Test materials endpoints"""
        print("\n=== TESTING MATERIALS ENDPOINTS ===")

        for role in ["student", "teacher"]:
            if not self.login(role):
                continue

            status, data = self.get_endpoint(role, "GET", "/v1/materials/")
            print(f"GET /materials/ ({role}) - Status: {status}")

    def test_assignments_endpoints(self):
        """Test assignments endpoints"""
        print("\n=== TESTING ASSIGNMENTS ENDPOINTS ===")

        for role in ["student", "teacher"]:
            if not self.login(role):
                continue

            status, data = self.get_endpoint(role, "GET", "/v1/assignments/")
            print(f"GET /assignments/ ({role}) - Status: {status}")

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("THE_BOT PLATFORM - API ENDPOINT TESTING")
        print(f"Base URL: {self.base_url}")
        print(f"Started at: {datetime.now()}")
        print("=" * 60)

        self.test_auth_failures()
        time.sleep(1)

        self.test_admin_endpoints()
        time.sleep(1)

        self.test_teacher_endpoints()
        time.sleep(1)

        self.test_student_endpoints()
        time.sleep(1)

        self.test_tutor_endpoints()
        time.sleep(1)

        self.test_parent_endpoints()
        time.sleep(1)

        self.test_profile_endpoints()
        time.sleep(1)

        self.test_materials_endpoints()
        time.sleep(1)

        self.test_assignments_endpoints()

        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total_tests - passed

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Issues Found: {len(self.issues)}")

        if self.issues:
            print("\n" + "=" * 60)
            print("ISSUES FOUND")
            print("=" * 60)

            for i, issue in enumerate(self.issues, 1):
                print(f"\nISSUE #{i}: {issue['type']}")
                print(f"  Severity: {issue['severity']}")
                print(f"  Endpoint: {issue['endpoint']}")
                print(f"  Status: {issue['status']}")
                print(f"  Error: {issue['error_text']}")
                print(f"  How to reproduce: {issue['how_to_reproduce']}")
                print(f"  Expected: {issue['expected_behavior']}")
                print(f"  Actual: {issue['actual_behavior']}")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
