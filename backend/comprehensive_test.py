#!/usr/bin/env python
"""POST-FIX TESTING SUITE with proper endpoint paths"""
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from materials.models import Subject

User = get_user_model()

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.start_time = datetime.now()

    def add_pass(self, name):
        self.passed.append(name)
        print(f"✓ {name}")

    def add_fail(self, name, error):
        self.failed.append((name, str(error)))
        print(f"✗ {name}: {error}")

    def summary(self):
        return {"passed": len(self.passed), "failed": len(self.failed), "total": len(self.passed) + len(self.failed)}

results = TestResults()

print("\n" + "="*70)
print("COMPREHENSIVE POST-FIX TESTING")
print("="*70 + "\n")

# Get tokens for all roles
try:
    student = User.objects.get(email="student1@test.com")
    teacher = User.objects.get(email="teacher1@test.com")
    admin = User.objects.get(email="admin@test.com")

    student_token = Token.objects.get_or_create(user=student)[0].key
    teacher_token = Token.objects.get_or_create(user=teacher)[0].key
    admin_token = Token.objects.get_or_create(user=admin)[0].key

    results.add_pass("Tokens created for all roles")
except Exception as e:
    results.add_fail("Get tokens", e)
    exit(1)

# Using Django test client with proper SERVER_NAME
with override_settings(ALLOWED_HOSTS=['*']):
    client = Client(SERVER_NAME='127.0.0.1')

    # Test 1: Student Profile - use /me/ endpoint
    print("\n[1] Profile Tests")
    try:
        r = client.get('/api/profile/me/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Student profile GET")
        else:
            results.add_fail("Student profile GET", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Student profile GET", e)

    # Test 2: Lessons List
    print("\n[2] Scheduling Tests")
    try:
        r = client.get('/api/scheduling/lessons/', HTTP_AUTHORIZATION=f'Token {teacher_token}')
        if r.status_code == 200:
            results.add_pass("Teacher lessons list")
        else:
            results.add_fail("Teacher lessons list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Teacher lessons list", e)

    # Test 3: Create Valid Lesson
    try:
        subject = Subject.objects.first()
        student_obj = User.objects.get(email="student1@test.com")
        data = {
            "subject": subject.id if subject else 1,
            "student": student_obj.id,
            "date": "2026-01-25",
            "start_time": "09:00:00",
            "end_time": "09:45:00",
        }
        import json as json_lib
        r = client.post('/api/scheduling/lessons/', 
                       data=json_lib.dumps(data),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=f'Token {teacher_token}')
        if r.status_code in [200, 201]:
            results.add_pass("Create valid lesson")
        else:
            results.add_fail("Create valid lesson", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Create valid lesson", e)

    # Test 4: Reject Invalid Lesson (time validation)
    try:
        subject = Subject.objects.first()
        student_obj = User.objects.get(email="student2@test.com")
        data = {
            "subject": subject.id if subject else 1,
            "student": student_obj.id,
            "date": "2026-01-25",
            "start_time": "10:00:00",
            "end_time": "09:00:00",
        }
        import json as json_lib
        r = client.post('/api/scheduling/lessons/',
                       data=json_lib.dumps(data),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=f'Token {teacher_token}')
        if r.status_code == 400:
            results.add_pass("Reject invalid lesson (time validation)")
        else:
            results.add_fail("Reject invalid lesson", f"Status: {r.status_code}, expected 400")
    except Exception as e:
        results.add_fail("Reject invalid lesson", e)

    # Test 5: Materials
    print("\n[3] Materials Tests")
    try:
        r = client.get('/api/materials/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Student materials list")
        else:
            results.add_fail("Student materials list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Student materials list", e)

    # Test 6: Assignments
    print("\n[4] Assignments Tests")
    try:
        r = client.get('/api/assignments/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Student assignments list")
        else:
            results.add_fail("Student assignments list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Student assignments list", e)

    # Test 7: Chat Rooms - use correct endpoint
    print("\n[5] Chat Tests")
    try:
        r = client.get('/api/chat/rooms/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Chat rooms list")
        else:
            results.add_fail("Chat rooms list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Chat rooms list", e)

    # Test 8: Permissions - Student should not access admin
    print("\n[6] Permission Tests")
    try:
        r = client.get('/api/admin/users/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 403:
            results.add_pass("Reject student access to admin")
        else:
            results.add_fail("Reject student access to admin", f"Expected 403, got {r.status_code}")
    except Exception as e:
        results.add_fail("Reject student access to admin", e)

    # Test 9: Admin access
    try:
        r = client.get('/api/admin/users/', HTTP_AUTHORIZATION=f'Token {admin_token}')
        if r.status_code == 200:
            results.add_pass("Admin access to admin endpoints")
        else:
            results.add_fail("Admin access to admin endpoints", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Admin access to admin endpoints", e)

    # Test 10: Teacher permissions
    print("\n[7] Additional Permission Tests")
    try:
        r = client.get('/api/scheduling/lessons/', HTTP_AUTHORIZATION=f'Token {teacher_token}')
        if r.status_code == 200:
            results.add_pass("Teacher can access scheduling")
        else:
            results.add_fail("Teacher can access scheduling", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Teacher can access scheduling", e)

# Summary
print("\n" + "="*70)
summary = results.summary()
print(f"PASSED: {summary['passed']}/{summary['total']}")
print(f"FAILED: {summary['failed']}/{summary['total']}")
print(f"Success Rate: {(summary['passed']/summary['total']*100):.1f}%" if summary['total'] > 0 else "N/A")
print("="*70 + "\n")

if results.failed:
    print("Failed tests:")
    for name, error in results.failed:
        print(f"  - {name}: {error}")

