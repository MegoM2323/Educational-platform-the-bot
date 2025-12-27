"""
Simple unit tests for Email Notification Service.
Tests core functionality without complex Django setup.
"""
import pytest
from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone

from .email_service import EmailNotificationService, EmailDeliveryStatus

User = get_user_model()


@pytest.mark.django_db
class TestEmailServiceBasic:
    """Basic tests for EmailNotificationService"""

    def test_service_initialization(self):
        """Test email service initializes correctly"""
        service = EmailNotificationService()
        assert service is not None
        assert service.default_from_email is not None

    def test_strip_html_basic(self):
        """Test HTML stripping"""
        service = EmailNotificationService()
        html = '<p>Hello</p><p>World</p>'
        plain = service._strip_html(html)
        assert 'Hello' in plain
        assert 'World' in plain
        assert '<p>' not in plain

    def test_strip_html_removes_scripts(self):
        """Test HTML stripping removes scripts"""
        service = EmailNotificationService()
        html = '<p>Hello</p><script>alert("xss")</script>'
        plain = service._strip_html(html)
        assert 'alert' not in plain
        assert 'Hello' in plain

    def test_get_default_subject(self):
        """Test default subject for notification types"""
        service = EmailNotificationService()
        subject = service._get_default_subject('assignment_new')
        assert subject == 'New Assignment'

    def test_get_default_subject_unknown(self):
        """Test default subject for unknown type"""
        service = EmailNotificationService()
        subject = service._get_default_subject('unknown')
        assert subject == 'Notification'


@pytest.mark.django_db
class TestEmailQueueing:
    """Test email queuing functionality"""

    def test_queue_notification_email(self):
        """Test queuing a notification email"""
        from .models import Notification

        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        notification = Notification.objects.create(
            recipient=user,
            type=Notification.Type.ASSIGNMENT_NEW,
            title='Test',
            message='Test message'
        )

        service = EmailNotificationService()
        queue_entry = service.queue_notification_email(notification)

        assert queue_entry.notification == notification
        assert queue_entry.channel == 'email'
        assert queue_entry.status == EmailDeliveryStatus.PENDING


@pytest.mark.django_db
class TestBounceHandling:
    """Test bounce handling"""

    def test_handle_permanent_bounce(self):
        """Test permanent bounce disables email"""
        from .models import NotificationSettings

        user = User.objects.create_user(
            username='test',
            email='bounce@example.com'
        )
        settings_obj = NotificationSettings.objects.create(
            user=user,
            email_notifications=True
        )

        service = EmailNotificationService()
        service.handle_bounce('bounce@example.com', bounce_type='permanent')

        settings_obj.refresh_from_db()
        assert settings_obj.email_notifications is False


@pytest.mark.django_db
class TestEmailSending:
    """Test email sending"""

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_simple_email(self):
        """Test sending a simple email"""
        service = EmailNotificationService()
        result = service.send_email(
            to_email='test@example.com',
            subject='Test',
            html_content='<p>Test</p>'
        )

        assert result is True
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == 'Test'

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_with_notification_id(self):
        """Test sending email with notification ID header"""
        service = EmailNotificationService()
        result = service.send_email(
            to_email='test@example.com',
            subject='Test',
            html_content='<p>Test</p>',
            notification_id=123
        )

        assert result is True
        email = mail.outbox[0]
        assert email.extra_headers.get('X-Notification-ID') == '123'
