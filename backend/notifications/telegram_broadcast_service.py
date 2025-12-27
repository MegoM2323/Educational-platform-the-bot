import logging
import os
from typing import Optional
import httpx
from django.utils import timezone
from .models import Broadcast, BroadcastRecipient

logger = logging.getLogger(__name__)


class TelegramBroadcastService:
    """Сервис для отправки рассылок через Telegram"""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if self.bot_token:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        else:
            self.api_url = None

    def send_broadcast(self, broadcast: Broadcast, message: str) -> dict:
        """
        Отправить рассылку всем получателям

        Args:
            broadcast: Объект Broadcast
            message: Текст сообщения

        Returns:
            {'sent': int, 'failed': int, 'errors': []}
        """
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN не установлен")
            return {'sent': 0, 'failed': 0, 'errors': ['Bot token not configured']}

        recipients = BroadcastRecipient.objects.filter(broadcast=broadcast).select_related('recipient')
        sent_count = 0
        failed_count = 0
        errors = []

        for recipient_record in recipients:
            user = recipient_record.recipient

            # Получить telegram_id в зависимости от роли
            telegram_id = self._get_user_telegram_id(user)

            if not telegram_id:
                failed_count += 1
                error_msg = 'Telegram ID not found'
                recipient_record.telegram_error = error_msg
                recipient_record.save()
                logger.debug(f"User {user.id} ({user.role}): {error_msg}")
                continue

            # Отправить сообщение
            message_id = self._send_message(telegram_id, message)

            if message_id:
                sent_count += 1
                recipient_record.telegram_sent = True
                recipient_record.telegram_message_id = message_id
                recipient_record.sent_at = timezone.now()
                recipient_record.save()
                logger.info(f"Message sent to user {user.id} (telegram_id={telegram_id}): message_id={message_id}")
            else:
                failed_count += 1
                error_msg = 'Failed to send via Telegram API'
                recipient_record.telegram_error = error_msg
                recipient_record.save()
                logger.error(f"Failed to send message to user {user.id} (telegram_id={telegram_id})")

        # Обновить статистику Broadcast
        broadcast.sent_count = sent_count
        broadcast.failed_count = failed_count
        broadcast.status = Broadcast.Status.SENT
        broadcast.sent_at = timezone.now()
        broadcast.save()

        logger.info(f"Broadcast #{broadcast.id} completed: sent={sent_count}, failed={failed_count}")

        return {'sent': sent_count, 'failed': failed_count}

    def _get_user_telegram_id(self, user) -> Optional[int]:
        """
        Получить telegram_id пользователя в зависимости от роли

        Args:
            user: Объект User

        Returns:
            telegram_id если найден, None если отсутствует
        """
        telegram_id = None

        try:
            if user.role == 'student' and hasattr(user, 'student_profile'):
                telegram_id = user.student_profile.telegram_id
            elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
                telegram_id = user.teacher_profile.telegram_id
            elif user.role == 'tutor' and hasattr(user, 'tutor_profile'):
                telegram_id = user.tutor_profile.telegram_id
            elif user.role == 'parent' and hasattr(user, 'parent_profile'):
                telegram_id = user.parent_profile.telegram_id
        except Exception as e:
            logger.error(f"Error getting telegram_id for user {user.id}: {e}")
            return None

        # Конвертировать в int если это строка
        if telegram_id:
            try:
                return int(telegram_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid telegram_id format for user {user.id}: {telegram_id}")
                return None

        return None

    def _send_message(self, chat_id: int, message: str) -> Optional[str]:
        """
        Отправить одно сообщение в Telegram

        Args:
            chat_id: Telegram chat ID
            message: Текст сообщения

        Returns:
            message_id если успешно, None если ошибка
        """
        try:
            response = httpx.post(
                f"{self.api_url}/sendMessage",
                json={
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return str(data['result']['message_id'])

            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout while sending message to chat_id={chat_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to send Telegram message to chat_id={chat_id}: {e}")
            return None
