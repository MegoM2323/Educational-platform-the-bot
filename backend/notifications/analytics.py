"""
Notification Analytics Service

Provides analytics and metrics for notification delivery, open rates,
and other metrics across different notification types and channels.
"""

from datetime import datetime, timedelta
from django.db.models import Count, Q, F, Case, When, Sum, Avg
from django.db.models.functions import TruncDate, TruncHour
from django.core.cache import cache
from django.utils import timezone

from .models import Notification, NotificationQueue, NotificationClick


class NotificationAnalytics:
    """
    Service for aggregating and calculating notification metrics
    """

    # Cache timeout in seconds (5 minutes)
    CACHE_TIMEOUT = 300

    @staticmethod
    def _get_cache_key(date_from, date_to, notification_type=None, channel=None, granularity='day', scope=None):
        """
        Generate cache key based on parameters
        """
        key_parts = [
            'notification_analytics',
            date_from.isoformat() if isinstance(date_from, datetime) else str(date_from),
            date_to.isoformat() if isinstance(date_to, datetime) else str(date_to),
            notification_type or 'all_types',
            channel or 'all_channels',
            granularity,
            scope or 'all_scopes',
        ]
        return ':'.join(key_parts)

    @staticmethod
    def get_metrics(date_from=None, date_to=None, notification_type=None, channel=None, granularity='day', scope=None):
        """
        Get aggregated notification metrics

        Args:
            date_from: Start date (YYYY-MM-DD or datetime)
            date_to: End date (YYYY-MM-DD or datetime)
            notification_type: Filter by notification type (e.g., 'assignment_new')
            channel: Filter by channel ('email', 'push', 'sms', 'in_app')
            granularity: Time grouping ('hour', 'day', 'week')
            scope: Filter by scope ('user', 'system', 'admin') - if None, includes all scopes

        Returns:
            Dictionary with metrics and analytics
        """
        # Convert date strings to datetime if needed
        if date_from is None:
            date_from = timezone.now() - timedelta(days=7)
        elif isinstance(date_from, str):
            try:
                date_from = datetime.fromisoformat(date_from)
            except (ValueError, TypeError):
                date_from = timezone.now() - timedelta(days=7)

        if date_to is None:
            date_to = timezone.now()
        elif isinstance(date_to, str):
            try:
                date_to = datetime.fromisoformat(date_to)
            except (ValueError, TypeError):
                date_to = timezone.now()

        # Ensure datetime objects are timezone-aware
        if date_from.tzinfo is None:
            date_from = timezone.make_aware(date_from)
        if date_to.tzinfo is None:
            date_to = timezone.make_aware(date_to)

        # Try to get from cache
        cache_key = NotificationAnalytics._get_cache_key(
            date_from, date_to, notification_type, channel, granularity, scope
        )
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        # Build base querysets
        notifications_qs = Notification.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        )

        queue_qs = NotificationQueue.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        )

        # Apply scope filter if specified
        if scope:
            notifications_qs = notifications_qs.filter(scope=scope)
            queue_qs = queue_qs.filter(notification__scope=scope)

        # Apply type filter
        if notification_type:
            notifications_qs = notifications_qs.filter(type=notification_type)
            queue_qs = queue_qs.filter(notification__type=notification_type)

        if channel:
            queue_qs = queue_qs.filter(channel=channel)

        # Calculate metrics
        total_sent = queue_qs.filter(status='sent').count()
        total_created = notifications_qs.count()
        total_delivered = queue_qs.filter(status='sent').count()
        total_opened = notifications_qs.filter(is_read=True).count()
        total_failed = queue_qs.filter(status='failed').count()

        # Count clicks for notifications in the date range
        clicks_qs = NotificationClick.objects.filter(
            notification__created_at__gte=date_from,
            notification__created_at__lte=date_to
        )
        if notification_type:
            clicks_qs = clicks_qs.filter(notification__type=notification_type)

        total_clicked = clicks_qs.values('notification').distinct().count()

        # Calculate rates (prevent division by zero)
        delivery_rate = (total_delivered / total_created * 100) if total_created > 0 else 0
        open_rate = (total_opened / total_created * 100) if total_created > 0 else 0
        click_rate = (total_clicked / total_created * 100) if total_created > 0 else 0

        # Build response
        result = {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'total_sent': total_created,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'delivery_rate': round(delivery_rate, 2),
            'open_rate': round(open_rate, 2),
            'click_rate': round(click_rate, 2),
            'by_type': NotificationAnalytics._get_by_type(
                notifications_qs, queue_qs
            ),
            'by_channel': NotificationAnalytics._get_by_channel(queue_qs),
            'by_time': NotificationAnalytics._get_by_time(
                notifications_qs, granularity
            ),
            'summary': NotificationAnalytics._get_summary(
                total_created, total_delivered, total_opened, total_failed, queue_qs, total_clicked
            ),
        }

        # Cache the result
        cache.set(cache_key, result, NotificationAnalytics.CACHE_TIMEOUT)

        return result

    @staticmethod
    def _get_by_type(notifications_qs, queue_qs):
        """
        Get metrics grouped by notification type
        """
        type_stats = {}

        # Count sent and delivered per type
        for notification_type, display_name in Notification.Type.choices:
            type_notifications = notifications_qs.filter(type=notification_type)
            type_queue = queue_qs.filter(notification__type=notification_type)

            sent_count = type_notifications.count()
            delivered_count = type_queue.filter(status='sent').count()
            opened_count = type_notifications.filter(is_read=True).count()

            # Count unique notifications with clicks
            clicked_count = NotificationClick.objects.filter(
                notification__type=notification_type,
                notification__in=notifications_qs
            ).values('notification').distinct().count()

            type_stats[notification_type] = {
                'count': sent_count,
                'delivered': delivered_count,
                'opened': opened_count,
                'clicked': clicked_count,
                'delivery_rate': round(
                    (delivered_count / sent_count * 100) if sent_count > 0 else 0,
                    2
                ),
                'open_rate': round(
                    (opened_count / sent_count * 100) if sent_count > 0 else 0,
                    2
                ),
                'click_rate': round(
                    (clicked_count / sent_count * 100) if sent_count > 0 else 0,
                    2
                ),
            }

        # Remove types with zero count
        return {k: v for k, v in type_stats.items() if v['count'] > 0}

    @staticmethod
    def _get_by_channel(queue_qs):
        """
        Get metrics grouped by delivery channel
        """
        channel_stats = {}

        channels = ['email', 'push', 'sms', 'in_app']
        for channel in channels:
            channel_queue = queue_qs.filter(channel=channel)

            sent_count = channel_queue.count()
            delivered_count = channel_queue.filter(status='sent').count()
            failed_count = channel_queue.filter(status='failed').count()

            if sent_count > 0:
                channel_stats[channel] = {
                    'count': sent_count,
                    'delivered': delivered_count,
                    'failed': failed_count,
                    'delivery_rate': round(
                        (delivered_count / sent_count * 100),
                        2
                    ),
                }

        return channel_stats

    @staticmethod
    def _get_by_time(notifications_qs, granularity='day'):
        """
        Get metrics grouped by time (hour, day, week)
        """
        time_stats = []

        if granularity == 'hour':
            trunc_func = TruncHour
            fmt = '%Y-%m-%d %H:00'
        else:  # Default to day
            trunc_func = TruncDate
            fmt = '%Y-%m-%d'

        time_data = (
            notifications_qs
            .annotate(time_bucket=trunc_func('created_at'))
            .values('time_bucket')
            .annotate(
                count=Count('id'),
                sent=Count('id', filter=Q(is_sent=True)),
                opened=Count('id', filter=Q(is_read=True))
            )
            .order_by('time_bucket')
        )

        for item in time_data:
            if item['time_bucket']:
                time_stats.append({
                    'time': item['time_bucket'].strftime(fmt),
                    'count': item['count'],
                    'sent': item['sent'],
                    'opened': item['opened'],
                })

        return time_stats

    @staticmethod
    def _get_summary(total_sent, total_delivered, total_opened, total_failed, queue_qs, total_clicked=0):
        """
        Get summary statistics
        """
        avg_delivery_time = None
        error_list = []

        try:
            # Handle case when queue_qs is None or empty
            if queue_qs is not None and queue_qs.exists():
                # Calculate average delivery time
                delivery_times = queue_qs.filter(
                    status='sent',
                    processed_at__isnull=False
                ).annotate(
                    delivery_time=F('processed_at') - F('created_at')
                ).values_list('delivery_time', flat=True)

                if delivery_times:
                    total_seconds = sum(
                        (t.total_seconds() if hasattr(t, 'total_seconds') else 0)
                        for t in delivery_times
                    )
                    if len(delivery_times) > 0:
                        avg_seconds = total_seconds / len(delivery_times)
                        avg_delivery_time = f"{avg_seconds:.1f} seconds"

                # Get failure reasons
                failure_errors = (
                    queue_qs
                    .filter(status='failed')
                    .values('error_message')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )

                error_list = [
                    f"{err.get('error_message', 'Unknown')} ({err.get('count', 0)})"
                    for err in failure_errors
                    if err.get('error_message')
                ]
        except Exception as e:
            # Log error but don't crash - return default values
            error_list = []
            avg_delivery_time = None

        return {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'total_failed': total_failed,
            'avg_delivery_time': avg_delivery_time or 'N/A',
            'failures': total_failed,
            'error_reasons': error_list,
        }

    @staticmethod
    def invalidate_cache(date_from=None, date_to=None, notification_type=None, channel=None, scope=None):
        """
        Invalidate cache for specific metrics

        This should be called when new notifications are created or status changes
        """
        if date_from is None:
            date_from = timezone.now() - timedelta(days=30)
        if date_to is None:
            date_to = timezone.now()

        # Invalidate all granularity levels for the given parameters
        for granularity in ['hour', 'day', 'week']:
            cache_key = NotificationAnalytics._get_cache_key(
                date_from, date_to, notification_type, channel, granularity, scope
            )
            cache.delete(cache_key)

    @staticmethod
    def get_delivery_rate(date_from=None, date_to=None, notification_type=None, channel=None):
        """
        Get delivery rate percentage
        """
        metrics = NotificationAnalytics.get_metrics(
            date_from, date_to, notification_type, channel
        )
        return metrics.get('delivery_rate', 0)

    @staticmethod
    def get_open_rate(date_from=None, date_to=None, notification_type=None, channel=None):
        """
        Get open rate percentage
        """
        metrics = NotificationAnalytics.get_metrics(
            date_from, date_to, notification_type, channel
        )
        return metrics.get('open_rate', 0)

    @staticmethod
    def get_click_rate(date_from=None, date_to=None, notification_type=None, channel=None):
        """
        Get click rate percentage
        """
        metrics = NotificationAnalytics.get_metrics(
            date_from, date_to, notification_type, channel
        )
        return metrics.get('click_rate', 0)

    @staticmethod
    def get_top_performing_types(date_from=None, date_to=None, limit=5):
        """
        Get notification types with highest open rates
        """
        metrics = NotificationAnalytics.get_metrics(
            date_from, date_to
        )

        by_type = metrics.get('by_type', {})
        sorted_types = sorted(
            by_type.items(),
            key=lambda x: x[1].get('open_rate', 0),
            reverse=True
        )

        return [
            {
                'type': type_key,
                'open_rate': data['open_rate'],
                'count': data['count'],
            }
            for type_key, data in sorted_types[:limit]
        ]

    @staticmethod
    def get_channel_performance(date_from=None, date_to=None):
        """
        Get performance metrics for each channel
        """
        metrics = NotificationAnalytics.get_metrics(
            date_from, date_to
        )

        return metrics.get('by_channel', {})

    @staticmethod
    def track_click(notification_id, user_id, action_type='link_click', action_url=None,
                   action_data=None, user_agent=None, ip_address=None):
        """
        Track a click on a notification.

        Args:
            notification_id: ID of the notification
            user_id: ID of the user who clicked
            action_type: Type of action (link_click, in_app_click, email_click, button_click)
            action_url: URL that was clicked (if applicable)
            action_data: Additional JSON data about the action
            user_agent: User agent string
            ip_address: IP address of the click

        Returns:
            NotificationClick instance or None if notification not found
        """
        try:
            notification = Notification.objects.get(id=notification_id)
            user = notification.recipient  # Get the recipient user from notification

            click = NotificationClick.objects.create(
                notification=notification,
                user=user,
                action_type=action_type,
                action_url=action_url,
                action_data=action_data or {},
                user_agent=user_agent or '',
                ip_address=ip_address
            )

            # Invalidate cache since metrics changed
            NotificationAnalytics.invalidate_cache()

            return click
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def get_notification_clicks(notification_id, action_type=None):
        """
        Get all clicks for a specific notification.

        Args:
            notification_id: ID of the notification
            action_type: Optional filter by action type

        Returns:
            QuerySet of NotificationClick objects
        """
        clicks = NotificationClick.objects.filter(notification_id=notification_id)

        if action_type:
            clicks = clicks.filter(action_type=action_type)

        return clicks

    @staticmethod
    def get_user_clicks_by_type(user_id, date_from=None, date_to=None):
        """
        Get clicks grouped by notification type for a specific user.

        Args:
            user_id: ID of the user
            date_from: Optional start date
            date_to: Optional end date

        Returns:
            Dictionary with click counts by type
        """
        if date_from is None:
            date_from = timezone.now() - timedelta(days=30)
        if date_to is None:
            date_to = timezone.now()

        clicks = NotificationClick.objects.filter(
            user_id=user_id,
            created_at__gte=date_from,
            created_at__lte=date_to
        ).values('notification__type').annotate(count=Count('id')).order_by('-count')

        return {item['notification__type']: item['count'] for item in clicks}
