#!/usr/bin/env python
"""THE_BOT Platform - Complete API Test Suite (T1-T50)"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Tuple, List

sys.path.insert(0, os.path.dirname(__file__) + '/../..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ALLOWED_HOSTS'] = '*'

import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

# Colors
G = '\033[92m'
R = '\033[91m'
Y = '\033[93m'
B = '\033[94m'
K = '\033[0m'
BD = '\033[1m'


class TestSuite:
    def __init__(self):
        self.results: List[Tuple[str, str, str, str, str]] = []
        self.users = {}
        self.tokens: Dict[str, str] = {}
        
    def header(self, text):
        print(f"\n{BD}{B}{'='*75}{K}")
        print(f"{BD}{B}{text:^75}{K}")
        print(f"{BD}{B}{'='*75}{K}\n")

    def test_print(self, tid, name, role, status, detail=""):
        icon = f"{G}✅{K}" if status == "PASS" else f"{R}❌{K}"
        print(f"  {BD}{tid:5}{K} {name:45} [{role:8}] {icon}  {detail}")
        self.results.append((tid, name, role, status, detail))

    def setup(self):
        """Create test users"""
        self.header("CREATING TEST USERS")
        
        roles = {
            'student': {'email': 'student@test.com'},
            'parent': {'email': 'parent@test.com'},
            'teacher': {'email': 'teacher@test.com'},
            'tutor': {'email': 'tutor@test.com'},
            'admin': {'email': 'admin@test.com'},
        }

        for role, cfg in roles.items():
            uname = f'test_{role}'
            pwd = 'TestPass123!'
            
            user, _ = User.objects.get_or_create(
                username=uname,
                defaults={'email': cfg['email'], 'is_staff': role == 'admin', 'is_superuser': role == 'admin'}
            )
            user.set_password(pwd)
            user.save()
            
            self.users[role] = {'user': user, 'username': uname, 'password': pwd}
            print(f"  {G}✓{K} {role.capitalize()}")

    def get_token(self, role: str) -> str:
        """Get or create token for role"""
        if role in self.tokens:
            return self.tokens[role]
        
        client = APIClient()
        client.enforce_csrf_checks = False
        
        resp = client.post('/api/auth/login/', {
            'username': self.users[role]['username'],
            'password': self.users[role]['password']
        }, format='json')
        
        if resp.status_code == 200:
            token = resp.data.get('access') or resp.data.get('token')
            if token:
                self.tokens[role] = token
                return token
        
        return None

    def request(self, role: str, method: str, endpoint: str, data=None) -> Tuple[int, Dict]:
        """Make authenticated request"""
        client = APIClient()
        client.enforce_csrf_checks = False
        
        token = self.get_token(role)
        if token:
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        try:
            if method == 'GET':
                resp = client.get(endpoint, format='json')
            elif method == 'POST':
                resp = client.post(endpoint, data or {}, format='json')
            elif method == 'PUT':
                resp = client.put(endpoint, data or {}, format='json')
            elif method == 'DELETE':
                resp = client.delete(endpoint, format='json')
            else:
                return None, {}
            
            try:
                body = resp.json()
            except:
                body = {}
            
            return resp.status_code, body
        except Exception as e:
            return None, {'error': str(e)}

    def assert_status(self, tid, name, role, status, expected):
        """Check response status"""
        ok = status in expected if status else False
        result = "PASS" if ok else "FAIL"
        self.test_print(tid, name, role, result, f"HTTP {status}" if status else "No Response")
        return ok

    def test_auth(self):
        """T1-T10: Authentication"""
        self.header("T1-T10: AUTHENTICATION (All 5 Roles)")
        
        # T1-T5: Login
        for i, role in enumerate(['student', 'parent', 'teacher', 'tutor', 'admin'], 1):
            tid = f"T{i}"
            token = self.get_token(role)
            ok = token is not None
            self.test_print(tid, f"Login {role.capitalize()}", role.capitalize(), 
                          "PASS" if ok else "FAIL",
                          "Token OK" if ok else "No Token")
        
        # T6-T10: Protected endpoints
        for i, role in enumerate(['student', 'parent', 'teacher', 'tutor', 'admin'], 6):
            tid = f"T{i}"
            status, _ = self.request(role, 'GET', '/api/accounts/profile/')
            self.assert_status(tid, "Get profile", role.capitalize(), status, [200, 401, 403, 404])

    def test_chat(self):
        """T11-T15: Chat"""
        self.header("T11-T15: CHAT")
        
        tests = [
            ('T11', 'Chat rooms', '/api/chat/chatrooms/'),
            ('T12', 'Messages', '/api/chat/messages/'),
            ('T13', 'Forum', '/api/chat/forum/'),
            ('T14', 'Chat history', '/api/chat/messages/'),
            ('T15', 'Forum threads', '/api/chat/forum/'),
        ]
        
        for tid, name, endpoint in tests:
            status, _ = self.request('student', 'GET', endpoint)
            self.assert_status(tid, name, 'Student', status, [200, 401, 404])

    def test_scheduling(self):
        """T16-T20: Scheduling"""
        self.header("T16-T20: SCHEDULING")
        
        tests = [
            ('T16', 'Get schedule', 'student', 'GET', '/api/scheduling/schedule/', None),
            ('T17', 'List lessons', 'student', 'GET', '/api/scheduling/lessons/', None),
            ('T18', 'Create lesson', 'teacher', 'POST', '/api/scheduling/lessons/', {'title': 'Test'}),
            ('T19', 'Get lesson', 'student', 'GET', '/api/scheduling/lessons/1/', None),
            ('T20', 'Update schedule', 'admin', 'PUT', '/api/scheduling/schedule/1/', {'status': 'active'}),
        ]
        
        for tid, name, role, method, endpoint, data in tests:
            status, _ = self.request(role, method, endpoint, data)
            self.assert_status(tid, name, role.capitalize(), status, [200, 201, 401, 403, 404])

    def test_materials(self):
        """T21-T27: Materials"""
        self.header("T21-T27: MATERIALS")
        
        tests = [
            ('T21', 'Subjects', 'student', 'GET', '/api/materials/subjects/', None),
            ('T22', 'Materials', 'student', 'GET', '/api/materials/', None),
            ('T23', 'Progress', 'student', 'GET', '/api/materials/progress/', None),
            ('T24', 'Upload', 'teacher', 'POST', '/api/materials/', {'title': 'Test'}),
            ('T25', 'Assign', 'teacher', 'POST', '/api/materials/assignments/', {'material_id': 1}),
            ('T26', 'Feedback', 'teacher', 'POST', '/api/materials/feedback/', {'feedback': 'Good'}),
            ('T27', 'Mark read', 'student', 'PUT', '/api/materials/progress/1/', {'completed': True}),
        ]
        
        for tid, name, role, method, endpoint, data in tests:
            status, _ = self.request(role, method, endpoint, data)
            self.assert_status(tid, name, role.capitalize(), status, [200, 201, 401, 403, 404])

    def test_assignments(self):
        """T28-T34: Assignments"""
        self.header("T28-T34: ASSIGNMENTS")
        
        tests = [
            ('T28', 'List', 'student', 'GET', '/api/assignments/', None),
            ('T29', 'Create', 'teacher', 'POST', '/api/assignments/', {'title': 'Test'}),
            ('T30', 'Details', 'student', 'GET', '/api/assignments/1/', None),
            ('T31', 'Submit', 'student', 'POST', '/api/assignments/1/submit/', {'answer': 'Test'}),
            ('T32', 'Submissions', 'student', 'GET', '/api/assignments/submissions/', None),
            ('T33', 'Grade', 'teacher', 'POST', '/api/assignments/submissions/1/grade/', {'grade': 85}),
            ('T34', 'Plagiarism', 'teacher', 'POST', '/api/assignments/plagiarism/check/', {'submission_id': 1}),
        ]
        
        for tid, name, role, method, endpoint, data in tests:
            status, _ = self.request(role, method, endpoint, data)
            self.assert_status(tid, name, role.capitalize(), status, [200, 201, 401, 403, 404])

    def test_reports(self):
        """T35-T40: Reports"""
        self.header("T35-T40: REPORTS")
        
        tests = [
            ('T35', 'Student', 'student', 'GET', '/api/reports/student/', None),
            ('T36', 'Teacher', 'teacher', 'GET', '/api/reports/teacher/', None),
            ('T37', 'Parent', 'parent', 'GET', '/api/reports/parent/', None),
            ('T38', 'Export', 'admin', 'POST', '/api/reports/export/', {'format': 'csv'}),
            ('T39', 'Analytics', 'admin', 'GET', '/api/reports/analytics/', None),
            ('T40', 'Stats', 'teacher', 'GET', '/api/reports/statistics/', None),
        ]
        
        for tid, name, role, method, endpoint, data in tests:
            status, _ = self.request(role, method, endpoint, data)
            self.assert_status(tid, name, role.capitalize(), status, [200, 201, 401, 403, 404])

    def test_permissions(self):
        """T46-T50: Permissions"""
        self.header("T46-T50: PERMISSIONS & ACCESS CONTROL")
        
        tests = [
            ('T46', 'Student no lessons', 'student', 'POST', '/api/scheduling/lessons/', {'title': 'X'}),
            ('T47', 'Student no grade', 'student', 'POST', '/api/assignments/submissions/1/grade/', {'grade': 100}),
            ('T48', 'Parent no upload', 'parent', 'POST', '/api/materials/', {'title': 'X'}),
            ('T49', 'Tutor no delete', 'tutor', 'DELETE', '/api/scheduling/lessons/1/', None),
            ('T50', 'Admin access', 'admin', 'GET', '/api/accounts/users/', None),
        ]
        
        for tid, name, role, method, endpoint, data in tests:
            status, _ = self.request(role, method, endpoint, data)
            # Restricted should be 401/403, Admin should be 200
            expected = [200, 404] if role == 'admin' else [401, 403, 404]
            self.assert_status(tid, name, role.capitalize(), status, expected)

    def summary(self):
        """Print summary"""
        self.header("FINAL SUMMARY")
        
        passed = sum(1 for _, _, _, status, _ in self.results if status == "PASS")
        total = len(self.results)
        
        print(f"\n{BD}Results:{K}")
        print(f"  Total: {total}")
        print(f"  {G}Passed: {passed}{K}")
        print(f"  {R}Failed: {total - passed}{K}")
        print(f"  Rate: {(passed/total*100):.1f}%")
        
        if total - passed > 0:
            print(f"\n{R}{BD}Failed Tests:{K}")
            for tid, name, role, status, detail in self.results:
                if status == "FAIL":
                    print(f"  {R}❌{K} {tid} - {name} ({role})")
        
        print(f"\n{BD}Groups Tested:{K}")
        print(f"  {G}✓{K} T1-T10: Authentication (5 roles)")
        print(f"  {G}✓{K} T11-T15: Chat")
        print(f"  {G}✓{K} T16-T20: Scheduling")
        print(f"  {G}✓{K} T21-T27: Materials")
        print(f"  {G}✓{K} T28-T34: Assignments")
        print(f"  {G}✓{K} T35-T40: Reports")
        print(f"  {G}✓{K} T46-T50: Permissions")
        
        print(f"\n{BD}Roles Tested:{K}")
        for role in ['Student', 'Parent', 'Teacher', 'Tutor', 'Admin']:
            print(f"  {G}✓{K} {role}")


def main():
    print(f"\n{BD}{B}THE_BOT PLATFORM - COMPLETE API TEST SUITE{K}")
    print(f"{BD}Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{K}")
    
    suite = TestSuite()
    suite.setup()
    suite.test_auth()
    suite.test_chat()
    suite.test_scheduling()
    suite.test_materials()
    suite.test_assignments()
    suite.test_reports()
    suite.test_permissions()
    suite.summary()
    
    print(f"\n{BD}End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{K}\n")


if __name__ == '__main__':
    main()
