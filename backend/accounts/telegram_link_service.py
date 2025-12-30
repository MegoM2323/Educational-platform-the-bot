"""
Сервис для привязки Telegram аккаунтов к веб-аккаунтам пользователей.
"""
import secrets
from datetime import timedelta
from typing import Dict, Any

from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .models import TelegramLinkToken, User


class TelegramLinkService:
    """Сервис управления привязкой Telegram"""

    MAX_TOKENS_PER_WINDOW = 5
    TOKEN_WINDOW_MINUTES = 10

    @classmethod
    def _get_token_ttl_minutes(cls) -> int:
        return getattr(settings, "TELEGRAM_LINK_TOKEN_TTL_MINUTES", 10)

    @classmethod
    def _check_rate_limit(cls, user: User) -> bool:
        window_start = timezone.now() - timedelta(minutes=cls.TOKEN_WINDOW_MINUTES)
        recent_tokens_count = TelegramLinkToken.objects.filter(
            user=user, created_at__gte=window_start
        ).count()
        return recent_tokens_count < cls.MAX_TOKENS_PER_WINDOW

    @classmethod
    def generate_link_token(cls, user: User) -> Dict[str, Any]:
        """
        Генерирует токен для привязки Telegram.
        Удаляет старые неиспользованные токены пользователя.
        Rate limit: не более 5 токенов за 10 минут.
        """
        if not cls._check_rate_limit(user):
            raise ValueError("Too many token requests. Please wait before trying again.")

        token = secrets.token_urlsafe(32)
        ttl_minutes = cls._get_token_ttl_minutes()
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

        # Use transaction to ensure atomicity of delete + create
        with transaction.atomic():
            TelegramLinkToken.objects.filter(user=user, is_used=False).delete()
            TelegramLinkToken.objects.create(user=user, token=token, expires_at=expires_at)

        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "THE_BOT_edu_bot")
        return {
            "token": token,
            "link": f"https://t.me/{bot_username}?start=link_{token}",
            "expires_at": expires_at.isoformat(),
            "ttl_minutes": ttl_minutes,
        }

    @classmethod
    def confirm_link(cls, token: str, telegram_id: int) -> Dict[str, Any]:
        """
        Подтверждает привязку Telegram по токену.
        Вызывается ботом после получения /start link_TOKEN.
        Uses transaction with select_for_update to prevent race conditions.
        """
        with transaction.atomic():
            try:
                # Lock the token row to prevent concurrent linking
                link_token = TelegramLinkToken.objects.select_for_update().select_related("user").get(
                    token=token, is_used=False
                )
            except TelegramLinkToken.DoesNotExist:
                return {"success": False, "error": "Invalid or expired token"}

            if link_token.is_expired():
                return {"success": False, "error": "Token expired"}

            # Check if telegram_id already linked, with lock to prevent race
            existing_user = User.objects.select_for_update().filter(telegram_id=telegram_id).first()
            if existing_user:
                return {
                    "success": False,
                    "error": "Telegram already linked to another account",
                }

            user = link_token.user
            user.telegram_id = telegram_id
            user.save(update_fields=["telegram_id"])

            link_token.is_used = True
            link_token.used_at = timezone.now()
            link_token.save(update_fields=["is_used", "used_at"])

            return {
                "success": True,
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.get_full_name(),
                "role": user.role,
            }

    @classmethod
    def unlink_telegram(cls, user: User) -> Dict[str, Any]:
        """Отвязывает Telegram от аккаунта пользователя."""
        if not user.telegram_id:
            return {"success": False, "error": "Telegram not linked"}

        user.telegram_id = None
        user.save(update_fields=["telegram_id"])
        return {"success": True}

    @classmethod
    def get_user_by_telegram_id(cls, telegram_id: int) -> User | None:
        """Получает пользователя по Telegram ID."""
        return User.objects.filter(telegram_id=telegram_id).first()

    @classmethod
    def is_telegram_linked(cls, user: User) -> bool:
        """Проверяет, привязан ли Telegram к аккаунту."""
        return bool(user.telegram_id)
