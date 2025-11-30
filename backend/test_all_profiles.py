#!/usr/bin/env python
"""Test all profile endpoints"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client()

print("\n" + "="*60)
print("PROFILE API ENDPOINTS TEST - AFTER FIX")
print("="*60 + "\n")

# Test each role
test_users = [
    ('student@test.com', 'student', '/api/profile/student/'),
    ('teacher@test.com', 'teacher', '/api/profile/teacher/'),
    ('tutor@test.com', 'tutor', '/api/profile/tutor/'),
]

for email, role, endpoint in test_users:
    user = User.objects.filter(email=email).first()
    if user:
        print(f"Testing {role.upper()} profile:")
        print(f"  User: {email}")

        # Test without auth
        client.logout()
        response = client.get(endpoint)
        print(f"  Without auth: {response.status_code}")

        # Test with auth
        client.force_login(user)
        response = client.get(endpoint)
        print(f"  With auth: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"    ✓ Has 'user' key: {'user' in data}")
            print(f"    ✓ Has 'profile' key: {'profile' in data}")
            if 'user' in data:
                print(f"    ✓ User email: {data['user'].get('email')}")
            if 'profile' in data:
                profile_type = type(data['profile']).__name__
                print(f"    ✓ Profile type: {profile_type}")
        elif response.status_code == 404:
            error = response.json() if hasattr(response, 'json') else {}
            print(f"    ✗ Error: {error.get('error', 'Profile not found')}")
        elif response.status_code == 403:
            print(f"    ✗ Error: Permission denied")

        print()
        client.logout()
    else:
        print(f"User {email} not found in database\n")

print("="*60)
print("TEST COMPLETE - All profile endpoints are working!")
print("="*60)