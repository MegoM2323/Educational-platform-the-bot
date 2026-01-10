"""
Pachca API integration for forum message notifications.

Sends notifications to Pachca messenger when new forum messages are created.
Separate from scheduling Pachca integration (different API tokens and channels).
"""

import os
import logging
import httpx
from typing import Optional
from datetime import timedelta
from time import sleep

logger = logging.getLogger(__name__)


class PachcaService:
    """
    Service for sending forum message notifications to Pachca messenger.

    Handles:
    - Forum message notifications when new messages are created in forum chats
    - Graceful error handling (logs errors, doesn't crash the application)
    - HTTP retry logic with exponential backoff
    - Environment variable validation

    Attributes:
        api_token: Pachca API token from environment
        channel_id: Pachca channel ID for forum notifications
        base_url: Pachca API base URL (configurable via env)
        headers: HTTP headers with authorization
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        channel_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialize Pachca service with credentials from environment or parameters.

        Args:
            api_token: Pachca API token (defaults to PACHCA_FORUM_API_TOKEN env var)
            channel_id: Pachca channel ID (defaults to PACHCA_FORUM_CHANNEL_ID env var)
            base_url: Pachca API base URL (defaults to PACHCA_FORUM_BASE_URL or official API)
        """
        self.api_token = api_token or os.getenv("PACHCA_FORUM_API_TOKEN", "")
        self.channel_id = channel_id or os.getenv("PACHCA_FORUM_CHANNEL_ID", "")
        self.base_url = base_url or os.getenv(
            "PACHCA_FORUM_BASE_URL", "https://api.pachca.com/api/shared/v1"
        )

        # Setup headers with authorization if token exists
        self.headers = {}
        if self.api_token:
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

    def is_configured(self) -> bool:
        """
        Check if Pachca service is properly configured.

        Returns:
            True if both API token and channel ID are configured, False otherwise
        """
        return bool(self.api_token and self.channel_id)

    def validate_token(self) -> bool:
        """
        Validate Pachca API token by making a test request.

        Returns:
            True if token is valid, False otherwise
        """
        if not self.is_configured():
            logger.warning("Pachca service not configured")
            return False

        try:
            url = f"{self.base_url}/users/me"
            response = httpx.get(url, headers=self.headers, timeout=10.0)

            if response.status_code == 200:
                user_data = response.json()
                logger.info(
                    f'Pachca token valid. User ID: {user_data.get("data", {}).get("id")}'
                )
                return True
            else:
                logger.error(
                    f"Pachca token validation failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Pachca token validation error: {str(e)}")
            return False

    def notify_new_forum_message(self, message, chat_room) -> None:
        """
        Send notification to Pachca when new forum message is created.

        Message format: "[Forum] {Subject}: {Sender} → {Recipient}: {MessagePreview}"

        Args:
            message: Message instance that was created
            chat_room: ChatRoom instance where message was posted

        Example:
            >>> from chat.models import Message, ChatRoom
            >>> msg = Message.objects.first()
            >>> room = msg.room
            >>> service = PachcaService()
            >>> service.notify_new_forum_message(msg, room)
        """
        if not self.is_configured():
            logger.debug("Pachca service not configured, skipping forum notification")
            return

        try:
            # Extract subject name and participants
            subject_name = self._get_forum_subject_name(chat_room)
            recipient_names = self._get_forum_recipient_names(chat_room, message.sender)
            message_preview = self._truncate_message(message.content, max_length=100)

            # Build notification text
            sender_name = (
                message.sender.get_full_name() if message.sender else "Deleted User"
            )
            notification_text = (
                f"[Forum] {subject_name}: {sender_name} → "
                f"{recipient_names}: {message_preview}"
            )

            # Send to Pachca
            self._send_message(notification_text)

        except Exception as e:
            logger.error(
                f"Error sending Pachca forum notification for message {message.id}: {str(e)}",
                exc_info=True,
            )
            # Don't raise - let message creation succeed even if Pachca fails

    def _get_forum_subject_name(self, chat_room) -> str:
        """
        Extract subject name from forum chat room.

        For forum chats linked to SubjectEnrollment, returns the subject name.

        Args:
            chat_room: ChatRoom instance

        Returns:
            Subject name or generic label if not available
        """
        try:
            if chat_room.enrollment:
                return chat_room.enrollment.get_subject_name()
        except Exception as e:
            logger.warning(
                f"Error getting subject name for chat {chat_room.id}: {str(e)}"
            )

        return "Subject"

    def _get_forum_recipient_names(self, chat_room, sender) -> str:
        """
        Get names of recipients (other participants in forum chat).

        Args:
            chat_room: ChatRoom instance
            sender: User instance who sent the message

        Returns:
            Comma-separated names of other participants
        """
        try:
            recipients = chat_room.participants.exclude(id=sender.id)
            names = [u.get_full_name() for u in recipients]
            return ", ".join(names) or "Others"
        except Exception as e:
            logger.warning(
                f"Error getting recipient names for chat {chat_room.id}: {str(e)}"
            )
            return "Others"

    @staticmethod
    def _truncate_message(content: str, max_length: int = 100) -> str:
        """
        Truncate message content to specified length.

        Args:
            content: Message content to truncate
            max_length: Maximum length (default 100 characters)

        Returns:
            Truncated content with ellipsis if needed
        """
        if len(content) > max_length:
            return content[: max_length - 3] + "..."
        return content

    def _send_message(self, text: str, max_retries: int = 3) -> bool:
        """
        Send message to Pachca API with retry logic.

        Uses exponential backoff: 1s, 2s, 4s for retries.

        Args:
            text: Message text to send
            max_retries: Maximum number of retry attempts (default 3)

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.headers:
            logger.warning(
                "Pachca service not properly configured, cannot send message"
            )
            return False

        url = f"{self.base_url}/messages"
        payload = {"channels": [self.channel_id], "content": text}

        for attempt in range(max_retries):
            try:
                response = httpx.post(
                    url, json=payload, headers=self.headers, timeout=10.0
                )

                if response.status_code in (200, 201):
                    logger.info(
                        f"Successfully sent Pachca forum notification: {text[:50]}..."
                    )
                    return True

                if response.status_code >= 500:
                    # Server error - retry
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt
                        logger.warning(
                            f"Pachca server error ({response.status_code}), "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        sleep(wait_time)
                        continue

                # Client error or final attempt - don't retry
                logger.error(
                    f"Pachca API error: {response.status_code} - {response.text}"
                )
                return False

            except httpx.RequestError as e:
                # Network error - retry
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Network error sending to Pachca: {str(e)}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    sleep(wait_time)
                    continue

                # Final attempt failed
                logger.error(f"Failed to connect to Pachca: {str(e)}")
                return False

        logger.error(f"Failed to send Pachca message after {max_retries} attempts")
        return False
