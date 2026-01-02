"""
Models for notification delivery channels.

Includes device tokens for push notifications and phone numbers for SMS.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class DeviceToken(models.Model):
    """
    Device tokens for push notifications.

    Stores device tokens from mobile and web clients for sending push notifications.
    """

    class DeviceType(models.TextChoices):
        iOS = "ios", "iOS Device"
        ANDROID = "android", "Android Device"
        WEB = "web", "Web Browser"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="device_tokens", verbose_name="User"
    )

    token = models.TextField(
        unique=True, verbose_name="Device Token", help_text="Device token for push notifications"
    )

    device_type = models.CharField(
        max_length=10, choices=DeviceType.choices, verbose_name="Device Type"
    )

    device_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Device Name",
        help_text='User-friendly name (e.g., "iPhone 12", "Chrome on MacBook")',
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether this token is currently active for receiving notifications",
    )

    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Last Used",
        help_text="Last time a notification was successfully sent to this device",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated")

    class Meta:
        app_label = "notifications"
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"
        ordering = ["-last_used_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["token"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_device_type_display()} ({self.device_name})"


class UserPhoneNumber(models.Model):
    """
    Phone numbers for SMS notifications.

    Stores verified phone numbers for users to receive SMS notifications.
    """

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending Verification"
        VERIFIED = "verified", "Verified"
        INVALID = "invalid", "Invalid"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="phone_number_record", verbose_name="User"
    )

    phone_number = models.CharField(
        max_length=20,
        verbose_name="Phone Number",
        help_text="Phone number in international format (e.g., +79876543210)",
    )

    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name="Verification Status",
    )

    verification_code = models.CharField(max_length=6, blank=True, verbose_name="Verification Code")

    verification_attempts = models.PositiveIntegerField(
        default=0, verbose_name="Verification Attempts"
    )

    verified_at = models.DateTimeField(blank=True, null=True, verbose_name="Verified At")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated")

    class Meta:
        app_label = "notifications"
        verbose_name = "User Phone Number"
        verbose_name_plural = "User Phone Numbers"

    def __str__(self):
        return f"{self.user.email} - {self.phone_number} ({self.get_status_display()})"
