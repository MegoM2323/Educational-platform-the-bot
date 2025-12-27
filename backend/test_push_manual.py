"""
Manual test for push notification service to verify functionality.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ENVIRONMENT'] = 'test'

django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from notifications.models import Notification
from notifications.push_service import PushNotificationService, get_push_service
from notifications.batch_push_service import BatchPushNotificationService, get_batch_push_service
from notifications.channels.models import DeviceToken

User = get_user_model()

def test_push_service():
    """Test push notification service."""
    print("\n=== Testing Push Notification Service ===\n")

    # Clean up
    User.objects.filter(email__startswith='test').delete()

    # Create test user
    user = User.objects.create_user(
        email='test_push@example.com',
        password='testpass123'
    )
    print(f"Created user: {user.email}")

    # Create test notification
    notification = Notification.objects.create(
        title='Test Notification',
        message='Test message content',
        recipient=user,
        type=Notification.Type.SYSTEM,
        priority=Notification.Priority.NORMAL
    )
    print(f"Created notification: {notification.title}")

    # Initialize service
    service = PushNotificationService()
    print(f"Service initialized - Rate limit: {service.rate_limit}/min")

    # Test device token registration
    print("\n--- Testing Device Token Registration ---")
    token1, created1 = service.register_device_token(
        user,
        'fcm_token_ios_1',
        'ios',
        'iPhone 13'
    )
    print(f"Registered token 1: {created1}")

    token2, created2 = service.register_device_token(
        user,
        'fcm_token_android_1',
        'android',
        'Samsung Galaxy'
    )
    print(f"Registered token 2: {created2}")

    token3, created3 = service.register_device_token(
        user,
        'fcm_token_web_1',
        'web',
        'Chrome Browser'
    )
    print(f"Registered token 3: {created3}")

    # Test getting user devices
    print("\n--- Testing Get User Devices ---")
    devices = service.get_user_devices(user)
    print(f"User has {len(devices)} devices:")
    for device in devices:
        print(f"  - {device['device_type'].upper()}: {device['device_name']}")

    # Test getting push stats
    print("\n--- Testing Push Statistics ---")
    stats = service.get_push_stats(user)
    print(f"User stats:")
    print(f"  - Total devices: {stats['total_devices']}")
    print(f"  - Active devices: {stats['active_devices']}")
    print(f"  - By type: {stats['by_device_type']}")

    # Test revoking token
    print("\n--- Testing Revoke Device Token ---")
    revoked = service.revoke_device_token(user, 'fcm_token_web_1')
    print(f"Token revoked: {revoked}")
    devices_after = service.get_user_devices(user)
    print(f"Devices after revoke: {len(devices_after)}")

    # Test cleanup
    print("\n--- Testing Token Cleanup ---")
    cleanup_stats = service.cleanup_expired_tokens()
    print(f"Cleanup results: {cleanup_stats}")

    # Test batch service
    print("\n--- Testing Batch Push Service ---")
    batch_service = get_batch_push_service()
    print(f"Batch service initialized - Batch size: {batch_service.batch_size}")

    # Create more users for batch testing
    users = [user]
    for i in range(5):
        u = User.objects.create_user(
            email=f'batch_test_{i}@example.com',
            password='testpass123'
        )
        users.append(u)
    print(f"Created {len(users)} users for batch test")

    # Get batch stats
    batch_stats = batch_service.get_batch_stats()
    print(f"Batch stats: {batch_stats}")

    print("\n=== All Tests Passed ===\n")

if __name__ == '__main__':
    try:
        test_push_service()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
