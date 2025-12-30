"""
API Views для привязки Telegram аккаунтов.
"""
import hmac
import logging

from django.conf import settings as django_settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .telegram_link_service import TelegramLinkService

logger = logging.getLogger(__name__)


class BotSecretAuthentication:
    """Проверка секретного ключа бота в заголовке X-Bot-Secret."""

    @staticmethod
    def verify_bot_secret(request) -> bool:
        bot_secret = getattr(django_settings, "TELEGRAM_BOT_SECRET", "")
        if not bot_secret:
            logger.error("[TelegramLink] TELEGRAM_BOT_SECRET not configured")
            return False
        request_secret = request.headers.get("X-Bot-Secret", "")
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(request_secret, bot_secret)


class GenerateTelegramLinkView(APIView):
    """
    POST /api/profile/telegram/generate-link/
    Генерирует токен и ссылку для привязки Telegram.
    Требует авторизации.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = TelegramLinkService.generate_link_token(request.user)
            logger.info(
                f"[TelegramLink] Generated link token for user_id={request.user.id} "
                f"email={request.user.email}"
            )
            return Response(result)
        except ValueError as e:
            logger.warning(f"[TelegramLink] Rate limit exceeded for user_id={request.user.id}: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except Exception as e:
            logger.error(
                f"[TelegramLink] Error generating link for user_id={request.user.id}: {e}",
                exc_info=True,
            )
            return Response(
                {"error": "Failed to generate link"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConfirmTelegramLinkView(APIView):
    """
    POST /api/profile/telegram/confirm/
    Подтверждает привязку Telegram.
    Вызывается ботом без авторизации (AllowAny), но требует X-Bot-Secret header.

    Headers:
        X-Bot-Secret: секретный ключ бота из settings.TELEGRAM_BOT_SECRET

    Body:
    {
        "token": "...",
        "telegram_id": 123456789
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        if not BotSecretAuthentication.verify_bot_secret(request):
            logger.warning(
                f"[TelegramLink] Unauthorized bot request from IP={request.META.get('REMOTE_ADDR')}"
            )
            return Response(
                {"success": False, "error": "Unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token = request.data.get("token")
        telegram_id = request.data.get("telegram_id")

        if not token or not telegram_id:
            return Response(
                {"success": False, "error": "token and telegram_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            return Response(
                {"success": False, "error": "telegram_id must be a number"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = TelegramLinkService.confirm_link(token, telegram_id)

        if result["success"]:
            logger.info(
                f"[TelegramLink] Successfully linked telegram_id={telegram_id} "
                f"to user_id={result.get('user_id')}"
            )
            return Response(result, status=status.HTTP_200_OK)
        else:
            logger.warning(
                f"[TelegramLink] Failed to link telegram_id={telegram_id}: {result.get('error')}"
            )
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class UnlinkTelegramView(APIView):
    """
    DELETE /api/profile/telegram/unlink/
    Отвязывает Telegram от аккаунта.
    Требует авторизации.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        result = TelegramLinkService.unlink_telegram(request.user)

        if result["success"]:
            logger.info(f"[TelegramLink] Unlinked telegram from user_id={request.user.id}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class TelegramStatusView(APIView):
    """
    GET /api/profile/telegram/status/
    Возвращает статус привязки Telegram.
    Требует авторизации.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "is_linked": bool(request.user.telegram_id),
                "telegram_id": request.user.telegram_id,
            }
        )
