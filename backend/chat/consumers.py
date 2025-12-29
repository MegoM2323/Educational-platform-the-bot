import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import transaction
from .models import ChatRoom, Message, MessageRead, ChatParticipant
from .serializers import MessageSerializer
from .permissions import check_parent_access_to_room
from accounts.models import User as UserModel

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

        # Добавляем родителя в participants после успешного подключения (если нужно)
        await self.add_parent_to_participants_if_needed()

        # Очищаем счётчик непрочитанных сообщений для этого пользователя
        await self.clear_unread_count()

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
        # Безопасное получение user из scope
        user = self.scope.get('user')

        # Проверяем, что user существует и аутентифицирован
        if not user or not getattr(user, 'is_authenticated', False):
            # Если пользователь не аутентифицирован, просто покидаем группу
            if hasattr(self, 'room_group_name') and self.room_group_name:
                try:
                    await self.channel_layer.group_discard(
                        self.room_group_name,
                        self.channel_name
                    )
                except Exception as e:
                    logger.error(f'Error leaving group on disconnect (unauthenticated): {e}', exc_info=True)
            return

        # Безопасное получение room_id
        room_id = getattr(self, 'room_id', None)

        if hasattr(self, 'room_group_name') and self.room_group_name:
            # Очищаем индикатор печати для отключающегося пользователя
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_stop',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                        }
                    }
                )
            except Exception as e:
                room_info = f'room {room_id}' if room_id else 'unknown room'
                logger.error(f'Error clearing typing on disconnect in {room_info}: {e}', exc_info=True)

            # Уведомляем других участников об отключении
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_left',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                        }
                    }
                )
            except Exception as e:
                room_info = f'room {room_id}' if room_id else 'unknown room'
                logger.error(f'Channel layer error broadcasting user_left in {room_info}: {e}', exc_info=True)

            # Покидаем группу комнаты
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                logger.warning(f'[GroupDiscard] Group={self.room_group_name}, Channel={self.channel_name}')
            except Exception as e:
                logger.error(f'Error leaving group {self.room_group_name}: {e}', exc_info=True)

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
            elif message_type == 'message_edit':
                await self.handle_message_edit(data)
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
            try:
                await self.mark_message_read(message_id)
            except Exception as e:
                # Не распространяем ошибку клиенту - silent fail для отметок о прочтении
                logger.error(f'Error marking message as read: {e}', exc_info=True)

    async def handle_message_edit(self, data):
        """Обработка редактирования сообщения"""
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()

        if not message_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message ID required',
                'code': 'validation_error'
            }))
            return

        if not new_content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content required',
                'code': 'validation_error'
            }))
            return

        # Редактируем сообщение в БД
        result = await self.edit_message(message_id, new_content)

        if result.get('error'):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': result['error'],
                'code': result.get('code', 'edit_error')
            }))
            return

        # Подтверждаем редактору успешное редактирование
        await self.send(text_data=json.dumps({
            'type': 'message_edit_confirmed',
            'message_id': message_id,
            'status': 'edited'
        }))

        # Рассылаем обновление всем участникам комнаты
        logger.info(f'[HandleMessageEdit] Broadcasting edit to group {self.room_group_name}, message_id={message_id}')
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message_id': message_id,
                    'content': new_content,
                    'is_edited': True,
                    'edited_at': result['edited_at'],
                }
            )
        except Exception as e:
            logger.error(f'Channel layer error broadcasting message_edited in room {self.room_id}: {e}', exc_info=True)

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

    async def message_edited(self, event):
        """Отправка уведомления о редактировании сообщения клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content'],
            'is_edited': event['is_edited'],
            'edited_at': event['edited_at'],
        }))

    @database_sync_to_async
    def check_room_access(self):
        """
        Проверка доступа к комнате.

        Проверяет доступ через:
        1. Admin/Staff bypass для форумных чатов (read-only)
        2. M2M participants (ChatRoom.participants)
        3. ChatParticipant записи (для обратной совместимости)
        4. Родительский доступ: если пользователь - родитель и его ребёнок является участником

        Дополнительная проверка для teacher:
        - Teacher может подключаться к FORUM_SUBJECT чатам (через enrollment или как participant)
        - Teacher может подключаться к FORUM_TUTOR чатам если явно добавлен как participant
        """
        try:
            room = ChatRoom.objects.select_related('enrollment').get(id=self.room_id)
            user = self.scope['user']
            user_id = user.id

            # Admin/Staff bypass - read-only access to all forum chats
            if user.is_staff or user.is_superuser:
                if room.type in [ChatRoom.Type.FORUM_SUBJECT, ChatRoom.Type.FORUM_TUTOR]:
                    logger.info(f'[check_room_access] Admin {user_id} granted read-only access to room {self.room_id}')
                    return True

            # Дополнительная проверка для teacher
            if user.role == UserModel.Role.TEACHER:
                # Teacher has access to FORUM_SUBJECT chats
                if room.type == ChatRoom.Type.FORUM_SUBJECT:
                    # Check enrollment assignment
                    if room.enrollment and room.enrollment.teacher_id == user_id:
                        if room.participants.filter(id=user_id).exists():
                            logger.debug(f'[check_room_access] Teacher {user_id} has access via enrollment')
                            return True
                    # Or if teacher is a participant (e.g., added by admin or created chat)
                    if room.participants.filter(id=user_id).exists():
                        logger.info(f'[check_room_access] Teacher {user_id} accessing FORUM_SUBJECT room {self.room_id} as participant')
                        return True

                # Teacher can also access FORUM_TUTOR if explicitly added as participant
                elif room.type == ChatRoom.Type.FORUM_TUTOR:
                    if room.participants.filter(id=user_id).exists():
                        logger.info(f'[check_room_access] Teacher {user_id} accessing FORUM_TUTOR room {self.room_id} as participant')
                        return True

                logger.warning(f'[check_room_access] Access denied for teacher {user_id} to room {self.room_id}')
                return False

            # Дополнительная проверка для tutor
            if user.role == UserModel.Role.TUTOR:
                # Tutor has access to FORUM_TUTOR chats
                if room.type == ChatRoom.Type.FORUM_TUTOR:
                    # Check if tutor is participant
                    if room.participants.filter(id=user_id).exists():
                        logger.debug(f'[check_room_access] Tutor {user_id} has access to FORUM_TUTOR room {self.room_id}')
                        return True
                    # Or check via student's tutor relationship
                    from accounts.models import StudentProfile
                    student_ids = room.participants.filter(role=UserModel.Role.STUDENT).values_list('id', flat=True)
                    if StudentProfile.objects.filter(user_id__in=student_ids, tutor=user).exists():
                        logger.debug(f'[check_room_access] Tutor {user_id} has access via student relationship')
                        return True

                # Tutor can also access FORUM_SUBJECT if explicitly added as participant
                elif room.type == ChatRoom.Type.FORUM_SUBJECT:
                    if room.participants.filter(id=user_id).exists():
                        logger.info(f'[check_room_access] Tutor {user_id} accessing FORUM_SUBJECT room {self.room_id} as participant')
                        return True

                logger.warning(f'[check_room_access] Access denied for tutor {user_id} to room {self.room_id}')
                return False

            # Проверка 1: M2M participants
            if room.participants.filter(id=user_id).exists():
                logger.debug(f'[check_room_access] User {user_id} has access via M2M participants')
                return True

            # Проверка 2: ChatParticipant (fallback для старых чатов)
            if ChatParticipant.objects.filter(room=room, user=user).exists():
                # Синхронизируем: добавляем в M2M атомарно
                with transaction.atomic():
                    # M2M add безопасен для дубликатов, не вызывает IntegrityError
                    room.participants.add(user)
                logger.info(f'[check_room_access] User {user_id} synced from ChatParticipant to M2M')
                return True

            # Проверка 3: Родительский доступ к чатам детей
            # Родители могут просматривать FORUM_SUBJECT и FORUM_TUTOR чаты своих детей
            # Используем централизованную функцию из permissions.py БЕЗ побочных эффектов
            # (добавление в participants будет после успешного accept)
            if user.role == UserModel.Role.PARENT:
                if check_parent_access_to_room(user, room, add_to_participants=False):
                    logger.info(f'[check_room_access] Parent {user_id} has child participant in room {self.room_id}')
                    # Сохраняем флаг для добавления родителя в participants после успешного connect
                    self.parent_needs_participant_add = True
                    self.parent_user_id = user_id
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
    def add_parent_to_participants_if_needed(self):
        """
        Добавляет родителя в participants комнаты после успешного WebSocket подключения.
        Вызывается только если self.parent_needs_participant_add = True (установлен в check_room_access).
        """
        if not getattr(self, 'parent_needs_participant_add', False):
            return

        try:
            room = ChatRoom.objects.get(id=self.room_id)
            user = User.objects.get(id=self.parent_user_id)
            with transaction.atomic():
                room.participants.add(user)
                ChatParticipant.objects.get_or_create(room=room, user=user)
            logger.info(f'[add_parent_to_participants] Added parent {self.parent_user_id} to room {self.room_id}')
            self.parent_needs_participant_add = False
        except Exception as e:
            logger.error(f'[add_parent_to_participants] Error adding parent to participants: {e}')

    @database_sync_to_async
    def check_user_is_participant(self, room_id):
        """
        Проверка, что текущий пользователь является участником комнаты.

        Проверяет в двух местах для обратной совместимости:
        1. ChatParticipant (предпочтительно)
        2. ChatRoom.participants M2M (fallback для старых чатов)

        Дополнительные проверки для ролей:
        - Teacher может быть участником FORUM_SUBJECT и FORUM_TUTOR чатов (если добавлен как participant)
        - Tutor может быть участником FORUM_TUTOR и FORUM_SUBJECT чатов (если добавлен как participant)
        """
        user = self.scope['user']

        try:
            room = ChatRoom.objects.select_related('enrollment').get(id=room_id)
        except ChatRoom.DoesNotExist:
            return False

        # Проверка типа чата для teacher
        # Teacher can access FORUM_SUBJECT and FORUM_TUTOR (if participant)
        if user.role == UserModel.Role.TEACHER:
            if room.type not in [ChatRoom.Type.FORUM_SUBJECT, ChatRoom.Type.FORUM_TUTOR]:
                return False

        # Проверка типа чата для tutor
        if user.role == UserModel.Role.TUTOR:
            # Tutor can access FORUM_TUTOR and FORUM_SUBJECT (if participant)
            if room.type not in [ChatRoom.Type.FORUM_TUTOR, ChatRoom.Type.FORUM_SUBJECT]:
                return False

        # Сначала проверяем ChatParticipant (быстрее и надежнее)
        if ChatParticipant.objects.filter(
            room_id=room_id,
            user=user
        ).exists():
            return True

        # Fallback: проверяем M2M participants для обратной совместимости
        if room.participants.filter(id=user.id).exists():
            # Создаем ChatParticipant атомарно для будущих проверок
            try:
                with transaction.atomic():
                    ChatParticipant.objects.get_or_create(
                        room=room,
                        user=user
                    )
            except Exception as e:
                # Игнорируем ошибки создания (возможен race condition), участник уже есть в M2M
                logger.debug(f'[check_user_is_participant] ChatParticipant sync skipped: {e}')
            return True

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
                    # Создаем ChatParticipant атомарно для будущих проверок
                    try:
                        with transaction.atomic():
                            ChatParticipant.objects.get_or_create(
                                room=room,
                                user=self.scope['user']
                            )
                    except Exception as e:
                        # Игнорируем ошибки создания (возможен race condition), участник уже есть в M2M
                        logger.debug(f'[create_message] ChatParticipant sync skipped: {e}')
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
    def edit_message(self, message_id, new_content):
        """
        Редактирование сообщения в БД.

        Проверяет:
        - Существование сообщения
        - Что пользователь является автором сообщения
        - Что сообщение принадлежит текущей комнате
        - Что сообщение не удалено

        Возвращает dict с edited_at или error.
        """
        from django.utils import timezone

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return {'error': 'Message not found', 'code': 'not_found'}

        # Проверяем что сообщение принадлежит текущей комнате
        if str(message.room_id) != str(self.room_id):
            logger.warning(
                f'[edit_message] Access denied: message {message_id} belongs to room {message.room_id}, '
                f'not {self.room_id}'
            )
            return {'error': 'Message does not belong to this room', 'code': 'access_denied'}

        # Проверяем что пользователь является автором
        if message.sender_id != self.scope['user'].id:
            logger.warning(
                f'[edit_message] Access denied: user {self.scope["user"].id} is not the sender of message {message_id}'
            )
            return {'error': 'You can only edit your own messages', 'code': 'access_denied'}

        # Проверяем что сообщение не удалено
        if message.is_deleted:
            return {'error': 'Cannot edit deleted message', 'code': 'validation_error'}

        # Обновляем сообщение
        message.content = new_content
        message.is_edited = True
        message.save(update_fields=['content', 'is_edited', 'updated_at'])

        logger.info(f'[edit_message] Message {message_id} edited by user {self.scope["user"].id}')
        return {'edited_at': message.updated_at.isoformat()}

    @database_sync_to_async
    def clear_unread_count(self):
        """
        Очистка счётчика непрочитанных сообщений при открытии чата.
        Обновляет last_read_at в ChatParticipant на текущее время.
        """
        from django.utils import timezone

        try:
            room = ChatRoom.objects.get(id=self.room_id)
            user = self.scope['user']

            # Обновляем или создаём запись ChatParticipant с текущим временем прочтения
            participant, created = ChatParticipant.objects.get_or_create(
                room=room,
                user=user
            )
            participant.last_read_at = timezone.now()
            participant.save(update_fields=['last_read_at'])

            logger.debug(f'[clear_unread_count] Cleared unread count for user {user.id} in room {self.room_id}')
        except ObjectDoesNotExist:
            logger.warning(f'[clear_unread_count] Room {self.room_id} not found')
        except Exception as e:
            logger.error(f'[clear_unread_count] Error clearing unread count: {e}')

    @database_sync_to_async
    def get_room_history(self):
        """Получение истории сообщений комнаты из БД"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            # Получаем ID последних 50 сообщений
            latest_ids = room.messages.filter(
                is_deleted=False
            ).order_by('-created_at').values('id')[:50]
            # Получаем эти сообщения в хронологическом порядке (старые первые)
            messages = room.messages.filter(
                id__in=latest_ids
            ).select_related('sender').order_by('created_at')
            return [MessageSerializer(msg).data for msg in messages]
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

        # Очищаем счётчик непрочитанных сообщений для общего чата
        await self.clear_general_unread_count()

        # Отправляем историю сообщений
        await self.send_general_chat_history()

    async def disconnect(self, close_code):
        # Безопасное получение user из scope
        user = self.scope.get('user')

        # Проверяем, что user существует и аутентифицирован
        if not user or not getattr(user, 'is_authenticated', False):
            # Если пользователь не аутентифицирован, просто покидаем группу
            if hasattr(self, 'room_group_name') and self.room_group_name:
                try:
                    await self.channel_layer.group_discard(
                        self.room_group_name,
                        self.channel_name
                    )
                except Exception as e:
                    logger.error(f'Error leaving general chat group on disconnect (unauthenticated): {e}', exc_info=True)
            return

        if hasattr(self, 'room_group_name') and self.room_group_name:
            # Очищаем индикатор печати для отключающегося пользователя
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_stop',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                        }
                    }
                )
            except Exception as e:
                logger.error(f'Error clearing typing on disconnect in general chat: {e}', exc_info=True)

            # Покидаем группу общего чата
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception as e:
                logger.error(f'Error leaving general chat group: {e}', exc_info=True)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'message_edit':
                await self.handle_message_edit(data)
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

    async def handle_message_edit(self, data):
        """Обработка редактирования сообщения в общем чате"""
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()

        if not message_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message ID required',
                'code': 'validation_error'
            }))
            return

        if not new_content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content required',
                'code': 'validation_error'
            }))
            return

        # Редактируем сообщение в БД
        result = await self.edit_general_message(message_id, new_content)

        if result.get('error'):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': result['error'],
                'code': result.get('code', 'edit_error')
            }))
            return

        # Подтверждаем редактору успешное редактирование
        await self.send(text_data=json.dumps({
            'type': 'message_edit_confirmed',
            'message_id': message_id,
            'status': 'edited'
        }))

        # Рассылаем обновление всем участникам общего чата
        logger.info(f'[HandleMessageEdit] Broadcasting edit to general chat, message_id={message_id}')
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message_id': message_id,
                    'content': new_content,
                    'is_edited': True,
                    'edited_at': result['edited_at'],
                }
            )
        except Exception as e:
            logger.error(f'Channel layer error broadcasting message_edited in general chat: {e}', exc_info=True)

    async def message_edited(self, event):
        """Отправка уведомления о редактировании сообщения клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content'],
            'is_edited': event['is_edited'],
            'edited_at': event['edited_at'],
        }))

    @database_sync_to_async
    def edit_general_message(self, message_id, new_content):
        """
        Редактирование сообщения в общем чате.

        Проверяет:
        - Существование сообщения
        - Что сообщение принадлежит общему чату
        - Что пользователь является автором сообщения
        - Что сообщение не удалено

        Возвращает dict с edited_at или error.
        """
        from django.utils import timezone

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return {'error': 'Message not found', 'code': 'not_found'}

        # Проверяем что сообщение принадлежит общему чату
        if message.room.type != ChatRoom.Type.GENERAL:
            logger.warning(
                f'[edit_general_message] Access denied: message {message_id} does not belong to general chat'
            )
            return {'error': 'Message does not belong to general chat', 'code': 'access_denied'}

        # Проверяем что пользователь является автором
        if message.sender_id != self.scope['user'].id:
            logger.warning(
                f'[edit_general_message] Access denied: user {self.scope["user"].id} is not the sender of message {message_id}'
            )
            return {'error': 'You can only edit your own messages', 'code': 'access_denied'}

        # Проверяем что сообщение не удалено
        if message.is_deleted:
            return {'error': 'Cannot edit deleted message', 'code': 'validation_error'}

        # Обновляем сообщение
        message.content = new_content
        message.is_edited = True
        message.save(update_fields=['content', 'is_edited', 'updated_at'])

        logger.info(f'[edit_general_message] Message {message_id} edited by user {self.scope["user"].id}')
        return {'edited_at': message.updated_at.isoformat()}

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

    @database_sync_to_async
    def clear_general_unread_count(self):
        """
        Очистка счётчика непрочитанных сообщений для общего чата.
        Обновляет last_read_at в ChatParticipant на текущее время.
        """
        from django.utils import timezone

        try:
            room = ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).first()
            if not room:
                return

            user = self.scope['user']

            # Обновляем или создаём запись ChatParticipant с текущим временем прочтения
            participant, created = ChatParticipant.objects.get_or_create(
                room=room,
                user=user
            )
            participant.last_read_at = timezone.now()
            participant.save(update_fields=['last_read_at'])

            logger.debug(f'[clear_general_unread_count] Cleared unread count for user {user.id} in general chat')
        except Exception as e:
            logger.error(f'[clear_general_unread_count] Error clearing unread count: {e}')


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
