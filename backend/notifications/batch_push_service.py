"""
Batch Push Notification Service.

Handles batch delivery of push notifications to multiple users with rate limiting
and delivery tracking.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from notifications.models import Notification, PushDeliveryLog
from notifications.push_service import get_push_service

User = get_user_model()
logger = logging.getLogger(__name__)


class BatchPushNotificationService:
    """
    Service for batch delivery of push notifications.

    Features:
    - Send notifications to multiple users
    - Rate limiting (max notifications per minute)
    - Batch processing with configurable batch size
    - Delivery tracking and retry logic
    - Statistics and reporting
    """

    # Default batch configuration
    DEFAULT_BATCH_SIZE = 100  # Users per batch
    DEFAULT_BATCH_DELAY = 1.0  # Seconds between batches
    DEFAULT_RATE_LIMIT_PER_MINUTE = 1000  # Max notifications per minute

    def __init__(self):
        """Initialize batch push service."""
        self.push_service = get_push_service()
        self.batch_size = getattr(
            settings,
            'BATCH_PUSH_NOTIFICATION_BATCH_SIZE',
            self.DEFAULT_BATCH_SIZE
        )
        self.batch_delay = getattr(
            settings,
            'BATCH_PUSH_NOTIFICATION_BATCH_DELAY',
            self.DEFAULT_BATCH_DELAY
        )
        self.rate_limit = getattr(
            settings,
            'BATCH_PUSH_NOTIFICATION_RATE_LIMIT',
            self.DEFAULT_RATE_LIMIT_PER_MINUTE
        )

    def send_to_users(
        self,
        notification: Notification,
        users: List[User],
        device_types: Optional[List[str]] = None,
        priority: str = 'normal',
        track_delivery: bool = True
    ) -> Dict[str, Any]:
        """
        Send notification to multiple users in batches.

        Args:
            notification: Notification object to send
            users: List of users to send to
            device_types: Optional device types to target
            priority: Notification priority ('low', 'normal', 'high', 'urgent')
            track_delivery: Whether to track delivery in PushDeliveryLog

        Returns:
            Dictionary with batch delivery statistics:
            {
                'status': 'success' | 'partial' | 'failed',
                'total_users': int,
                'total_batches': int,
                'total_devices': int,
                'devices_sent': int,
                'devices_failed': int,
                'delivery_logs': int,
                'batches': [
                    {
                        'batch_num': int,
                        'user_count': int,
                        'devices_sent': int,
                        'devices_failed': int,
                        'duration': float
                    }
                ],
                'errors': List[str]
            }
        """
        result = {
            'status': 'success',
            'total_users': len(users),
            'total_batches': 0,
            'total_devices': 0,
            'devices_sent': 0,
            'devices_failed': 0,
            'delivery_logs': 0,
            'batches': [],
            'errors': []
        }

        if not users:
            logger.warning("No users provided for batch push notification")
            result['status'] = 'skipped'
            return result

        # Check rate limiting
        if not self._check_batch_rate_limit(len(users)):
            result['status'] = 'failed'
            result['errors'].append('Rate limit exceeded')
            logger.warning(
                f"Batch push rate limit exceeded for {len(users)} users"
            )
            return result

        # Process users in batches
        total_batches = (len(users) + self.batch_size - 1) // self.batch_size
        result['total_batches'] = total_batches

        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(users))
            batch_users = users[start_idx:end_idx]

            try:
                batch_start = time.time()

                batch_result = self._send_batch(
                    notification,
                    batch_users,
                    device_types,
                    priority,
                    track_delivery
                )

                batch_duration = time.time() - batch_start

                # Aggregate results
                result['total_devices'] += batch_result.get('total_devices', 0)
                result['devices_sent'] += batch_result.get('devices_sent', 0)
                result['devices_failed'] += batch_result.get('devices_failed', 0)
                result['delivery_logs'] += batch_result.get('delivery_logs', 0)

                result['batches'].append({
                    'batch_num': batch_num + 1,
                    'user_count': len(batch_users),
                    'devices_sent': batch_result.get('devices_sent', 0),
                    'devices_failed': batch_result.get('devices_failed', 0),
                    'duration': batch_duration
                })

                # Add any batch errors
                if batch_result.get('errors'):
                    result['errors'].extend(batch_result['errors'])

                # Delay between batches if not the last one
                if batch_num < total_batches - 1:
                    time.sleep(self.batch_delay)

            except Exception as e:
                error_msg = f"Batch {batch_num + 1} failed: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
                result['status'] = 'partial'

        # Determine overall status
        if result['devices_sent'] == 0:
            result['status'] = 'failed'
        elif result['devices_failed'] > 0:
            result['status'] = 'partial'

        return result

    def send_to_user_list(
        self,
        notification: Notification,
        user_ids: List[int],
        device_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send notification to users by ID list.

        Args:
            notification: Notification to send
            user_ids: List of user IDs
            device_types: Optional device types to target

        Returns:
            Dictionary with delivery results
        """
        try:
            users = User.objects.filter(id__in=user_ids).select_related(
                'notification_settings'
            )
            return self.send_to_users(notification, list(users), device_types)
        except Exception as e:
            logger.error(f"Error sending to user list: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'total_users': 0,
            }

    def send_to_query(
        self,
        notification: Notification,
        user_query,
        device_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send notification to users matching a queryset.

        Args:
            notification: Notification to send
            user_query: Django queryset of users
            device_types: Optional device types to target

        Returns:
            Dictionary with delivery results
        """
        try:
            users = list(user_query.select_related('notification_settings'))
            return self.send_to_users(notification, users, device_types)
        except Exception as e:
            logger.error(f"Error sending to query: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'total_users': 0,
            }

    def get_batch_stats(self) -> Dict[str, Any]:
        """
        Get statistics about batch push operations.

        Returns:
            Dictionary with batch delivery statistics
        """
        try:
            all_logs = PushDeliveryLog.objects.all()

            total = all_logs.count()
            success = all_logs.filter(success=True).count()
            failed = all_logs.filter(success=False).count()

            # Stats by status
            by_status = defaultdict(int)
            for log in all_logs.values('status').distinct():
                status = log['status']
                count = all_logs.filter(status=status).count()
                by_status[status] = count

            # Recent stats (last 24 hours)
            cutoff = timezone.now() - timedelta(hours=24)
            recent = all_logs.filter(sent_at__gte=cutoff)
            recent_success = recent.filter(success=True).count()
            recent_total = recent.count()

            return {
                'total_logs': total,
                'total_success': success,
                'total_failed': failed,
                'success_rate': (success / total * 100) if total > 0 else 0,
                'by_status': dict(by_status),
                'last_24h': {
                    'total': recent_total,
                    'success': recent_success,
                    'success_rate': (recent_success / recent_total * 100) if recent_total > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting batch stats: {e}")
            return {'error': str(e)}

    # Private methods

    def _send_batch(
        self,
        notification: Notification,
        users: List[User],
        device_types: Optional[List[str]],
        priority: str,
        track_delivery: bool
    ) -> Dict[str, Any]:
        """Send notification to a batch of users."""
        result = {
            'total_devices': 0,
            'devices_sent': 0,
            'devices_failed': 0,
            'delivery_logs': 0,
            'errors': []
        }

        for user in users:
            try:
                # Send to user
                send_result = self.push_service.send_to_user(
                    notification,
                    user,
                    device_types
                )

                if send_result.get('status') == 'sent':
                    result['devices_sent'] += send_result.get('sent_count', 1)
                else:
                    result['devices_failed'] += send_result.get('failed_count', 0)

                result['total_devices'] += send_result.get('total_devices', 0)

                # Track delivery if requested
                if track_delivery and send_result.get('status') != 'skipped':
                    logs_created = self._create_delivery_logs(
                        notification,
                        user,
                        send_result
                    )
                    result['delivery_logs'] += logs_created

            except Exception as e:
                logger.error(f"Error sending to user {user.id}: {e}")
                result['errors'].append(f"User {user.id}: {str(e)}")
                result['devices_failed'] += 1

        return result

    def _create_delivery_logs(
        self,
        notification: Notification,
        user: User,
        send_result: Dict[str, Any]
    ) -> int:
        """Create PushDeliveryLog records for tracking."""
        created_count = 0

        try:
            status_map = {
                'sent': PushDeliveryLog.DeliveryStatus.SENT,
                'partial': PushDeliveryLog.DeliveryStatus.PARTIAL,
                'failed': PushDeliveryLog.DeliveryStatus.FAILED,
                'skipped': PushDeliveryLog.DeliveryStatus.SKIPPED,
            }

            status = status_map.get(
                send_result.get('status'),
                PushDeliveryLog.DeliveryStatus.PENDING
            )

            # Create log entry
            log = PushDeliveryLog.objects.create(
                notification=notification,
                user=user,
                status=status,
                success=(status == PushDeliveryLog.DeliveryStatus.SENT),
                payload_size=len(json.dumps({
                    'title': notification.title,
                    'message': notification.message,
                }))
            )

            created_count += 1

            # If sent, mark as delivered
            if status == PushDeliveryLog.DeliveryStatus.SENT:
                log.mark_delivered()

            # If failed, mark as failed
            elif status == PushDeliveryLog.DeliveryStatus.FAILED:
                error_msg = send_result.get('error', 'Unknown error')
                log.mark_failed(error_msg)

            return created_count

        except Exception as e:
            logger.error(f"Error creating delivery logs: {e}")
            return created_count

    def _check_batch_rate_limit(self, user_count: int) -> bool:
        """
        Check if batch is within rate limit.

        Args:
            user_count: Number of users in batch

        Returns:
            True if within limit, False otherwise
        """
        cache_key = 'batch_push_notifications_sent'
        current_count = cache.get(cache_key, 0)

        if current_count + user_count > self.rate_limit:
            return False

        # Increment counter and set expiration to 1 minute
        cache.set(cache_key, current_count + user_count, 60)
        return True


# Singleton instance
_batch_service_instance = None


def get_batch_push_service() -> BatchPushNotificationService:
    """Get or create the batch push service singleton."""
    global _batch_service_instance
    if _batch_service_instance is None:
        _batch_service_instance = BatchPushNotificationService()
    return _batch_service_instance
