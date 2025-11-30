#!/usr/bin/env python
"""Test profile API endpoints using Django test client"""

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

def test_profiles():
    client = Client()

    print("\n" + "="*50)
    print("PROFILE API ENDPOINTS TEST")
    print("="*50 + "\n")

    # Test 1: Check if endpoints exist
    print("1. Testing endpoint existence without auth:")

    endpoints = [
        '/api/profile/student/',
        '/api/profile/teacher/',
        '/api/profile/tutor/',
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        print(f"   {endpoint} - Status: {response.status_code}")
        if response.status_code != 401:
            print(f"      Response: {response.content[:100]}")

    print("\n2. Testing with authentication:")

    # Try to find test users
    users = {
        'student': User.objects.filter(email='student@test.com').first(),
        'teacher': User.objects.filter(email='teacher@test.com').first(),
        'tutor': User.objects.filter(email='tutor@test.com').first(),
    }

    for role, user in users.items():
        if user:
            print(f"\n   Testing {role} profile:")
            client.force_login(user)
            response = client.get(f'/api/profile/{role}/')
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      Has user data: {'user' in data}")
                print(f"      Has profile data: {'profile' in data}")
                if 'error' in data:
                    print(f"      Error: {data['error']}")
            elif response.status_code == 404:
                print(f"      Error: Profile not found")
            elif response.status_code == 403:
                print(f"      Error: Permission denied")
            client.logout()
        else:
            print(f"\n   No test {role} user found")

    print("\n3. Checking URL patterns registration:")
    from django.urls import get_resolver
    resolver = get_resolver()

    # Get all URL patterns
    url_names = []
    for pattern in resolver.url_patterns:
        if hasattr(pattern, 'name') and pattern.name:
            if 'profile' in pattern.name:
                url_names.append(pattern.name)

    print(f"   Found {len(url_names)} profile-related URL patterns:")
    for name in url_names:
        print(f"      - {name}")

if __name__ == '__main__':
    test_profiles()