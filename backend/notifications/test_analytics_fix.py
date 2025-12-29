"""
Unit tests for Analytics Metrics 400 Error Fix
Tests for NotificationMetricsQuerySerializer and NotificationAnalytics
"""

import os
import sys
import django

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('ENVIRONMENT', 'test')

# Configure Django
django.setup()

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone
from datetime import datetime, timedelta
from notifications.serializers import NotificationMetricsQuerySerializer
from notifications.analytics import NotificationAnalytics


class TestNotificationMetricsQuerySerializer(unittest.TestCase):
    """Test serializer with optional fields and defaults"""

    def test_all_fields_optional(self):
        """Test that all fields are optional"""
        serializer = NotificationMetricsQuerySerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get('granularity'), 'day')

    def test_date_from_optional(self):
        """Test that date_from is optional"""
        serializer = NotificationMetricsQuerySerializer(data={'granularity': 'day'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get('date_from'))

    def test_date_to_optional(self):
        """Test that date_to is optional"""
        serializer = NotificationMetricsQuerySerializer(data={'granularity': 'day'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get('date_to'))

    def test_type_optional(self):
        """Test that type is optional"""
        serializer = NotificationMetricsQuerySerializer(data={'granularity': 'day'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get('type'))

    def test_channel_optional(self):
        """Test that channel is optional"""
        serializer = NotificationMetricsQuerySerializer(data={'granularity': 'day'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get('channel'))

    def test_granularity_has_default(self):
        """Test that granularity has default value"""
        serializer = NotificationMetricsQuerySerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get('granularity'), 'day')

    def test_valid_channel_choice(self):
        """Test that valid channel choice is accepted"""
        serializer = NotificationMetricsQuerySerializer(data={'channel': 'email'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get('channel'), 'email')

    def test_valid_granularity_choices(self):
        """Test that all granularity choices are valid"""
        for gran in ['hour', 'day', 'week']:
            serializer = NotificationMetricsQuerySerializer(data={'granularity': gran})
            self.assertTrue(serializer.is_valid(), f"Failed for granularity: {gran}")
            self.assertEqual(serializer.validated_data.get('granularity'), gran)

    def test_null_values_accepted(self):
        """Test that null values are accepted for optional fields"""
        data = {
            'date_from': None,
            'date_to': None,
            'type': None,
            'channel': None,
            'granularity': 'day'
        }
        serializer = NotificationMetricsQuerySerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestNotificationAnalyticsMetrics(unittest.TestCase):
    """Test NotificationAnalytics.get_metrics() with defaults"""

    @patch('notifications.analytics.Notification')
    @patch('notifications.analytics.NotificationQueue')
    @patch('notifications.analytics.NotificationClick')
    def test_get_metrics_with_no_params(self, mock_click, mock_queue, mock_notif):
        """Test get_metrics with no parameters (uses defaults)"""
        # Mock querysets
        mock_notif_qs = MagicMock()
        mock_notif_qs.filter.return_value = mock_notif_qs
        mock_notif_qs.count.return_value = 0
        mock_notif.objects.filter.return_value = mock_notif_qs

        mock_queue_qs = MagicMock()
        mock_queue_qs.filter.return_value = mock_queue_qs
        mock_queue_qs.count.return_value = 0
        mock_queue_qs.exists.return_value = False
        mock_queue.objects.filter.return_value = mock_queue_qs

        mock_click_qs = MagicMock()
        mock_click_qs.filter.return_value = mock_click_qs
        mock_click_qs.values.return_value = mock_click_qs
        mock_click_qs.distinct.return_value = mock_click_qs
        mock_click_qs.count.return_value = 0
        mock_click.objects.filter.return_value = mock_click_qs

        # Call get_metrics with no params
        with patch('notifications.analytics.cache'):
            result = NotificationAnalytics.get_metrics()

        # Should return dict with expected structure
        self.assertIsInstance(result, dict)
        self.assertIn('total_sent', result)
        self.assertIn('total_delivered', result)
        self.assertIn('delivery_rate', result)
        self.assertIn('summary', result)

    @patch('notifications.analytics.Notification')
    @patch('notifications.analytics.NotificationQueue')
    @patch('notifications.analytics.NotificationClick')
    def test_get_metrics_empty_database(self, mock_click, mock_queue, mock_notif):
        """Test get_metrics with empty database returns zeros"""
        # Mock empty querysets
        mock_notif_qs = MagicMock()
        mock_notif_qs.filter.return_value = mock_notif_qs
        mock_notif_qs.count.return_value = 0
        mock_notif.objects.filter.return_value = mock_notif_qs
        mock_notif.Type.choices = [('assignment_new', 'Assignment'),]

        mock_queue_qs = MagicMock()
        mock_queue_qs.filter.return_value = mock_queue_qs
        mock_queue_qs.count.return_value = 0
        mock_queue_qs.exists.return_value = False
        mock_queue.objects.filter.return_value = mock_queue_qs

        mock_click_qs = MagicMock()
        mock_click_qs.filter.return_value = mock_click_qs
        mock_click_qs.values.return_value = mock_click_qs
        mock_click_qs.distinct.return_value = mock_click_qs
        mock_click_qs.count.return_value = 0
        mock_click.objects.filter.return_value = mock_click_qs

        with patch('notifications.analytics.cache'):
            result = NotificationAnalytics.get_metrics()

        # Should return all zeros, not errors
        self.assertEqual(result.get('total_sent'), 0)
        self.assertEqual(result.get('total_delivered'), 0)
        self.assertEqual(result.get('total_opened'), 0)
        self.assertEqual(result.get('delivery_rate'), 0)

    def test_get_metrics_handles_string_dates(self):
        """Test get_metrics handles string date inputs"""
        # This tests that string conversion is wrapped in try-catch
        with patch('notifications.analytics.Notification'), \
             patch('notifications.analytics.NotificationQueue'), \
             patch('notifications.analytics.NotificationClick'), \
             patch('notifications.analytics.cache'):

            # Should not raise exception with string dates
            try:
                result = NotificationAnalytics.get_metrics(
                    date_from='2025-12-20',
                    date_to='2025-12-29'
                )
                # Should succeed or return default values
                self.assertIsInstance(result, dict)
            except Exception as e:
                self.fail(f"get_metrics raised {e} with valid string dates")

    def test_get_metrics_handles_invalid_dates(self):
        """Test get_metrics handles invalid date strings gracefully"""
        with patch('notifications.analytics.Notification'), \
             patch('notifications.analytics.NotificationQueue'), \
             patch('notifications.analytics.NotificationClick'), \
             patch('notifications.analytics.cache'):

            # Should not crash with invalid dates - should use defaults
            try:
                result = NotificationAnalytics.get_metrics(
                    date_from='invalid-date',
                    date_to='also-invalid'
                )
                # Should succeed with default dates
                self.assertIsInstance(result, dict)
            except Exception as e:
                self.fail(f"get_metrics raised {e} with invalid dates")


class TestAnalyticsSummary(unittest.TestCase):
    """Test _get_summary with edge cases"""

    def test_summary_empty_queue(self):
        """Test _get_summary with empty queue queryset"""
        mock_queue_qs = MagicMock()
        mock_queue_qs.exists.return_value = False

        result = NotificationAnalytics._get_summary(
            total_sent=0,
            total_delivered=0,
            total_opened=0,
            total_failed=0,
            queue_qs=mock_queue_qs
        )

        self.assertEqual(result['total_sent'], 0)
        self.assertEqual(result['total_delivered'], 0)
        self.assertEqual(result['failures'], 0)
        self.assertEqual(result['error_reasons'], [])
        self.assertEqual(result['avg_delivery_time'], 'N/A')

    def test_summary_with_data(self):
        """Test _get_summary with some data"""
        mock_queue_qs = MagicMock()
        mock_queue_qs.exists.return_value = True
        mock_filtered = MagicMock()
        mock_filtered.annotate.return_value = mock_filtered
        mock_filtered.values_list.return_value = []
        mock_queue_qs.filter.return_value = mock_filtered

        result = NotificationAnalytics._get_summary(
            total_sent=10,
            total_delivered=8,
            total_opened=5,
            total_failed=2,
            queue_qs=mock_queue_qs
        )

        self.assertEqual(result['total_sent'], 10)
        self.assertEqual(result['total_delivered'], 8)
        self.assertEqual(result['total_opened'], 5)
        self.assertEqual(result['failures'], 2)

    def test_summary_handles_none_queue(self):
        """Test _get_summary handles None queue gracefully"""
        result = NotificationAnalytics._get_summary(
            total_sent=5,
            total_delivered=4,
            total_opened=2,
            total_failed=1,
            queue_qs=None
        )

        self.assertEqual(result['total_sent'], 5)
        self.assertEqual(result['failures'], 1)
        self.assertEqual(result['error_reasons'], [])


if __name__ == '__main__':
    unittest.main()
