import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any
from .models import Application
from core.json_utils import safe_json_response

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Сервис для отправки уведомлений через Telegram
    Специализируется на отправке учетных данных и статусов заявок
    """
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN

    def _get_base_url(self) -> str:
        """Build base URL using current bot token (token might be patched in tests)."""
        return f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_credentials(self, telegram_id: str, username: str, password: str, role: str, 
                        child_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Отправляет учетные данные пользователю в Telegram
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Имя пользователя для входа
            password: Пароль для входа
            role: Роль пользователя (student, teacher, parent)
            child_name: Имя ребенка (для родительских аккаунтов)
            
        Returns:
            Dict с ответом от Telegram API или None в случае ошибки
        """
        if not telegram_id:
            logger.error("Telegram telegram_id не настроен")
            return None
        
        message = self._format_credentials_message(username, password, role, child_name)
        return self._send_message(telegram_id, message)
    
    def send_parent_link(self, telegram_id: str, parent_username: str, parent_password: str, 
                        child_name: str) -> Optional[Dict[str, Any]]:
        """
        Отправляет родительские учетные данные с информацией о ребенке
        
        Args:
            telegram_id: ID родителя в Telegram
            parent_username: Имя пользователя родителя
            parent_password: Пароль родителя
            child_name: Имя ребенка
            
        Returns:
            Dict с ответом от Telegram API или None в случае ошибки
        """
        if not telegram_id:
            logger.error("Telegram telegram_id не настроен")
            return None
        
        message = self._format_parent_credentials_message(
            parent_username, parent_password, child_name
        )
        return self._send_message(telegram_id, message)
    
    def send_application_status(self, telegram_id: str, status: str, 
                               details: str = None) -> Optional[Dict[str, Any]]:
        """
        Отправляет уведомление о статусе заявки
        
        Args:
            telegram_id: ID пользователя в Telegram
            status: Статус заявки (approved, rejected)
            details: Дополнительные детали
            
        Returns:
            Dict с ответом от Telegram API или None в случае ошибки
        """
        if not telegram_id:
            logger.error("Telegram telegram_id не настроен")
            return None
        
        message = self._format_status_message(status, details)
        return self._send_message(telegram_id, message)
    
    def _send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение в Telegram
        
        Args:
            chat_id: ID чата для отправки
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML или Markdown)
            
        Returns:
            Dict с ответом от Telegram API или None в случае ошибки
        """
        url = f"{self._get_base_url()}/sendMessage"
        
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
                logger.info(f"Сообщение успешно отправлено в Telegram. Chat ID: {chat_id}, Message ID: {result['result']['message_id']}")
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
    
    def _format_credentials_message(self, username: str, password: str, role: str, 
                                   child_name: str = None) -> str:
        """
        Форматирует сообщение с учетными данными
        
        Args:
            username: Имя пользователя
            password: Пароль
            role: Роль пользователя
            child_name: Имя ребенка (для родителей)
            
        Returns:
            Отформатированное сообщение
        """
        role_names = {
            'student': 'Студент',
            'teacher': 'Преподаватель',
            'parent': 'Родитель',
            'tutor': 'Тьютор'
        }
        
        role_emojis = {
            'student': '🎓',
            'teacher': '👨‍🏫',
            'parent': '👨‍👩‍👧‍👦',
            'tutor': '🎯'
        }
        
        emoji = role_emojis.get(role, '👤')
        role_display = role_names.get(role, role)
        
        message = f"""
{emoji} <b>Ваш аккаунт создан!</b>

🎉 Поздравляем! Ваша заявка одобрена.

<b>Данные для входа:</b>
👤 <b>Логин:</b> <code>{username}</code>
🔐 <b>Пароль:</b> <code>{password}</code>
🎭 <b>Роль:</b> {role_display}
"""
        
        if child_name and role == 'parent':
            message += f"\n👶 <b>Ребенок:</b> {child_name}"
        
        message += f"""

🌐 <b>Ссылка для входа:</b> https://your-platform.com/login

⚠️ <b>Важно:</b>
• Сохраните эти данные в безопасном месте
• Не передавайте их третьим лицам
• Рекомендуем сменить пароль после первого входа

📞 Если у вас есть вопросы, обращайтесь к нашей поддержке.
"""
        
        return message
    
    def _format_parent_credentials_message(self, parent_username: str, parent_password: str, 
                                         child_name: str) -> str:
        """
        Форматирует сообщение с родительскими учетными данными
        
        Args:
            parent_username: Имя пользователя родителя
            parent_password: Пароль родителя
            child_name: Имя ребенка
            
        Returns:
            Отформатированное сообщение
        """
        message = f"""
👨‍👩‍👧‍👦 <b>Родительский аккаунт создан!</b>

🎉 Для вашего ребенка <b>{child_name}</b> создан аккаунт студента, а для вас - родительский аккаунт для контроля успеваемости.

<b>Ваши данные для входа:</b>
👤 <b>Логин:</b> <code>{parent_username}</code>
🔐 <b>Пароль:</b> <code>{parent_password}</code>
🎭 <b>Роль:</b> Родитель

👶 <b>Ребенок:</b> {child_name}

🌐 <b>Ссылка для входа:</b> https://your-platform.com/login

<b>В родительском аккаунте вы сможете:</b>
📊 Отслеживать успеваемость ребенка
💳 Управлять платежами за обучение
📈 Просматривать статистику и отчеты
📝 Получать отчеты от преподавателей

⚠️ <b>Важно:</b>
• Сохраните эти данные в безопасном месте
• Не передавайте их третьим лицам
• Рекомендуем сменить пароль после первого входа

📞 Если у вас есть вопросы, обращайтесь к нашей поддержке.
"""
        
        return message
    
    def _format_status_message(self, status: str, details: str = None) -> str:
        """
        Форматирует сообщение о статусе заявки
        
        Args:
            status: Статус заявки
            details: Дополнительные детали
            
        Returns:
            Отформатированное сообщение
        """
        if status == Application.Status.APPROVED:
            message = """
✅ <b>Заявка одобрена!</b>

🎉 Поздравляем! Ваша заявка на обучение была одобрена.
Ваши учетные данные будут отправлены в отдельном сообщении.
"""
        elif status == Application.Status.REJECTED:
            message = """
❌ <b>Заявка отклонена</b>

К сожалению, ваша заявка на обучение была отклонена.
"""
        else:
            message = f"""
📋 <b>Статус заявки изменен</b>

Новый статус: {status}
"""
        
        if details:
            message += f"\n\n📝 <b>Дополнительная информация:</b>\n{details}"
        
        message += "\n\n📞 Если у вас есть вопросы, обращайтесь к нашей поддержке."
        
        return message
    
    def test_connection(self) -> bool:
        """
        Проверяет соединение с Telegram API
        
        Returns:
            True если соединение успешно, False в противном случае
        """
        if not self.bot_token:
            logger.error("Telegram bot token не настроен")
            return False
        
        url = f"{self._get_base_url()}/getMe"
        
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
telegram_notification_service = TelegramNotificationService()