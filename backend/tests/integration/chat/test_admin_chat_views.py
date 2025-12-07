"""
Integration-тесты для admin chat API endpoints

Тестирует:
- AdminChatRoomListView (GET /api/chat/admin/rooms/)
- AdminChatRoomMessagesView (GET /api/chat/admin/rooms/<room_id>/messages/)
- AdminChatRoomDetailView (GET /api/chat/admin/rooms/<room_id>/)
- AdminChatStatsView (GET /api/chat/admin/stats/)

Проверяет:
- Доступ только для admin пользователей
- Корректность возвращаемых данных
- Пагинация сообщений
- Обработка ошибок (404, 403)
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from chat.models import ChatRoom, Message

User = get_user_model()


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminChatRoomListView:
    """Тесты для GET /api/admin/chat/rooms/"""

    def setup_method(self):
        self.client = APIClient()
        self.endpoint = '/api/chat/admin/rooms/'

    def test_get_rooms_as_admin_returns_200(self, admin_user, student_user):
        """Admin может получить список всех комнат"""
        ChatRoom.objects.create(
            name="Test Room 1",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        ChatRoom.objects.create(
            name="Test Room 2",
            type=ChatRoom.Type.GROUP,
            created_by=student_user
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_200_OK

    def test_get_rooms_returns_success_response(self, admin_user, student_user):
        """Ответ содержит success=true и данные"""
        ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.data['success'] is True
        assert 'data' in response.data
        assert 'rooms' in response.data['data']
        assert 'count' in response.data['data']

    def test_get_rooms_returns_all_rooms(self, admin_user, student_user, teacher_user):
        """Возвращает все комнаты"""
        room1 = ChatRoom.objects.create(
            name="Room 1",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        room2 = ChatRoom.objects.create(
            name="Room 2",
            type=ChatRoom.Type.GROUP,
            created_by=teacher_user
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['count'] == 2
        assert len(response.data['data']['rooms']) == 2

    def test_get_rooms_includes_room_details(self, admin_user, student_user):
        """Каждая комната включает необходимые поля"""
        room = ChatRoom.objects.create(
            name="Test Room",
            description="Test description",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        room_data = response.data['data']['rooms'][0]
        assert room_data['id'] == room.id
        assert room_data['name'] == "Test Room"
        assert room_data['type'] == ChatRoom.Type.DIRECT

    def test_get_rooms_as_non_admin_returns_403(self, student_user):
        """Non-admin пользователь получает 403"""
        self.client.force_authenticate(user=student_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_rooms_as_unauthenticated_returns_403(self):
        """Неавторизованный пользователь получает 403 (не admin)"""
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_rooms_as_teacher_returns_403(self, teacher_user):
        """Teacher пользователь получает 403"""
        self.client.force_authenticate(user=teacher_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_rooms_empty_list(self, admin_user):
        """Пустой список когда нет комнат"""
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['count'] == 0
        assert len(response.data['data']['rooms']) == 0

    def test_get_rooms_includes_participants_info(self, admin_user, student_user, teacher_user):
        """Каждая комната включает информацию об участниках"""
        room = ChatRoom.objects.create(
            name="Group Room",
            type=ChatRoom.Type.GROUP,
            created_by=student_user
        )
        room.participants.add(student_user, teacher_user)

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        room_data = response.data['data']['rooms'][0]
        assert 'participants' in room_data
        assert room_data['participants_count'] == 2

    def test_get_rooms_includes_last_message(self, admin_user, student_user):
        """Комната включает информацию о последнем сообщении"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        Message.objects.create(
            room=room,
            sender=student_user,
            content="Last message"
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        room_data = response.data['data']['rooms'][0]
        assert 'last_message' in room_data
        assert room_data['last_message'] is not None


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminChatRoomMessagesView:
    """Тесты для GET /api/admin/chat/rooms/<room_id>/messages/"""

    def setup_method(self):
        self.client = APIClient()

    def test_get_messages_as_admin_returns_200(self, admin_user, student_user):
        """Admin может получить сообщения комнаты"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        Message.objects.create(
            room=room,
            sender=student_user,
            content="Test message"
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK

    def test_get_messages_returns_success_response(self, admin_user, student_user):
        """Ответ содержит success=true и сообщения"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        Message.objects.create(
            room=room,
            sender=student_user,
            content="Test message"
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.data['success'] is True
        assert 'data' in response.data
        assert 'messages' in response.data['data']
        assert 'count' in response.data['data']
        assert 'room_id' in response.data['data']

    def test_get_messages_returns_all_messages(self, admin_user, student_user):
        """Возвращает все сообщения комнаты"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        for i in range(5):
            Message.objects.create(
                room=room,
                sender=student_user,
                content=f"Message {i}"
            )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['count'] == 5
        assert len(response.data['data']['messages']) == 5

    def test_get_messages_includes_message_details(self, admin_user, student_user):
        """Каждое сообщение включает необходимые поля"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        msg = Message.objects.create(
            room=room,
            sender=student_user,
            content="Test message"
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        message_data = response.data['data']['messages'][0]
        assert message_data['id'] == msg.id
        assert message_data['content'] == "Test message"
        assert 'sender_name' in message_data

    def test_get_messages_nonexistent_room_returns_404(self, admin_user):
        """Несуществующая комната возвращает 404"""
        endpoint = '/api/chat/admin/rooms/999/messages/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['success'] is False

    def test_get_messages_as_non_admin_returns_403(self, student_user):
        """Non-admin пользователь получает 403"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/'
        self.client.force_authenticate(user=student_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_messages_empty_room(self, admin_user, student_user):
        """Пустая комната возвращает пустой список сообщений"""
        room = ChatRoom.objects.create(
            name="Empty Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['count'] == 0
        assert len(response.data['data']['messages']) == 0

    def test_get_messages_with_limit_parameter(self, admin_user, student_user):
        """Параметр limit ограничивает количество сообщений"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        for i in range(10):
            Message.objects.create(
                room=room,
                sender=student_user,
                content=f"Message {i}"
            )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/?limit=3'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert len(response.data['data']['messages']) == 3
        assert response.data['data']['limit'] == 3

    def test_get_messages_with_offset_parameter(self, admin_user, student_user):
        """Параметр offset применяет пагинацию"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        for i in range(10):
            Message.objects.create(
                room=room,
                sender=student_user,
                content=f"Message {i}"
            )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/?limit=5&offset=2'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.data['data']['offset'] == 2

    def test_get_messages_limit_capped_at_500(self, admin_user, student_user):
        """Лимит не может быть больше 500"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/?limit=1000'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.data['data']['limit'] == 500

    def test_get_messages_invalid_limit_returns_400(self, admin_user, student_user):
        """Невалидный limit возвращает 400"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/?limit=not_a_number'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False

    def test_get_messages_negative_offset_corrected(self, admin_user, student_user):
        """Отрицательный offset исправляется на 0"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        Message.objects.create(
            room=room,
            sender=student_user,
            content="Message"
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/messages/?offset=-5'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.data['data']['offset'] == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminChatRoomDetailView:
    """Тесты для GET /api/admin/chat/rooms/<room_id>/"""

    def setup_method(self):
        self.client = APIClient()

    def test_get_room_detail_as_admin_returns_200(self, admin_user, student_user):
        """Admin может получить детали комнаты"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_200_OK

    def test_get_room_detail_returns_success_response(self, admin_user, student_user):
        """Ответ содержит success=true и детали комнаты"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.data['success'] is True
        assert 'data' in response.data
        assert 'room' in response.data['data']

    def test_get_room_detail_includes_statistics(self, admin_user, student_user):
        """Возвращает статистику по комнате"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        room.participants.add(student_user)

        for i in range(3):
            Message.objects.create(
                room=room,
                sender=student_user,
                content=f"Message {i}"
            )

        endpoint = f'/api/chat/admin/rooms/{room.id}/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert 'participants_count' in response.data['data']
        assert 'messages_count' in response.data['data']
        assert response.data['data']['participants_count'] == 1
        assert response.data['data']['messages_count'] == 3

    def test_get_room_detail_nonexistent_returns_404(self, admin_user):
        """Несуществующая комната возвращает 404"""
        endpoint = '/api/chat/admin/rooms/999/'
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_room_detail_as_non_admin_returns_403(self, student_user):
        """Non-admin пользователь получает 403"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        endpoint = f'/api/chat/admin/rooms/{room.id}/'
        self.client.force_authenticate(user=student_user)
        response = self.client.get(endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminChatStatsView:
    """Тесты для GET /api/admin/chat/stats/"""

    def setup_method(self):
        self.client = APIClient()
        self.endpoint = '/api/chat/admin/stats/'

    def test_get_stats_as_admin_returns_200(self, admin_user):
        """Admin может получить статистику"""
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_200_OK

    def test_get_stats_returns_success_response(self, admin_user):
        """Ответ содержит success=true и статистику"""
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.data['success'] is True
        assert 'data' in response.data

    def test_get_stats_includes_all_fields(self, admin_user):
        """Статистика включает все необходимые поля"""
        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        required_fields = [
            'total_rooms',
            'active_rooms',
            'total_messages',
            'forum_subject_rooms',
            'direct_rooms',
            'group_rooms'
        ]

        for field in required_fields:
            assert field in response.data['data']

    def test_get_stats_counts_rooms(self, admin_user, student_user):
        """Статистика правильно считает комнаты"""
        ChatRoom.objects.create(
            name="Room 1",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        ChatRoom.objects.create(
            name="Room 2",
            type=ChatRoom.Type.GROUP,
            created_by=student_user
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get(self.endpoint)

        assert response.data['data']['total_rooms'] == 2

    def test_get_stats_as_non_admin_returns_403(self, student_user):
        """Non-admin пользователь получает 403"""
        self.client.force_authenticate(user=student_user)
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_stats_as_unauthenticated_returns_403(self):
        """Неавторизованный пользователь получает 403 (не admin)"""
        response = self.client.get(self.endpoint)

        assert response.status_code == status.HTTP_403_FORBIDDEN
