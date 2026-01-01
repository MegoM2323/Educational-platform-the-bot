#!/usr/bin/env python
"""FINAL POST-FIX TESTING SUITE"""
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from materials.models import Subject, SubjectEnrollment

User = get_user_model()

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.start_time = datetime.now()

    def add_pass(self, name, details=""):
        self.passed.append(name)
        print(f"✓ {name}")

    def add_fail(self, name, error):
        self.failed.append((name, str(error)))
        print(f"✗ {name}: {error}")

    def summary(self):
        return {"passed": len(self.passed), "failed": len(self.failed), "total": len(self.passed) + len(self.failed)}

results = TestResults()

print("\n" + "="*70)
print("FINAL POST-FIX TESTING SUITE")
print("="*70 + "\n")

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

with override_settings(ALLOWED_HOSTS=['*']):
    client = Client(SERVER_NAME='127.0.0.1')

    # [1] AUTHENTICATION & PROFILES
    print("\n[1] Profile Tests")
    try:
        r = client.get('/api/profile/me/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Student profile GET")
        else:
            results.add_fail("Student profile GET", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Student profile GET", e)

    try:
        r = client.get('/api/profile/me/', HTTP_AUTHORIZATION=f'Token {teacher_token}')
        if r.status_code == 200:
            results.add_pass("Teacher profile GET")
        else:
            results.add_fail("Teacher profile GET", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Teacher profile GET", e)

    try:
        r = client.get('/api/profile/me/', HTTP_AUTHORIZATION=f'Token {admin_token}')
        if r.status_code == 200:
            results.add_pass("Admin profile GET")
        else:
            results.add_fail("Admin profile GET", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Admin profile GET", e)

    # [2] SCHEDULING TESTS
    print("\n[2] Scheduling Tests")
    try:
        r = client.get('/api/scheduling/lessons/', HTTP_AUTHORIZATION=f'Token {teacher_token}')
        if r.status_code == 200:
            results.add_pass("Teacher lessons list")
        else:
            results.add_fail("Teacher lessons list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Teacher lessons list", e)

    # Create valid lesson with correct subject
    try:
        enrollment = SubjectEnrollment.objects.filter(teacher=teacher, student=student).first()
        if enrollment:
            subject = enrollment.subject
            data = {
                "subject": subject.id,
                "student": student.id,
                "date": "2026-02-10",
                "start_time": "10:00:00",
                "end_time": "10:45:00",
            }
            r = client.post('/api/scheduling/lessons/', 
                           data=json.dumps(data),
                           content_type='application/json',
                           HTTP_AUTHORIZATION=f'Token {teacher_token}')
            if r.status_code in [200, 201]:
                results.add_pass("Create valid lesson")
            else:
                results.add_fail("Create valid lesson", f"Status: {r.status_code}")
        else:
            results.add_fail("Create valid lesson", "No subject enrollment found")
    except Exception as e:
        results.add_fail("Create valid lesson", e)

    # Reject invalid lesson
    try:
        enrollment = SubjectEnrollment.objects.filter(teacher=teacher).first()
        if enrollment:
            student2 = enrollment.student
            subject = enrollment.subject
            data = {
                "subject": subject.id,
                "student": student2.id,
                "date": "2026-02-10",
                "start_time": "11:00:00",
                "end_time": "10:00:00",
            }
            r = client.post('/api/scheduling/lessons/',
                           data=json.dumps(data),
                           content_type='application/json',
                           HTTP_AUTHORIZATION=f'Token {teacher_token}')
            if r.status_code == 400:
                results.add_pass("Reject invalid lesson (time validation)")
            else:
                results.add_fail("Reject invalid lesson", f"Expected 400, got {r.status_code}")
        else:
            results.add_fail("Reject invalid lesson", "No enrollment found")
    except Exception as e:
        results.add_fail("Reject invalid lesson", e)

    # [3] MATERIALS
    print("\n[3] Materials Tests")
    try:
        r = client.get('/api/materials/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Student materials list")
        else:
            results.add_fail("Student materials list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Student materials list", e)

    # [4] ASSIGNMENTS
    print("\n[4] Assignments Tests")
    try:
        r = client.get('/api/assignments/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Student assignments list")
        else:
            results.add_fail("Student assignments list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Student assignments list", e)

    # [5] CHAT
    print("\n[5] Chat Tests")
    try:
        r = client.get('/api/chat/rooms/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 200:
            results.add_pass("Chat rooms list")
        else:
            results.add_fail("Chat rooms list", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Chat rooms list", e)

    # [6] PERMISSIONS
    print("\n[6] Permission Tests")
    try:
        r = client.get('/api/admin/users/', HTTP_AUTHORIZATION=f'Token {student_token}')
        if r.status_code == 403:
            results.add_pass("Reject student access to admin")
        else:
            results.add_fail("Reject student access to admin", f"Expected 403, got {r.status_code}")
    except Exception as e:
        results.add_fail("Reject student access to admin", e)

    try:
        r = client.get('/api/admin/users/', HTTP_AUTHORIZATION=f'Token {admin_token}')
        if r.status_code == 200:
            results.add_pass("Admin access to admin endpoints")
        else:
            results.add_fail("Admin access to admin endpoints", f"Status: {r.status_code}")
    except Exception as e:
        results.add_fail("Admin access to admin endpoints", e)

    # [7] REGRESSION TESTS
    print("\n[7] Regression Tests")
    endpoints_to_test = [
        ('/api/profile/me/', 'GET', student_token, 'Get profile'),
        ('/api/materials/', 'GET', student_token, 'Get materials'),
        ('/api/assignments/', 'GET', student_token, 'Get assignments'),
        ('/api/chat/rooms/', 'GET', student_token, 'Get chat rooms'),
        ('/api/scheduling/lessons/', 'GET', teacher_token, 'Get lessons'),
    ]

    for endpoint, method, token, name in endpoints_to_test:
        try:
            if method == 'GET':
                r = client.get(endpoint, HTTP_AUTHORIZATION=f'Token {token}')
            if r.status_code == 200:
                results.add_pass(f"Regression: {name}")
            else:
                results.add_fail(f"Regression: {name}", f"Status: {r.status_code}")
        except Exception as e:
            results.add_fail(f"Regression: {name}", e)

# Summary
print("\n" + "="*70)
summary = results.summary()
print(f"PASSED: {summary['passed']}/{summary['total']}")
print(f"FAILED: {summary['failed']}/{summary['total']}")
if summary['total'] > 0:
    print(f"Success Rate: {(summary['passed']/summary['total']*100):.1f}%")
print("="*70)

status = "PASSED" if summary['failed'] == 0 else "FAILED"
print(f"\nOverall Status: {status}")

if results.failed:
    print("\nFailed tests:")
    for name, error in results.failed:
        print(f"  - {name}: {error}")

