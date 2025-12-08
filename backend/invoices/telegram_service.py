"""
Telegram Service для Invoice System
Отправка уведомлений о счетах в Telegram с кнопками оплаты
"""
import requests
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from core.json_utils import safe_json_response

logger = logging.getLogger(__name__)


class InvoiceTelegramService:
    """
    Сервис для отправки счетов через Telegram бота

    Функциональность:
    - Отправка уведомления о счете родителю
    - Inline-кнопка для перехода к оплате
    - Обновление сообщения при изменении статуса
    - Редактирование сообщения при оплате
    """

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.disabled = settings.TELEGRAM_DISABLED

    def send_invoice_notification(self, invoice) -> Optional[str]:
        """
        Отправляет уведомление о новом счете родителю в Telegram

        Args:
            invoice: Invoice объект

        Returns:
            message_id из Telegram или None в случае ошибки

        Примечание:
            Требуется наличие parent.parent_profile.telegram_id
        """
        if self.disabled:
            logger.debug("Telegram notifications disabled in test environment")
            return None

        if not self.bot_token:
            logger.error("Telegram bot token не настроен")
            return None

        # Проверяем наличие telegram_id у родителя
        if not hasattr(invoice.parent, 'parent_profile'):
            logger.warning(f"У родителя {invoice.parent.id} нет профиля ParentProfile")
            return None

        parent_telegram_id = invoice.parent.parent_profile.telegram_id
        if not parent_telegram_id:
            logger.info(f"У родителя {invoice.parent.id} не указан telegram_id, пропускаем отправку")
            return None

        # Форматируем сообщение
        message_text = self.format_invoice_message(invoice)

        # Создаем inline-клавиатуру с кнопкой оплаты
        keyboard = self.create_payment_keyboard(invoice)

        # Отправляем сообщение
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': parent_telegram_id,
            'text': message_text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
            'reply_markup': keyboard
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = safe_json_response(response)
            if result and result.get('ok'):
                message_id = str(result['result']['message_id'])
                logger.info(
                    f"Уведомление о счете #{invoice.id} отправлено в Telegram. "
                    f"Chat ID: {parent_telegram_id}, Message ID: {message_id}"
                )
                return message_id
            else:
                error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
                logger.error(f"Ошибка отправки уведомления о счете в Telegram: {error_msg}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке уведомления о счете в Telegram: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления о счете в Telegram: {e}")
            return None

    def format_invoice_message(self, invoice) -> str:
        """
        Форматирует счет в сообщение для Telegram

        Args:
            invoice: Invoice объект

        Returns:
            Отформатированное HTML-сообщение
        """
        status_emoji = {
            'draft': '📝',
            'sent': '📤',
            'viewed': '👁',
            'paid': '✅',
            'cancelled': '❌',
            'overdue': '⏰'
        }

        emoji = status_emoji.get(invoice.status, '📋')

        # Форматируем дату оплаты
        due_date_str = invoice.due_date.strftime('%d.%m.%Y')

        # Основное сообщение
        message = f"""
{emoji} <b>Счет на оплату</b>

👤 <b>Студент:</b> {invoice.student.get_full_name()}
💰 <b>Сумма:</b> {invoice.amount} руб.
📅 <b>Срок оплаты:</b> {due_date_str}

📝 <b>Описание услуг:</b>
{invoice.description}

🆔 <b>Номер счета:</b> #{invoice.id}
📊 <b>Статус:</b> {invoice.get_status_display()}
"""

        # Добавляем информацию о предмете, если есть
        if invoice.enrollment:
            message += f"\n📚 <b>Предмет:</b> {invoice.enrollment.subject.name}"
            if invoice.enrollment.teacher:
                message += f"\n👨‍🏫 <b>Преподаватель:</b> {invoice.enrollment.teacher.get_full_name()}"

        # Добавляем дату отправки
        if invoice.sent_at:
            sent_date_str = invoice.sent_at.strftime('%d.%m.%Y в %H:%M')
            message += f"\n\n📬 <b>Дата отправки:</b> {sent_date_str}"

        # Добавляем предупреждение если просрочен
        if invoice.is_overdue and invoice.status not in ['paid', 'cancelled']:
            message += "\n\n⚠️ <b>Внимание:</b> Срок оплаты истек"

        return message.strip()

    def create_payment_keyboard(self, invoice) -> Dict[str, Any]:
        """
        Создает inline-клавиатуру с кнопками для счета

        Args:
            invoice: Invoice объект

        Returns:
            JSON-структура inline_keyboard для Telegram
        """
        # Если счет оплачен или отменен - не показываем кнопку оплаты
        if invoice.status in ['paid', 'cancelled']:
            return {
                'inline_keyboard': [
                    [
                        {
                            'text': '👁️ Посмотреть на сайте',
                            'url': f"{settings.FRONTEND_URL}/dashboard/parent/invoices?invoice_id={invoice.id}"
                        }
                    ]
                ]
            }

        # Для неоплаченных счетов - кнопка оплаты и просмотра
        payment_url = f"{settings.FRONTEND_URL}/dashboard/parent/invoices?invoice_id={invoice.id}&action=pay"

        return {
            'inline_keyboard': [
                [
                    {
                        'text': '💳 Оплатить',
                        'url': payment_url
                    }
                ],
                [
                    {
                        'text': '👁️ Посмотреть на сайте',
                        'url': f"{settings.FRONTEND_URL}/dashboard/parent/invoices?invoice_id={invoice.id}"
                    }
                ]
            ]
        }

    def update_invoice_message(self, invoice) -> bool:
        """
        Обновляет существующее сообщение о счете в Telegram

        Используется при изменении статуса счета (например, оплата)

        Args:
            invoice: Invoice объект с заполненным telegram_message_id

        Returns:
            True если сообщение успешно обновлено, False иначе
        """
        if self.disabled:
            logger.debug("Telegram notifications disabled in test environment")
            return False

        if not self.bot_token:
            logger.error("Telegram bot token не настроен")
            return False

        if not invoice.telegram_message_id:
            logger.warning(f"У счета #{invoice.id} нет telegram_message_id, пропускаем обновление")
            return False

        if not hasattr(invoice.parent, 'parent_profile'):
            logger.warning(f"У родителя {invoice.parent.id} нет профиля ParentProfile")
            return False

        parent_telegram_id = invoice.parent.parent_profile.telegram_id
        if not parent_telegram_id:
            logger.warning(f"У родителя {invoice.parent.id} не указан telegram_id, пропускаем обновление")
            return False

        # Форматируем обновленное сообщение
        message_text = self.format_invoice_message(invoice)

        # Обновляем клавиатуру
        keyboard = self.create_payment_keyboard(invoice)

        # Редактируем сообщение
        url = f"{self.base_url}/editMessageText"
        data = {
            'chat_id': parent_telegram_id,
            'message_id': invoice.telegram_message_id,
            'text': message_text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
            'reply_markup': keyboard
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = safe_json_response(response)
            if result and result.get('ok'):
                logger.info(
                    f"Сообщение о счете #{invoice.id} обновлено в Telegram. "
                    f"Chat ID: {parent_telegram_id}, Message ID: {invoice.telegram_message_id}"
                )
                return True
            else:
                error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
                logger.error(f"Ошибка обновления сообщения о счете в Telegram: {error_msg}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при обновлении сообщения о счете в Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении сообщения о счете в Telegram: {e}")
            return False

    def send_payment_confirmation(self, invoice) -> Optional[str]:
        """
        Отправляет отдельное сообщение-подтверждение об оплате счета

        Используется как дополнительное уведомление после оплаты

        Args:
            invoice: Оплаченный Invoice объект

        Returns:
            message_id нового сообщения или None
        """
        if self.disabled:
            logger.debug("Telegram notifications disabled in test environment")
            return None

        if not self.bot_token:
            logger.error("Telegram bot token не настроен")
            return None

        if not hasattr(invoice.parent, 'parent_profile'):
            logger.warning(f"У родителя {invoice.parent.id} нет профиля ParentProfile")
            return None

        parent_telegram_id = invoice.parent.parent_profile.telegram_id
        if not parent_telegram_id:
            logger.info(f"У родителя {invoice.parent.id} не указан telegram_id, пропускаем отправку")
            return None

        # Форматируем сообщение-подтверждение
        paid_date_str = invoice.paid_at.strftime('%d.%m.%Y в %H:%M') if invoice.paid_at else timezone.now().strftime('%d.%m.%Y в %H:%M')

        message = f"""
✅ <b>Счет оплачен</b>

🆔 <b>Номер счета:</b> #{invoice.id}
👤 <b>Студент:</b> {invoice.student.get_full_name()}
💰 <b>Сумма:</b> {invoice.amount} руб.
📅 <b>Дата оплаты:</b> {paid_date_str}

Спасибо за своевременную оплату! 🎉
"""

        # Отправляем сообщение
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': parent_telegram_id,
            'text': message.strip(),
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = safe_json_response(response)
            if result and result.get('ok'):
                message_id = str(result['result']['message_id'])
                logger.info(
                    f"Подтверждение оплаты счета #{invoice.id} отправлено в Telegram. "
                    f"Chat ID: {parent_telegram_id}, Message ID: {message_id}"
                )
                return message_id
            else:
                error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
                logger.error(f"Ошибка отправки подтверждения оплаты в Telegram: {error_msg}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке подтверждения оплаты в Telegram: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке подтверждения оплаты в Telegram: {e}")
            return None


# Создаем глобальный экземпляр сервиса
invoice_telegram_service = InvoiceTelegramService()
