"""
Webhook view для обработки Telegram updates.
Альтернатива polling режиму для production.
"""
import hmac
import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .telegram_link_service import TelegramLinkService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    POST /api/telegram/webhook/<secret>/
    Обрабатывает updates от Telegram.
    Secret токен в URL для аутентификации.
    """

    def post(self, request: HttpRequest, secret: str) -> HttpResponse:
        bot_secret = getattr(settings, "TELEGRAM_BOT_SECRET", "")
        if not bot_secret:
            logger.error("[TelegramWebhook] TELEGRAM_BOT_SECRET not configured")
            return HttpResponse(status=500)

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(secret, bot_secret):
            logger.warning(
                f"[TelegramWebhook] Invalid secret from IP={request.META.get('REMOTE_ADDR')}"
            )
            return HttpResponse(status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("[TelegramWebhook] Invalid JSON body")
            return HttpResponse(status=400)

        self._process_update(data)
        return HttpResponse(status=200)

    def _process_update(self, data: dict[str, Any]) -> None:
        """Обрабатывает Telegram update"""
        message = data.get("message")
        if not message:
            return

        text = message.get("text", "")
        if not text.startswith("/start"):
            return

        from_user = message.get("from")
        if not from_user:
            return

        telegram_id = from_user.get("id")
        if not telegram_id:
            return

        chat_id = message.get("chat", {}).get("id")
        if not chat_id:
            return

        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            self._send_message(
                chat_id,
                "Добро пожаловать! Для привязки аккаунта используйте ссылку из личного кабинета.",
            )
            return

        param = parts[1].strip()
        if not param.startswith("link_"):
            self._send_message(
                chat_id,
                "Неверный формат токена. Используйте ссылку из личного кабинета.",
            )
            return

        token = param[5:]

        try:
            result = TelegramLinkService.confirm_link(token, telegram_id)
        except Exception as e:
            logger.error(f"[TelegramWebhook] Error confirming link: {e}")
            self._send_message(
                chat_id,
                "Произошла ошибка при привязке аккаунта. Попробуйте позже.",
            )
            return

        if result.get("success"):
            full_name = result.get("full_name", "")
            self._send_message(
                chat_id,
                f"Аккаунт успешно привязан!\n\nДобро пожаловать, {full_name}!",
            )
            logger.info(
                f"[TelegramWebhook] Linked telegram_id={telegram_id} -> user_id={result.get('user_id')}"
            )
        else:
            error = result.get("error", "Unknown error")
            error_messages = {
                "Invalid or expired token": "Недействительный или истёкший токен. Получите новую ссылку в личном кабинете.",
                "Token expired": "Срок действия токена истёк. Получите новую ссылку в личном кабинете.",
                "Telegram already linked to another account": "Этот Telegram уже привязан к другому аккаунту.",
            }
            message = error_messages.get(error, f"Ошибка привязки: {error}")
            self._send_message(chat_id, message)
            logger.warning(
                f"[TelegramWebhook] Link failed for telegram_id={telegram_id}: {error}"
            )

    def _send_message(self, chat_id: int, text: str) -> bool:
        """Отправляет сообщение через Telegram API"""
        import requests

        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not bot_token:
            logger.error("[TelegramWebhook] TELEGRAM_BOT_TOKEN not configured")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            response = requests.post(
                url,
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"[TelegramWebhook] Failed to send message: {e}")
            return False
