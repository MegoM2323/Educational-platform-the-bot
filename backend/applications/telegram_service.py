import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any

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
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"Сообщение успешно отправлено в Telegram. Message ID: {result['result']['message_id']}")
                return result
            else:
                logger.error(f"Ошибка отправки в Telegram: {result.get('description', 'Неизвестная ошибка')}")
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
        message = f"""
🎓 <b>Новая заявка на обучение</b>

👤 <b>Ученик:</b> {application.student_name}
👨‍👩‍👧‍👦 <b>Родитель:</b> {application.parent_name}
📞 <b>Телефон:</b> {application.phone}
📧 <b>Email:</b> {application.email}
🎯 <b>Класс:</b> {application.grade}
        
📅 <b>Дата подачи:</b> {application.created_at.strftime('%d.%m.%Y в %H:%M')}
"""
        
        if application.goal:
            message += f"\n🎯 <b>Цель обучения:</b> {application.goal}"
        
        if application.message:
            message += f"\n💬 <b>Дополнительная информация:</b>\n{application.message}"
        
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
        
        message = f"""
{emoji} <b>Обновление статуса заявки</b>

👤 <b>Ученик:</b> {application.student_name}
📞 <b>Телефон:</b> {application.phone}
🆔 <b>ID заявки:</b> #{application.id}

📊 <b>Статус изменен:</b> {status_name}
⏰ <b>Время:</b> {application.updated_at.strftime('%d.%m.%Y в %H:%M')}
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
            
            result = response.json()
            if result.get('ok'):
                bot_info = result['result']
                logger.info(f"Telegram бот подключен: @{bot_info.get('username', 'Unknown')}")
                return True
            else:
                logger.error(f"Ошибка проверки Telegram бота: {result.get('description', 'Неизвестная ошибка')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при проверке Telegram бота: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке Telegram бота: {e}")
            return False


# Создаем экземпляр сервиса
telegram_service = TelegramService()
