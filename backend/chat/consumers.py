import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from .models import ChatRoom, Message, MessageRead, ChatParticipant
from .serializers import MessageSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


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
            await self.close()
            return

        # Проверяем, что пользователь имеет доступ к комнате
        has_access = await self.check_room_access()
        logger.warning(f'[ChatConsumer] Room access check: {has_access}')
        if not has_access:
            logger.warning(f'[ChatConsumer] Connection rejected: no room access')
            await self.close()
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
    
    async def disconnect(self, close_code):
        # Покидаем группу комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.warning(f'[GroupDiscard] Group={self.room_group_name}, Channel={self.channel_name}')
        
        # Уведомляем других участников об отключении
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
    
    async def receive(self, text_data):
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
            return

        # Создаем сообщение
        message = await self.create_message(content)
        logger.warning(f'[HandleChatMessage] Created message: {message}')
        if message:
            # Отправляем сообщение всем участникам группы
            logger.warning(f'[HandleChatMessage] Broadcasting to group {self.room_group_name}, message_id={message.get("id", "unknown")}')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message
                }
            )
            logger.warning(f'[HandleChatMessage] Broadcast completed for message_id={message.get("id", "unknown")}')
    
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
        """Проверка доступа к комнате"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.participants.filter(id=self.scope['user'].id).exists()
        except ObjectDoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, content):
        """Создание нового сообщения"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
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
            messages = room.messages.select_related('sender').order_by('-created_at')[:50]
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
            await self.close()
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
            return
        
        # Создаем сообщение в общем чате
        message = await self.create_general_message(content)
        if message:
            # Отправляем сообщение всем участникам группы
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message
                }
            )
    
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
            
            messages = room.messages.select_related('sender').order_by('-created_at')[:50]
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
        
        # Проверяем, что пользователь аутентифицирован и запрашивает свои уведомления
        if not self.scope['user'].is_authenticated or str(self.scope['user'].id) != self.user_id:
            await self.close()
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
        
        # Проверяем, что пользователь аутентифицирован и запрашивает свои обновления
        if not self.scope['user'].is_authenticated or str(self.scope['user'].id) != self.user_id:
            await self.close()
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
