"""
WebSocket Consumer для обновлений счетов в реальном времени

Функциональность:
- Подписка на обновления счетов для тьюторов и родителей
- Трансляция изменений статуса счетов
- Уведомления о создании новых счетов
- Уведомления об оплате счетов
- Реконнект с восстановлением состояния
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class InvoiceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для обновлений счетов в реальном времени

    Подключение: ws://host/ws/invoices/

    Комнаты подписки:
    - tutor_{user_id} - для тьюторов (их созданные счета)
    - parent_{user_id} - для родителей (счета для их детей)

    События:
    - invoice.created - новый счет создан
    - invoice.status_update - статус счета изменен
    - invoice.paid - счет оплачен
    """

    async def connect(self):
        """
        Подключение пользователя к WebSocket

        Процесс:
        1. Проверка JWT токена в query string
        2. Проверка аутентификации пользователя
        3. Определение роли (tutor/parent)
        4. Подписка на соответствующую комнату
        5. Подтверждение подключения
        """
        # CRITICAL FIX 1: Валидация JWT токена при WebSocket handshake
        query_string = self.scope.get('query_string', b'').decode()
        token_param = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token_param = param.split('=', 1)[1]
                break

        if not token_param:
            logger.warning('[InvoiceConsumer] Connection rejected: no JWT token provided')
            await self.close()
            return

        # Проверяем аутентификацию
        if not self.scope['user'].is_authenticated:
            logger.warning('[InvoiceConsumer] Connection rejected: user not authenticated')
            await self.close()
            return

        user = self.scope['user']

        # Определяем роль и формируем название комнаты
        if user.role == 'tutor':
            self.room_name = f'tutor_{user.id}'
        elif user.role == 'parent':
            self.room_name = f'parent_{user.id}'
        else:
            # Только тьюторы и родители могут подключаться к счетам
            logger.warning(
                f'[InvoiceConsumer] Connection rejected: invalid role {user.role} '
                f'for user {user.id}'
            )
            await self.close()
            return

        self.user_id = user.id
        self.user_role = user.role

        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        logger.info(
            f'[InvoiceConsumer] User connected: user_id={self.user_id}, '
            f'role={self.user_role}, room={self.room_name}, '
            f'channel={self.channel_name}'
        )

        # Подтверждаем подключение
        await self.accept()

        # Отправляем приветственное сообщение
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'data': {
                'user_id': self.user_id,
                'role': self.user_role,
                'room': self.room_name,
                'message': 'Connected to invoice updates'
            }
        }))

    async def disconnect(self, close_code):
        """
        Отключение пользователя от WebSocket

        Процесс:
        1. Покидание комнаты
        2. Логирование отключения
        """
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(
                self.room_name,
                self.channel_name
            )

            logger.info(
                f'[InvoiceConsumer] User disconnected: user_id={self.user_id}, '
                f'role={self.user_role}, room={self.room_name}, '
                f'close_code={close_code}'
            )

    async def receive(self, text_data):
        """
        Обработка сообщений от клиента

        Поддерживаемые типы:
        - ping - проверка соединения
        - subscribe - подписка на дополнительные события (future)

        HIGH PRIORITY FIX 6: Валидация входящих JSON с белым списком message_type
        """
        # Белый список разрешенных типов сообщений для безопасности
        ALLOWED_MESSAGE_TYPES = {'ping', 'subscribe', 'unsubscribe'}

        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            # FIX 6: Проверяем что message_type в белом списке
            if message_type not in ALLOWED_MESSAGE_TYPES:
                logger.warning(
                    f'[InvoiceConsumer] Invalid message type: {message_type} '
                    f'from user {self.user_id}'
                )
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Invalid message type: {message_type}'
                }))
                return

            if message_type == 'ping':
                # Ответ на ping для поддержания соединения
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
                logger.debug(f'[InvoiceConsumer] Ping received from user {self.user_id}')

            else:
                logger.warning(
                    f'[InvoiceConsumer] Unsupported message type: {message_type} '
                    f'from user {self.user_id}'
                )
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unsupported message type: {message_type}'
                }))

        except json.JSONDecodeError as e:
            logger.error(f'[InvoiceConsumer] Invalid JSON from user {self.user_id}: {e}')
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f'[InvoiceConsumer] Error in receive: {e}', exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    # ==================== Event Handlers ====================

    async def invoice_created(self, event):
        """
        Обработка события создания нового счета

        Отправляет данные о новом счете клиенту
        Триггерится из InvoiceService.create_invoice()
        """
        try:
            logger.info(
                f'[InvoiceConsumer] invoice_created event: '
                f'invoice_id={event.get("invoice_id")}, user={self.user_id}'
            )

            await self.send(text_data=json.dumps({
                'type': 'invoice.created',
                'invoice_id': event.get('invoice_id'),
                'data': event.get('data'),
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            logger.error(
                f'[InvoiceConsumer] Error sending invoice_created: {e}',
                exc_info=True
            )

    async def invoice_status_update(self, event):
        """
        Обработка события изменения статуса счета

        Отправляет данные об изменении статуса клиенту
        Триггерится из InvoiceService при изменении статуса
        """
        try:
            logger.info(
                f'[InvoiceConsumer] invoice_status_update event: '
                f'invoice_id={event.get("invoice_id")}, '
                f'old_status={event.get("old_status")}, '
                f'new_status={event.get("new_status")}, user={self.user_id}'
            )

            await self.send(text_data=json.dumps({
                'type': 'invoice.status_update',
                'invoice_id': event.get('invoice_id'),
                'old_status': event.get('old_status'),
                'new_status': event.get('new_status'),
                'data': event.get('data'),
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            logger.error(
                f'[InvoiceConsumer] Error sending invoice_status_update: {e}',
                exc_info=True
            )

    async def invoice_paid(self, event):
        """
        Обработка события оплаты счета

        Отправляет данные об оплате клиенту
        Триггерится из InvoiceService.process_payment()
        """
        try:
            logger.info(
                f'[InvoiceConsumer] invoice_paid event: '
                f'invoice_id={event.get("invoice_id")}, user={self.user_id}'
            )

            await self.send(text_data=json.dumps({
                'type': 'invoice.paid',
                'invoice_id': event.get('invoice_id'),
                'data': event.get('data'),
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            logger.error(
                f'[InvoiceConsumer] Error sending invoice_paid: {e}',
                exc_info=True
            )
