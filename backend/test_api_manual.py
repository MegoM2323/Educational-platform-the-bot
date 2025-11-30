#!/usr/bin/env python
"""Manual API testing script for scheduling endpoints."""

import os
import sys
import django
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ENVIRONMENT'] = 'test'

django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from materials.models import Subject
from scheduling.models import TeacherAvailability
from accounts.models import TeacherProfile

User = get_user_model()

# Create test user and token
teacher = User.objects.create_user(
    username='test_teacher',
    email='test_teacher@test.com',
    password='TestPass123!',
    role='teacher',
    first_name='Test',
    last_name='Teacher'
)
TeacherProfile.objects.create(user=teacher)
token = Token.objects.create(user=teacher)

# Create subject
subject = Subject.objects.create(name='Mathematics', description='Math test')

# Create API client
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

print("=" * 60)
print("Testing Availability API Endpoints")
print("=" * 60)

# Test 1: Create availability with subject_ids
print("\n1. Testing POST /api/scheduling/availability/")
print("   Creating availability template...")

payload = {
    'weekday': 1,  # Tuesday
    'start_time': '14:00',
    'end_time': '17:00',
    'slot_duration': 60,
    'max_students': 1,
    'subject_ids': [subject.id]
}

response = client.post(
    '/api/scheduling/availability/',
    payload,
    format='json'
)

print(f"   Status Code: {response.status_code}")
if response.status_code != 201:
    print(f"   ERROR: {response.data}")
else:
    print(f"   SUCCESS: Created availability {response.data.get('id')}")
    availability_id = response.data.get('id')

# Test 2: List availability
print("\n2. Testing GET /api/scheduling/availability/")
response = client.get('/api/scheduling/availability/')
print(f"   Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"   Found {response.data.get('count', 0)} availabilities")
else:
    print(f"   ERROR: {response.data}")

# Test 3: Generate slots
print("\n3. Testing POST /api/scheduling/availability/{id}/generate-slots/")
if response.status_code == 200 and 'availability_id' in locals():
    payload = {
        'start_date': '2025-11-27',
        'end_date': '2025-12-03',
        'force_regenerate': False
    }
    
    response = client.post(
        f'/api/scheduling/availability/{availability_id}/generate-slots/',
        payload,
        format='json'
    )
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"   SUCCESS: {response.data.get('message')}")
    else:
        print(f"   ERROR: {response.data}")

print("\n" + "=" * 60)
print("Testing Booking API Endpoints")
print("=" * 60)

# Create student for booking tests
student = User.objects.create_user(
    username='test_student',
    email='test_student@test.com',
    password='TestPass123!',
    role='student',
    first_name='Test',
    last_name='Student'
)
from accounts.models import StudentProfile
StudentProfile.objects.create(user=student)

student_token = Token.objects.create(user=student)
student_client = APIClient()
student_client.credentials(HTTP_AUTHORIZATION=f'Token {student_token.key}')

# Test 4: List time slots
print("\n4. Testing GET /api/scheduling/time-slots/")
response = student_client.get('/api/scheduling/time-slots/')
print(f"   Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"   Found {response.data.get('count', 0)} time slots")
else:
    print(f"   ERROR: {response.data}")

print("\n" + "=" * 60)
