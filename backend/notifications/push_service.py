"""
Push Notification Service via SMS.

Handles sending push notifications to users via SMS.
Includes batch delivery, rate limiting, and delivery tracking.
"""

import logging
from datetime import timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

from notifications.channels.models import DeviceToken
from notifications.channels.sms import SMSChannel
from notifications.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


class PushNotificationService:
    """
    Service for managing push notifications via SMS.

    Provides:
    - Single user SMS notification sending
    - Batch user SMS sending
    - Rate limiting
    - Delivery status tracking
    """

    # Rate limiting constants
    DEFAULT_RATE_LIMIT_PER_MINUTE = 100  # Max messages per minute
    DEFAULT_BATCH_SIZE = 500  # Max users per batch request
    DEFAULT_BATCH_DELAY = 0.1  # Seconds between batches

    def __init__(self):
        """Initialize the push notification service."""
        self.sms_channel = SMSChannel()
        self.rate_limit = getattr(
            settings, "PUSH_NOTIFICATION_RATE_LIMIT_PER_MINUTE", self.DEFAULT_RATE_LIMIT_PER_MINUTE
        )
        self.batch_size = getattr(settings, "PUSH_NOTIFICATION_BATCH_SIZE", self.DEFAULT_BATCH_SIZE)
        self.batch_delay = getattr(
            settings, "PUSH_NOTIFICATION_BATCH_DELAY", self.DEFAULT_BATCH_DELAY
        )

    def send_to_user(
        self, notification: Notification, user: User, device_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to a specific user across all their devices.

        Args:
            notification: Notification object to send
            user: User to send to
            device_types: Optional list of device types to target
                         (e.g., ['ios', 'android', 'web'])

        Returns:
            Dictionary with delivery results:
            {
                'status': 'sent' | 'partial' | 'skipped' | 'failed',
                'total_devices': int,
                'sent_count': int,
                'failed_count': int,
                'skipped_count': int,
                'devices': {
                    'ios': {'sent': int, 'failed': int},
                    'android': {'sent': int, 'failed': int},
                    'web': {'sent': int, 'failed': int}
                }
            }
        """
        try:
            # Check rate limiting
            if not self._check_rate_limit(user):
                logger.warning(f"Rate limit exceeded for user {user.id} push notifications")
                return {
                    "status": "skipped",
                    "reason": "Rate limit exceeded",
                    "total_devices": 0,
                }

            # Get user's device tokens
            device_tokens = self._get_user_device_tokens(user, device_types)

            if not device_tokens:
                logger.info(f"No device tokens found for user {user.id}")
                return {
                    "status": "skipped",
                    "reason": "No device tokens",
                    "total_devices": 0,
                }

            # Send to batch
            return self._send_to_devices(notification, user, device_tokens)

        except Exception as e:
            logger.error(f"Error sending push to user {user.id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "total_devices": 0,
            }

    def send_to_users(
        self,
        notification: Notification,
        users: List[User],
        device_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a notification to multiple users.

        Args:
            notification: Notification object to send
            users: List of users to send to
            device_types: Optional list of device types to target

        Returns:
            Dictionary with aggregated delivery results
        """
        results = {
            "status": "success",
            "total_users": len(users),
            "users_sent": 0,
            "users_skipped": 0,
            "users_failed": 0,
            "total_devices": 0,
            "devices_sent": 0,
            "devices_failed": 0,
            "user_results": [],
        }

        for user in users:
            try:
                user_result = self.send_to_user(notification, user, device_types)
                results["user_results"].append(
                    {"user_id": user.id, "email": user.email, "result": user_result}
                )

                # Aggregate results
                results["total_devices"] += user_result.get("total_devices", 0)
                results["devices_sent"] += user_result.get("sent_count", 0)
                results["devices_failed"] += user_result.get("failed_count", 0)

                if user_result["status"] == "sent":
                    results["users_sent"] += 1
                elif user_result["status"] == "failed":
                    results["users_failed"] += 1
                else:
                    results["users_skipped"] += 1

            except Exception as e:
                logger.error(f"Error sending to user {user.id}: {e}")
                results["users_failed"] += 1

        return results

    def register_device_token(
        self, user: User, token: str, device_type: str, device_name: str = ""
    ) -> Tuple[DeviceToken, bool]:
        """
        Register or update a device token for push notifications.

        Args:
            user: User who owns the device
            token: Device token
            device_type: Type of device ('ios', 'android', 'web')
            device_name: Optional user-friendly device name

        Returns:
            Tuple of (DeviceToken object, created boolean)
        """
        try:
            device_token, created = DeviceToken.objects.update_or_create(
                token=token,
                defaults={
                    "user": user,
                    "device_type": device_type,
                    "device_name": device_name or "",
                    "is_active": True,
                    "last_used_at": timezone.now(),
                },
            )

            if created:
                logger.info(
                    f"Registered device token for user {user.id}: " f"{device_type} ({device_name})"
                )
            else:
                logger.info(f"Updated device token for user {user.id}: {device_type}")

            return device_token, created

        except Exception as e:
            logger.error(f"Error registering device token: {e}")
            raise

    def revoke_device_token(self, user: User, token: str) -> bool:
        """
        Revoke a device token (mark as inactive).

        Args:
            user: User who owns the device
            token: Device token to revoke

        Returns:
            True if revoked, False if not found
        """
        try:
            device_token = DeviceToken.objects.filter(user=user, token=token).first()

            if device_token:
                device_token.is_active = False
                device_token.save()
                logger.info(f"Revoked device token for user {user.id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error revoking device token: {e}")
            return False

    def get_user_devices(self, user: User) -> List[Dict[str, Any]]:
        """
        Get list of registered devices for a user.

        Args:
            user: User to get devices for

        Returns:
            List of device information dictionaries
        """
        try:
            devices = DeviceToken.objects.filter(user=user).order_by("-last_used_at", "-created_at")

            return [
                {
                    "id": device.id,
                    "device_type": device.device_type,
                    "device_name": device.device_name,
                    "is_active": device.is_active,
                    "last_used_at": device.last_used_at,
                    "created_at": device.created_at,
                }
                for device in devices
            ]

        except Exception as e:
            logger.error(f"Error getting user devices: {e}")
            return []

    def cleanup_expired_tokens(self) -> Dict[str, int]:
        """
        Clean up expired or invalid device tokens.

        Marks tokens as inactive if they haven't been used in 90 days
        or if previous send attempts indicate they're invalid.

        Returns:
            Dictionary with cleanup statistics
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=90)
            cutoff_date_no_use = timezone.now() - timedelta(days=30)

            # Tokens never used after registration for 30+ days
            inactive = DeviceToken.objects.filter(
                is_active=True, last_used_at__isnull=True, created_at__lt=cutoff_date_no_use
            ).update(is_active=False)

            # Tokens not used in 90+ days
            stale = DeviceToken.objects.filter(is_active=True, last_used_at__lt=cutoff_date).update(
                is_active=False
            )

            logger.info(f"Cleaned up {inactive} inactive + {stale} stale device tokens")

            return {
                "inactive_tokens": inactive,
                "stale_tokens": stale,
                "total_cleaned": inactive + stale,
            }

        except Exception as e:
            logger.error(f"Error cleaning up tokens: {e}")
            return {"error": str(e)}

    def get_push_stats(self, user: Optional[User] = None) -> Dict[str, Any]:
        """
        Get statistics about push notification delivery.

        Args:
            user: Optional user to get stats for. If None, returns system stats.

        Returns:
            Dictionary with push notification statistics
        """
        try:
            if user:
                devices = DeviceToken.objects.filter(user=user)
            else:
                devices = DeviceToken.objects.all()

            total = devices.count()
            active = devices.filter(is_active=True).count()
            inactive = devices.filter(is_active=False).count()

            by_type = {}
            for device_type in DeviceToken.DeviceType.choices:
                type_key = device_type[0]
                count = devices.filter(device_type=type_key, is_active=True).count()
                if count > 0:
                    by_type[type_key] = count

            return {
                "total_devices": total,
                "active_devices": active,
                "inactive_devices": inactive,
                "by_device_type": by_type,
            }

        except Exception as e:
            logger.error(f"Error getting push stats: {e}")
            return {"error": str(e)}

    # Private methods

    def _get_user_device_tokens(
        self, user: User, device_types: Optional[List[str]] = None
    ) -> List[DeviceToken]:
        """Get active device tokens for a user."""
        query = DeviceToken.objects.filter(user=user, is_active=True)

        if device_types:
            query = query.filter(device_type__in=device_types)

        return list(query.values_list("id", "token", "device_type"))

    def _send_to_devices(
        self, notification: Notification, user: User, device_tokens: List[Tuple[int, str, str]]
    ) -> Dict[str, Any]:
        """
        Send notification to user via SMS.

        Args:
            notification: Notification to send
            user: Target user
            device_tokens: List of (id, token, device_type) tuples (unused)

        Returns:
            Dictionary with delivery results
        """
        result = {
            "status": "sent",
            "total_devices": 1,
            "sent_count": 0,
            "failed_count": 0,
            "devices": {"sms": {"sent": 0, "failed": 0}},
        }

        if not user.phone_number:
            result["status"] = "skipped"
            result["total_devices"] = 0
            return result

        try:
            # Send via SMS channel
            send_result = self.sms_channel.send(notification, user)

            if send_result.get("status") == "sent":
                result["sent_count"] = 1
                result["devices"]["sms"]["sent"] = 1
            else:
                result["failed_count"] = 1
                result["devices"]["sms"]["failed"] = 1
                result["status"] = "failed"

        except Exception as e:
            logger.error(f"Error sending SMS to user {user.id}: {e}")
            result["failed_count"] = 1
            result["devices"]["sms"]["failed"] = 1
            result["status"] = "failed"

        return result

    def _check_rate_limit(self, user: User) -> bool:
        """
        Check if user is within rate limit for push notifications.

        Uses cache to track push notifications sent in the last minute.

        Args:
            user: User to check rate limit for

        Returns:
            True if within limit, False otherwise
        """
        cache_key = f"push_notifications_sent_{user.id}"
        current_count = cache.get(cache_key, 0)

        if current_count >= self.rate_limit:
            return False

        # Increment counter and set expiration to 1 minute
        cache.set(cache_key, current_count + 1, 60)
        return True


# Singleton instance
_push_service_instance = None


def get_push_service() -> PushNotificationService:
    """Get or create the push notification service singleton."""
    global _push_service_instance
    if _push_service_instance is None:
        _push_service_instance = PushNotificationService()
    return _push_service_instance
