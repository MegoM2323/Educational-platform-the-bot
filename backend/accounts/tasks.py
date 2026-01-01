"""
Celery tasks for accounts app.
"""
from celery import shared_task
from django.utils import timezone
import logging

from .models import TelegramLinkToken

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_telegram_tokens():
    """
    Удаляет истекшие неиспользованные токены привязки Telegram.
    Выполняется периодически (e.g., каждый час).
    """
    try:
        now = timezone.now()
        expired_count = TelegramLinkToken.objects.filter(
            expires_at__lt=now, is_used=False
        ).delete()[0]

        if expired_count > 0:
            logger.info(f"[TelegramTasks] Cleaned up {expired_count} expired tokens")

        return {"success": True, "deleted_count": expired_count}
    except Exception as e:
        logger.error(f"[TelegramTasks] Error cleaning up expired tokens: {e}")
        return {"success": False, "error": str(e)}
