"""
Integration tests for Forum system.

Tests the complete forum workflow including:
- Signal-based automatic chat creation on enrollment
- Message creation and persistence
- Forum chat types and participants
"""

import pytest
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from chat.models import ChatRoom, Message
from materials.models import Subject, SubjectEnrollment


@pytest.fixture
def api_client():
    """Create API client for testing"""
    return APIClient()


@pytest.mark.integration
@pytest.mark.django_db
class TestForumChatSignalIntegration:
    """Integration tests for forum chat creation via signals"""

    def test_enrollment_creates_forum_chats(self, student_user, teacher_user, subject):
        """Test that SubjectEnrollment creation automatically creates forum chats"""
        # Create enrollment - this should trigger signal to create chats
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Verify FORUM_SUBJECT chat was created
        subject_chats = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )
        assert subject_chats.exists()
        assert subject_chats.count() == 1

        # Verify chat has correct participants
        chat = subject_chats.first()
        assert student_user in chat.participants.all()
        assert teacher_user in chat.participants.all()

    def test_enrollment_creates_tutor_chat_when_tutor_assigned(self, student_user, teacher_user, tutor_user, subject):
        """Test that tutor chat is created when student has tutor"""
        # Assign tutor to student
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Verify both chats were created
        all_chats = ChatRoom.objects.filter(enrollment=enrollment)
        assert all_chats.count() == 2

        # Verify types
        types = list(all_chats.values_list('type', flat=True))
        assert ChatRoom.Type.FORUM_SUBJECT in types
        assert ChatRoom.Type.FORUM_TUTOR in types

    def test_chat_name_format(self, student_user, teacher_user, subject):
        """Test forum chat name has correct format"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Format: "{Subject} - {Student} ↔ {Teacher}"
        expected_name = f"{subject.name} - {student_user.get_full_name()} ↔ {teacher_user.get_full_name()}"
        assert chat.name == expected_name


@pytest.mark.integration
@pytest.mark.django_db
class TestForumMessageIntegration:
    """Integration tests for forum messages"""

    def test_create_message_in_forum_chat(self, student_user, teacher_user, enrollment):
        """Test creating message in forum chat"""
        forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Create message
        message = Message.objects.create(
            room=forum_chat,
            sender=student_user,
            content="Test forum message",
            message_type=Message.Type.TEXT
        )

        # Verify message exists
        assert message.id is not None
        assert message.sender == student_user
        assert message.room == forum_chat

        # Verify message appears in chat
        assert forum_chat.messages.filter(id=message.id).exists()

    def test_multiple_messages_in_sequence(self, student_user, teacher_user, enrollment):
        """Test multiple messages in forum chat"""
        forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Student sends message
        msg1 = Message.objects.create(
            room=forum_chat,
            sender=student_user,
            content="Student question"
        )

        # Teacher replies
        msg2 = Message.objects.create(
            room=forum_chat,
            sender=teacher_user,
            content="Teacher answer"
        )

        # Verify message order
        messages = list(forum_chat.messages.all())
        assert len(messages) == 2
        assert messages[0] == msg1
        assert messages[1] == msg2

    def test_messages_persisted_to_database(self, student_user, teacher_user, enrollment):
        """Test messages are correctly stored in database"""
        forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        message_content = "Important forum message"

        # Create message
        Message.objects.create(
            room=forum_chat,
            sender=student_user,
            content=message_content
        )

        # Retrieve and verify
        retrieved = Message.objects.get(content=message_content)
        assert retrieved.sender == student_user
        assert retrieved.room == forum_chat


@pytest.mark.integration
@pytest.mark.django_db
class TestForumChatTypes:
    """Integration tests for forum chat types"""

    def test_forum_subject_type(self, student_user, teacher_user, subject):
        """Test FORUM_SUBJECT chat type"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.type == ChatRoom.Type.FORUM_SUBJECT
        assert chat.type == 'forum_subject'

    def test_forum_tutor_type(self, student_user, teacher_user, tutor_user, subject):
        """Test FORUM_TUTOR chat type"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        assert chat.type == ChatRoom.Type.FORUM_TUTOR
        assert chat.type == 'forum_tutor'

    def test_different_chat_types_for_different_subjects(self, student_user, teacher_user):
        """Test multiple enrollments create separate chats"""
        subject1 = Subject.objects.create(name="Math")
        subject2 = Subject.objects.create(name="English")

        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject1,
            teacher=teacher_user
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user
        )

        chat1 = ChatRoom.objects.get(enrollment=enrollment1)
        chat2 = ChatRoom.objects.get(enrollment=enrollment2)

        assert chat1.id != chat2.id
        assert chat1.name != chat2.name


@pytest.mark.integration
@pytest.mark.django_db
class TestForumChatParticipants:
    """Integration tests for forum chat participants"""

    def test_student_and_teacher_in_subject_chat(self, student_user, teacher_user, enrollment):
        """Test student and teacher are participants in subject chat"""
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.participants.count() == 2
        assert student_user in chat.participants.all()
        assert teacher_user in chat.participants.all()

    def test_student_and_tutor_in_tutor_chat(self, student_user, teacher_user, tutor_user, subject):
        """Test student and tutor are participants in tutor chat"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        assert chat.participants.count() == 2
        assert student_user in chat.participants.all()
        assert tutor_user in chat.participants.all()

    def test_only_specific_participants_in_chat(self, student_user, teacher_user, parent_user, enrollment):
        """Test that only participants can see chat"""
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Parent should not be in chat
        assert parent_user not in chat.participants.all()


@pytest.mark.integration
@pytest.mark.django_db
class TestForumChatIdempotency:
    """Integration tests for signal idempotency"""

    def test_re_saving_enrollment_does_not_duplicate_chats(self, student_user, teacher_user, subject):
        """Test that signal is idempotent"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        initial_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).count()
        assert initial_count == 1

        # Re-save enrollment multiple times
        enrollment.save()
        enrollment.save()
        enrollment.save()

        # Should still have only 1 chat
        final_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).count()
        assert final_count == 1

    def test_multiple_enrollments_dont_interfere(self, student_user, teacher_user):
        """Test multiple enrollments create independent chats"""
        subject1 = Subject.objects.create(name="Subject1")
        subject2 = Subject.objects.create(name="Subject2")

        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject1,
            teacher=teacher_user
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user
        )

        # Each enrollment should have exactly 1 chat
        chat1_count = ChatRoom.objects.filter(enrollment=enrollment1).count()
        chat2_count = ChatRoom.objects.filter(enrollment=enrollment2).count()

        assert chat1_count == 1
        assert chat2_count == 1
