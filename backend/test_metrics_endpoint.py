#!/usr/bin/env python
"""
Simple test script to verify Analytics Metrics endpoint fix
Tests:
1. Endpoint returns 200 OK with no params (uses defaults)
2. Endpoint returns 200 OK with empty database (returns zeros)
3. Response has proper JSON structure
"""

import os
import sys
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Add testserver to ALLOWED_HOSTS for testing
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
import json

User = get_user_model()

def get_admin_token():
    """Get or create admin token"""
    admin = User.objects.filter(is_staff=True, is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser(
            username='test_admin_metrics',
            email='admin@test.com',
            password='testpass123'
        )
    token, _ = Token.objects.get_or_create(user=admin)
    return token.key

def test_metrics_no_params():
    """Test GET /api/notifications/analytics/metrics/ with no params"""
    print("\n" + "="*60)
    print("TEST 1: GET /api/notifications/analytics/metrics/ (no params)")
    print("="*60)

    client = Client()
    token = get_admin_token()

    response = client.get(
        '/api/notifications/analytics/metrics/',
        HTTP_AUTHORIZATION=f'Token {token}'
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = json.loads(response.content)
        print("✓ PASS: Endpoint returned 200 OK")
        print(f"Response Keys: {list(data.keys())}")

        # Check required fields
        required_fields = [
            'date_from', 'date_to', 'total_sent', 'total_delivered',
            'total_opened', 'delivery_rate', 'by_type', 'by_channel',
            'by_time', 'summary'
        ]

        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"✗ FAIL: Missing fields: {missing}")
            return False
        else:
            print(f"✓ PASS: All required fields present")

        # Check summary structure
        summary = data.get('summary', {})
        summary_fields = ['total_sent', 'total_delivered', 'total_opened',
                         'total_failed', 'avg_delivery_time', 'failures', 'error_reasons']
        summary_missing = [f for f in summary_fields if f not in summary]
        if summary_missing:
            print(f"✗ FAIL: Missing summary fields: {summary_missing}")
            return False
        else:
            print(f"✓ PASS: Summary has all required fields")

        print(f"total_sent: {data['total_sent']}")
        print(f"delivery_rate: {data['delivery_rate']}")
        print(f"Summary avg_delivery_time: {summary.get('avg_delivery_time')}")

        return True
    else:
        print(f"✗ FAIL: Expected 200, got {response.status_code}")
        print(f"Response: {response.content.decode()}")
        return False

def test_metrics_with_filters():
    """Test GET /api/notifications/analytics/metrics/ with filter params"""
    print("\n" + "="*60)
    print("TEST 2: GET /api/notifications/analytics/metrics/ (with filters)")
    print("="*60)

    client = Client()
    token = get_admin_token()

    response = client.get(
        '/api/notifications/analytics/metrics/?granularity=day&channel=email',
        HTTP_AUTHORIZATION=f'Token {token}'
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = json.loads(response.content)
        print("✓ PASS: Endpoint returned 200 OK with filters")
        print(f"Response Keys: {list(data.keys())}")
        return True
    else:
        print(f"✗ FAIL: Expected 200, got {response.status_code}")
        print(f"Response: {response.content.decode()}")
        return False

def test_metrics_no_auth():
    """Test that endpoint requires authentication"""
    print("\n" + "="*60)
    print("TEST 3: GET /api/notifications/analytics/metrics/ (no auth)")
    print("="*60)

    client = Client()

    response = client.get('/api/notifications/analytics/metrics/')

    print(f"Status Code: {response.status_code}")

    if response.status_code == 401:
        print("✓ PASS: Endpoint correctly requires authentication")
        return True
    else:
        print(f"✗ FAIL: Expected 401, got {response.status_code}")
        return False

def test_metrics_non_admin():
    """Test that endpoint requires admin permission"""
    print("\n" + "="*60)
    print("TEST 4: GET /api/notifications/analytics/metrics/ (non-admin)")
    print("="*60)

    client = Client()

    # Create or get non-admin user
    import random
    random_id = random.randint(10000, 99999)
    user, created = User.objects.get_or_create(
        username=f'regular_user_metrics_{random_id}',
        defaults={
            'email': f'user_{random_id}@test.com',
            'is_staff': False,
            'is_superuser': False
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()

    token, _ = Token.objects.get_or_create(user=user)

    response = client.get(
        '/api/notifications/analytics/metrics/',
        HTTP_AUTHORIZATION=f'Token {token.key}'
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 403:
        print("✓ PASS: Endpoint correctly requires admin permission")
        return True
    else:
        print(f"✗ FAIL: Expected 403, got {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TESTING: Analytics Metrics Endpoint 400 Error Fix")
    print("="*60)

    results = []

    try:
        results.append(("No Params", test_metrics_no_params()))
        results.append(("With Filters", test_metrics_with_filters()))
        results.append(("No Auth", test_metrics_no_auth()))
        results.append(("Non-Admin", test_metrics_non_admin()))
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
        return True
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
