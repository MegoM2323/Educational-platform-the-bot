import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class TelegramNotificationService:
    """Сервис для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    def send_payment_notification(self, payment):
        """Отправляет уведомление о успешном платеже"""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat_id not configured")
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
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Request error sending Telegram notification: {e}")
            return False
    
    def test_connection(self):
        """Тестирует подключение к Telegram API"""
        if not self.bot_token or not self.chat_id:
            return False, "Bot token or chat_id not configured"
        
        try:
            test_message = "🧪 Тестовое сообщение от бота платежей"
            return self._send_message(test_message), "Test message sent"
        except Exception as e:
            return False, f"Test failed: {e}"
