#!/usr/bin/env python
"""Check profile API endpoints"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client()

print("\n" + "="*50)
print("CHECKING PROFILE API ENDPOINTS")
print("="*50 + "\n")

# Test endpoints without auth
endpoints = [
    '/api/profile/student/',
    '/api/profile/teacher/',
    '/api/profile/tutor/',
]

print("1. Testing endpoints WITHOUT authentication:")
for endpoint in endpoints:
    response = client.get(endpoint)
    print(f"   {endpoint:<30} Status: {response.status_code}")

print("\n2. Checking test users in database:")
test_users = [
    'student@test.com',
    'teacher@test.com',
    'tutor@test.com',
]

for email in test_users:
    user = User.objects.filter(email=email).first()
    if user:
        print(f"   ✓ Found: {email} (role: {user.role})")
    else:
        print(f"   ✗ Not found: {email}")

print("\n3. Testing WITH authentication:")
# Get first user of each role
roles = ['student', 'teacher', 'tutor']
for role in roles:
    user = User.objects.filter(role=role).first()
    if user:
        print(f"\n   Testing as {role} ({user.email}):")
        client.force_login(user)
        response = client.get(f'/api/profile/{role}/')
        print(f"      Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"      Has 'user' key: {'user' in data}")
            print(f"      Has 'profile' key: {'profile' in data}")
        elif response.status_code == 404:
            print(f"      Error: {response.json().get('error', 'Profile not found')}")
        elif response.status_code == 403:
            print(f"      Error: Permission denied")
        client.logout()
    else:
        print(f"\n   No {role} users found in database")

print("\n4. Checking URL configuration:")
from django.urls import resolve, Resolver404

for endpoint in endpoints:
    try:
        match = resolve(endpoint)
        print(f"   {endpoint:<30} → {match.view_name}")
    except Resolver404:
        print(f"   {endpoint:<30} → NOT FOUND!")

print("\n" + "="*50)
print("TEST COMPLETE")
print("="*50)
