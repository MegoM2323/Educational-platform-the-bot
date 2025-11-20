"""
Unit-тесты для views приложения chat

Тестирует:
- ChatRoomViewSet
- MessageViewSet
- ChatParticipantViewSet
- GeneralChatViewSet
- MessageThreadViewSet
"""
import pytest
import json
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from chat.models import (
    ChatRoom,
    Message,
    MessageRead,
    MessageThread,
    ChatParticipant
)


@pytest.fixture
def api_client():
    """API client для тестов"""
    return APIClient()


@pytest.fixture
def chat_room(teacher_user):
    """Фикстура для чат-комнаты"""
    return ChatRoom.objects.create(
        name="Тестовая комната",
        type=ChatRoom.Type.GROUP,
        created_by=teacher_user
    )


@pytest.fixture
def general_chat_room(teacher_user):
    """Фикстура для общего форума"""
    return ChatRoom.objects.create(
        name="Общий форум",
        type=ChatRoom.Type.GENERAL,
        created_by=teacher_user
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestChatRoomViewSet:
    """Тесты для ChatRoomViewSet"""

    def test_list_chat_rooms_unauthenticated(self, api_client):
        """Неавторизованный пользователь не может получить список чатов"""
        response = api_client.get('/api/chat/rooms/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_chat_rooms_authenticated(self, api_client, student_user, chat_room):
        """Авторизованный пользователь получает только свои чаты"""
        # Добавляем студента в чат
        chat_room.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/rooms/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == chat_room.id

    def test_list_chat_rooms_filters_by_participant(self, api_client, student_user, teacher_user):
        """Пользователь видит только чаты, где он участник"""
        # Чат со студентом
        room1 = ChatRoom.objects.create(
            name="Чат студента",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )
        room1.participants.add(student_user)

        # Чат без студента
        ChatRoom.objects.create(
            name="Чат учителя",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/rooms/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_retrieve_chat_room(self, api_client, student_user, chat_room):
        """Получение конкретного чата"""
        chat_room.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/rooms/{chat_room.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == chat_room.id
        assert response.data['name'] == "Тестовая комната"

    def test_create_chat_room(self, api_client, teacher_user):
        """Создание новой чат-комнаты"""
        api_client.force_authenticate(user=teacher_user)

        data = {
            'name': 'Новая комната',
            'description': 'Описание',
            'type': ChatRoom.Type.GROUP
        }

        response = api_client.post('/api/chat/rooms/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert ChatRoom.objects.filter(name='Новая комната').exists()

        # Создатель должен быть добавлен в участники
        room = ChatRoom.objects.get(name='Новая комната')
        assert teacher_user in room.participants.all()

    def test_join_chat_room(self, api_client, student_user, chat_room):
        """Присоединение к чату"""
        api_client.force_authenticate(user=student_user)

        response = api_client.post(f'/api/chat/rooms/{chat_room.id}/join/')

        assert response.status_code == status.HTTP_200_OK
        assert student_user in chat_room.participants.all()

    def test_join_chat_room_already_member(self, api_client, student_user, chat_room):
        """Попытка присоединиться к чату, где уже участник"""
        chat_room.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/rooms/{chat_room.id}/join/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'уже участвуете' in response.data['error'].lower()

    def test_leave_chat_room(self, api_client, student_user, chat_room):
        """Покинуть чат"""
        chat_room.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/rooms/{chat_room.id}/leave/')

        assert response.status_code == status.HTTP_200_OK
        assert student_user not in chat_room.participants.all()

    def test_leave_chat_room_not_member(self, api_client, student_user, chat_room):
        """Попытка покинуть чат, где не участник"""
        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/rooms/{chat_room.id}/leave/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не участвуете' in response.data['error'].lower()

    def test_get_chat_room_messages(self, api_client, student_user, teacher_user, chat_room):
        """Получение сообщений чата"""
        chat_room.participants.add(student_user)

        # Создаем сообщения
        Message.objects.create(room=chat_room, sender=teacher_user, content="Сообщение 1")
        Message.objects.create(room=chat_room, sender=student_user, content="Сообщение 2")

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/rooms/{chat_room.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_get_chat_room_messages_with_pagination(self, api_client, student_user, teacher_user, chat_room):
        """Получение сообщений чата с пагинацией"""
        chat_room.participants.add(student_user)

        # Создаем много сообщений
        for i in range(60):
            Message.objects.create(room=chat_room, sender=teacher_user, content=f"Сообщение {i}")

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/rooms/{chat_room.id}/messages/?limit=20&offset=0')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 20

    def test_mark_room_messages_as_read(self, api_client, student_user, teacher_user, chat_room):
        """Отметить сообщения комнаты как прочитанные"""
        chat_room.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/rooms/{chat_room.id}/mark_read/')

        assert response.status_code == status.HTTP_200_OK

        # Проверяем, что создан ChatParticipant с last_read_at
        participant = ChatParticipant.objects.get(room=chat_room, user=student_user)
        assert participant.last_read_at is not None

    def test_get_chat_room_participants(self, api_client, student_user, teacher_user, chat_room):
        """Получение участников чата"""
        chat_room.participants.add(student_user, teacher_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/rooms/{chat_room.id}/participants/')

        assert response.status_code == status.HTTP_200_OK
        # Может быть 0, если нет ChatParticipant записей, или 2 если есть

    def test_get_chat_stats(self, api_client, student_user, teacher_user):
        """Получение статистики чатов"""
        # Создаем несколько чатов
        room1 = ChatRoom.objects.create(name="Чат 1", created_by=teacher_user, type=ChatRoom.Type.DIRECT)
        room2 = ChatRoom.objects.create(name="Чат 2", created_by=teacher_user, type=ChatRoom.Type.GROUP)

        room1.participants.add(student_user)
        room2.participants.add(student_user)

        # Создаем сообщения
        Message.objects.create(room=room1, sender=teacher_user, content="Сообщение")

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/rooms/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_rooms' in response.data
        assert 'total_messages' in response.data
        assert response.data['total_rooms'] == 2

    def test_filter_chat_rooms_by_type(self, api_client, student_user, teacher_user):
        """Фильтрация чатов по типу"""
        direct = ChatRoom.objects.create(name="Direct", created_by=teacher_user, type=ChatRoom.Type.DIRECT)
        group = ChatRoom.objects.create(name="Group", created_by=teacher_user, type=ChatRoom.Type.GROUP)

        direct.participants.add(student_user)
        group.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/rooms/?type=direct')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['type'] == ChatRoom.Type.DIRECT

    def test_search_chat_rooms_by_name(self, api_client, student_user, teacher_user):
        """Поиск чатов по названию"""
        room1 = ChatRoom.objects.create(name="Математика", created_by=teacher_user, type=ChatRoom.Type.GROUP)
        room2 = ChatRoom.objects.create(name="Физика", created_by=teacher_user, type=ChatRoom.Type.GROUP)

        room1.participants.add(student_user)
        room2.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/rooms/?search=Математика')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageViewSet:
    """Тесты для MessageViewSet"""

    def test_list_messages_unauthenticated(self, api_client):
        """Неавторизованный пользователь не может получить список сообщений"""
        response = api_client.get('/api/chat/messages/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_messages_authenticated(self, api_client, student_user, teacher_user, chat_room):
        """Авторизованный пользователь получает только сообщения из своих чатов"""
        chat_room.participants.add(student_user)

        message = Message.objects.create(room=chat_room, sender=teacher_user, content="Сообщение")

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_create_message(self, api_client, student_user, chat_room):
        """Создание сообщения"""
        chat_room.participants.add(student_user)

        api_client.force_authenticate(user=student_user)

        data = {
            'room': chat_room.id,
            'content': 'Новое сообщение'
        }

        response = api_client.post('/api/chat/messages/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Message.objects.filter(content='Новое сообщение').exists()

        message = Message.objects.get(content='Новое сообщение')
        assert message.sender == student_user

    def test_mark_message_as_read(self, api_client, student_user, teacher_user, chat_room):
        """Отметить сообщение как прочитанное"""
        chat_room.participants.add(student_user)

        message = Message.objects.create(room=chat_room, sender=teacher_user, content="Сообщение")

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/messages/{message.id}/mark_read/')

        assert response.status_code == status.HTTP_200_OK
        assert MessageRead.objects.filter(message=message, user=student_user).exists()

    def test_mark_message_as_read_not_participant(self, api_client, student_user, teacher_user, chat_room):
        """Нельзя отметить сообщение, если не участник чата"""
        message = Message.objects.create(room=chat_room, sender=teacher_user, content="Сообщение")

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/messages/{message.id}/mark_read/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reply_to_message(self, api_client, student_user, teacher_user, chat_room):
        """Ответ на сообщение"""
        chat_room.participants.add(student_user)

        original = Message.objects.create(room=chat_room, sender=teacher_user, content="Оригинал")

        api_client.force_authenticate(user=student_user)

        data = {
            'content': 'Ответ',
            'sender': student_user.id
        }

        response = api_client.post(f'/api/chat/messages/{original.id}/reply/', data)

        assert response.status_code == status.HTTP_201_CREATED

        # Проверяем, что создан ответ
        reply = Message.objects.get(content='Ответ')
        assert reply.reply_to == original

    def test_reply_to_message_not_participant(self, api_client, student_user, teacher_user, chat_room):
        """Нельзя ответить на сообщение, если не участник чата"""
        message = Message.objects.create(room=chat_room, sender=teacher_user, content="Сообщение")

        api_client.force_authenticate(user=student_user)

        data = {
            'content': 'Попытка ответить'
        }

        response = api_client.post(f'/api/chat/messages/{message.id}/reply/', data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_message_replies(self, api_client, student_user, teacher_user, chat_room):
        """Получение ответов на сообщение"""
        chat_room.participants.add(student_user)

        original = Message.objects.create(room=chat_room, sender=teacher_user, content="Оригинал")
        Message.objects.create(room=chat_room, sender=student_user, content="Ответ 1", reply_to=original)
        Message.objects.create(room=chat_room, sender=teacher_user, content="Ответ 2", reply_to=original)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/messages/{original.id}/replies/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_filter_messages_by_room(self, api_client, student_user, teacher_user):
        """Фильтрация сообщений по комнате"""
        room1 = ChatRoom.objects.create(name="Комната 1", created_by=teacher_user, type=ChatRoom.Type.DIRECT)
        room2 = ChatRoom.objects.create(name="Комната 2", created_by=teacher_user, type=ChatRoom.Type.DIRECT)

        room1.participants.add(student_user)
        room2.participants.add(student_user)

        Message.objects.create(room=room1, sender=teacher_user, content="Сообщение в комнате 1")
        Message.objects.create(room=room2, sender=teacher_user, content="Сообщение в комнате 2")

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/messages/?room={room1.id}')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestGeneralChatViewSet:
    """Тесты для GeneralChatViewSet"""

    def test_get_general_chat_unauthenticated(self, api_client):
        """Неавторизованный пользователь не может получить общий чат"""
        response = api_client.get('/api/chat/general/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_or_create_general_chat(self, api_client, student_user):
        """Получение или создание общего чата"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/')

        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data
        assert ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).exists()

    def test_get_general_chat_messages(self, api_client, student_user, teacher_user, general_chat_room):
        """Получение сообщений общего чата"""
        Message.objects.create(room=general_chat_room, sender=teacher_user, content="Общее сообщение")

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/messages/')

        assert response.status_code == status.HTTP_200_OK

    def test_send_message_to_general_chat(self, api_client, student_user):
        """Отправка сообщения в общий чат"""
        api_client.force_authenticate(user=student_user)

        data = {
            'content': 'Сообщение в общий чат'
        }

        response = api_client.post('/api/chat/general/send_message/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Message.objects.filter(content='Сообщение в общий чат').exists()

    def test_send_empty_message_to_general_chat(self, api_client, student_user):
        """Попытка отправить пустое сообщение"""
        api_client.force_authenticate(user=student_user)

        data = {}

        response = api_client.post('/api/chat/general/send_message/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_general_chat_threads(self, api_client, student_user, teacher_user, general_chat_room):
        """Получение тредов общего чата"""
        MessageThread.objects.create(
            room=general_chat_room,
            title="Тестовый тред",
            created_by=teacher_user
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_general_chat_thread(self, api_client, student_user):
        """Создание треда в общем чате"""
        api_client.force_authenticate(user=student_user)

        data = {
            'title': 'Новый тред'
        }

        response = api_client.post('/api/chat/general/create_thread/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert MessageThread.objects.filter(title='Новый тред').exists()

    def test_create_thread_without_title(self, api_client, student_user):
        """Попытка создать тред без заголовка"""
        api_client.force_authenticate(user=student_user)

        data = {}

        response = api_client.post('/api/chat/general/create_thread/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageThreadViewSet:
    """Тесты для MessageThreadViewSet"""

    def test_list_threads_unauthenticated(self, api_client):
        """Неавторизованный пользователь не может получить список тредов"""
        response = api_client.get('/api/chat/threads/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_threads_authenticated(self, api_client, student_user, teacher_user, general_chat_room):
        """Авторизованный пользователь получает треды из своих чатов"""
        general_chat_room.participants.add(student_user)

        MessageThread.objects.create(
            room=general_chat_room,
            title="Тред 1",
            created_by=teacher_user
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/threads/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_thread(self, api_client, teacher_user, general_chat_room):
        """Создание треда"""
        api_client.force_authenticate(user=teacher_user)

        data = {
            'title': 'Новая тема'
        }

        response = api_client.post('/api/chat/threads/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert MessageThread.objects.filter(title='Новая тема').exists()

    def test_get_thread_messages(self, api_client, student_user, teacher_user, general_chat_room):
        """Получение сообщений треда"""
        general_chat_room.participants.add(student_user)

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Тред",
            created_by=teacher_user
        )

        Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="Сообщение в треде",
            thread=thread
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')

        assert response.status_code == status.HTTP_200_OK

    def test_send_message_to_thread(self, api_client, student_user, teacher_user, general_chat_room):
        """Отправка сообщения в тред"""
        general_chat_room.participants.add(student_user)

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Тред",
            created_by=teacher_user
        )

        api_client.force_authenticate(user=student_user)

        data = {
            'content': 'Сообщение в треде'
        }

        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', data)

        assert response.status_code == status.HTTP_201_CREATED

        # Проверяем, что сообщение привязано к треду
        message = Message.objects.get(content='Сообщение в треде')
        assert message.thread == thread

    def test_pin_thread(self, api_client, teacher_user, general_chat_room):
        """Закрепление треда"""
        general_chat_room.participants.add(teacher_user)

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Тред",
            created_by=teacher_user
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')

        assert response.status_code == status.HTTP_200_OK

        thread.refresh_from_db()
        assert thread.is_pinned is True

    def test_unpin_thread(self, api_client, teacher_user, general_chat_room):
        """Открепление треда"""
        general_chat_room.participants.add(teacher_user)

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Тред",
            created_by=teacher_user,
            is_pinned=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/unpin/')

        assert response.status_code == status.HTTP_200_OK

        thread.refresh_from_db()
        assert thread.is_pinned is False

    def test_lock_thread(self, api_client, teacher_user, general_chat_room):
        """Блокировка треда"""
        general_chat_room.participants.add(teacher_user)

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Тред",
            created_by=teacher_user
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')

        assert response.status_code == status.HTTP_200_OK

        thread.refresh_from_db()
        assert thread.is_locked is True

    def test_unlock_thread(self, api_client, teacher_user, general_chat_room):
        """Разблокировка треда"""
        general_chat_room.participants.add(teacher_user)

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Тред",
            created_by=teacher_user,
            is_locked=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/unlock/')

        assert response.status_code == status.HTTP_200_OK

        thread.refresh_from_db()
        assert thread.is_locked is False


@pytest.mark.unit
@pytest.mark.django_db
class TestChatParticipantViewSet:
    """Тесты для ChatParticipantViewSet"""

    def test_list_participants_unauthenticated(self, api_client):
        """Неавторизованный пользователь не может получить список участников"""
        response = api_client.get('/api/chat/participants/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_participants_authenticated(self, api_client, student_user, teacher_user, chat_room):
        """Авторизованный пользователь получает участников своих чатов"""
        chat_room.participants.add(student_user, teacher_user)

        ChatParticipant.objects.create(room=chat_room, user=student_user)
        ChatParticipant.objects.create(room=chat_room, user=teacher_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/participants/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
