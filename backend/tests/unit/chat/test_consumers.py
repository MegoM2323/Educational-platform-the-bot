"""
Unit-тесты для WebSocket consumers приложения chat

Тестирует:
- ChatConsumer
- GeneralChatConsumer
- NotificationConsumer
- DashboardConsumer
"""
import pytest
import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from chat.models import ChatRoom, Message, MessageRead, ChatParticipant
from chat.consumers import (
    ChatConsumer,
    GeneralChatConsumer,
    NotificationConsumer,
    DashboardConsumer
)


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumer:
    """Тесты для ChatConsumer"""

    @database_sync_to_async
    def create_chat_room(self, teacher_user, student_user):
        """Создание чат-комнаты"""
        room = ChatRoom.objects.create(
            name="Тестовый чат",
            type=ChatRoom.Type.DIRECT,
            created_by=teacher_user
        )
        room.participants.add(student_user, teacher_user)
        return room

    async def test_connect_authenticated(self, student_user, teacher_user):
        """Успешное подключение аутентифицированного пользователя"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_connect_unauthenticated(self, student_user, teacher_user):
        """Отклонение неаутентифицированного пользователя"""
        from django.contrib.auth.models import AnonymousUser

        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = AnonymousUser()
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is False

    async def test_connect_without_room_access(self, student_user, teacher_user, parent_user):
        """Отклонение пользователя без доступа к комнате"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        # parent_user не добавлен в participants
        communicator.scope['user'] = parent_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is False

    async def test_disconnect(self, student_user, teacher_user):
        """Корректное отключение"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()
        await communicator.disconnect()

        # Проверяем, что отключение прошло без ошибок
        assert True

    async def test_receive_chat_message(self, student_user, teacher_user):
        """Получение и обработка chat_message"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # 1. Пропускаем историю сообщений
        history_response = await communicator.receive_from()
        history_data = json.loads(history_response)
        assert history_data['type'] == 'room_history'

        # 2. Пропускаем user_joined от самого себя
        user_joined_response = await communicator.receive_from()
        user_joined_data = json.loads(user_joined_response)
        assert user_joined_data['type'] == 'user_joined'

        # 3. Отправляем сообщение
        await communicator.send_to(text_data=json.dumps({
            'type': 'chat_message',
            'content': 'Привет!'
        }))

        # 4. Получаем ответ - chat_message
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'chat_message'
        assert 'message' in data
        assert data['message']['content'] == 'Привет!'

        await communicator.disconnect()

    async def test_receive_empty_message(self, student_user, teacher_user):
        """Пустое сообщение не должно обрабатываться"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # Пропускаем историю
        await communicator.receive_from()
        # Пропускаем user_joined
        await communicator.receive_from()

        # Отправляем пустое сообщение
        await communicator.send_to(text_data=json.dumps({
            'type': 'chat_message',
            'content': '   '
        }))

        # Consumer просто игнорирует пустое сообщение (return в handle_chat_message)
        # Не должно быть нового сообщения, должен быть таймаут
        import asyncio
        try:
            await asyncio.wait_for(
                communicator.receive_from(),
                timeout=0.5
            )
            # Если получили что-то - это ошибка
            assert False, "Не должно быть ответа на пустое сообщение"
        except asyncio.TimeoutError:
            # Таймаут - это ожидаемое поведение
            pass

        await communicator.disconnect()

    async def test_receive_typing_indicator(self, student_user, teacher_user):
        """Обработка индикатора печати"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # Пропускаем историю
        await communicator.receive_from()
        # Пропускаем user_joined
        await communicator.receive_from()

        # Отправляем typing
        await communicator.send_to(text_data=json.dumps({
            'type': 'typing'
        }))

        # Должен вернуться typing indicator (broadcast через group_send)
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'typing'
        assert 'user' in data
        assert data['user']['id'] == student_user.id

        await communicator.disconnect()

    async def test_receive_typing_stop(self, student_user, teacher_user):
        """Обработка остановки печати"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # Пропускаем историю
        await communicator.receive_from()
        # Пропускаем user_joined
        await communicator.receive_from()

        # Отправляем typing_stop
        await communicator.send_to(text_data=json.dumps({
            'type': 'typing_stop'
        }))

        # Должен вернуться typing_stop (broadcast через group_send)
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'typing_stop'
        assert 'user' in data
        assert data['user']['id'] == student_user.id

        await communicator.disconnect()

    async def test_message_saved_to_database(self, student_user, teacher_user):
        """Проверка сохранения сообщения в БД"""
        room = await self.create_chat_room(teacher_user, student_user)

        @database_sync_to_async
        def get_message_count():
            return Message.objects.filter(room=room).count()

        initial_count = await get_message_count()

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # Пропускаем историю
        await communicator.receive_from()
        # Пропускаем user_joined
        await communicator.receive_from()

        # Отправляем сообщение
        await communicator.send_to(text_data=json.dumps({
            'type': 'chat_message',
            'content': 'Тестовое сообщение'
        }))

        # Получаем ответ
        response = await communicator.receive_from()
        data = json.loads(response)
        assert data['type'] == 'chat_message'

        # Проверяем, что сообщение сохранено в БД
        final_count = await get_message_count()
        assert final_count == initial_count + 1

        await communicator.disconnect()

    async def test_broadcast_to_group(self, student_user, teacher_user):
        """Проверка broadcast сообщения в группу"""
        room = await self.create_chat_room(teacher_user, student_user)

        # Создаем два соединения (два участника)
        communicator1 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator1.scope['user'] = student_user
        communicator1.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        communicator2 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator2.scope['user'] = teacher_user
        communicator2.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator1.connect()

        # communicator1: пропускаем историю и user_joined от себя
        await communicator1.receive_from()  # room_history
        await communicator1.receive_from()  # user_joined (student)

        await communicator2.connect()

        # communicator2: пропускаем историю и user_joined от себя
        await communicator2.receive_from()  # room_history
        await communicator2.receive_from()  # user_joined (teacher)

        # communicator1 получит user_joined от communicator2
        user_joined = await communicator1.receive_from()
        assert json.loads(user_joined)['type'] == 'user_joined'

        # Отправляем сообщение от студента
        await communicator1.send_to(text_data=json.dumps({
            'type': 'chat_message',
            'content': 'Сообщение от студента'
        }))

        # Оба должны получить сообщение (broadcast)
        response1 = await communicator1.receive_from()
        response2 = await communicator2.receive_from()

        data1 = json.loads(response1)
        data2 = json.loads(response2)

        assert data1['type'] == 'chat_message'
        assert data2['type'] == 'chat_message'
        assert data1['message']['content'] == 'Сообщение от студента'
        assert data2['message']['content'] == 'Сообщение от студента'

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_user_joined_notification(self, student_user, teacher_user):
        """Проверка уведомления о присоединении пользователя"""
        room = await self.create_chat_room(teacher_user, student_user)

        # Первый пользователь подключается
        communicator1 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator1.scope['user'] = teacher_user
        communicator1.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator1.connect()
        await communicator1.receive_from()  # history

        # Второй пользователь подключается
        communicator2 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator2.scope['user'] = student_user
        communicator2.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator2.connect()

        # Первый пользователь должен получить уведомление о присоединении
        response = await communicator1.receive_from()
        data = json.loads(response)

        assert data['type'] == 'user_joined'
        assert 'user' in data

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_receive_room_history(self, student_user, teacher_user):
        """Проверка отправки истории сообщений при подключении"""
        room = await self.create_chat_room(teacher_user, student_user)

        @database_sync_to_async
        def create_messages():
            Message.objects.create(room=room, sender=teacher_user, content="Сообщение 1")
            Message.objects.create(room=room, sender=student_user, content="Сообщение 2")

        await create_messages()

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # Должна прийти история
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'room_history'
        assert 'messages' in data
        assert len(data['messages']) == 2

        await communicator.disconnect()

    async def test_invalid_json(self, student_user, teacher_user):
        """Обработка невалидного JSON"""
        room = await self.create_chat_room(teacher_user, student_user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{room.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'room_id': str(room.id)}}

        await communicator.connect()

        # Пропускаем историю
        await communicator.receive_from()

        # Отправляем невалидный JSON
        await communicator.send_to(text_data="invalid json{{{")

        # Должна прийти ошибка
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'error'
        assert 'Invalid JSON' in data['message']

        await communicator.disconnect()


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestGeneralChatConsumer:
    """Тесты для GeneralChatConsumer"""

    async def test_connect_authenticated(self, student_user):
        """Успешное подключение к общему чату"""
        communicator = WebsocketCommunicator(
            GeneralChatConsumer.as_asgi(),
            '/ws/general/'
        )
        communicator.scope['user'] = student_user

        connected, subprotocol = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_connect_unauthenticated(self):
        """Отклонение неаутентифицированного пользователя"""
        from django.contrib.auth.models import AnonymousUser

        communicator = WebsocketCommunicator(
            GeneralChatConsumer.as_asgi(),
            '/ws/general/'
        )
        communicator.scope['user'] = AnonymousUser()

        connected, subprotocol = await communicator.connect()
        assert connected is False

    async def test_receive_chat_message_in_general(self, student_user, teacher_user):
        """Получение сообщения в общем чате"""
        @database_sync_to_async
        def create_general_room():
            room, created = ChatRoom.objects.get_or_create(
                type=ChatRoom.Type.GENERAL,
                defaults={
                    'name': 'Общий форум',
                    'description': 'Общий чат для всех',
                    'created_by': teacher_user
                }
            )
            return room

        await create_general_room()

        communicator = WebsocketCommunicator(
            GeneralChatConsumer.as_asgi(),
            '/ws/general/'
        )
        communicator.scope['user'] = student_user

        await communicator.connect()

        # Пропускаем историю
        history_response = await communicator.receive_from()
        history_data = json.loads(history_response)
        assert history_data['type'] == 'room_history'

        # Отправляем сообщение
        await communicator.send_to(text_data=json.dumps({
            'type': 'chat_message',
            'content': 'Сообщение в общем чате'
        }))

        # Получаем ответ
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'chat_message'
        assert data['message']['content'] == 'Сообщение в общем чате'

        await communicator.disconnect()

    async def test_typing_in_general_chat(self, student_user):
        """Индикатор печати в общем чате"""
        communicator = WebsocketCommunicator(
            GeneralChatConsumer.as_asgi(),
            '/ws/general/'
        )
        communicator.scope['user'] = student_user

        await communicator.connect()

        # Пропускаем историю
        history_response = await communicator.receive_from()
        history_data = json.loads(history_response)
        assert history_data['type'] == 'room_history'

        # Отправляем typing
        await communicator.send_to(text_data=json.dumps({
            'type': 'typing'
        }))

        # Должен вернуться typing (broadcast)
        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'typing'
        assert 'user' in data
        assert data['user']['id'] == student_user.id

        await communicator.disconnect()

    async def test_general_chat_message_saved_to_db(self, student_user, teacher_user):
        """Проверка сохранения сообщения общего чата в БД"""
        @database_sync_to_async
        def create_general_room():
            room, created = ChatRoom.objects.get_or_create(
                type=ChatRoom.Type.GENERAL,
                defaults={
                    'name': 'Общий форум',
                    'created_by': teacher_user
                }
            )
            return room

        @database_sync_to_async
        def get_message_count():
            room = ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).first()
            if not room:
                return 0
            return Message.objects.filter(room=room).count()

        await create_general_room()
        initial_count = await get_message_count()

        communicator = WebsocketCommunicator(
            GeneralChatConsumer.as_asgi(),
            '/ws/general/'
        )
        communicator.scope['user'] = student_user

        await communicator.connect()

        # Пропускаем историю
        history_response = await communicator.receive_from()
        history_data = json.loads(history_response)
        assert history_data['type'] == 'room_history'

        # Отправляем сообщение
        await communicator.send_to(text_data=json.dumps({
            'type': 'chat_message',
            'content': 'Тест'
        }))

        # Получаем ответ
        response = await communicator.receive_from()
        data = json.loads(response)
        assert data['type'] == 'chat_message'

        final_count = await get_message_count()
        assert final_count == initial_count + 1

        await communicator.disconnect()


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestNotificationConsumer:
    """Тесты для NotificationConsumer"""

    async def test_connect_authenticated_own_notifications(self, student_user):
        """Успешное подключение к своим уведомлениям"""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            f'/ws/notifications/{student_user.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'user_id': str(student_user.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_connect_unauthorized_other_user_notifications(self, student_user, teacher_user):
        """Отклонение при попытке подключиться к чужим уведомлениям"""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            f'/ws/notifications/{teacher_user.id}/'
        )
        communicator.scope['user'] = student_user  # Пытается подключиться к уведомлениям teacher_user
        communicator.scope['url_route'] = {'kwargs': {'user_id': str(teacher_user.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is False

    async def test_connect_unauthenticated(self, student_user):
        """Отклонение неаутентифицированного пользователя"""
        from django.contrib.auth.models import AnonymousUser

        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            f'/ws/notifications/{student_user.id}/'
        )
        communicator.scope['user'] = AnonymousUser()
        communicator.scope['url_route'] = {'kwargs': {'user_id': str(student_user.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is False


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestDashboardConsumer:
    """Тесты для DashboardConsumer"""

    async def test_connect_authenticated_own_dashboard(self, student_user):
        """Успешное подключение к своему дашборду"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            f'/ws/dashboard/{student_user.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'user_id': str(student_user.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_connect_unauthorized_other_user_dashboard(self, student_user, teacher_user):
        """Отклонение при попытке подключиться к чужому дашборду"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            f'/ws/dashboard/{teacher_user.id}/'
        )
        communicator.scope['user'] = student_user
        communicator.scope['url_route'] = {'kwargs': {'user_id': str(teacher_user.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is False

    async def test_connect_unauthenticated(self, student_user):
        """Отклонение неаутентифицированного пользователя"""
        from django.contrib.auth.models import AnonymousUser

        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            f'/ws/dashboard/{student_user.id}/'
        )
        communicator.scope['user'] = AnonymousUser()
        communicator.scope['url_route'] = {'kwargs': {'user_id': str(student_user.id)}}

        connected, subprotocol = await communicator.connect()
        assert connected is False
