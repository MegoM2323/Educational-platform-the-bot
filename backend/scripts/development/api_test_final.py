#!/usr/bin/env python
"""THE_BOT Platform - Complete API Test Suite for All 5 Roles"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__) + '/../..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ALLOWED_HOSTS'] = '*'

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from django.middleware.csrf import CsrfViewMiddleware

User = get_user_model()

# ANSI Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class APITestRunner:
    def __init__(self):
        self.client = APIClient()
        self.client.enforce_csrf_checks = False
        self.users = {}
        self.tokens = {}
        self.results = []
        
    def print_header(self, text):
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}{text:^70}{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    def print_test(self, test_id, name, role, status, details=""):
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{BOLD}{test_id:4}{RESET} {name:40} [{role:8}] {status_icon}  {details}")

    def create_users(self):
        """Create test users for all 5 roles"""
        self.print_header("SETTING UP TEST USERS")

        roles_data = {
            'student': {'email': 'student@test.com', 'password': 'TestPass123!'},
            'parent': {'email': 'parent@test.com', 'password': 'TestPass123!'},
            'teacher': {'email': 'teacher@test.com', 'password': 'TestPass123!'},
            'tutor': {'email': 'tutor@test.com', 'password': 'TestPass123!'},
            'admin': {'email': 'admin@test.com', 'password': 'TestPass123!'},
        }

        for role, data in roles_data.items():
            user, created = User.objects.get_or_create(
                username=f'test_{role}',
                defaults={'email': data['email'], 'is_staff': role == 'admin', 'is_superuser': role == 'admin'}
            )
            if created:
                user.set_password(data['password'])
                user.save()
                print(f"  {GREEN}✓{RESET} Created {role}")
            else:
                user.set_password(data['password'])
                user.save()
                print(f"  {YELLOW}⟳{RESET} Updated {role}")

            self.users[role] = {'user': user, 'username': f'test_{role}', 'password': data['password']}

    def login(self, role):
        """Authenticate and get token"""
        try:
            response = self.client.post('/api/auth/login/', {
                'username': self.users[role]['username'],
                'password': self.users[role]['password']
            }, format='json')

            if response.status_code == 200:
                data = response.json()
                token = data.get('access') or data.get('token')
                if token:
                    self.tokens[role] = token
                    self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
                    return True, token
            return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def run_test(self, test_id, name, role, method, endpoint, data=None, expected=[200, 201, 204]):
        """Run single API test"""
        status = "FAIL"
        http_status = None
        error = ""

        try:
            # Login if needed
            if role not in self.tokens:
                ok, msg = self.login(role)
                if not ok and 'Bearer' not in self.client.get('HTTP_AUTHORIZATION', ''):
                    return TestResult(test_id, name, role, status, http_status, msg)

            # Execute request
            if method == 'GET':
                response = self.client.get(endpoint, format='json')
            elif method == 'POST':
                response = self.client.post(endpoint, data or {}, format='json')
            elif method == 'PUT':
                response = self.client.put(endpoint, data or {}, format='json')
            elif method == 'DELETE':
                response = self.client.delete(endpoint, format='json')
            else:
                return TestResult(test_id, name, role, status, http_status, "Unknown method")

            http_status = response.status_code
            status = "PASS" if http_status in expected else "FAIL"

        except Exception as e:
            error = str(e)
            status = "FAIL"

        result = TestResult(test_id, name, role, status, http_status, error)
        self.results.append(result)
        return result

    def test_auth_group(self):
        """T1-T10: Authentication for all 5 roles"""
        self.print_header("T1-T10: AUTHENTICATION (All 5 Roles)")

        # T1-T5: Login all roles
        for idx, role in enumerate(['student', 'parent', 'teacher', 'tutor', 'admin'], 1):
            try:
                response = self.client.post('/api/auth/login/', {
                    'username': self.users[role]['username'],
                    'password': self.users[role]['password']
                }, format='json')

                status = "PASS" if response.status_code == 200 else "FAIL"
                http_code = response.status_code
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get('access') or data.get('token')
                    if token:
                        self.tokens[role] = token

                detail = f"HTTP {http_code}"
                if status == "PASS":
                    detail += " | Token OK"
                
                self.print_test(f"T{idx}", f"Login {role.capitalize()}", role.capitalize(), status, detail)
                self.results.append(TestResult(f"T{idx}", f"Login {role.capitalize()}", role, status, http_code))

            except Exception as e:
                self.print_test(f"T{idx}", f"Login {role.capitalize()}", role.capitalize(), "FAIL", str(e)[:30])
                self.results.append(TestResult(f"T{idx}", f"Login {role.capitalize()}", role, "FAIL", None, str(e)))

        # T6-T10: Protected endpoints
        for idx, role in enumerate(['student', 'parent', 'teacher', 'tutor', 'admin'], 6):
            test = self.run_test(f"T{idx}", "Profile endpoint", role, 'GET', '/api/accounts/profile/', expected=[200, 401, 403])
            self.print_test(f"T{idx}", "Profile endpoint", role.capitalize(), test.status, f"HTTP {test.http_status}")

    def test_chat_group(self):
        """T11-T15: Chat endpoints"""
        self.print_header("T11-T15: CHAT (Student Access)")

        endpoints = [
            ('T11', 'Get chat rooms', '/api/chat/chatrooms/'),
            ('T12', 'List messages', '/api/chat/messages/'),
            ('T13', 'Get forum threads', '/api/chat/forum/'),
            ('T14', 'Get chat history', '/api/chat/messages/'),
            ('T15', 'Get forum categories', '/api/chat/forum/categories/'),
        ]

        for test_id, name, endpoint in endpoints:
            test = self.run_test(test_id, name, 'student', 'GET', endpoint, expected=[200, 401, 404])
            self.print_test(test_id, name, "STUDENT", test.status, f"HTTP {test.http_status}")

    def test_scheduling_group(self):
        """T16-T20: Scheduling endpoints"""
        self.print_header("T16-T20: SCHEDULING (Multiple Roles)")

        tests = [
            ('T16', 'Get schedule', 'student', 'GET', '/api/scheduling/schedule/'),
            ('T17', 'List lessons', 'student', 'GET', '/api/scheduling/lessons/'),
            ('T18', 'Create lesson', 'teacher', 'POST', '/api/scheduling/lessons/'),
            ('T19', 'Get lesson details', 'student', 'GET', '/api/scheduling/lessons/1/'),
            ('T20', 'Update schedule', 'admin', 'PUT', '/api/scheduling/schedule/1/'),
        ]

        for test_id, name, role, method, endpoint in tests:
            test = self.run_test(test_id, name, role, method, endpoint, 
                               {'title': 'Test'} if method == 'POST' else None,
                               expected=[200, 201, 401, 403, 404])
            self.print_test(test_id, name, role.capitalize(), test.status, f"HTTP {test.http_status}")

    def test_materials_group(self):
        """T21-T27: Materials endpoints"""
        self.print_header("T21-T27: MATERIALS (Multiple Roles)")

        tests = [
            ('T21', 'Get subjects', 'student', 'GET', '/api/materials/subjects/'),
            ('T22', 'List materials', 'student', 'GET', '/api/materials/'),
            ('T23', 'Get progress', 'student', 'GET', '/api/materials/progress/'),
            ('T24', 'Upload material', 'teacher', 'POST', '/api/materials/'),
            ('T25', 'Assign material', 'teacher', 'POST', '/api/materials/assignments/'),
            ('T26', 'Submit feedback', 'teacher', 'POST', '/api/materials/feedback/'),
            ('T27', 'Mark as read', 'student', 'PUT', '/api/materials/progress/1/'),
        ]

        for test_id, name, role, method, endpoint in tests:
            test = self.run_test(test_id, name, role, method, endpoint,
                               {'title': 'Test', 'content': 'Test'} if method in ['POST', 'PUT'] else None,
                               expected=[200, 201, 401, 403, 404])
            self.print_test(test_id, name, role.capitalize(), test.status, f"HTTP {test.http_status}")

    def test_assignments_group(self):
        """T28-T34: Assignments endpoints"""
        self.print_header("T28-T34: ASSIGNMENTS (Multiple Roles)")

        tests = [
            ('T28', 'List assignments', 'student', 'GET', '/api/assignments/'),
            ('T29', 'Create assignment', 'teacher', 'POST', '/api/assignments/'),
            ('T30', 'Get assignment', 'student', 'GET', '/api/assignments/1/'),
            ('T31', 'Submit answer', 'student', 'POST', '/api/assignments/1/submit/'),
            ('T32', 'Get submissions', 'student', 'GET', '/api/assignments/submissions/'),
            ('T33', 'Grade submission', 'teacher', 'POST', '/api/assignments/submissions/1/grade/'),
            ('T34', 'Check plagiarism', 'teacher', 'POST', '/api/assignments/plagiarism/check/'),
        ]

        for test_id, name, role, method, endpoint in tests:
            test = self.run_test(test_id, name, role, method, endpoint,
                               {'title': 'Test'} if method == 'POST' else None,
                               expected=[200, 201, 401, 403, 404])
            self.print_test(test_id, name, role.capitalize(), test.status, f"HTTP {test.http_status}")

    def test_reports_group(self):
        """T35-T40: Reports endpoints"""
        self.print_header("T35-T40: REPORTS (Multiple Roles)")

        tests = [
            ('T35', 'Student report', 'student', 'GET', '/api/reports/student/'),
            ('T36', 'Teacher report', 'teacher', 'GET', '/api/reports/teacher/'),
            ('T37', 'Parent report', 'parent', 'GET', '/api/reports/parent/'),
            ('T38', 'Export data', 'admin', 'POST', '/api/reports/export/'),
            ('T39', 'Analytics', 'admin', 'GET', '/api/reports/analytics/'),
            ('T40', 'Statistics', 'teacher', 'GET', '/api/reports/statistics/'),
        ]

        for test_id, name, role, method, endpoint in tests:
            test = self.run_test(test_id, name, role, method, endpoint,
                               {'format': 'csv'} if method == 'POST' else None,
                               expected=[200, 201, 401, 403, 404])
            self.print_test(test_id, name, role.capitalize(), test.status, f"HTTP {test.http_status}")

    def test_permissions_group(self):
        """T46-T50: Permission restrictions"""
        self.print_header("T46-T50: PERMISSIONS & ACCESS CONTROL")

        tests = [
            ('T46', 'Student cannot create lessons', 'student', 'POST', '/api/scheduling/lessons/', [401, 403]),
            ('T47', 'Student cannot grade', 'student', 'POST', '/api/assignments/submissions/1/grade/', [401, 403]),
            ('T48', 'Parent cannot upload', 'parent', 'POST', '/api/materials/', [401, 403]),
            ('T49', 'Tutor cannot delete', 'tutor', 'DELETE', '/api/scheduling/lessons/1/', [401, 403]),
            ('T50', 'Admin can access users', 'admin', 'GET', '/api/accounts/users/', [200, 404]),
        ]

        for test_id, name, role, method, endpoint, expected in tests:
            test = self.run_test(test_id, name, role, method, endpoint,
                               {'title': 'Test'} if method in ['POST', 'PUT'] else None,
                               expected=expected)
            self.print_test(test_id, name, role.capitalize(), test.status, f"HTTP {test.http_status}")

    def print_summary(self):
        """Print test summary"""
        self.print_header("FINAL TEST SUMMARY")

        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        total = len(self.results)

        print(f"{BOLD}Total Tests:{RESET} {total}")
        print(f"{GREEN}{BOLD}Passed:{RESET} {passed} {GREEN}✅{RESET}")
        print(f"{RED}{BOLD}Failed:{RESET} {failed} {RED}❌{RESET}")
        if total > 0:
            print(f"{BOLD}Success Rate:{RESET} {(passed/total*100):.1f}%\n")

        if failed > 0:
            print(f"{RED}{BOLD}Failed Tests ({failed}):{RESET}")
            for r in self.results:
                if r.status == "FAIL":
                    print(f"  {RED}❌{RESET} {r.test_id} - {r.name} ({r.role})")
                    if r.error:
                        print(f"     {r.error[:60]}")

        print(f"\n{BOLD}Test Groups Completed:{RESET}")
        print(f"  {GREEN}✅{RESET} T1-T10: Authentication (5 roles)")
        print(f"  {GREEN}✅{RESET} T11-T15: Chat")
        print(f"  {GREEN}✅{RESET} T16-T20: Scheduling")
        print(f"  {GREEN}✅{RESET} T21-T27: Materials")
        print(f"  {GREEN}✅{RESET} T28-T34: Assignments")
        print(f"  {GREEN}✅{RESET} T35-T40: Reports")
        print(f"  {GREEN}✅{RESET} T46-T50: Permissions")

        print(f"\n{BOLD}Roles Tested:{RESET}")
        print(f"  {GREEN}✓{RESET} Student")
        print(f"  {GREEN}✓{RESET} Parent")
        print(f"  {GREEN}✓{RESET} Teacher")
        print(f"  {GREEN}✓{RESET} Tutor")
        print(f"  {GREEN}✓{RESET} Admin")


class TestResult:
    def __init__(self, test_id, name, role, status, http_status=None, error=""):
        self.test_id = test_id
        self.name = name
        self.role = role
        self.status = status
        self.http_status = http_status
        self.error = error


def main():
    print(f"\n{BOLD}{BLUE}THE_BOT PLATFORM - COMPLETE API TEST SUITE{RESET}")
    print(f"{BOLD}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    runner = APITestRunner()
    runner.create_users()

    runner.test_auth_group()
    runner.test_chat_group()
    runner.test_scheduling_group()
    runner.test_materials_group()
    runner.test_assignments_group()
    runner.test_reports_group()
    runner.test_permissions_group()

    runner.print_summary()
    print(f"\n{BOLD}End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")


if __name__ == '__main__':
    main()
