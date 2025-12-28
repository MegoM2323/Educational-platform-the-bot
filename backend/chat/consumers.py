import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from .models import ChatRoom, Message, MessageRead, ChatParticipant
from .serializers import MessageSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

# WebSocket message size limit (default 1MB)
WEBSOCKET_MESSAGE_MAX_LENGTH = getattr(settings, 'WEBSOCKET_MESSAGE_MAX_LENGTH', 1048576)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для чат-комнат
    """

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # DEBUG: Log connection attempt
        logger.warning(f'[ChatConsumer] Connection attempt: room={self.room_id}, user={self.scope["user"]}, authenticated={self.scope["user"].is_authenticated}')

        # Проверяем, что пользователь аутентифицирован
        if not self.scope['user'].is_authenticated:
            logger.warning(f'[ChatConsumer] Connection rejected: user not authenticated')
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Authentication required',
                'code': 'auth_error'
            }))
            await self.close(code=4001)
            return

        # Проверяем, что пользователь имеет доступ к комнате
        has_access = await self.check_room_access()
        logger.warning(f'[ChatConsumer] Room access check: {has_access}')
        if not has_access:
            logger.warning(f'[ChatConsumer] Connection rejected: no room access')
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Access denied to this room',
                'code': 'access_error'
            }))
            await self.close(code=4002)
            return

        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        logger.warning(f'[GroupAdd] Room={self.room_id}, Group={self.room_group_name}, Channel={self.channel_name}, User={self.scope["user"].username}')

        await self.accept()

        # Отправляем историю сообщений
        await self.send_room_history()

        # Уведомляем других участников о подключении
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'user': {
                        'id': self.scope['user'].id,
                        'username': self.scope['user'].username,
                        'first_name': self.scope['user'].first_name,
                        'last_name': self.scope['user'].last_name,
                    }
                }
            )
            logger.warning(f'[ChatConsumer] Broadcasting user_joined to {self.room_group_name}')
        except Exception as e:
            logger.error(f'Channel layer error broadcasting user_joined in room {self.room_id}: {e}', exc_info=True)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            # Очищаем индикатор печати для отключающегося пользователя
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_stop',
                        'user': {
                            'id': self.scope['user'].id,
                            'username': self.scope['user'].username,
                        }
                    }
                )
            except Exception as e:
                logger.error(f'Error clearing typing on disconnect in room {self.room_id}: {e}', exc_info=True)

            # Уведомляем других участников об отключении
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_left',
                        'user': {
                            'id': self.scope['user'].id,
                            'username': self.scope['user'].username,
                        }
                    }
                )
            except Exception as e:
                logger.error(f'Channel layer error broadcasting user_left in room {self.room_id}: {e}', exc_info=True)

            # Покидаем группу комнаты
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.warning(f'[GroupDiscard] Group={self.room_group_name}, Channel={self.channel_name}')

    async def receive(self, text_data):
        # Проверяем размер сообщения для защиты от DoS
        if len(text_data) > WEBSOCKET_MESSAGE_MAX_LENGTH:
            logger.warning(f"WebSocket message size exceeds limit: {len(text_data)} > {WEBSOCKET_MESSAGE_MAX_LENGTH}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message too large'
            }))
            return

        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'mark_read':
                await self.handle_mark_read(data)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    async def handle_chat_message(self, data):
        """Обработка нового сообщения"""
        content = data.get('content', '').strip()
        if not content:
            # Отправляем ошибку валидации отправителю
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content required',
                'code': 'validation_error'
            }))
            return

        # Проверяем, что пользователь является участником комнаты (защита от IDOR)
        if not await self.check_user_is_participant(self.room_id):
            logger.warning(f'[HandleChatMessage] Access denied: user {self.scope["user"].id} is not a participant in room {self.room_id}')
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'You are not a participant in this room',
                'code': 'access_denied'
            }))
            return

        # Создаем сообщение
        message = await self.create_message(content)
        logger.warning(f'[HandleChatMessage] Created message: {message}')
        if message:
            # Подтверждаем отправителю, что сообщение сохранено
            await self.send(text_data=json.dumps({
                'type': 'message_sent',
                'message_id': message.get('id'),
                'status': 'delivered'
            }))
            # Отправляем сообщение всем участникам группы
            logger.warning(f'[HandleChatMessage] Broadcasting to group {self.room_group_name}, message_id={message.get("id", "unknown")}')
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message
                    }
                )
                logger.warning(f'[HandleChatMessage] Broadcast completed for message_id={message.get("id", "unknown")}')
            except Exception as e:
                logger.error(f'Channel layer error in room {self.room_id}: {e}', exc_info=True)
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Message delivery failed',
                    'code': 'channel_error'
                }))
        else:
            # Сообщаем отправителю об ошибке сохранения
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to save message',
                'code': 'save_error'
            }))

    async def handle_typing(self, data):
        """Обработка индикатора печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing',
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                    'first_name': self.scope['user'].first_name,
                    'last_name': self.scope['user'].last_name,
                }
            }
        )

    async def handle_typing_stop(self, data):
        """Обработка остановки печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_stop',
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                }
            }
        )

    async def handle_mark_read(self, data):
        """Обработка отметки о прочтении"""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_read(message_id)

    async def chat_message(self, event):
        """Отправка сообщения клиенту"""
        logger.warning(f'[ChatMessage Handler] CALLED! Event={event}')
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
        logger.warning(f'[ChatMessage Handler] SENT to client! message_id={event["message"].get("id", "unknown")}')

    async def typing(self, event):
        """Отправка индикатора печати клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user']
        }))

    async def typing_stop(self, event):
        """Отправка остановки печати клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'typing_stop',
            'user': event['user']
        }))

    async def user_joined(self, event):
        """Уведомление о присоединении пользователя"""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user']
        }))

    async def user_left(self, event):
        """Уведомление об уходе пользователя"""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user']
        }))

    @database_sync_to_async
    def check_room_access(self):
        """
        Проверка доступа к комнате.

        Проверяет доступ через:
        1. M2M participants (ChatRoom.participants)
        2. ChatParticipant записи (для обратной совместимости)
        3. Родительский доступ: если пользователь - родитель и его ребёнок является участником
        """
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            user = self.scope['user']
            user_id = user.id

            # Проверка 1: M2M participants
            if room.participants.filter(id=user_id).exists():
                logger.debug(f'[check_room_access] User {user_id} has access via M2M participants')
                return True

            # Проверка 2: ChatParticipant (fallback для старых чатов)
            if ChatParticipant.objects.filter(room=room, user=user).exists():
                # Синхронизируем: добавляем в M2M если ещё нет
                room.participants.add(user)
                logger.info(f'[check_room_access] User {user_id} synced from ChatParticipant to M2M')
                return True

            # Проверка 3: Родительский доступ к чатам детей
            # Родители могут просматривать FORUM_SUBJECT и FORUM_TUTOR чаты своих детей
            if user.role == 'parent':
                from accounts.models import StudentProfile
                # Получаем ID всех детей этого родителя
                children_ids = StudentProfile.objects.filter(
                    parent=user
                ).values_list('user_id', flat=True)

                # Проверяем, является ли хотя бы один ребёнок участником комнаты
                if children_ids and room.participants.filter(id__in=children_ids).exists():
                    # Добавляем родителя в участники для будущих проверок
                    room.participants.add(user)
                    ChatParticipant.objects.get_or_create(room=room, user=user)
                    logger.info(
                        f'[check_room_access] Parent {user_id} granted access to room {self.room_id} '
                        f'via child relationship and added to participants'
                    )
                    return True

            logger.warning(
                f'[check_room_access] Access denied: user {user_id} (role={user.role}) '
                f'is not a participant in room {self.room_id} (type={room.type})'
            )
            return False
        except ObjectDoesNotExist:
            logger.warning(f'[check_room_access] Room {self.room_id} does not exist')
            return False

    @database_sync_to_async
    def check_user_is_participant(self, room_id):
        """
        Проверка, что текущий пользователь является участником комнаты.

        Проверяет в двух местах для обратной совместимости:
        1. ChatParticipant (предпочтительно)
        2. ChatRoom.participants M2M (fallback для старых чатов)
        """
        # Сначала проверяем ChatParticipant (быстрее и надежнее)
        if ChatParticipant.objects.filter(
            room_id=room_id,
            user=self.scope['user']
        ).exists():
            return True

        # Fallback: проверяем M2M participants для обратной совместимости
        try:
            room = ChatRoom.objects.get(id=room_id)
            if room.participants.filter(id=self.scope['user'].id).exists():
                # Создаем ChatParticipant для будущих проверок
                ChatParticipant.objects.get_or_create(
                    room=room,
                    user=self.scope['user']
                )
                return True
        except ChatRoom.DoesNotExist:
            pass

        return False

    @database_sync_to_async
    def create_message(self, content):
        """Создание нового сообщения"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)

            # Дополнительная проверка участия (defense-in-depth)
            # Проверяем ChatParticipant или M2M participants для обратной совместимости
            is_participant = ChatParticipant.objects.filter(room=room, user=self.scope['user']).exists()

            if not is_participant:
                # Fallback: проверяем M2M participants
                if room.participants.filter(id=self.scope['user'].id).exists():
                    # Создаем ChatParticipant для будущих проверок
                    ChatParticipant.objects.get_or_create(
                        room=room,
                        user=self.scope['user']
                    )
                    is_participant = True

            if not is_participant:
                logger.warning(f'[CreateMessage] Access denied: user {self.scope["user"].id} is not a participant in room {self.room_id}')
                return None

            message = Message.objects.create(
                room=room,
                sender=self.scope['user'],
                content=content
            )
            return MessageSerializer(message).data
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Отметка сообщения как прочитанного"""
        try:
            message = Message.objects.get(id=message_id)
            MessageRead.objects.get_or_create(
                message=message,
                user=self.scope['user']
            )
        except ObjectDoesNotExist:
            pass

    @database_sync_to_async
    def get_room_history(self):
        """Получение истории сообщений комнаты из БД"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            messages = room.messages.filter(is_deleted=False).select_related('sender').order_by('-created_at')[:50]
            return [MessageSerializer(msg).data for msg in reversed(messages)]
        except ObjectDoesNotExist:
            return []

    async def send_room_history(self):
        """Отправка истории сообщений клиенту"""
        messages = await self.get_room_history()
        await self.send(text_data=json.dumps({
            'type': 'room_history',
            'messages': messages
        }))


class GeneralChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для общего чата
    """

    async def connect(self):
        self.room_group_name = 'general_chat'

        # Проверяем, что пользователь аутентифицирован
        if not self.scope['user'].is_authenticated:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Authentication required',
                'code': 'auth_error'
            }))
            await self.close(code=4001)
            return

        # Присоединяемся к группе общего чата
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Отправляем историю сообщений
        await self.send_general_chat_history()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.room_group_name:
            # Очищаем индикатор печати для отключающегося пользователя
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_stop',
                        'user': {
                            'id': self.scope['user'].id,
                            'username': self.scope['user'].username,
                        }
                    }
                )
            except Exception as e:
                logger.error(f'Error clearing typing on disconnect in general chat: {e}', exc_info=True)

            # Покидаем группу общего чата
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in general chat receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    async def handle_chat_message(self, data):
        """Обработка нового сообщения в общем чате"""
        content = data.get('content', '').strip()
        if not content:
            # Отправляем ошибку валидации отправителю
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content required',
                'code': 'validation_error'
            }))
            return

        # Создаем сообщение в общем чате
        message = await self.create_general_message(content)
        if message:
            # Подтверждаем отправителю, что сообщение сохранено
            await self.send(text_data=json.dumps({
                'type': 'message_sent',
                'message_id': message.get('id'),
                'status': 'delivered'
            }))
            # Отправляем сообщение всем участникам группы
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message
                    }
                )
            except Exception as e:
                logger.error(f'Channel layer error in general chat: {e}', exc_info=True)
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Message delivery failed',
                    'code': 'channel_error'
                }))
        else:
            # Сообщаем отправителю об ошибке сохранения
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to save message',
                'code': 'save_error'
            }))

    async def handle_typing(self, data):
        """Обработка индикатора печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing',
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                    'first_name': self.scope['user'].first_name,
                    'last_name': self.scope['user'].last_name,
                }
            }
        )

    async def handle_typing_stop(self, data):
        """Обработка остановки печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_stop',
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                }
            }
        )

    async def chat_message(self, event):
        """Отправка сообщения клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def typing(self, event):
        """Отправка индикатора печати клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user']
        }))

    async def typing_stop(self, event):
        """Отправка остановки печати клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'typing_stop',
            'user': event['user']
        }))

    @database_sync_to_async
    def create_general_message(self, content):
        """Создание нового сообщения в общем чате"""
        try:
            # Получаем или создаем общую комнату
            room, created = ChatRoom.objects.get_or_create(
                type=ChatRoom.Type.GENERAL,
                defaults={
                    'name': 'Общий форум',
                    'description': 'Общий чат для всех пользователей',
                    'created_by': self.scope['user']
                }
            )

            message = Message.objects.create(
                room=room,
                sender=self.scope['user'],
                content=content
            )
            return MessageSerializer(message).data
        except Exception as e:
            logger.error(f"Error creating general message: {e}")
            return None

    async def send_general_chat_history(self):
        """Отправка истории сообщений общего чата"""
        messages = await self.get_general_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'room_history',
            'messages': messages
        }))

    @database_sync_to_async
    def get_general_chat_history(self):
        """Получение истории сообщений общего чата"""
        try:
            room = ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).first()
            if not room:
                return []

            messages = room.messages.filter(is_deleted=False).select_related('sender').order_by('-created_at')[:50]
            return [MessageSerializer(msg).data for msg in reversed(messages)]
        except Exception as e:
            logger.error(f"Error getting general chat history: {e}")
            return []


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для уведомлений пользователя
    """

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.notification_group_name = f'notifications_{self.user_id}'

        # Проверяем, что пользователь аутентифицирован
        if not self.scope['user'].is_authenticated:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Authentication required',
                'code': 'auth_error'
            }))
            await self.close(code=4001)
            return

        # Проверяем, что пользователь запрашивает свои уведомления
        if str(self.scope['user'].id) != self.user_id:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Access denied to notifications',
                'code': 'access_error'
            }))
            await self.close(code=4002)
            return

        # Присоединяемся к группе уведомлений пользователя
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Уведомления обычно только отправляются, не принимаются
        pass

    async def notification(self, event):
        """Отправка уведомления клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для обновлений дашборда пользователя
    """

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.dashboard_group_name = f'dashboard_{self.user_id}'

        # Проверяем, что пользователь аутентифицирован
        if not self.scope['user'].is_authenticated:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Authentication required',
                'code': 'auth_error'
            }))
            await self.close(code=4001)
            return

        # Проверяем, что пользователь запрашивает свои обновления
        if str(self.scope['user'].id) != self.user_id:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Access denied to dashboard',
                'code': 'access_error'
            }))
            await self.close(code=4002)
            return

        # Присоединяемся к группе обновлений дашборда пользователя
        await self.channel_layer.group_add(
            self.dashboard_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.dashboard_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Обновления дашборда обычно только отправляются, не принимаются
        pass

    async def dashboard_update(self, event):
        """Отправка обновления дашборда клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))
