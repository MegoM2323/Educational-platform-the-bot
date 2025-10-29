import requests
import logging
from django.conf import settings
from core.json_utils import safe_json_response

logger = logging.getLogger(__name__)

class TelegramNotificationService:
    """Сервис для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        # Все уведомления об оплате направляем в лог-канал
        self.chat_id = getattr(settings, 'TELEGRAM_LOG_CHAT_ID', None)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    def send_payment_notification(self, payment):
        """Отправляет уведомление о успешном платеже"""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or TELEGRAM_LOG_CHAT_ID not configured")
            return False
        
        try:
            message = self._format_payment_message(payment)
            return self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def _format_payment_message(self, payment):
        """Форматирует сообщение о платеже"""
        amount = payment.amount
        service_name = payment.service_name or "Не указано"
        customer_fio = payment.customer_fio or "Не указано"
        payment_id = payment.id
        
        message = f"""
💳 *Новый успешный платеж!*

💰 *Сумма:* {amount} ₽
🏢 *Услуга:* {service_name}
👤 *Плательщик:* {customer_fio}
🆔 *ID платежа:* `{payment_id}`
📅 *Время:* {payment.paid_at.strftime('%d.%m.%Y %H:%M')}

✅ Платеж успешно обработан
        """.strip()
        
        return message
    
    def _send_message(self, message):
        """Отправляет сообщение в Telegram"""
        try:
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(
                self.api_url,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                response_data = safe_json_response(response, {})
                error_description = response_data.get('description', 'Unknown error') if response_data else 'Не удалось распарсить ответ'
                logger.error(f"Telegram API error: {response.status_code} - {error_description}")
                
                # Специальная обработка ошибок
                if response.status_code == 400:
                    if "chat not found" in error_description.lower():
                        logger.error("Chat not found. Проверьте TELEGRAM_LOG_CHAT_ID")
                    elif "bot was blocked" in error_description.lower():
                        logger.error("Бот заблокирован пользователем")
                    elif "can't parse entities" in error_description.lower():
                        logger.error("Ошибка форматирования сообщения")
                elif response.status_code == 403:
                    if "bot was blocked" in error_description.lower():
                        logger.error("Бот заблокирован пользователем")
                    elif "group chat was upgraded" in error_description.lower():
                        logger.error("Чат был преобразован в супергруппу")
                
                return False
                
        except requests.RequestException as e:
            logger.error(f"Request error sending Telegram notification: {e}")
            return False
    
    def get_bot_info(self):
        """Получает информацию о боте"""
        if not self.bot_token:
            return False, "Bot token not configured"
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = safe_json_response(response)
                if bot_info:
                    return True, bot_info
                else:
                    return False, "Не удалось распарсить ответ от Telegram API"
            else:
                return False, f"API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"Request error: {e}"
    
    def test_connection(self):
        """Тестирует подключение к Telegram API"""
        if not self.bot_token or not self.chat_id:
            return False, "Bot token or chat_id not configured"
        
        # Сначала проверим информацию о боте
        bot_ok, bot_info = self.get_bot_info()
        if not bot_ok:
            return False, f"Bot info error: {bot_info}"
        
        # Затем попробуем отправить тестовое сообщение
        try:
            test_message = "🧪 Тестовое сообщение от бота платежей"
            success = self._send_message(test_message)
            if success:
                return True, f"Test message sent successfully. Bot: @{bot_info['result']['username']}"
            else:
                return False, "Failed to send test message"
        except Exception as e:
            return False, f"Test failed: {e}"
