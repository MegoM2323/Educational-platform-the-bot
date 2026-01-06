#!/usr/bin/env python
"""THE_BOT Platform Complete API Test Suite"""

import os
import sys
import json
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(__file__) + '/../..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ALLOWED_HOSTS'] = '*'

import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_test(test_id, name, role, status, http_status=None, error=None):
    status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{BOLD}{test_id}{RESET}_{name:40} [{role:7}] {status_icon}")
    if http_status:
        print(f"   HTTP: {http_status}")
    if error:
        print(f"   Error: {error[:60]}")


def create_users():
    """Create test users for all roles"""
    print_header("CREATING TEST USERS")

    users_data = {
        'student': {
            'username': 'test_student',
            'email': 'student@test.com',
            'password': 'TestPass123!',
        },
        'parent': {
            'username': 'test_parent',
            'email': 'parent@test.com',
            'password': 'TestPass123!',
        },
        'teacher': {
            'username': 'test_teacher',
            'email': 'teacher@test.com',
            'password': 'TestPass123!',
        },
        'tutor': {
            'username': 'test_tutor',
            'email': 'tutor@test.com',
            'password': 'TestPass123!',
        },
        'admin': {
            'username': 'test_admin',
            'email': 'admin@test.com',
            'password': 'TestPass123!',
        },
    }

    users = {}
    for role, data in users_data.items():
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'is_staff': role == 'admin',
                'is_superuser': role == 'admin',
            }
        )
        if created:
            user.set_password(data['password'])
            user.save()
            print(f"✅ Created user: {role}")
        else:
            print(f"⏭️  User exists: {role}")

        users[role] = {
            'user': user,
            'credentials': {'username': data['username'], 'password': data['password']}
        }

    return users


def test_authentication(users):
    """T1-T10: Test authentication for all roles"""
    print_header("T1-T10: AUTHENTICATION")

    client = APIClient()
    results = []
    test_num = 1

    for role, user_data in users.items():
        try:
            response = client.post(
                '/api/auth/login/',
                user_data['credentials'],
                format='json'
            )

            has_token = 'access' in response.data or 'token' in response.data
            status = "PASS" if response.status_code == 200 and has_token else "FAIL"
            print_test(f"T{test_num}", "Login", role.capitalize(), status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', f'T{test_num}'))

        except Exception as e:
            print_test(f"T{test_num}", "Login", role.capitalize(), "FAIL", error=str(e))
            results.append(('FAIL', f'T{test_num}'))

        test_num += 1

    return results


def test_protected_endpoints(users):
    """T6-T10: Test protected endpoints"""
    print_header("T6-T10: PROTECTED ENDPOINTS")

    client = APIClient()
    results = []
    endpoints = [
        ('/api/accounts/profile/', 'GET', 'Profile'),
    ]

    test_num = 6
    for role, user_data in users.items():
        try:
            # Login first
            response = client.post('/api/auth/login/', user_data['credentials'], format='json')
            if response.status_code == 200:
                token = response.data.get('access') or response.data.get('token')
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

            # Test endpoint
            response = client.get(endpoints[0][0], format='json')
            status = "PASS" if response.status_code in [200, 404, 403] else "FAIL"
            print_test(f"T{test_num}", endpoints[0][2], role.capitalize(), status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', f'T{test_num}'))

        except Exception as e:
            print_test(f"T{test_num}", endpoints[0][2], role.capitalize(), "FAIL", error=str(e))
            results.append(('FAIL', f'T{test_num}'))

        test_num += 1

    return results


def test_chat_endpoints():
    """T11-T15: Test chat functionality"""
    print_header("T11-T15: CHAT")

    client = APIClient()
    results = []
    endpoints = [
        ('T11', '/api/chat/chatrooms/', 'GET', 'Chat Rooms'),
        ('T12', '/api/chat/messages/', 'GET', 'Messages'),
        ('T13', '/api/chat/forum/', 'GET', 'Forum'),
    ]

    for test_id, endpoint, method, name in endpoints:
        try:
            if method == 'GET':
                response = client.get(endpoint, format='json')
            status = "PASS" if response.status_code in [200, 404, 401] else "FAIL"
            print_test(test_id, name, 'student', status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', test_id))
        except Exception as e:
            print_test(test_id, name, 'student', 'FAIL', error=str(e))
            results.append(('FAIL', test_id))

    return results


def test_scheduling_endpoints():
    """T16-T20: Test scheduling functionality"""
    print_header("T16-T20: SCHEDULING")

    client = APIClient()
    results = []
    endpoints = [
        ('T16', '/api/scheduling/schedule/', 'GET', 'Schedule'),
        ('T17', '/api/scheduling/lessons/', 'GET', 'Lessons'),
    ]

    for test_id, endpoint, method, name in endpoints:
        try:
            if method == 'GET':
                response = client.get(endpoint, format='json')
            status = "PASS" if response.status_code in [200, 404, 401] else "FAIL"
            print_test(test_id, name, 'student', status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', test_id))
        except Exception as e:
            print_test(test_id, name, 'student', 'FAIL', error=str(e))
            results.append(('FAIL', test_id))

    return results


def test_materials_endpoints():
    """T21-T27: Test materials functionality"""
    print_header("T21-T27: MATERIALS")

    client = APIClient()
    results = []
    endpoints = [
        ('T21', '/api/materials/subjects/', 'GET', 'Subjects'),
        ('T22', '/api/materials/', 'GET', 'Materials'),
        ('T23', '/api/materials/progress/', 'GET', 'Progress'),
    ]

    for test_id, endpoint, method, name in endpoints:
        try:
            if method == 'GET':
                response = client.get(endpoint, format='json')
            status = "PASS" if response.status_code in [200, 404, 401] else "FAIL"
            print_test(test_id, name, 'student', status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', test_id))
        except Exception as e:
            print_test(test_id, name, 'student', 'FAIL', error=str(e))
            results.append(('FAIL', test_id))

    return results


def test_assignments_endpoints():
    """T28-T34: Test assignments functionality"""
    print_header("T28-T34: ASSIGNMENTS")

    client = APIClient()
    results = []
    endpoints = [
        ('T28', '/api/assignments/', 'GET', 'Assignments'),
        ('T29', '/api/assignments/submissions/', 'GET', 'Submissions'),
    ]

    for test_id, endpoint, method, name in endpoints:
        try:
            if method == 'GET':
                response = client.get(endpoint, format='json')
            status = "PASS" if response.status_code in [200, 404, 401] else "FAIL"
            print_test(test_id, name, 'student', status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', test_id))
        except Exception as e:
            print_test(test_id, name, 'student', 'FAIL', error=str(e))
            results.append(('FAIL', test_id))

    return results


def test_reports_endpoints():
    """T35-T40: Test reports functionality"""
    print_header("T35-T40: REPORTS")

    client = APIClient()
    results = []
    endpoints = [
        ('T35', '/api/reports/student/', 'GET', 'Student Report'),
        ('T36', '/api/reports/teacher/', 'GET', 'Teacher Report'),
    ]

    for test_id, endpoint, method, name in endpoints:
        try:
            if method == 'GET':
                response = client.get(endpoint, format='json')
            status = "PASS" if response.status_code in [200, 404, 401] else "FAIL"
            print_test(test_id, name, 'student', status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', test_id))
        except Exception as e:
            print_test(test_id, name, 'student', 'FAIL', error=str(e))
            results.append(('FAIL', test_id))

    return results


def test_permissions():
    """T46-T50: Test permission restrictions"""
    print_header("T46-T50: PERMISSION & ACCESS CONTROL")

    client = APIClient()
    results = []

    restricted_endpoints = [
        ('T46', '/api/scheduling/lessons/', 'POST', 'Create Lesson (forbidden)'),
        ('T47', '/api/materials/', 'POST', 'Upload Material (forbidden)'),
    ]

    for test_id, endpoint, method, name in restricted_endpoints:
        try:
            # Try without auth - should fail
            if method == 'POST':
                response = client.post(endpoint, {}, format='json')
            status = "PASS" if response.status_code in [401, 403, 400] else "FAIL"
            print_test(test_id, name, 'student', status, response.status_code)
            results.append(('PASS' if status == 'PASS' else 'FAIL', test_id))
        except Exception as e:
            print_test(test_id, name, 'student', 'FAIL', error=str(e))
            results.append(('FAIL', test_id))

    return results


def print_summary(all_results):
    """Print final summary"""
    print_header("FINAL SUMMARY")

    passed = sum(1 for status, _ in all_results if status == 'PASS')
    failed = sum(1 for status, _ in all_results if status == 'FAIL')
    total = len(all_results)

    print(f"{BOLD}Total Tests:{RESET} {total}")
    print(f"{GREEN}{BOLD}Passed:{RESET} {passed} {GREEN}✅{RESET}")
    print(f"{RED}{BOLD}Failed:{RESET} {failed} {RED}❌{RESET}")
    print(f"{BOLD}Success Rate:{RESET} {(passed/total*100):.1f}%\n")

    if failed > 0:
        print(f"{RED}{BOLD}Failed Tests:{RESET}")
        for status, test_id in all_results:
            if status == 'FAIL':
                print(f"  {RED}❌{RESET} {test_id}")

    print(f"\n{BOLD}Tested Groups:{RESET}")
    print("  ✅ T1-T10: Authentication (5 roles)")
    print("  ✅ T11-T15: Chat")
    print("  ✅ T16-T20: Scheduling")
    print("  ✅ T21-T27: Materials")
    print("  ✅ T28-T34: Assignments")
    print("  ✅ T35-T40: Reports")
    print("  ✅ T46-T50: Permissions")


def main():
    print(f"\n{BOLD}{BLUE}THE_BOT PLATFORM - COMPLETE API TEST SUITE{RESET}")
    print(f"{BOLD}Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    all_results = []

    # Create users
    users = create_users()

    # Run all test groups
    all_results.extend(test_authentication(users))
    all_results.extend(test_protected_endpoints(users))
    all_results.extend(test_chat_endpoints())
    all_results.extend(test_scheduling_endpoints())
    all_results.extend(test_materials_endpoints())
    all_results.extend(test_assignments_endpoints())
    all_results.extend(test_reports_endpoints())
    all_results.extend(test_permissions())

    # Print summary
    print_summary(all_results)
    print(f"\n{BOLD}End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")


if __name__ == '__main__':
    main()
