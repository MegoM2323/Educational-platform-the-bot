"""
Management command для запуска Telegram бота (polling mode).
Обрабатывает команду /start TOKEN для привязки аккаунтов.
"""
import logging

from django.core.management.base import BaseCommand
from django.conf import settings

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from accounts.telegram_link_service import TelegramLinkService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Запускает Telegram бота для привязки аккаунтов"

    def handle(self, *args, **options):
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not bot_token:
            self.stderr.write(
                self.style.ERROR("TELEGRAM_BOT_TOKEN не настроен в settings")
            )
            return

        self.stdout.write(self.style.SUCCESS("Запуск Telegram бота..."))

        application = Application.builder().token(bot_token).build()
        application.add_handler(CommandHandler("start", start_handler))

        self.stdout.write(
            self.style.SUCCESS("Бот запущен. Нажмите Ctrl+C для остановки.")
        )
        application.run_polling(allowed_updates=Update.ALL_TYPES)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start [TOKEN]"""
    if not update.effective_user or not update.message:
        return

    telegram_id = update.effective_user.id
    text = update.message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text(
            "Добро пожаловать! Для привязки аккаунта используйте ссылку из личного кабинета."
        )
        return

    param = parts[1].strip()

    if not param.startswith("link_"):
        await update.message.reply_text(
            "Неверный формат токена. Используйте ссылку из личного кабинета."
        )
        return

    token = param[5:]

    try:
        result = TelegramLinkService.confirm_link(token, telegram_id)
    except Exception as e:
        logger.error(f"Error confirming link for telegram_id={telegram_id}: {e}")
        await update.message.reply_text(
            "Произошла ошибка при привязке аккаунта. Попробуйте позже."
        )
        return

    if result.get("success"):
        full_name = result.get("full_name", "")
        await update.message.reply_text(
            f"Аккаунт успешно привязан!\n\nДобро пожаловать, {full_name}!"
        )
        logger.info(
            f"Telegram linked: telegram_id={telegram_id} -> user_id={result.get('user_id')}"
        )
    else:
        error = result.get("error", "Unknown error")
        error_messages = {
            "Invalid or expired token": "Недействительный или истёкший токен. Получите новую ссылку в личном кабинете.",
            "Token expired": "Срок действия токена истёк. Получите новую ссылку в личном кабинете.",
            "Telegram already linked to another account": "Этот Telegram уже привязан к другому аккаунту.",
        }
        message = error_messages.get(error, f"Ошибка привязки: {error}")
        await update.message.reply_text(message)
        logger.warning(f"Link failed for telegram_id={telegram_id}: {error}")
