"""
Secure one-click unsubscribe functionality for email notifications.

Token Generation & Validation:
- HMAC-SHA256(user_id + notification_type + secret)
- Token valid for 30 days
- Expiry included in token signature

Unsubscribe Endpoint:
- GET /api/notifications/unsubscribe/{token}/
- Validate token signature and expiry
- Extract user_id and notification_type from token
- Update NotificationSettings based on query param: ?type=assignments|materials|messages|all
"""

import hmac
import hashlib
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from urllib.parse import quote, unquote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import NotificationSettings

User = get_user_model()
logger = logging.getLogger('audit')


class UnsubscribeTokenGenerator:
    """
    Generates and validates secure unsubscribe tokens using HMAC-SHA256.

    Token structure:
    {
        "user_id": 123,
        "notification_types": ["assignments", "materials"],
        "expires_at": "2025-01-26T12:00:00Z"
    }

    Signed with HMAC-SHA256 using SECRET_KEY
    """

    TOKEN_EXPIRY_DAYS = 30

    @staticmethod
    def generate(user_id: int, notification_types: Optional[list] = None) -> str:
        """
        Generate a secure unsubscribe token.

        Args:
            user_id: User ID to unsubscribe
            notification_types: List of types to unsubscribe from
                               (assignments, materials, messages, all)
                               If None, token is valid for all types

        Returns:
            Signed base64-encoded token
        """
        if notification_types is None:
            notification_types = ["all"]

        expires_at = timezone.now() + timedelta(days=UnsubscribeTokenGenerator.TOKEN_EXPIRY_DAYS)

        payload = {
            "user_id": user_id,
            "notification_types": notification_types,
            "expires_at": expires_at.isoformat()
        }

        # Serialize payload to JSON
        payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        payload_bytes = payload_json.encode('utf-8')

        # Create HMAC-SHA256 signature
        secret = settings.SECRET_KEY.encode('utf-8')
        signature = hmac.new(secret, payload_bytes, hashlib.sha256).digest()

        # Combine: signature + payload
        combined = signature + payload_bytes

        # Encode as base64url (URL-safe)
        token = base64.urlsafe_b64encode(combined).decode('utf-8').rstrip('=')

        return token

    @staticmethod
    def validate(token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate and extract data from an unsubscribe token.

        Args:
            token: Signed base64-encoded token

        Returns:
            (is_valid, data_dict)
            - is_valid: True if token is valid and not expired
            - data_dict: Extracted payload or None if invalid

        Validation checks:
        - Token signature is correct
        - Token is not expired (30 days)
        - user_id and notification_types are present
        """
        try:
            # Decode from base64url
            padding = 4 - (len(token) % 4)
            if padding != 4:
                token += '=' * padding

            combined = base64.urlsafe_b64decode(token)

            # Extract signature and payload
            signature = combined[:32]  # SHA256 = 32 bytes
            payload_bytes = combined[32:]

            # Verify signature
            secret = settings.SECRET_KEY.encode('utf-8')
            expected_signature = hmac.new(secret, payload_bytes, hashlib.sha256).digest()

            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(f"Invalid unsubscribe token signature")
                return False, None

            # Parse payload
            payload = json.loads(payload_bytes.decode('utf-8'))

            # Validate expiry
            expires_at = datetime.fromisoformat(payload['expires_at'])
            if timezone.now() > expires_at:
                logger.warning(f"Unsubscribe token expired for user {payload.get('user_id')}")
                return False, None

            # Validate required fields
            if 'user_id' not in payload or 'notification_types' not in payload:
                return False, None

            return True, payload

        except (ValueError, json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to validate unsubscribe token: {e}")
            return False, None


class UnsubscribeService:
    """
    Processes unsubscribe requests and updates NotificationSettings.
    """

    NOTIFICATION_TYPE_MAPPING = {
        'assignments': 'assignment_notifications',
        'materials': 'material_notifications',
        'messages': 'message_notifications',
        'reports': 'report_notifications',
        'payments': 'payment_notifications',
        'invoices': 'invoice_notifications',
        'system': 'system_notifications',
        'all': None,  # Special case: disable all
    }

    @staticmethod
    def unsubscribe(user_id: int, notification_types: list, ip_address: str = None,
                   user_agent: str = None, token_used: bool = False) -> Dict:
        """
        Unsubscribe user from specified notification types.

        Args:
            user_id: User to unsubscribe
            notification_types: List of types to disable
                               (assignments, materials, messages, all)
            ip_address: IP address of unsubscriber (for audit trail)
            user_agent: User agent string (for audit trail)
            token_used: Whether unsubscribe was via secure token link

        Returns:
            Dict with status and updated settings

        Updates NotificationSettings:
        - type=assignments: set assignment_notifications=False
        - type=all: set all notification flags to False

        Records unsubscribe event in NotificationUnsubscribe model for GDPR compliance.
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"Unsubscribe failed: user {user_id} not found")
            return {
                'success': False,
                'error': 'User not found',
                'message': f'User {user_id} does not exist'
            }

        try:
            settings_obj = user.notification_settings
        except NotificationSettings.DoesNotExist:
            # Create default settings if not exists
            settings_obj = NotificationSettings.objects.create(user=user)

        # Track what was disabled
        disabled_types = []

        if 'all' in notification_types:
            # Disable all channels
            settings_obj.email_notifications = False
            settings_obj.push_notifications = False
            settings_obj.sms_notifications = False
            disabled_types = ['all']
            logger.info(f"User {user_id} ({user.email}) unsubscribed from ALL notifications")
        else:
            # Disable specific types
            for notif_type in notification_types:
                if notif_type in UnsubscribeService.NOTIFICATION_TYPE_MAPPING:
                    field_name = UnsubscribeService.NOTIFICATION_TYPE_MAPPING[notif_type]
                    if field_name:  # Skip 'all' case
                        setattr(settings_obj, field_name, False)
                        disabled_types.append(notif_type)

            logger.info(
                f"User {user_id} ({user.email}) unsubscribed from: {', '.join(disabled_types)}"
            )

        settings_obj.save()

        # Record unsubscribe event for GDPR compliance
        try:
            from .models import NotificationUnsubscribe
            NotificationUnsubscribe.objects.create(
                user=user,
                notification_types=disabled_types if disabled_types != ['all'] else [],
                channel='email',  # Default to email, could be parameterized
                ip_address=ip_address,
                user_agent=user_agent,
                token_used=token_used
            )
        except Exception as e:
            logger.warning(f"Failed to record unsubscribe event: {e}")

        return {
            'success': True,
            'message': f'Successfully unsubscribed from: {", ".join(disabled_types)}',
            'disabled_types': disabled_types,
            'user_id': user_id,
            'user_email': user.email,
        }


def generate_unsubscribe_token(user_id: int, notification_type: Optional[str] = None) -> str:
    """
    Generate an unsubscribe token for email footer.

    Args:
        user_id: User ID
        notification_type: Specific type to unsubscribe from
                          (assignments, materials, messages, all)
                          If None, token is valid for 'all'

    Returns:
        URL-safe unsubscribe token

    Example:
        # In email template:
        # {{ unsubscribe_url }}
        # Token is embedded in the URL:
        # https://example.com/api/notifications/unsubscribe/{{ token }}/
    """
    types = [notification_type] if notification_type else None
    return UnsubscribeTokenGenerator.generate(user_id, types)


def get_unsubscribe_url(token: str, base_url: str = None) -> str:
    """
    Get the full unsubscribe URL for email template.

    Args:
        token: Unsubscribe token
        base_url: Base URL (defaults to settings.FRONTEND_URL or settings.ALLOWED_HOSTS[0])

    Returns:
        Full unsubscribe URL

    Example:
        url = get_unsubscribe_url(token)
        # Returns: https://example.com/api/notifications/unsubscribe/abc123.../
    """
    if base_url is None:
        base_url = getattr(settings, 'FRONTEND_URL', '')
        if not base_url and hasattr(settings, 'ALLOWED_HOSTS') and settings.ALLOWED_HOSTS:
            # Use first allowed host as fallback
            host = settings.ALLOWED_HOSTS[0]
            protocol = 'https' if not settings.DEBUG else 'http'
            base_url = f"{protocol}://{host}"

    return f"{base_url}/api/notifications/unsubscribe/{token}/"
