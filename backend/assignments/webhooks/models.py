"""
Webhook-related models for logging and audit trails.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class FailedWebhookLog(models.Model):
    """
    Log of failed webhook attempts for retry and debugging.

    Helps identify integration issues and provides audit trail
    for webhook processing failures.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Retry'
        PROCESSING = 'processing', 'Being Retried'
        FAILED = 'failed', 'Failed (Max Retries)'
        SUCCESS = 'success', 'Succeeded on Retry'

    submission_id = models.IntegerField(
        verbose_name='Submission ID',
        db_index=True
    )

    payload = models.JSONField(
        verbose_name='Webhook Payload',
        help_text='Complete webhook payload that failed'
    )

    error_message = models.TextField(
        verbose_name='Error Message',
        help_text='Exception message from processing'
    )

    remote_ip = models.GenericIPAddressField(
        verbose_name='Remote IP',
        help_text='IP address that sent the webhook'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Retry Status'
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Retry Count',
        help_text='Number of retry attempts (max 3)'
    )

    last_retry_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Last Retry Time'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Failed Webhook Log'
        verbose_name_plural = 'Failed Webhook Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['submission_id', 'status'],
                name='webhook_submission_status_idx'
            ),
            models.Index(
                fields=['status', '-created_at'],
                name='webhook_status_date_idx'
            ),
            models.Index(
                fields=['retry_count'],
                name='webhook_retry_count_idx'
            ),
        ]

    def __str__(self):
        return f"Failed Webhook - Submission {self.submission_id} (Retry {self.retry_count})"

    def can_retry(self) -> bool:
        """Check if webhook can be retried (max 3 attempts)"""
        return self.retry_count < 3

    def increment_retry(self):
        """Increment retry count and update status"""
        from django.utils import timezone
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        if self.retry_count >= 3:
            self.status = self.Status.FAILED
        self.save()


class WebhookSignatureLog(models.Model):
    """
    Log of all webhook signature verification attempts.

    Provides audit trail for security verification and helps
    identify potential security issues or malformed requests.
    """

    submission_id = models.IntegerField(
        verbose_name='Submission ID',
        db_index=True
    )

    signature = models.CharField(
        max_length=64,
        verbose_name='Signature',
        help_text='HMAC-SHA256 signature from header'
    )

    is_valid = models.BooleanField(
        verbose_name='Signature Valid',
        db_index=True
    )

    remote_ip = models.GenericIPAddressField(
        verbose_name='Remote IP'
    )

    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='User Agent'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Webhook Signature Log'
        verbose_name_plural = 'Webhook Signature Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['submission_id', '-created_at'],
                name='sig_submission_date_idx'
            ),
            models.Index(
                fields=['is_valid', '-created_at'],
                name='sig_valid_date_idx'
            ),
            models.Index(
                fields=['remote_ip', '-created_at'],
                name='sig_ip_date_idx'
            ),
        ]

    def __str__(self):
        status = 'Valid' if self.is_valid else 'Invalid'
        return f"Webhook Signature - Submission {self.submission_id} ({status})"


class WebhookAuditTrail(models.Model):
    """
    Complete audit trail of webhook processing for compliance and debugging.

    Records every step of webhook processing from receipt through grade application.
    """

    submission_id = models.IntegerField(
        verbose_name='Submission ID',
        db_index=True
    )

    event_type = models.CharField(
        max_length=50,
        choices=[
            ('received', 'Webhook Received'),
            ('signature_verified', 'Signature Verified'),
            ('replay_check', 'Replay Attack Check'),
            ('submission_found', 'Submission Found'),
            ('grade_applied', 'Grade Applied'),
            ('notification_sent', 'Notification Sent'),
            ('error', 'Processing Error'),
        ],
        verbose_name='Event Type'
    )

    details = models.JSONField(
        verbose_name='Event Details',
        help_text='Structured data about the event'
    )

    created_by = models.CharField(
        max_length=100,
        verbose_name='Created By',
        help_text='Service or user that created the event'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Webhook Audit Trail'
        verbose_name_plural = 'Webhook Audit Trails'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['submission_id', 'event_type'],
                name='audit_submission_event_idx'
            ),
            models.Index(
                fields=['event_type', '-created_at'],
                name='audit_event_date_idx'
            ),
        ]

    def __str__(self):
        return f"Audit {self.event_type} - Submission {self.submission_id}"
