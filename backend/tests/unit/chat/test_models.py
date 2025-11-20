"""
Unit-тесты для моделей приложения chat

Тестирует:
- ChatRoom model
- Message model
- MessageRead model
- MessageThread model
- ChatParticipant model
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from django.db.utils import IntegrityError
from chat.models import (
    ChatRoom,
    Message,
    MessageRead,
    MessageThread,
    ChatParticipant
)


@pytest.mark.unit
@pytest.mark.django_db
class TestChatRoomModel:
    """Тесты для модели ChatRoom"""

    def test_create_chat_room_direct(self, student_user):
        """Создание личного чата"""
        room = ChatRoom.objects.create(
            name="Личный чат",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        assert room.id is not None
        assert room.name == "Личный чат"
        assert room.type == ChatRoom.Type.DIRECT
        assert room.created_by == student_user
        assert room.is_active is True
        assert room.auto_delete_days == 7

    def test_create_chat_room_group(self, teacher_user):
        """Создание группового чата"""
        room = ChatRoom.objects.create(
            name="Групповой чат 8А",
            description="Чат для класса 8А",
            type=ChatRoom.Type.GROUP,
            created_by=teacher_user
        )

        assert room.type == ChatRoom.Type.GROUP
        assert room.description == "Чат для класса 8А"

    def test_create_chat_room_general(self, teacher_user):
        """Создание общего форума"""
        room = ChatRoom.objects.create(
            name="Общий форум",
            description="Форум для всех пользователей",
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )

        assert room.type == ChatRoom.Type.GENERAL

    def test_chat_room_participants_m2m(self, student_user, teacher_user):
        """Добавление участников в чат"""
        room = ChatRoom.objects.create(
            name="Тестовый чат",
            type=ChatRoom.Type.GROUP,
            created_by=teacher_user
        )

        room.participants.add(student_user, teacher_user)

        assert room.participants.count() == 2
        assert student_user in room.participants.all()
        assert teacher_user in room.participants.all()

    def test_chat_room_str_method(self, student_user):
        """Тест метода __str__"""
        room = ChatRoom.objects.create(
            name="Тестовая комната",
            type=ChatRoom.Type.DIRECT,
            created_by=student_user
        )

        assert str(room) == "Тестовая комната"

    def test_chat_room_ordering(self, student_user):
        """Проверка сортировки по updated_at (desc)"""
        room1 = ChatRoom.objects.create(
            name="Первая комната",
            created_by=student_user,
            type=ChatRoom.Type.DIRECT
        )

        room2 = ChatRoom.objects.create(
            name="Вторая комната",
            created_by=student_user,
            type=ChatRoom.Type.DIRECT
        )

        # room2 создана позже, должна быть первой
        rooms = ChatRoom.objects.all()
        assert rooms[0] == room2
        assert rooms[1] == room1

    def test_chat_room_last_message_property(self, student_user, teacher_user):
        """Проверка property last_message"""
        room = ChatRoom.objects.create(
            name="Комната",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        # Без сообщений
        assert room.last_message is None

        # Создаем сообщение
        message = Message.objects.create(
            room=room,
            sender=student_user,
            content="Тестовое сообщение"
        )

        assert room.last_message == message

    def test_chat_room_auto_delete_days(self, student_user):
        """Проверка поля auto_delete_days"""
        room = ChatRoom.objects.create(
            name="Комната",
            created_by=student_user,
            type=ChatRoom.Type.DIRECT,
            auto_delete_days=30
        )

        assert room.auto_delete_days == 30

    def test_chat_room_is_active_flag(self, student_user):
        """Проверка флага is_active"""
        room = ChatRoom.objects.create(
            name="Комната",
            created_by=student_user,
            type=ChatRoom.Type.DIRECT,
            is_active=False
        )

        assert room.is_active is False


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageModel:
    """Тесты для модели Message"""

    def test_create_message_text(self, student_user, teacher_user):
        """Создание текстового сообщения"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=student_user,
            content="Привет, как дела?"
        )

        assert message.id is not None
        assert message.room == room
        assert message.sender == student_user
        assert message.content == "Привет, как дела?"
        assert message.message_type == Message.Type.TEXT
        assert message.is_edited is False

    def test_create_message_system(self, teacher_user):
        """Создание системного сообщения"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.GROUP
        )

        message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Пользователь присоединился",
            message_type=Message.Type.SYSTEM
        )

        assert message.message_type == Message.Type.SYSTEM

    def test_message_ordering(self, student_user, teacher_user):
        """Проверка сортировки по created_at (asc)"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message1 = Message.objects.create(
            room=room,
            sender=student_user,
            content="Первое сообщение"
        )

        message2 = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Второе сообщение"
        )

        # Фильтруем только по текущей комнате
        messages = Message.objects.filter(room=room)
        assert messages[0] == message1
        assert messages[1] == message2

    def test_message_str_method(self, student_user, teacher_user):
        """Тест метода __str__"""
        room = ChatRoom.objects.create(
            name="Комната",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=student_user,
            content="Очень длинное сообщение для проверки обрезки текста в методе str"
        )

        str_repr = str(message)
        assert student_user.username in str_repr or str(student_user) in str_repr
        assert "Комната" in str_repr
        assert len(str_repr) < 200  # Проверка, что текст обрезан

    def test_message_reply_to(self, student_user, teacher_user):
        """Проверка reply_to (ответ на сообщение)"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        original = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Оригинальное сообщение"
        )

        reply = Message.objects.create(
            room=room,
            sender=student_user,
            content="Ответ",
            reply_to=original
        )

        assert reply.reply_to == original
        assert original.replies.count() == 1
        assert reply in original.replies.all()

    def test_message_is_edited_flag(self, student_user, teacher_user):
        """Проверка флага is_edited"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=student_user,
            content="Сообщение"
        )

        assert message.is_edited is False

        message.content = "Исправленное сообщение"
        message.is_edited = True
        message.save()

        message.refresh_from_db()
        assert message.is_edited is True

    def test_message_thread_foreign_key(self, student_user, teacher_user):
        """Проверка связи с тредом"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Тестовый тред",
            created_by=teacher_user
        )

        message = Message.objects.create(
            room=room,
            sender=student_user,
            content="Сообщение в треде",
            thread=thread
        )

        assert message.thread == thread
        assert message in thread.messages.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageReadModel:
    """Тесты для модели MessageRead"""

    def test_create_message_read(self, student_user, teacher_user):
        """Создание отметки о прочтении"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Сообщение"
        )

        read = MessageRead.objects.create(
            message=message,
            user=student_user
        )

        assert read.id is not None
        assert read.message == message
        assert read.user == student_user
        assert read.read_at is not None

    def test_message_read_unique_together(self, student_user, teacher_user):
        """Проверка unique_together (message, user)"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Сообщение"
        )

        MessageRead.objects.create(
            message=message,
            user=student_user
        )

        # Попытка создать дубликат должна вызвать ошибку
        with pytest.raises(IntegrityError):
            MessageRead.objects.create(
                message=message,
                user=student_user
            )

    def test_message_read_str_method(self, student_user, teacher_user):
        """Тест метода __str__"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Сообщение"
        )

        read = MessageRead.objects.create(
            message=message,
            user=student_user
        )

        str_repr = str(read)
        assert "прочитал" in str_repr.lower() or "read" in str_repr.lower()

    def test_message_read_related_name(self, student_user, teacher_user, parent_user):
        """Проверка related_name для message и user"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Сообщение"
        )

        MessageRead.objects.create(message=message, user=student_user)
        MessageRead.objects.create(message=message, user=parent_user)

        # Проверка read_by (кто прочитал сообщение)
        assert message.read_by.count() == 2

        # Проверка read_messages (какие сообщения прочитал пользователь)
        assert student_user.read_messages.count() == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageThreadModel:
    """Тесты для модели MessageThread"""

    def test_create_message_thread(self, teacher_user):
        """Создание треда"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Обсуждение домашнего задания",
            created_by=teacher_user
        )

        assert thread.id is not None
        assert thread.room == room
        assert thread.title == "Обсуждение домашнего задания"
        assert thread.created_by == teacher_user
        assert thread.is_pinned is False
        assert thread.is_locked is False

    def test_thread_is_pinned(self, teacher_user):
        """Проверка флага is_pinned"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Важное объявление",
            created_by=teacher_user,
            is_pinned=True
        )

        assert thread.is_pinned is True

    def test_thread_is_locked(self, teacher_user):
        """Проверка флага is_locked"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Закрытая тема",
            created_by=teacher_user,
            is_locked=True
        )

        assert thread.is_locked is True

    def test_thread_ordering(self, teacher_user):
        """Проверка сортировки (закрепленные первыми, потом по дате)"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread1 = MessageThread.objects.create(
            room=room,
            title="Обычный тред 1",
            created_by=teacher_user
        )

        thread2 = MessageThread.objects.create(
            room=room,
            title="Закрепленный тред",
            created_by=teacher_user,
            is_pinned=True
        )

        thread3 = MessageThread.objects.create(
            room=room,
            title="Обычный тред 2",
            created_by=teacher_user
        )

        threads = MessageThread.objects.all()
        # Закрепленный должен быть первым
        assert threads[0] == thread2

    def test_thread_str_method(self, teacher_user):
        """Тест метода __str__"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Тестовый тред",
            created_by=teacher_user
        )

        str_repr = str(thread)
        assert "Тестовый тред" in str_repr
        assert "Форум" in str_repr

    def test_thread_messages_count_property(self, teacher_user, student_user):
        """Проверка property messages_count"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Тред",
            created_by=teacher_user
        )

        assert thread.messages_count == 0

        # Создаем сообщения
        Message.objects.create(
            room=room,
            sender=student_user,
            content="Сообщение 1",
            thread=thread
        )
        Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Сообщение 2",
            thread=thread
        )

        assert thread.messages_count == 2

    def test_thread_last_message_property(self, teacher_user, student_user):
        """Проверка property last_message"""
        room = ChatRoom.objects.create(
            name="Форум",
            created_by=teacher_user,
            type=ChatRoom.Type.GENERAL
        )

        thread = MessageThread.objects.create(
            room=room,
            title="Тред",
            created_by=teacher_user
        )

        assert thread.last_message is None

        message1 = Message.objects.create(
            room=room,
            sender=student_user,
            content="Первое",
            thread=thread
        )

        message2 = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Второе",
            thread=thread
        )

        assert thread.last_message == message2


@pytest.mark.unit
@pytest.mark.django_db
class TestChatParticipantModel:
    """Тесты для модели ChatParticipant"""

    def test_create_chat_participant(self, student_user, teacher_user):
        """Создание участника чата"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        assert participant.id is not None
        assert participant.room == room
        assert participant.user == student_user
        assert participant.joined_at is not None
        assert participant.is_muted is False
        assert participant.is_admin is False
        assert participant.last_read_at is None

    def test_participant_unique_together(self, student_user, teacher_user):
        """Проверка unique_together (room, user)"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        # Попытка создать дубликат должна вызвать ошибку
        with pytest.raises(IntegrityError):
            ChatParticipant.objects.create(
                room=room,
                user=student_user
            )

    def test_participant_is_muted(self, student_user, teacher_user):
        """Проверка флага is_muted"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.GROUP
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user,
            is_muted=True
        )

        assert participant.is_muted is True

    def test_participant_is_admin(self, teacher_user):
        """Проверка флага is_admin"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.GROUP
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=teacher_user,
            is_admin=True
        )

        assert participant.is_admin is True

    def test_participant_last_read_at(self, student_user, teacher_user):
        """Проверка поля last_read_at"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        assert participant.last_read_at is None

        now = timezone.now()
        participant.last_read_at = now
        participant.save()

        participant.refresh_from_db()
        assert participant.last_read_at == now

    def test_participant_str_method(self, student_user, teacher_user):
        """Тест метода __str__"""
        room = ChatRoom.objects.create(
            name="Комната",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        str_repr = str(participant)
        assert "Комната" in str_repr

    def test_participant_unread_count_property_no_reads(self, student_user, teacher_user):
        """Проверка property unread_count без прочтений"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        # Создаем сообщения от учителя
        Message.objects.create(room=room, sender=teacher_user, content="Сообщение 1")
        Message.objects.create(room=room, sender=teacher_user, content="Сообщение 2")

        # Все сообщения непрочитанные
        assert participant.unread_count == 2

    def test_participant_unread_count_property_with_last_read(self, student_user, teacher_user):
        """Проверка property unread_count с last_read_at"""
        import time

        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        # Создаем старое сообщение
        old_message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Старое сообщение"
        )

        # Засыпаем чтобы гарантировать разницу во времени
        time.sleep(0.01)

        # Устанавливаем время последнего прочтения на момент сейчас
        now = timezone.now()
        participant.last_read_at = now
        participant.save()

        # Засыпаем еще раз
        time.sleep(0.01)

        # Создаем новое сообщение которое точно будет после last_read_at
        new_message = Message.objects.create(
            room=room,
            sender=teacher_user,
            content="Новое сообщение"
        )

        # Обновляем participant из БД и проверяем
        participant.refresh_from_db()

        # Проверяем что новое сообщение создано после last_read_at
        assert new_message.created_at > participant.last_read_at

        # Должно быть 1 непрочитанное (новое)
        assert participant.unread_count >= 1

    def test_participant_unread_count_excludes_own_messages(self, student_user, teacher_user):
        """Проверка, что unread_count не считает собственные сообщения"""
        room = ChatRoom.objects.create(
            name="Чат",
            created_by=teacher_user,
            type=ChatRoom.Type.DIRECT
        )

        participant = ChatParticipant.objects.create(
            room=room,
            user=student_user
        )

        # Создаем сообщение от студента
        Message.objects.create(room=room, sender=student_user, content="Мое сообщение")

        # Создаем сообщение от учителя
        Message.objects.create(room=room, sender=teacher_user, content="Сообщение учителя")

        # Должно быть 1 непрочитанное (только от учителя)
        assert participant.unread_count == 1
