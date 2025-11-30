#!/usr/bin/env python
"""Test profile API endpoints"""
import os
import sys
import django
from django.test import Client

# Setup Django
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

# Create test client
client = Client()

def test_profile_endpoints():
    print("Testing Profile API Endpoints\n")

    # Test without authentication
    print("1. Testing /api/profile/student/ without auth:")
    response = client.get('/api/profile/student/')
    print(f"   Status: {response.status_code}")
    if response.status_code != 401:
        print(f"   Response: {response.json()}")
    print()

    # Login as student
    print("2. Testing login as student:")
    try:
        # Get or create test student
        student = User.objects.filter(email='student@test.com').first()
        if student:
            print(f"   Found student: {student.email}")
            # Force login
            client.force_login(student)

            print("\n3. Testing /api/profile/student/ with auth:")
            response = client.get('/api/profile/student/')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   User data: {data.get('user', {}).get('email')}")
                print(f"   Profile exists: {'profile' in data}")
            else:
                print(f"   Response: {response.json()}")
        else:
            print("   No test student found in database")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n4. Testing other profile endpoints:")
    # Test teacher endpoint
    response = client.get('/api/profile/teacher/')
    print(f"   /api/profile/teacher/ - Status: {response.status_code}")

    # Test tutor endpoint
    response = client.get('/api/profile/tutor/')
    print(f"   /api/profile/tutor/ - Status: {response.status_code}")

    print("\n5. Checking URL patterns:")
    from django.urls import reverse, NoReverseMatch
    try:
        url = reverse('student_profile_api')
        print(f"   student_profile_api URL: {url}")
    except NoReverseMatch:
        print("   student_profile_api URL not found")

    try:
        url = reverse('teacher_profile_api')
        print(f"   teacher_profile_api URL: {url}")
    except NoReverseMatch:
        print("   teacher_profile_api URL not found")

    try:
        url = reverse('tutor_profile_api')
        print(f"   tutor_profile_api URL: {url}")
    except NoReverseMatch:
        print("   tutor_profile_api URL not found")

if __name__ == '__main__':
    test_profile_endpoints()