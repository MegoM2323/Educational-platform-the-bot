#!/usr/bin/env python
"""Validate specific fixes mentioned in the changelog"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from materials.models import Subject, SubjectEnrollment
import json

User = get_user_model()
print("\n" + "="*70)
print("VALIDATION OF SPECIFIC FIXES")
print("="*70 + "\n")

# Get test users
student = User.objects.get(email="student1@test.com")
teacher = User.objects.get(email="teacher1@test.com")
teacher_token = Token.objects.get_or_create(user=teacher)[0].key

with override_settings(ALLOWED_HOSTS=['*']):
    client = Client(SERVER_NAME='127.0.0.1')

    # Fix 1: Time validation in lessons
    print("[1] Time Validation Fix (H1)")
    print("-" * 70)
    enrollment = SubjectEnrollment.objects.filter(teacher=teacher, student=student).first()
    if enrollment:
        subject = enrollment.subject
        
        # Test 1: Valid time (start < end)
        data = {
            "subject": subject.id,
            "student": student.id,
            "date": "2026-03-01",
            "start_time": "14:00:00",
            "end_time": "15:00:00"
        }
        r = client.post('/api/scheduling/lessons/',
                       data=json.dumps(data),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=f'Token {teacher_token}')
        print(f"  Valid time (14:00-15:00): Status {r.status_code} {'✓' if r.status_code in [200, 201] else '✗'}")
        
        # Test 2: Invalid time (start > end)
        data['start_time'] = "15:00:00"
        data['end_time'] = "14:00:00"
        data['date'] = "2026-03-02"
        r = client.post('/api/scheduling/lessons/',
                       data=json.dumps(data),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=f'Token {teacher_token}')
        print(f"  Invalid time (15:00-14:00): Status {r.status_code} {'✓' if r.status_code == 400 else '✗'}")
        
        # Test 3: Equal time (start == end)
        data['start_time'] = "14:00:00"
        data['end_time'] = "14:00:00"
        data['date'] = "2026-03-03"
        r = client.post('/api/scheduling/lessons/',
                       data=json.dumps(data),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=f'Token {teacher_token}')
        print(f"  Equal time (14:00-14:00): Status {r.status_code} {'✓' if r.status_code == 400 else '✗'}")

    # Fix 2: Permission enforcement
    print("\n[2] Permission Enforcement Fix (H2)")
    print("-" * 70)
    
    # Student tries to access teacher endpoint
    student_token = Token.objects.get_or_create(user=student)[0].key
    r = client.post('/api/scheduling/lessons/',
                   data=json.dumps({}),
                   content_type='application/json',
                   HTTP_AUTHORIZATION=f'Token {student_token}')
    print(f"  Student create lesson: Status {r.status_code} {'✓' if r.status_code == 403 else '✗'} (expected 403)")
    
    # Fix 3: Subject enrollment validation
    print("\n[3] Subject Enrollment Validation (H3)")
    print("-" * 70)
    
    # Get a subject NOT taught by teacher to student1
    all_subjects = Subject.objects.all()
    enrolled_subjects = SubjectEnrollment.objects.filter(teacher=teacher, student=student).values_list('subject_id', flat=True)
    
    # Find a subject not in the enrollment
    non_enrolled_subject = all_subjects.exclude(id__in=enrolled_subjects).first()
    if non_enrolled_subject:
        data = {
            "subject": non_enrolled_subject.id,
            "student": student.id,
            "date": "2026-03-04",
            "start_time": "16:00:00",
            "end_time": "17:00:00"
        }
        r = client.post('/api/scheduling/lessons/',
                       data=json.dumps(data),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=f'Token {teacher_token}')
        print(f"  Teacher creates lesson for non-enrolled subject: Status {r.status_code} {'✓' if r.status_code == 403 else '✗'}")
    else:
        print(f"  Teacher creates lesson for non-enrolled subject: SKIP (all subjects enrolled)")

    # Fix 4: CORS protection
    print("\n[4] CORS Protection (H4)")
    print("-" * 70)
    from django.conf import settings
    print(f"  DEBUG mode: {settings.DEBUG}")
    print(f"  CORS_ALLOW_ALL_ORIGINS: {settings.CORS_ALLOW_ALL_ORIGINS}")
    print(f"  CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}")
    print(f"  ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"  ✓ CORS properly configured" if not settings.CORS_ALLOW_ALL_ORIGINS else "✗ CORS too permissive")

print("\n" + "="*70)
print("VALIDATION COMPLETE")
print("="*70 + "\n")

