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
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение в Telegram канал
        
        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML или Markdown)
            
        Returns:
            Dict с ответом от Telegram API или None в случае ошибки
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram bot token или chat_id не настроены")
            return None
        
        url = f"{self.base_url}/sendMessage"
        
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = safe_json_response(response)
            if result and result.get('ok'):
                logger.info(f"Сообщение успешно отправлено в Telegram. Message ID: {result['result']['message_id']}")
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
        
        result = self.send_message(message)
        if result and result.get('ok'):
            return str(result['result']['message_id'])
        return None
    
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
