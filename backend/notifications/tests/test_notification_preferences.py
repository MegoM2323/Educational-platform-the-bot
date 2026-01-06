"""
Tests for Notification Preferences Backend (T_NTF_006)

Tests cover:
1. NotificationSettings model with new fields
2. Auto-creation of NotificationSettings for new users
3. GET /api/accounts/notification-settings/ endpoint
4. PATCH /api/accounts/notification-settings/ endpoint
5. Preference defaults
6. Timezone field validation
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from notifications.models import NotificationSettings

User = get_user_model()


@pytest.mark.django_db
class TestNotificationSettingsModel:
    """Test NotificationSettings model"""

    def test_notification_settings_creation(self):
        """Test creating NotificationSettings"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='student'
        )

        settings = NotificationSettings.objects.create(user=user)

        assert settings.user == user
        assert settings.email_notifications is True
        assert settings.push_notifications is True
        assert settings.sms_notifications is False
        assert settings.in_app_notifications is True
        assert settings.quiet_hours_enabled is False
        assert settings.timezone == 'UTC'

    def test_notification_settings_defaults(self):
        """Test default values for NotificationSettings"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='student'
        )

        settings = NotificationSettings.objects.create(user=user)

        # Channel preferences
        assert settings.email_notifications is True
        assert settings.push_notifications is True
        assert settings.sms_notifications is False
        assert settings.in_app_notifications is True

        # Notification type preferences
        assert settings.assignment_notifications is True
        assert settings.material_notifications is True
        assert settings.message_notifications is True
        assert settings.payment_notifications is True
        assert settings.invoice_notifications is True
        assert settings.system_notifications is True

        # Quiet hours
        assert settings.quiet_hours_enabled is False
        assert settings.quiet_hours_start is None
        assert settings.quiet_hours_end is None

        # Timezone
        assert settings.timezone == 'UTC'

    def test_timezone_choices(self):
        """Test timezone field has valid choices"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='student'
        )

        # Valid timezone
        settings = NotificationSettings.objects.create(
            user=user,
            timezone='Europe/Moscow'
        )
        assert settings.timezone == 'Europe/Moscow'

        # Test another valid timezone
        user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123',
            role='student'
        )
        settings2 = NotificationSettings.objects.create(
            user=user2,
            timezone='US/Eastern'
        )
        assert settings2.timezone == 'US/Eastern'

    def test_quiet_hours_fields(self):
        """Test quiet hours fields"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='student'
        )

        settings = NotificationSettings.objects.create(
            user=user,
            quiet_hours_enabled=True,
            quiet_hours_start='21:00',
            quiet_hours_end='08:00'
        )

        assert settings.quiet_hours_enabled is True
        assert str(settings.quiet_hours_start) == '21:00:00'
        assert str(settings.quiet_hours_end) == '08:00:00'


@pytest.mark.django_db
class TestNotificationSettingsEndpoint:
    """Test notification settings API endpoint"""

    def setup_method(self):
        """Setup for each test"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='student'
        )

    def test_get_notification_settings(self):
        """Test GET /api/accounts/notification-settings/"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/accounts/notification-settings/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check channel preferences
        assert data['email_notifications'] is True
        assert data['push_notifications'] is True
        assert data['sms_notifications'] is False
        assert data['in_app_notifications'] is True

        # Check notification type preferences
        assert data['assignment_notifications'] is True
        assert data['material_notifications'] is True
        assert data['message_notifications'] is True
        assert data['payment_notifications'] is True
        assert data['invoice_notifications'] is True
        assert data['system_notifications'] is True

        # Check quiet hours
        assert data['quiet_hours_enabled'] is False
        assert data['timezone'] == 'UTC'

    def test_update_notification_settings(self):
        """Test PATCH /api/accounts/notification-settings/"""
        self.client.force_authenticate(user=self.user)

        payload = {
            'email_notifications': False,
            'push_notifications': False,
            'quiet_hours_enabled': True,
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '09:00',
            'timezone': 'Europe/Moscow'
        }

        response = self.client.patch(
            '/api/accounts/notification-settings/',
            data=payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['email_notifications'] is False
        assert data['push_notifications'] is False
        assert data['quiet_hours_enabled'] is True
        assert data['timezone'] == 'Europe/Moscow'

        # Verify in database
        settings = NotificationSettings.objects.get(user=self.user)
        assert settings.email_notifications is False
        assert settings.push_notifications is False
        assert settings.timezone == 'Europe/Moscow'

    def test_update_notification_type_preferences(self):
        """Test updating notification type preferences"""
        self.client.force_authenticate(user=self.user)

        payload = {
            'assignment_notifications': False,
            'material_notifications': False,
            'message_notifications': True,
            'payment_notifications': False,
            'invoice_notifications': False
        }

        response = self.client.patch(
            '/api/accounts/notification-settings/',
            data=payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        settings = NotificationSettings.objects.get(user=self.user)
        assert settings.assignment_notifications is False
        assert settings.material_notifications is False
        assert settings.message_notifications is True
        assert settings.payment_notifications is False

    def test_unauthorized_access(self):
        """Test that unauthenticated users can't access endpoint"""
        response = self.client.get('/api/accounts/notification-settings/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_partial_update(self):
        """Test partial update (PATCH) only updates specified fields"""
        self.client.force_authenticate(user=self.user)

        # First update
        payload1 = {'email_notifications': False}
        response1 = self.client.patch(
            '/api/accounts/notification-settings/',
            data=payload1,
            format='json'
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second update with different field
        payload2 = {'timezone': 'US/Pacific'}
        response2 = self.client.patch(
            '/api/accounts/notification-settings/',
            data=payload2,
            format='json'
        )
        assert response2.status_code == status.HTTP_200_OK
        data = response2.json()

        # Check that first update is still there
        assert data['email_notifications'] is False
        # Check new update
        assert data['timezone'] == 'US/Pacific'


@pytest.mark.django_db
class TestNotificationSettingsAutoCreation:
    """Test automatic creation of NotificationSettings for new users"""

    def test_auto_create_on_user_creation(self):
        """Test that NotificationSettings is auto-created when new user is created"""
        import os
        # Set environment to non-test to trigger signal
        original_env = os.environ.get('ENVIRONMENT')
        os.environ['ENVIRONMENT'] = 'development'

        try:
            user = User.objects.create_user(
                email='newuser@example.com',
                password='testpass123',
                role='student'
            )

            # Check that NotificationSettings was created
            settings = NotificationSettings.objects.filter(user=user).first()
            assert settings is not None
            assert settings.user == user
            assert settings.timezone == 'UTC'
        finally:
            # Restore environment
            if original_env:
                os.environ['ENVIRONMENT'] = original_env
            else:
                os.environ.pop('ENVIRONMENT', None)

    def test_auto_create_for_different_roles(self):
        """Test auto-creation for different user roles"""
        import os
        original_env = os.environ.get('ENVIRONMENT')
        os.environ['ENVIRONMENT'] = 'development'

        try:
            roles = ['student', 'teacher', 'tutor', 'parent']

            for i, role in enumerate(roles):
                user = User.objects.create_user(
                    email=f'user{i}@example.com',
                    password='testpass123',
                    role=role
                )

                settings = NotificationSettings.objects.filter(user=user).first()
                assert settings is not None, f"NotificationSettings not created for role {role}"
                assert settings.user == user
        finally:
            if original_env:
                os.environ['ENVIRONMENT'] = original_env
            else:
                os.environ.pop('ENVIRONMENT', None)
