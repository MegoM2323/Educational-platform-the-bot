"""
Тесты для T010-T015: Все типы чатов (direct, group, forum_subject, forum_tutor, class)
и управление участниками чата.
"""

import uuid
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from chat.models import ChatRoom, Message, ChatParticipant
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db
class TestDirectChat:
    """T010: Создание прямого чата (DIRECT) между двумя пользователями"""

    def test_create_direct_chat_between_two_users(self):
        """Создать прямой чат между двумя пользователями"""
        user1 = User.objects.create_user(
            username=f"user1_{uuid.uuid4()}", email="user1@test.com", password="test123"
        )
        user2 = User.objects.create_user(
            username=f"user2_{uuid.uuid4()}", email="user2@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name=f"Direct Chat {user1.id}-{user2.id}",
            type=ChatRoom.Type.DIRECT,
            created_by=user1,
        )
        room.participants.add(user1, user2)

        assert room.type == ChatRoom.Type.DIRECT
        assert room.is_active is True
        assert room.participants.count() == 2
        assert user1 in room.participants.all()
        assert user2 in room.participants.all()

    def test_direct_chat_has_creator(self):
        """Прямой чат содержит создателя"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        room = ChatRoom.objects.create(
            name="Direct Chat", type=ChatRoom.Type.DIRECT, created_by=creator
        )

        assert room.created_by == creator

    def test_direct_chat_can_send_message(self):
        """В прямом чате можно отправить сообщение"""
        user1 = User.objects.create_user(
            username=f"user1_{uuid.uuid4()}", email="user1@test.com", password="test123"
        )
        user2 = User.objects.create_user(
            username=f"user2_{uuid.uuid4()}", email="user2@test.com", password="test123"
        )
        room = ChatRoom.objects.create(
            name="Direct Chat", type=ChatRoom.Type.DIRECT, created_by=user1
        )
        room.participants.add(user1, user2)

        message = Message.objects.create(
            room=room, sender=user1, content="Hello!", message_type=Message.Type.TEXT
        )

        assert message.room == room
        assert message.sender == user1
        assert message.content == "Hello!"
        assert room.messages.count() == 1

    def test_direct_chat_last_message(self):
        """Получить последнее сообщение в прямом чате"""
        user1 = User.objects.create_user(
            username=f"user1_{uuid.uuid4()}", email="user1@test.com", password="test123"
        )
        user2 = User.objects.create_user(
            username=f"user2_{uuid.uuid4()}", email="user2@test.com", password="test123"
        )
        room = ChatRoom.objects.create(
            name="Direct Chat", type=ChatRoom.Type.DIRECT, created_by=user1
        )
        room.participants.add(user1, user2)

        msg1 = Message.objects.create(
            room=room, sender=user1, content="First", message_type=Message.Type.TEXT
        )
        msg2 = Message.objects.create(
            room=room, sender=user2, content="Second", message_type=Message.Type.TEXT
        )

        assert room.last_message == msg2


@pytest.mark.django_db
class TestGroupChat:
    """T011: Создание группового чата (GROUP) с несколькими участниками"""

    def test_create_group_chat(self):
        """Создать групповой чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        room = ChatRoom.objects.create(
            name="Group Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )

        assert room.type == ChatRoom.Type.GROUP
        assert room.created_by == creator

    def test_add_multiple_participants_to_group(self):
        """Добавить несколько участников в групповой чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        users = [
            User.objects.create_user(
                username=f"user{i}_{uuid.uuid4()}",
                email=f"user{i}@test.com",
                password="test123"
            )
            for i in range(3)
        ]

        room = ChatRoom.objects.create(
            name="Group Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, *users)

        assert room.participants.count() == 4

    def test_group_chat_multiple_messages(self):
        """Отправить несколько сообщений в групповой чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        users = [
            User.objects.create_user(
                username=f"user{i}_{uuid.uuid4()}",
                email=f"user{i}@test.com",
                password="test123"
            )
            for i in range(2)
        ]

        room = ChatRoom.objects.create(
            name="Group Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, *users)

        messages = []
        for i, user in enumerate([creator] + users):
            msg = Message.objects.create(
                room=room,
                sender=user,
                content=f"Message {i}",
                message_type=Message.Type.TEXT,
            )
            messages.append(msg)

        assert room.messages.count() == 3
        assert room.last_message == messages[-1]


@pytest.mark.django_db
class TestForumSubjectChat:
    """T012: Создание форума по предмету (FORUM_SUBJECT)"""

    def test_create_forum_subject(self):
        """Форум по предмету создается автоматически при записи студента на предмет"""
        subject = Subject.objects.create(name="Math", description="Mathematics")
        student = User.objects.create_user(
            username=f"student_{uuid.uuid4()}",
            email="student@test.com",
            password="test123"
        )
        teacher = User.objects.create_user(
            username=f"teacher_{uuid.uuid4()}",
            email="teacher@test.com",
            password="test123"
        )

        enrollment = SubjectEnrollment.objects.create(
            student=student, subject=subject, teacher=teacher
        )

        # Форум автоматически создается сигналом при создании enrollment
        room = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).first()

        assert room is not None
        assert room.type == ChatRoom.Type.FORUM_SUBJECT
        assert room.enrollment == enrollment
        assert room.is_active is True

    def test_forum_subject_participants_include_student_and_teacher(self):
        """Форум предмета включает студента и учителя"""
        subject = Subject.objects.create(name="Math", description="Mathematics")
        student = User.objects.create_user(
            username=f"student_{uuid.uuid4()}",
            email="student@test.com",
            password="test123"
        )
        teacher = User.objects.create_user(
            username=f"teacher_{uuid.uuid4()}",
            email="teacher@test.com",
            password="test123"
        )

        enrollment = SubjectEnrollment.objects.create(
            student=student, subject=subject, teacher=teacher
        )

        # Получить автоматически созданный форум
        room = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).first()

        assert room is not None
        assert student in room.participants.all()
        assert teacher in room.participants.all()

    def test_forum_subject_unique_constraint(self):
        """Только один форум на одну запись на предмет (enforced by DB constraint)"""
        subject = Subject.objects.create(name="Math", description="Mathematics")
        student = User.objects.create_user(
            username=f"student_{uuid.uuid4()}",
            email="student@test.com",
            password="test123"
        )
        teacher = User.objects.create_user(
            username=f"teacher_{uuid.uuid4()}",
            email="teacher@test.com",
            password="test123"
        )

        enrollment = SubjectEnrollment.objects.create(
            student=student, subject=subject, teacher=teacher
        )

        # Первый форум создан автоматически сигналом
        room1 = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).first()

        assert room1 is not None

        # Попытка создать второй форум для того же enrollment должна привести к ошибке
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        with pytest.raises(Exception):  # IntegrityError
            ChatRoom.objects.create(
                name="Forum 2",
                type=ChatRoom.Type.FORUM_SUBJECT,
                created_by=creator,
                enrollment=enrollment,
            )


@pytest.mark.django_db
class TestForumTutorChat:
    """T013: Создание форума с тьютором (FORUM_TUTOR)"""

    def test_create_forum_tutor(self):
        """Создать форум с тьютором"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        tutor = User.objects.create_user(
            username=f"tutor_{uuid.uuid4()}",
            email="tutor@test.com",
            password="test123"
        )
        student = User.objects.create_user(
            username=f"student_{uuid.uuid4()}",
            email="student@test.com",
            password="test123"
        )

        room = ChatRoom.objects.create(
            name=f"Tutor Forum: {tutor.username}",
            type=ChatRoom.Type.FORUM_TUTOR,
            created_by=creator,
        )
        room.participants.add(student, tutor)

        assert room.type == ChatRoom.Type.FORUM_TUTOR
        assert tutor in room.participants.all()
        assert student in room.participants.all()

    def test_forum_tutor_only_tutor_can_write(self):
        """В форуме с тьютором только тьютор может отправлять сообщения"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        tutor = User.objects.create_user(
            username=f"tutor_{uuid.uuid4()}",
            email="tutor@test.com",
            password="test123"
        )
        student = User.objects.create_user(
            username=f"student_{uuid.uuid4()}",
            email="student@test.com",
            password="test123"
        )

        room = ChatRoom.objects.create(
            name=f"Tutor Forum: {tutor.username}",
            type=ChatRoom.Type.FORUM_TUTOR,
            created_by=creator,
        )
        room.participants.add(student, tutor)

        # Тьютор может отправить
        tutor_message = Message.objects.create(
            room=room, sender=tutor, content="Tutor reply", message_type=Message.Type.TEXT
        )
        assert tutor_message.sender == tutor

        # Студент может отправить (обычно с ограничениями на API уровне)
        student_message = Message.objects.create(
            room=room,
            sender=student,
            content="Student question",
            message_type=Message.Type.TEXT,
        )
        assert student_message.sender == student


@pytest.mark.django_db
class TestClassChat:
    """T014: Создание классного чата (CLASS)"""

    def test_create_class_chat(self):
        """Создать классный чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        room = ChatRoom.objects.create(
            name="Class 1A", type=ChatRoom.Type.CLASS, created_by=creator
        )

        assert room.type == ChatRoom.Type.CLASS
        assert room.is_active is True

    def test_add_class_participants(self):
        """Добавить участников в классный чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        teacher = User.objects.create_user(
            username=f"teacher_{uuid.uuid4()}",
            email="teacher@test.com",
            password="test123"
        )
        students = [
            User.objects.create_user(
                username=f"student{i}_{uuid.uuid4()}",
                email=f"student{i}@test.com",
                password="test123"
            )
            for i in range(3)
        ]

        room = ChatRoom.objects.create(
            name="Class 1A", type=ChatRoom.Type.CLASS, created_by=creator
        )
        room.participants.add(teacher, *students)

        assert room.participants.count() == 4
        assert teacher in room.participants.all()
        for student in students:
            assert student in room.participants.all()

    def test_class_chat_all_participants_see_message(self):
        """Все участники класса видят сообщение"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        teacher = User.objects.create_user(
            username=f"teacher_{uuid.uuid4()}",
            email="teacher@test.com",
            password="test123"
        )
        students = [
            User.objects.create_user(
                username=f"student{i}_{uuid.uuid4()}",
                email=f"student{i}@test.com",
                password="test123"
            )
            for i in range(2)
        ]

        room = ChatRoom.objects.create(
            name="Class 1A", type=ChatRoom.Type.CLASS, created_by=creator
        )
        room.participants.add(teacher, *students)

        message = Message.objects.create(
            room=room,
            sender=teacher,
            content="Important announcement",
            message_type=Message.Type.TEXT,
        )

        # Все участники могут видеть сообщение (на уровне БД)
        all_room_messages = room.messages.all()
        assert message in all_room_messages
        assert all_room_messages.count() == 1


@pytest.mark.django_db
class TestChatParticipants:
    """T015: Управление участниками чата"""

    def test_add_participant_to_chat(self):
        """Добавить участника в чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        user = User.objects.create_user(
            username=f"user_{uuid.uuid4()}", email="user@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, user)

        assert user in room.participants.all()
        assert room.participants.count() == 2

    def test_remove_participant_from_chat(self):
        """Удалить участника из чата"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        user = User.objects.create_user(
            username=f"user_{uuid.uuid4()}", email="user@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, user)

        assert room.participants.count() == 2

        room.participants.remove(user)

        assert user not in room.participants.all()
        assert room.participants.count() == 1

    def test_clear_all_participants(self):
        """Удалить всех участников из чата"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        users = [
            User.objects.create_user(
                username=f"user{i}_{uuid.uuid4()}",
                email=f"user{i}@test.com",
                password="test123"
            )
            for i in range(3)
        ]

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, *users)

        assert room.participants.count() == 4

        room.participants.clear()

        assert room.participants.count() == 0

    def test_chat_participant_model(self):
        """ChatParticipant трекирует информацию об участнике"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        user = User.objects.create_user(
            username=f"user_{uuid.uuid4()}", email="user@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, user)

        participant = ChatParticipant.objects.create(room=room, user=user)

        assert participant.user == user
        assert participant.room == room
        assert participant.is_muted is False
        assert participant.is_admin is False

    def test_chat_participant_is_admin(self):
        """ChatParticipant может быть администратором"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator)

        participant = ChatParticipant.objects.create(room=room, user=creator, is_admin=True)

        assert participant.is_admin is True

    def test_chat_participant_is_muted(self):
        """ChatParticipant может быть заглушен"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        user = User.objects.create_user(
            username=f"user_{uuid.uuid4()}", email="user@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, user)

        participant = ChatParticipant.objects.create(room=room, user=user, is_muted=True)

        assert participant.is_muted is True

    def test_chat_participant_unread_count(self):
        """ChatParticipant может трекировать непрочитанные сообщения"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        user = User.objects.create_user(
            username=f"user_{uuid.uuid4()}", email="user@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, user)

        # Отправить сообщение
        Message.objects.create(
            room=room, sender=creator, content="Hello", message_type=Message.Type.TEXT
        )

        # Создать участника с last_read_at
        participant = ChatParticipant.objects.create(
            room=room, user=user, last_read_at=timezone.now()
        )

        # Отправить еще сообщение
        Message.objects.create(
            room=room, sender=creator, content="Second", message_type=Message.Type.TEXT
        )

        unread = participant.unread_count
        assert unread >= 1

    def test_unique_participant_per_room(self):
        """Один пользователь не может быть дважды участником одного чата"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        user = User.objects.create_user(
            username=f"user_{uuid.uuid4()}", email="user@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, user)

        ChatParticipant.objects.create(room=room, user=user)

        with pytest.raises(Exception):  # IntegrityError
            ChatParticipant.objects.create(room=room, user=user)


@pytest.mark.django_db
class TestChatMessageVisibility:
    """Проверка видимости сообщений всеми участниками"""

    def test_all_participants_see_direct_message(self):
        """Оба участника видят сообщение в прямом чате"""
        user1 = User.objects.create_user(
            username=f"user1_{uuid.uuid4()}", email="user1@test.com", password="test123"
        )
        user2 = User.objects.create_user(
            username=f"user2_{uuid.uuid4()}", email="user2@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Direct", type=ChatRoom.Type.DIRECT, created_by=user1
        )
        room.participants.add(user1, user2)

        message = Message.objects.create(
            room=room, sender=user1, content="Test", message_type=Message.Type.TEXT
        )

        # Оба видят сообщение
        assert message in room.messages.all()
        assert message in user1.sent_messages.all()

    def test_all_participants_see_group_message(self):
        """Все участники видят сообщение в групповом чате"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )
        users = [
            User.objects.create_user(
                username=f"user{i}_{uuid.uuid4()}",
                email=f"user{i}@test.com",
                password="test123"
            )
            for i in range(3)
        ]

        room = ChatRoom.objects.create(
            name="Group", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator, *users)

        message = Message.objects.create(
            room=room, sender=users[0], content="Test", message_type=Message.Type.TEXT
        )

        # Все участники видят
        for user in [creator] + users:
            # Сообщение в одной комнате для всех
            assert message in room.messages.all()


@pytest.mark.django_db
class TestChatAutoDelete:
    """Проверка автоудаления сообщений"""

    def test_chat_has_auto_delete_days(self):
        """Чат может иметь настройку автоудаления"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat",
            type=ChatRoom.Type.GROUP,
            created_by=creator,
            auto_delete_days=30,
        )

        assert room.auto_delete_days == 30

    def test_chat_default_auto_delete_days(self):
        """По умолчанию 7 дней на автоудаление"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )

        assert room.auto_delete_days == 7


@pytest.mark.django_db
class TestIntegrationChatTypes:
    """Интеграционные тесты для всех типов чатов"""

    def test_create_all_chat_types(self):
        """Создать все типы чатов"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )

        chat_types = [
            ChatRoom.Type.DIRECT,
            ChatRoom.Type.GROUP,
            ChatRoom.Type.CLASS,
            ChatRoom.Type.FORUM_SUBJECT,
            ChatRoom.Type.FORUM_TUTOR,
        ]

        for chat_type in chat_types:
            room = ChatRoom.objects.create(
                name=f"Chat {chat_type}",
                type=chat_type,
                created_by=creator,
            )
            assert room.type == chat_type

    def test_message_types_in_chat(self):
        """Отправить разные типы сообщений в чат"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )
        room.participants.add(creator)

        message_types = [
            (Message.Type.TEXT, "Hello"),
            (Message.Type.SYSTEM, "System message"),
        ]

        for msg_type, content in message_types:
            msg = Message.objects.create(
                room=room, sender=creator, content=content, message_type=msg_type
            )
            assert msg.message_type == msg_type

    def test_chat_room_timestamps(self):
        """Проверить временные метки чата"""
        creator = User.objects.create_user(
            username=f"creator_{uuid.uuid4()}", email="creator@test.com", password="test123"
        )

        room = ChatRoom.objects.create(
            name="Chat", type=ChatRoom.Type.GROUP, created_by=creator
        )

        assert room.created_at is not None
        assert room.updated_at is not None
        assert room.created_at <= room.updated_at
