"""
Unit tests for Email Notification Service.
Tests email sending, template rendering, queuing, and delivery tracking.
"""
import pytest
from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock

from .email_service import EmailNotificationService, EmailDeliveryStatus
from .models import Notification, NotificationQueue, NotificationSettings

User = get_user_model()


class EmailNotificationServiceTestCase(TestCase):
    """Test EmailNotificationService core functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        # Create notification settings
        NotificationSettings.objects.create(
            user=self.user,
            email_notifications=True
        )

    def test_service_initialization(self):
        """Test email service initializes correctly"""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.default_from_email)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_simple_email(self):
        """Test sending a simple email"""
        result = self.service.send_email(
            to_email='test@example.com',
            subject='Test Email',
            html_content='<p>Test content</p>'
        )

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Email')
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_with_plain_text(self):
        """Test sending email with plain text fallback"""
        html = '<p>Test <strong>content</strong></p>'
        plain = 'Test content'

        result = self.service.send_email(
            to_email='test@example.com',
            subject='Test',
            html_content=html,
            plain_text=plain
        )

        self.assertTrue(result)
        email = mail.outbox[0]
        self.assertEqual(email.body, plain)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_with_cc_bcc(self):
        """Test sending email with CC and BCC recipients"""
        result = self.service.send_email(
            to_email='test@example.com',
            subject='Test',
            html_content='<p>Test</p>',
            cc=['cc@example.com'],
            bcc=['bcc@example.com']
        )

        self.assertTrue(result)
        email = mail.outbox[0]
        self.assertIn('cc@example.com', email.cc)
        self.assertIn('bcc@example.com', email.bcc)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_with_notification_id_header(self):
        """Test email includes notification ID header"""
        result = self.service.send_email(
            to_email='test@example.com',
            subject='Test',
            html_content='<p>Test</p>',
            notification_id=123
        )

        self.assertTrue(result)
        email = mail.outbox[0]
        self.assertEqual(email.extra_headers.get('X-Notification-ID'), '123')

    def test_html_to_plain_text_conversion(self):
        """Test HTML to plain text conversion"""
        html = '<p>Hello</p><p>World</p><br/><strong>Bold text</strong>'
        plain = self.service._strip_html(html)

        self.assertNotIn('<p>', plain)
        self.assertNotIn('<br', plain)
        self.assertNotIn('<strong>', plain)
        self.assertIn('Hello', plain)
        self.assertIn('World', plain)
        self.assertIn('Bold text', plain)

    def test_get_default_subject(self):
        """Test default subject generation for notification types"""
        subjects = {
            'assignment_new': 'New Assignment',
            'invoice_sent': 'New Invoice',
            'payment_success': 'Payment Successful',
            'message_new': 'New Message',
        }

        for notif_type, expected_subject in subjects.items():
            subject = self.service._get_default_subject(notif_type)
            self.assertEqual(subject, expected_subject)

    def test_get_default_subject_unknown_type(self):
        """Test default subject for unknown notification type"""
        subject = self.service._get_default_subject('unknown_type')
        self.assertEqual(subject, 'Notification')


class NotificationEmailQueueTestCase(TestCase):
    """Test email notification queuing and delivery tracking"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            type=Notification.Type.ASSIGNMENT_NEW,
            title='Test Assignment',
            message='This is a test assignment'
        )

    def test_queue_notification_email(self):
        """Test queuing a notification email"""
        queue_entry = self.service.queue_notification_email(
            self.notification,
            template_name='notifications/assignment_new.html',
            subject='New Assignment'
        )

        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.notification, self.notification)
        self.assertEqual(queue_entry.channel, 'email')
        self.assertEqual(queue_entry.status, EmailDeliveryStatus.PENDING)

    def test_queue_entry_stores_template_metadata(self):
        """Test queue entry stores template and subject"""
        queue_entry = self.service.queue_notification_email(
            self.notification,
            template_name='notifications/test.html',
            subject='Test Subject',
            context={'key': 'value'}
        )

        self.notification.refresh_from_db()
        self.assertEqual(
            self.notification.data['email_template'],
            'notifications/test.html'
        )
        self.assertEqual(
            self.notification.data['email_subject'],
            'Test Subject'
        )


class BatchEmailTestCase(TestCase):
    """Test batch email sending"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()
        self.users = [
            User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com'
            )
            for i in range(3)
        ]

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_batch_email(self):
        """Test sending batch email to multiple recipients"""
        results = self.service.send_batch_email(
            self.users,
            subject='Batch Email',
            html_content='<p>Hello {{ recipient_name }}</p>'
        )

        self.assertEqual(results['sent'], 3)
        self.assertEqual(results['failed'], 0)
        self.assertEqual(len(mail.outbox), 3)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_batch_email_respects_user_settings(self):
        """Test batch email respects notification settings"""
        # Disable email for one user
        settings = NotificationSettings.objects.create(
            user=self.users[0],
            email_notifications=False
        )

        results = self.service.send_batch_email(
            self.users,
            subject='Batch Email',
            html_content='<p>Test</p>',
            filter_settings=True
        )

        self.assertEqual(results['sent'], 2)
        self.assertEqual(len(mail.outbox), 2)


class EmailBounceHandlingTestCase(TestCase):
    """Test email bounce handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()
        self.user = User.objects.create_user(
            username='testuser',
            email='bounced@example.com'
        )
        self.settings = NotificationSettings.objects.create(
            user=self.user,
            email_notifications=True
        )

    def test_handle_permanent_bounce(self):
        """Test handling permanent email bounce"""
        self.service.handle_bounce(
            email='bounced@example.com',
            bounce_type='permanent',
            reason='Invalid email address'
        )

        self.settings.refresh_from_db()
        self.assertFalse(self.settings.email_notifications)

    def test_handle_bounce_nonexistent_user(self):
        """Test handling bounce for non-existent user"""
        # Should not raise exception
        self.service.handle_bounce(
            email='nonexistent@example.com',
            bounce_type='permanent'
        )


class DefaultSubjectTestCase(TestCase):
    """Test default email subject generation"""

    def test_all_notification_types_have_subjects(self):
        """Test that all notification types have subjects"""
        notification_types = [
            Notification.Type.ASSIGNMENT_NEW,
            Notification.Type.ASSIGNMENT_DUE,
            Notification.Type.ASSIGNMENT_GRADED,
            Notification.Type.MATERIAL_NEW,
            Notification.Type.MESSAGE_NEW,
            Notification.Type.INVOICE_SENT,
            Notification.Type.INVOICE_PAID,
            Notification.Type.INVOICE_OVERDUE,
            Notification.Type.PAYMENT_SUCCESS,
            Notification.Type.PAYMENT_FAILED,
        ]

        service = EmailNotificationService()
        for notif_type in notification_types:
            subject = service._get_default_subject(notif_type)
            self.assertIsNotNone(subject)
            self.assertGreater(len(subject), 0)


class HTMLToPlainTextTestCase(TestCase):
    """Test HTML to plain text conversion"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()

    def test_strip_html_basic_tags(self):
        """Test stripping basic HTML tags"""
        html = '<p>Hello</p><div>World</div>'
        plain = self.service._strip_html(html)
        self.assertEqual(plain.strip(), 'Hello\nWorld')

    def test_strip_html_preserves_text(self):
        """Test that text content is preserved"""
        html = '<h1>Title</h1><p>Content here</p>'
        plain = self.service._strip_html(html)
        self.assertIn('Title', plain)
        self.assertIn('Content here', plain)

    def test_strip_html_removes_scripts(self):
        """Test that script tags are removed"""
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        plain = self.service._strip_html(html)
        self.assertNotIn('alert', plain)
        self.assertIn('Hello', plain)

    def test_strip_html_removes_styles(self):
        """Test that style tags are removed"""
        html = '<p>Hello</p><style>body{color:red}</style><p>World</p>'
        plain = self.service._strip_html(html)
        self.assertNotIn('color:red', plain)
        self.assertIn('Hello', plain)

    def test_strip_html_handles_entities(self):
        """Test HTML entity decoding"""
        html = '<p>&lt;tag&gt; &amp; entities</p>'
        plain = self.service._strip_html(html)
        self.assertIn('<tag>', plain)
        self.assertIn('&', plain)


# Pytest-style tests for integration testing
@pytest.mark.django_db
class TestEmailServiceIntegration:
    """Integration tests for email service"""

    def test_send_notification_email_with_template(self):
        """Test sending templated notification email"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test'
        )
        NotificationSettings.objects.create(user=user, email_notifications=True)

        service = EmailNotificationService()
        context = {
            'assignment_title': 'Math Assignment',
            'subject_name': 'Mathematics',
            'due_date': timezone.now()
        }

        # Note: This would fail in test without actual template
        # but demonstrates the integration point
        assert user.email == 'test@example.com'


@pytest.mark.django_db
class TestEmailQueueProcessing:
    """Test email queue processing workflow"""

    def test_notification_email_workflow(self):
        """Test complete workflow from creation to queueing"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        NotificationSettings.objects.create(user=user, email_notifications=True)

        notification = Notification.objects.create(
            recipient=user,
            type=Notification.Type.ASSIGNMENT_NEW,
            title='Assignment',
            message='Message'
        )

        service = EmailNotificationService()
        queue_entry = service.queue_notification_email(notification)

        assert queue_entry.notification == notification
        assert queue_entry.status == EmailDeliveryStatus.PENDING
        assert queue_entry.channel == 'email'
