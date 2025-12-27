"""
Firebase Cloud Messaging (FCM) push notification channel.

Handles push notifications to mobile and web devices via Firebase.
"""

import json
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.contrib.auth import get_user_model

from .base import AbstractChannel, ChannelValidationError, ChannelDeliveryError

User = get_user_model()
logger = logging.getLogger(__name__)


class FirebasePushChannel(AbstractChannel):
    """
    Firebase Cloud Messaging push notification channel.

    Sends notifications to devices registered with Firebase Cloud Messaging.
    Requires firebase_project_id and firebase_service_account_key in settings.
    """

    # FCM API endpoint
    FCM_API_URL = "https://fcm.googleapis.com/v1/projects/{}/messages:send"

    # FCM error codes that are transient (can be retried)
    TRANSIENT_ERRORS = {
        'INTERNAL',
        'UNAVAILABLE',
        'DEADLINE_EXCEEDED',
    }

    # FCM error codes that are permanent (should not be retried)
    PERMANENT_ERRORS = {
        'INVALID_ARGUMENT',
        'FAILED_PRECONDITION',
        'PERMISSION_DENIED',
        'NOT_FOUND',
    }

    def __init__(self):
        """Initialize Firebase push channel."""
        super().__init__()
        self.project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None)
        self.service_account_key = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY', None)
        self.access_token = None
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that Firebase is properly configured."""
        if not self.project_id or not self.service_account_key:
            self.logger.warning(
                "Firebase push notifications not configured. "
                "Set FIREBASE_PROJECT_ID and FIREBASE_SERVICE_ACCOUNT_KEY."
            )

    def _get_access_token(self) -> Optional[str]:
        """
        Get Firebase access token from service account.

        Returns:
            Access token string or None if not configured
        """
        if not self.service_account_key or not self.project_id:
            return None

        try:
            from google.auth import _helpers
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            # Parse service account key if it's a string
            if isinstance(self.service_account_key, str):
                service_account_info = json.loads(self.service_account_key)
            else:
                service_account_info = self.service_account_key

            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )

            # Refresh to get access token
            credentials.refresh(Request())
            return credentials.token

        except Exception as e:
            self.logger.error(f"Failed to get Firebase access token: {e}")
            return None

    def validate_recipient(self, recipient: User) -> bool:
        """
        Validate that recipient has a device token for push notifications.

        Args:
            recipient: User to validate

        Returns:
            True if user has device tokens, False otherwise
        """
        try:
            # Check if user has any device tokens
            from notifications.channels.models import DeviceToken
            return DeviceToken.objects.filter(
                user=recipient,
                is_active=True
            ).exists()
        except Exception as e:
            self.logger.error(f"Error validating recipient {recipient.id}: {e}")
            return False

    def get_channel_name(self) -> str:
        """Get the name of this channel."""
        return 'push'

    def _build_fcm_payload(self, notification: Any, device_token: str) -> Dict[str, Any]:
        """
        Build Firebase Cloud Messaging payload.

        Args:
            notification: Notification object
            device_token: Device token to send to

        Returns:
            Dictionary with FCM message payload
        """
        payload = {
            'message': {
                'token': device_token,
                'notification': {
                    'title': notification.title[:100],  # FCM limit
                    'body': notification.message[:240],  # FCM limit
                },
                'data': {
                    'notification_id': str(notification.id),
                    'action_type': notification.type,
                    'priority': notification.priority,
                }
            }
        }

        # Add click action for opening the app
        payload['message']['notification']['click_action'] = 'OPEN_APP'

        # Add additional data from notification if present
        if hasattr(notification, 'data') and notification.data:
            for key, value in notification.data.items():
                if isinstance(value, (str, int, float, bool)):
                    payload['message']['data'][f'extra_{key}'] = str(value)

        return payload

    def _send_to_device(self, payload: Dict[str, Any]) -> bool:
        """
        Send message to device via Firebase API.

        Args:
            payload: FCM message payload

        Returns:
            True if successful, False otherwise
        """
        if not self.project_id:
            return False

        access_token = self._get_access_token()
        if not access_token:
            self.logger.error("Could not obtain Firebase access token")
            return False

        try:
            url = self.FCM_API_URL.format(self.project_id)
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return True

            # Handle FCM errors
            self._handle_fcm_error(response)
            return False

        except requests.Timeout:
            self.logger.error("Firebase request timeout")
            return False
        except requests.RequestException as e:
            self.logger.error(f"Firebase request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending to Firebase: {e}")
            return False

    def _handle_fcm_error(self, response: requests.Response) -> None:
        """
        Handle Firebase API error responses.

        Args:
            response: Response from Firebase API
        """
        try:
            error_data = response.json()
            if 'error' in error_data:
                error_msg = error_data['error'].get('message', 'Unknown error')
                error_code = error_data['error'].get('code', 'UNKNOWN')
                self.logger.error(f"Firebase error {error_code}: {error_msg}")
        except Exception as e:
            self.logger.error(f"Failed to parse Firebase error: {e}")

    def send(self, notification: Any, recipient: User) -> Dict[str, Any]:
        """
        Send push notification via Firebase.

        Args:
            notification: Notification object to send
            recipient: User to send to

        Returns:
            Dictionary with delivery status and metadata

        Raises:
            ChannelValidationError: If recipient has no device tokens
            ChannelDeliveryError: If delivery fails
        """
        if not self.validate_recipient(recipient):
            self.log_delivery(notification, recipient, 'skipped',
                            'No valid device tokens')
            return {
                'status': 'skipped',
                'reason': 'No device tokens',
            }

        try:
            from notifications.channels.models import DeviceToken

            # Get all active device tokens for the user
            device_tokens = DeviceToken.objects.filter(
                user=recipient,
                is_active=True
            ).values_list('token', flat=True)

            sent_count = 0
            failed_count = 0

            for device_token in device_tokens:
                try:
                    payload = self._build_fcm_payload(notification, device_token)

                    if self._send_to_device(payload):
                        sent_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    self.logger.error(f"Error sending to device {device_token}: {e}")
                    failed_count += 1

            if sent_count > 0:
                self.log_delivery(notification, recipient, 'sent')
                return {
                    'status': 'sent',
                    'sent_count': sent_count,
                    'failed_count': failed_count,
                }
            else:
                self.log_delivery(notification, recipient, 'failed',
                                'All devices failed')
                raise ChannelDeliveryError('All device sends failed')

        except ChannelDeliveryError:
            raise
        except Exception as e:
            self.log_delivery(notification, recipient, 'failed', str(e))
            raise ChannelDeliveryError(f"Firebase send failed: {e}")
