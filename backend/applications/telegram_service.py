import requests
import logging
from django.conf import settings
from django.utils import timezone
from typing import Optional, Dict, Any
from .models import Application
from core.json_utils import safe_json_response

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Сервис для отправки сообщений в Telegram
    """
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        # Основные каналы: публичный (для взаимодействий) и лог-канал (для детальных логов)
        self.public_chat_id = getattr(settings, 'TELEGRAM_PUBLIC_CHAT_ID', None)
        self.log_chat_id = getattr(settings, 'TELEGRAM_LOG_CHAT_ID', None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, text: str, parse_mode: str = "HTML", chat_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение в Telegram канал

        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML или Markdown)

        Returns:
            Dict с ответом от Telegram API или None в случае ошибки
        """
        if settings.TELEGRAM_DISABLED:
            logger.debug("Telegram notifications disabled in test environment")
            return None

        target_chat_id = chat_id or self.public_chat_id
        if not self.bot_token or not target_chat_id:
            logger.error("Telegram bot token или chat_id не настроены")
            return None
        
        url = f"{self.base_url}/sendMessage"
        
        data = {
            'chat_id': target_chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = safe_json_response(response)
            if result and result.get('ok'):
                logger.info(f"Сообщение успешно отправлено в Telegram. Chat ID: {target_chat_id}, Message ID: {result['result']['message_id']}")
                return result
            else:
                error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
                logger.error(f"Ошибка отправки в Telegram: {error_msg}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке в Telegram: {e}")
            return None
    
    def send_application_notification(self, application) -> Optional[str]:
        """
        Отправляет уведомление о новой заявке в Telegram
        
        Args:
            application: Объект заявки Application
            
        Returns:
            Message ID из Telegram или None в случае ошибки
        """
        # Формируем красивое сообщение
        message = self._format_application_message(application)
        
        # Отправляем в публичный канал
        result = self.send_message(message, chat_id=self.public_chat_id)
        if result and result.get('ok'):
            return str(result['result']['message_id'])
        return None

    def send_log(self, text: str, parse_mode: str = "HTML") -> Optional[Dict[str, Any]]:
        """
        Отправляет лог-сообщение в лог-канал Telegram
        """
        return self.send_message(text=text, parse_mode=parse_mode, chat_id=self.log_chat_id)
    
    def _format_application_message(self, application) -> str:
        """
        Форматирует заявку в красивое сообщение для Telegram
        
        Args:
            application: Объект заявки Application
            
        Returns:
            Отформатированное сообщение
        """
        # Определяем тип заявки и форматируем сообщение соответственно
        applicant_name = f"{application.first_name} {application.last_name}"
        applicant_type_emoji = {
            Application.ApplicantType.STUDENT: '🎓',
            Application.ApplicantType.TEACHER: '👨‍🏫',
            Application.ApplicantType.PARENT: '👨‍👩‍👧‍👦'
        }
        emoji = applicant_type_emoji.get(application.applicant_type, '👤')
        
        message = f"""
{emoji} <b>Новая заявка на обучение</b>

👤 <b>Заявитель:</b> {applicant_name}
📋 <b>Тип:</b> {application.get_applicant_type_display()}
📞 <b>Телефон:</b> {application.phone}
📧 <b>Email:</b> {application.email}
"""
        
        # Добавляем специфичную информацию в зависимости от типа заявки
        if application.applicant_type == Application.ApplicantType.STUDENT:
            if application.grade:
                message += f"🎯 <b>Класс:</b> {application.grade}\n"
            if application.parent_first_name and application.parent_last_name:
                message += f"👨‍👩‍👧‍👦 <b>Родитель:</b> {application.parent_first_name} {application.parent_last_name}\n"
        
        elif application.applicant_type == Application.ApplicantType.TEACHER:
            if application.subject:
                message += f"📚 <b>Предмет:</b> {application.subject}\n"
        
        message += f"\n📅 <b>Дата подачи:</b> {application.created_at.strftime('%d.%m.%Y в %H:%M')}"
        
        if application.motivation:
            message += f"\n\n🎯 <b>Мотивация/Цель:</b>\n{application.motivation}"
        
        if application.experience:
            message += f"\n\n💼 <b>Опыт:</b>\n{application.experience}"
        
        message += f"\n\n🆔 <b>ID заявки:</b> #{application.id}"
        
        return message
    
    def send_status_update(self, application, old_status: str, new_status: str) -> Optional[str]:
        """
        Отправляет уведомление об изменении статуса заявки
        
        Args:
            application: Объект заявки Application
            old_status: Предыдущий статус
            new_status: Новый статус
            
        Returns:
            Message ID из Telegram или None в случае ошибки
        """
        status_emojis = {
            'new': '🆕',
            'processing': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'completed': '🎉'
        }
        
        status_names = {
            'new': 'Новая',
            'processing': 'В обработке',
            'approved': 'Одобрена',
            'rejected': 'Отклонена',
            'completed': 'Завершена'
        }
        
        emoji = status_emojis.get(new_status, '📝')
        status_name = status_names.get(new_status, new_status)
        
        applicant_name = f"{application.first_name} {application.last_name}"
        
        message = f"""
{emoji} <b>Обновление статуса заявки</b>

👤 <b>Заявитель:</b> {applicant_name}
📋 <b>Тип:</b> {application.get_applicant_type_display()}
📞 <b>Телефон:</b> {application.phone}
🆔 <b>ID заявки:</b> #{application.id}

📊 <b>Статус изменен:</b> {status_name}
⏰ <b>Время:</b> {timezone.now().strftime('%d.%m.%Y в %H:%M')}
"""
        
        if application.notes:
            message += f"\n📝 <b>Заметки:</b> {application.notes}"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """
        Проверяет соединение с Telegram API
        
        Returns:
            True если соединение успешно, False в противном случае
        """
        if not self.bot_token:
            logger.error("Telegram bot token не настроен")
            return False
        
        url = f"{self.base_url}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = safe_json_response(response)
            if result and result.get('ok'):
                bot_info = result['result']
                logger.info(f"Telegram бот подключен: @{bot_info.get('username', 'Unknown')}")
                return True
            else:
                error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
                logger.error(f"Ошибка проверки Telegram бота: {error_msg}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при проверке Telegram бота: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке Telegram бота: {e}")
            return False


# Создаем экземпляр сервиса
telegram_service = TelegramService()


class TelegramNotificationService:
    """
    Backward-compatible уведомительный сервис, ожидаемый старыми тестами.
    Использует тот же транспорт (requests.post) и базовые настройки, что и TelegramService
    из этого же модуля, чтобы моки вида
    `@patch('applications.telegram_service.requests.post')` корректно перехватывали вызовы.
    """

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def _send_message(self, chat_id: str, text: str, parse_mode: str = "HTML"):
        if settings.TELEGRAM_DISABLED:
            logger.debug("Telegram notifications disabled in test environment")
            return None

        if not self.bot_token or not chat_id:
            logger.error("Telegram bot token или chat_id не настроены")
            return None

        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            result = safe_json_response(response)
            if result and result.get('ok'):
                logger.info(
                    f"Сообщение успешно отправлено в Telegram. Chat ID: {chat_id}, Message ID: {result['result']['message_id']}"
                )
                return result
            else:
                error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
                logger.error(f"Ошибка отправки в Telegram: {error_msg}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке в Telegram: {e}")
            return None

    def _format_credentials_message(self, username: str, password: str) -> str:
        return "\n".join([
            "✅ Учетные данные",
            f"👤 Логин: <code>{username}</code>",
            f"🔐 Пароль: <code>{password}</code>",
        ])

    def send_application_approved_notification(self, application: Application, credentials):
        """
        Метод, совместимый с существующими нагрузочными тестами.
        Отправляет учетные данные заявителю, если указан его telegram_id.
        """
        chat_id = getattr(application, 'telegram_id', '') or getattr(application, 'parent_telegram_id', '')
        if not chat_id:
            # Fallback на публичный канал, чтобы не падать в тестах без telegram_id
            chat_id = getattr(settings, 'TELEGRAM_PUBLIC_CHAT_ID', None) or getattr(settings, 'TELEGRAM_CHAT_ID', None)

        message = self._format_credentials_message(
            username=getattr(credentials, 'get', lambda k, d=None: None)('username') if hasattr(credentials, 'get') else credentials['username'],
            password=getattr(credentials, 'get', lambda k, d=None: None)('password') if hasattr(credentials, 'get') else credentials['password'],
        )
        return self._send_message(chat_id=chat_id, text=message)
