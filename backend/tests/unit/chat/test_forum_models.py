"""
Unit tests for forum chat models.

Tests forum-specific ChatRoom types (FORUM_SUBJECT, FORUM_TUTOR) and Message model
for forum chats.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from chat.models import ChatRoom, Message
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestChatRoomForumModels:
    """Tests for forum-specific ChatRoom model functionality"""

    def test_create_forum_subject_chat(self, student_user, teacher_user, subject):
        """Test creating a FORUM_SUBJECT type chat room"""
        chat = ChatRoom.objects.create(
            name="Математика - Иван Иванов ↔ Мария Петрова",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user,
            description="Forum for Математика between Иван Иванов and Мария Петрова"
        )

        assert chat.id is not None
        assert chat.type == ChatRoom.Type.FORUM_SUBJECT
        assert chat.created_by == student_user
        assert chat.is_active is True
        assert chat.enrollment is None  # Not yet linked to enrollment

    def test_create_forum_tutor_chat(self, student_user, tutor_user):
        """Test creating a FORUM_TUTOR type chat room"""
        chat = ChatRoom.objects.create(
            name="Математика - Иван Иванов ↔ Сергей Сидоров",
            type=ChatRoom.Type.FORUM_TUTOR,
            created_by=student_user,
            description="Forum for Математика between student and tutor"
        )

        assert chat.id is not None
        assert chat.type == ChatRoom.Type.FORUM_TUTOR
        assert chat.created_by == student_user
        assert chat.is_active is True
        assert chat.enrollment is None

    def test_forum_chat_with_subject_enrollment(self, student_user, teacher_user, enrollment):
        """Test creating forum chat linked to SubjectEnrollment"""
        # Use get_or_create to avoid UNIQUE constraint violation
        # (enrollment fixture may have already created chat via signal)
        chat, created = ChatRoom.objects.get_or_create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
            defaults={
                'name': f"{enrollment.get_subject_name()} - {student_user.get_full_name()} ↔ {teacher_user.get_full_name()}",
                'created_by': student_user
            }
        )

        assert chat.id is not None
        assert chat.enrollment == enrollment
        assert chat.enrollment.student == student_user
        assert chat.enrollment.teacher == teacher_user

    def test_forum_chat_participants(self, student_user, teacher_user):
        """Test adding participants to forum chat"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        chat.participants.add(student_user, teacher_user)

        assert chat.participants.count() == 2
        assert student_user in chat.participants.all()
        assert teacher_user in chat.participants.all()

    def test_forum_chat_type_choices(self):
        """Test forum types are available in ChatRoom.Type"""
        assert hasattr(ChatRoom.Type, 'FORUM_SUBJECT')
        assert hasattr(ChatRoom.Type, 'FORUM_TUTOR')
        assert ChatRoom.Type.FORUM_SUBJECT == 'forum_subject'
        assert ChatRoom.Type.FORUM_TUTOR == 'forum_tutor'

    def test_forum_chat_created_by_student(self, student_user, teacher_user):
        """Test that forum chat can be created_by a student"""
        chat = ChatRoom.objects.create(
            name="Student created forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        assert chat.created_by == student_user
        assert chat.created_by.role == User.Role.STUDENT

    def test_forum_chat_auto_delete_days(self, student_user):
        """Test auto_delete_days setting for forum chat"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user,
            auto_delete_days=30
        )

        assert chat.auto_delete_days == 30

    def test_forum_chat_default_auto_delete_days(self, student_user):
        """Test default auto_delete_days is 7"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        assert chat.auto_delete_days == 7

    def test_forum_chat_is_active_default(self, student_user):
        """Test forum chat is_active defaults to True"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        assert chat.is_active is True

    def test_forum_chat_indexes(self):
        """Test database indexes exist for forum queries"""
        indexes = [idx.name for idx in ChatRoom._meta.indexes]
        assert 'chat_type_enrollment_idx' in indexes
        assert 'chat_type_active_idx' in indexes


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageInForumChat:
    """Tests for Message model in forum chats"""

    def test_create_message_in_forum_chat(self, student_user, teacher_user):
        """Test creating a message in forum chat"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )
        chat.participants.add(student_user, teacher_user)

        message = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Hello from student",
            message_type=Message.Type.TEXT
        )

        assert message.id is not None
        assert message.room == chat
        assert message.sender == student_user
        assert message.content == "Hello from student"
        assert message.message_type == Message.Type.TEXT
        assert message.created_at is not None

    def test_message_text_type(self, student_user):
        """Test TEXT message type"""
        chat = ChatRoom.objects.create(
            name="Test",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        msg = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Test message",
            message_type=Message.Type.TEXT
        )

        assert msg.message_type == Message.Type.TEXT

    def test_message_in_forum_subject_chat(self, student_user, teacher_user, enrollment):
        """Test message in FORUM_SUBJECT type chat"""
        # Use get_or_create to avoid UNIQUE constraint violation
        chat, created = ChatRoom.objects.get_or_create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
            defaults={
                'name': "Subject Forum",
                'created_by': student_user
            }
        )
        chat.participants.add(student_user, teacher_user)

        message = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Question about subject"
        )

        assert message.room.type == ChatRoom.Type.FORUM_SUBJECT
        assert message.room.enrollment == enrollment

    def test_message_in_forum_tutor_chat(self, student_user, tutor_user, enrollment):
        """Test message in FORUM_TUTOR type chat"""
        chat = ChatRoom.objects.create(
            name="Tutor Forum",
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment,
            created_by=student_user
        )
        chat.participants.add(student_user, tutor_user)

        message = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Question for tutor"
        )

        assert message.room.type == ChatRoom.Type.FORUM_TUTOR
        assert message.room.enrollment == enrollment

    def test_message_from_teacher(self, student_user, teacher_user):
        """Test teacher can send message to forum chat"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )
        chat.participants.add(student_user, teacher_user)

        message = Message.objects.create(
            room=chat,
            sender=teacher_user,
            content="Reply from teacher"
        )

        assert message.sender == teacher_user
        assert message.sender.role == User.Role.TEACHER

    def test_message_from_tutor(self, student_user, tutor_user):
        """Test tutor can send message to forum chat"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_TUTOR,
            created_by=student_user
        )
        chat.participants.add(student_user, tutor_user)

        message = Message.objects.create(
            room=chat,
            sender=tutor_user,
            content="Reply from tutor"
        )

        assert message.sender == tutor_user
        assert message.sender.role == User.Role.TUTOR

    def test_message_is_edited_default(self, student_user):
        """Test is_edited defaults to False"""
        chat = ChatRoom.objects.create(
            name="Test",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        message = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Test"
        )

        assert message.is_edited is False

    def test_message_ordering_in_chat(self, student_user):
        """Test messages are ordered by created_at"""
        chat = ChatRoom.objects.create(
            name="Test",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        msg1 = Message.objects.create(
            room=chat,
            sender=student_user,
            content="First message"
        )

        msg2 = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Second message"
        )

        msg3 = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Third message"
        )

        messages = list(chat.messages.all())
        assert len(messages) == 3
        assert messages[0] == msg1
        assert messages[1] == msg2
        assert messages[2] == msg3

    def test_chat_last_message_property(self, student_user):
        """Test last_message property returns last message"""
        chat = ChatRoom.objects.create(
            name="Test",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        msg1 = Message.objects.create(
            room=chat,
            sender=student_user,
            content="First"
        )

        msg2 = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Last"
        )

        assert chat.last_message == msg2

    def test_multiple_messages_in_forum_chat(self, student_user, teacher_user):
        """Test multiple messages between student and teacher"""
        chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )
        chat.participants.add(student_user, teacher_user)

        # Student sends message
        msg1 = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Hello teacher"
        )

        # Teacher replies
        msg2 = Message.objects.create(
            room=chat,
            sender=teacher_user,
            content="Hello student"
        )

        assert chat.messages.count() == 2
        assert chat.messages.first() == msg1
        assert chat.messages.last() == msg2

    def test_message_str_representation(self, student_user):
        """Test message string representation"""
        chat = ChatRoom.objects.create(
            name="Test",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user
        )

        message = Message.objects.create(
            room=chat,
            sender=student_user,
            content="Test message content"
        )

        str_repr = str(message)
        assert student_user.get_full_name() in str_repr
        assert "Test message" in str_repr
