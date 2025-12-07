"""
Unit-тесты для AdminChatService

Тестирует:
- AdminChatService.get_all_rooms() - получение всех комнат
- AdminChatService.get_room_messages() - получение сообщений комнаты
- AdminChatService.get_room_by_id() - получение деталей комнаты
- AdminChatService.get_chat_stats() - получение статистики
"""
import pytest
from django.test import TestCase
from django.utils import timezone
from chat.models import ChatRoom, Message
from chat.services.admin_chat_service import AdminChatService
from datetime import timedelta
from conftest import StudentUserFactory, ParentUserFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestAdminChatServiceGetAllRooms:
    """Тесты для метода get_all_rooms()"""

    def test_get_all_rooms_empty(self):
        """Получение всех комнат когда их нет"""
        rooms = AdminChatService.get_all_rooms()

        assert rooms.count() == 0

    def test_get_all_rooms_single_room(self, student_user):
        """Получение списка с одной комнатой"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        rooms = AdminChatService.get_all_rooms()

        assert rooms.count() == 1
        assert rooms[0].id == room.id

    def test_get_all_rooms_multiple_types(self, student_user, teacher_user):
        """Получение комнат разных типов"""
        room1 = ChatRoom.objects.create(
            name="Direct Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        room2 = ChatRoom.objects.create(
            name="Group Chat",
            type=ChatRoom.Type.GROUP,
            created_by=teacher_user
        )
        room3 = ChatRoom.objects.create(
            name="General Forum",
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )

        rooms = AdminChatService.get_all_rooms()

        assert rooms.count() == 3
        room_ids = [r.id for r in rooms]
        assert room1.id in room_ids
        assert room2.id in room_ids
        assert room3.id in room_ids

    def test_get_all_rooms_ordering_by_updated_at(self, student_user):
        """Комнаты сортируются по updated_at в убывающем порядке"""
        room1 = ChatRoom.objects.create(
            name="Old Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        # Имитируем старую дату
        ChatRoom.objects.filter(id=room1.id).update(
            updated_at=timezone.now() - timedelta(days=1)
        )

        room2 = ChatRoom.objects.create(
            name="New Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        rooms = list(AdminChatService.get_all_rooms())

        # Новая комната должна быть первой
        assert rooms[0].id == room2.id
        assert rooms[1].id == room1.id

    def test_get_all_rooms_includes_participants(self, student_user, teacher_user):
        """Результат включает информацию об участниках"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.GROUP,
            created_by=student_user
        )
        room.participants.add(student_user, teacher_user)

        rooms = AdminChatService.get_all_rooms()
        room_data = rooms[0]

        # Проверяем что участники доступны
        assert room_data.participants.count() == 2

    def test_get_all_rooms_includes_counts(self, student_user):
        """Результат включает аннотированные counts"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        room.participants.add(student_user)

        # Добавляем сообщения
        Message.objects.create(
            room=room,
            sender=student_user,
            content="Test message 1"
        )
        Message.objects.create(
            room=room,
            sender=student_user,
            content="Test message 2"
        )

        rooms = AdminChatService.get_all_rooms()
        room_data = rooms[0]

        # Проверяем что counts аннотированы
        assert hasattr(room_data, 'participants_count')
        assert hasattr(room_data, 'messages_count')
        assert room_data.participants_count == 1
        assert room_data.messages_count == 2

    def test_get_all_rooms_includes_created_by(self, student_user):
        """Результат включает информацию о создателе"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        rooms = AdminChatService.get_all_rooms()
        room_data = rooms[0]

        # Создатель должен быть доступен (select_related)
        assert room_data.created_by.id == student_user.id


@pytest.mark.unit
@pytest.mark.django_db
class TestAdminChatServiceGetRoomMessages:
    """Тесты для метода get_room_messages()"""

    def test_get_room_messages_empty(self, student_user):
        """Получение сообщений для пустой комнаты"""
        room = ChatRoom.objects.create(
            name="Empty Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        messages = AdminChatService.get_room_messages(room.id)

        assert len(list(messages)) == 0

    def test_get_room_messages_single_message(self, student_user):
        """Получение одного сообщения"""
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

        messages = AdminChatService.get_room_messages(room.id)

        assert messages.count() == 1
        assert messages[0].id == msg.id

    def test_get_room_messages_multiple_messages(self, student_user, teacher_user):
        """Получение нескольких сообщений"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.GROUP,
            created_by=student_user
        )

        msg1 = Message.objects.create(
            room=room,
            sender=student_user,
            content="Message 1"
        )
        msg2 = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Message 2"
        )
        msg3 = Message.objects.create(
            room=room,
            sender=student_user,
            content="Message 3"
        )

        messages = AdminChatService.get_room_messages(room.id)

        assert messages.count() == 3

    def test_get_room_messages_ordering(self, student_user):
        """Сообщения сортируются по created_at в убывающем порядке"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        msg1 = Message.objects.create(
            room=room,
            sender=student_user,
            content="First message"
        )
        msg2 = Message.objects.create(
            room=room,
            sender=student_user,
            content="Second message"
        )

        messages = list(AdminChatService.get_room_messages(room.id))

        # Последнее созданное сообщение должно быть первым (desc order)
        assert messages[0].id == msg2.id
        assert messages[1].id == msg1.id

    def test_get_room_messages_with_limit(self, student_user):
        """Ограничение количества сообщений через limit"""
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

        messages = AdminChatService.get_room_messages(room.id, limit=3)

        assert messages.count() == 3

    def test_get_room_messages_with_offset(self, student_user):
        """Пагинация через offset"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        created_messages = []
        for i in range(5):
            msg = Message.objects.create(
                room=room,
                sender=student_user,
                content=f"Message {i}"
            )
            created_messages.append(msg)

        # Получаем с offset 2
        messages = AdminChatService.get_room_messages(room.id, limit=10, offset=2)

        # Должны быть последние 3 сообщения (из-за desc order, offset применяется после)
        assert messages.count() == 3

    def test_get_room_messages_limit_and_offset(self, student_user):
        """Сочетание limit и offset"""
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

        messages = AdminChatService.get_room_messages(room.id, limit=3, offset=2)

        assert messages.count() == 3

    def test_get_room_messages_nonexistent_room_raises(self):
        """Исключение при несуществующей комнате"""
        with pytest.raises(ChatRoom.DoesNotExist):
            AdminChatService.get_room_messages(room_id=999)

    def test_get_room_messages_includes_sender(self, student_user):
        """Сообщения включают информацию об отправителе (select_related)"""
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

        messages = AdminChatService.get_room_messages(room.id)
        message_data = messages[0]

        # Отправитель должен быть доступен (select_related)
        assert message_data.sender.id == student_user.id


@pytest.mark.unit
@pytest.mark.django_db
class TestAdminChatServiceGetRoomById:
    """Тесты для метода get_room_by_id()"""

    def test_get_room_by_id_exists(self, student_user):
        """Получение существующей комнаты по ID"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        result = AdminChatService.get_room_by_id(room.id)

        assert result.id == room.id
        assert result.name == "Test Room"

    def test_get_room_by_id_nonexistent(self):
        """Исключение при несуществующей комнате"""
        with pytest.raises(ChatRoom.DoesNotExist):
            AdminChatService.get_room_by_id(999)

    def test_get_room_by_id_includes_annotations(self, student_user):
        """Результат включает аннотированные поля"""
        room = ChatRoom.objects.create(
            name="Test Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        room.participants.add(student_user)

        result = AdminChatService.get_room_by_id(room.id)

        assert hasattr(result, 'participants_count')
        assert hasattr(result, 'messages_count')
        assert result.participants_count == 1
        assert result.messages_count == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestAdminChatServiceGetChatStats:
    """Тесты для метода get_chat_stats()"""

    def test_get_chat_stats_empty_database(self):
        """Статистика при пустой БД"""
        stats = AdminChatService.get_chat_stats()

        assert stats['total_rooms'] == 0
        assert stats['active_rooms'] == 0
        assert stats['total_messages'] == 0
        assert stats['forum_subject_rooms'] == 0
        assert stats['direct_rooms'] == 0
        assert stats['group_rooms'] == 0

    def test_get_chat_stats_with_rooms(self, student_user, teacher_user):
        """Статистика с несколькими комнатами"""
        # Создаем комнаты разных типов
        direct_room = ChatRoom.objects.create(
            name="Direct",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )
        group_room = ChatRoom.objects.create(
            name="Group",
            type=ChatRoom.Type.GROUP,
            created_by=teacher_user
        )
        general_room = ChatRoom.objects.create(
            name="General",
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )

        stats = AdminChatService.get_chat_stats()

        assert stats['total_rooms'] == 3
        assert stats['active_rooms'] == 3
        assert stats['direct_rooms'] == 1
        assert stats['group_rooms'] == 1

    def test_get_chat_stats_counts_messages(self, student_user):
        """Статистика считает сообщения"""
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

        stats = AdminChatService.get_chat_stats()

        assert stats['total_messages'] == 5

    def test_get_chat_stats_inactive_rooms(self, student_user):
        """Статистика различает активные и неактивные комнаты"""
        room1 = ChatRoom.objects.create(
            name="Active Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user,
            is_active=True
        )
        room2 = ChatRoom.objects.create(
            name="Inactive Room",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user,
            is_active=False
        )

        stats = AdminChatService.get_chat_stats()

        assert stats['total_rooms'] == 2
        assert stats['active_rooms'] == 1

    def test_get_chat_stats_forum_subject_rooms(self, student_user):
        """Статистика различает типы комнат"""
        # Просто проверяем что метод возвращает правильные значения
        # Не создаем forum_subject (может конфликтовать с unique constraint)
        room = ChatRoom.objects.create(
            name="Forum Subject Test",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user,
            enrollment=None  # Явно не устанавливаем enrollment
        )

        stats = AdminChatService.get_chat_stats()

        assert stats['forum_subject_rooms'] == 1

    def test_get_chat_stats_returns_dict(self):
        """Метод возвращает словарь со всеми ключами"""
        stats = AdminChatService.get_chat_stats()

        required_keys = [
            'total_rooms',
            'active_rooms',
            'total_messages',
            'forum_subject_rooms',
            'direct_rooms',
            'group_rooms'
        ]

        for key in required_keys:
            assert key in stats
            assert isinstance(stats[key], int)
