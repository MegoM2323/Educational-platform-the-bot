"""
Email notification service with SMTP support, template integration, and delivery tracking.
Supports async sending via Celery with retry logic.
"""
import logging
from typing import Dict, Optional, List, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailDeliveryStatus:
    """Enum for email delivery statuses"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    SENT = 'sent'
    FAILED = 'failed'
    BOUNCED = 'bounced'
    RETRY = 'retry'


class EmailNotificationService:
    """
    Service for sending email notifications via SMTP with template support.

    Features:
    - HTML and plain text email support
    - Jinja2 template rendering
    - Async sending via Celery
    - Delivery status tracking
    - Bounce handling
    - Retry logic with exponential backoff
    """

    # Default sender email
    DEFAULT_FROM_EMAIL = None
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 300  # 5 minutes

    def __init__(self):
        """Initialize email service with settings from Django config"""
        self.default_from_email = getattr(
            settings,
            'DEFAULT_FROM_EMAIL',
            getattr(settings, 'EMAIL_HOST_USER', 'noreply@thebot.platform')
        )
        self.use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        self.email_backend = getattr(settings, 'EMAIL_BACKEND', None)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        notification_id: Optional[int] = None
    ) -> bool:
        """
        Send email with HTML template and plain text fallback.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            plain_text: Plain text fallback (auto-generated if not provided)
            cc: CC recipients list
            bcc: BCC recipients list
            tags: Email metadata tags
            notification_id: Associated Notification ID for tracking

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create multipart message with plain text and HTML alternatives
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=plain_text or self._strip_html(html_content),
                from_email=self.default_from_email,
                to=[to_email],
                cc=cc or [],
                bcc=bcc or []
            )

            # Attach HTML version
            email_message.attach_alternative(html_content, "text/html")

            # Add custom headers for tracking
            if notification_id:
                email_message['X-Notification-ID'] = str(notification_id)
            if tags:
                email_message['X-Email-Tags'] = ','.join(
                    f"{k}:{v}" for k, v in tags.items()
                )

            # Send email
            result = email_message.send(fail_silently=False)

            logger.info(
                f"Email sent successfully to {to_email} "
                f"(notification_id={notification_id})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send email to {to_email}: {str(e)} "
                f"(notification_id={notification_id})",
                exc_info=True
            )
            return False

    def send_notification_email(
        self,
        recipient: User,
        notification_type: str,
        context: Dict[str, Any],
        template_name: str = None,
        subject: str = None,
        notification_id: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a templated notification email to a user.

        Args:
            recipient: User object to send email to
            notification_type: Type of notification (e.g., 'assignment_new')
            context: Template context variables
            template_name: Override template name (auto-determined from notification_type)
            subject: Override subject line
            notification_id: Associated Notification ID
            tags: Email metadata tags

        Returns:
            bool: True if email sent successfully
        """
        # Import here to avoid circular imports during initialization
        from .models import NotificationSettings

        # Check if user has email notifications enabled
        try:
            settings_obj = getattr(recipient, 'notification_settings', None)
            if settings_obj and not settings_obj.email_notifications:
                logger.info(
                    f"Email notifications disabled for user {recipient.id}"
                )
                return False
        except NotificationSettings.DoesNotExist:
            pass

        # Determine template and subject
        if not template_name:
            template_name = f"notifications/{notification_type}.html"

        if not subject:
            subject = self._get_default_subject(notification_type)

        # Add recipient name to context
        context = {
            'recipient': recipient,
            'recipient_name': recipient.get_full_name() or recipient.username,
            'recipient_email': recipient.email,
            **context
        }

        # Render template
        try:
            html_content = render_to_string(template_name, context)
        except Exception as e:
            logger.error(
                f"Failed to render template {template_name}: {str(e)}"
            )
            return False

        # Send email
        tags = tags or {}
        tags['notification_type'] = notification_type

        return self.send_email(
            to_email=recipient.email,
            subject=subject,
            html_content=html_content,
            notification_id=notification_id,
            tags=tags
        )

    def send_batch_email(
        self,
        recipients: List[User],
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
        filter_settings: bool = True
    ) -> Dict[str, int]:
        """
        Send email to multiple recipients (batch sending).

        Args:
            recipients: List of User objects to send to
            subject: Email subject
            html_content: HTML email body
            plain_text: Plain text fallback
            filter_settings: Whether to respect user notification settings

        Returns:
            Dict with 'sent' and 'failed' counts
        """
        results = {'sent': 0, 'failed': 0}

        for recipient in recipients:
            try:
                # Skip if email notifications disabled for user
                if filter_settings:
                    settings_obj = getattr(recipient, 'notification_settings', None)
                    if settings_obj and not settings_obj.email_notifications:
                        continue

                success = self.send_email(
                    to_email=recipient.email,
                    subject=subject,
                    html_content=html_content,
                    plain_text=plain_text,
                    tags={'batch': 'true'}
                )

                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1

            except Exception as e:
                logger.error(
                    f"Error sending to {recipient.email}: {str(e)}"
                )
                results['failed'] += 1

        return results

    def queue_notification_email(
        self,
        notification,  # Notification model
        template_name: str = None,
        subject: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Queue an email notification for async delivery.
        Creates a NotificationQueue entry for Celery task processing.

        Args:
            notification: Notification object
            template_name: Template to use for email
            subject: Email subject line
            context: Additional template context

        Returns:
            Queue entry object
        """
        # Import here to avoid circular imports
        from .models import NotificationQueue

        queue_entry = NotificationQueue.objects.create(
            notification=notification,
            channel='email',
            status=EmailDeliveryStatus.PENDING
        )

        # Store template info in notification data for Celery task
        if not notification.data:
            notification.data = {}

        notification.data['email_template'] = template_name
        notification.data['email_subject'] = subject
        notification.data['email_context'] = context or {}
        notification.save()

        logger.info(f"Queued email for notification {notification.id}")
        return queue_entry

    def handle_bounce(
        self,
        email: str,
        bounce_type: str = 'permanent',
        reason: str = None
    ) -> None:
        """
        Handle email bounce (permanent or temporary).

        Args:
            email: Email address that bounced
            bounce_type: 'permanent' or 'temporary'
            reason: Bounce reason/message
        """
        # Import here to avoid circular imports during initialization
        from .models import NotificationSettings

        logger.warning(
            f"Email bounce ({bounce_type}): {email} - {reason}"
        )

        try:
            user = User.objects.get(email=email)
            if bounce_type == 'permanent':
                # Disable email notifications for this user
                settings_obj, created = NotificationSettings.objects.get_or_create(
                    user=user
                )
                settings_obj.email_notifications = False
                settings_obj.save()
                logger.info(f"Disabled email notifications for {email}")
        except User.DoesNotExist:
            logger.warning(f"User not found for bounced email: {email}")

    @staticmethod
    def _strip_html(html_content: str) -> str:
        """
        Strip HTML tags to create plain text version.

        Args:
            html_content: HTML string

        Returns:
            str: Plain text version
        """
        import re
        from html import unescape

        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)

        # Replace br, div, p, li with newlines
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</(div|p|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        text = unescape(text)

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)

        return text

    @staticmethod
    def _get_default_subject(notification_type: str) -> str:
        """
        Get default email subject for notification type.

        Args:
            notification_type: Type of notification

        Returns:
            str: Default subject line
        """
        subjects = {
            'assignment_new': 'New Assignment',
            'assignment_due': 'Assignment Due Soon',
            'assignment_graded': 'Your Assignment Has Been Graded',
            'material_new': 'New Learning Material',
            'material_published': 'Material Published',
            'message_new': 'New Message',
            'report_ready': 'Your Report Is Ready',
            'payment_success': 'Payment Successful',
            'payment_failed': 'Payment Failed',
            'payment_processed': 'Payment Status Update',
            'invoice_sent': 'New Invoice',
            'invoice_paid': 'Invoice Paid',
            'invoice_overdue': 'Overdue Invoice',
            'invoice_viewed': 'Invoice Viewed',
            'student_created': 'Student Account Created',
            'subject_assigned': 'Subject Assigned',
            'homework_submitted': 'Homework Submitted',
            'system': 'System Notification',
            'reminder': 'Reminder',
        }
        return subjects.get(notification_type, 'Notification')


# Singleton instance
_email_service = None


def get_email_service() -> EmailNotificationService:
    """Get or create email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailNotificationService()
    return _email_service
