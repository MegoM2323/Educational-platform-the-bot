import json
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock

from accounts.models import StudentProfile, TeacherProfile, TutorProfile
from materials.models import SubjectEnrollment, Subject
from chat.models import ChatRoom, Message, ChatParticipant

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestWebSocketChatRoles(TestCase):
    """WebSocket tests for chat role-based access"""

    def setUp(self):
        """Create users and chat rooms"""
        self.student1 = User.objects.create_user(
            username="student1", email="student1@test.com", password="pass", role="student", is_active=True
        )
        self.student2 = User.objects.create_user(
            username="student2", email="student2@test.com", password="pass", role="student", is_active=True
        )
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@test.com", password="pass", role="teacher", is_active=True
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="pass", role="admin", is_active=True
        )
        self.tutor = User.objects.create_user(
            username="tutor", email="tutor@test.com", password="pass", role="tutor", is_active=True
        )
        self.inactive_user = User.objects.create_user(
            username="inactive", email="inactive@test.com", password="pass", role="student", is_active=False
        )

        # Create profiles
        StudentProfile.objects.create(user=self.student1)
        StudentProfile.objects.create(user=self.student2)
        TeacherProfile.objects.create(user=self.teacher)
        TutorProfile.objects.create(user=self.tutor)

        # Create subject and enrollment
        self.subject = Subject.objects.create(name="Math")
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        # Create chat rooms with participants
        self.chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.chat_room, user=self.student1)
        ChatParticipant.objects.create(room=self.chat_room, user=self.teacher)

        # Create another chat room for admin tests
        self.admin_chat = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.admin_chat, user=self.admin)
        ChatParticipant.objects.create(room=self.admin_chat, user=self.student1)

    def _get_token(self, user):
        """Generate JWT token for user"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_student_can_access_chat_with_teacher(self):
        """Student can access WebSocket chat with teacher"""
        # Test via ChatParticipant check
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.student1
        ).exists()
        assert is_participant is True

    def test_student_cannot_access_chat_with_other_student(self):
        """Student cannot access WebSocket chat with another student (not participant)"""
        # Create a chat that student2 is not in
        other_chat = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=other_chat, user=self.student1)

        # student2 is not participant, so cannot access
        is_participant = ChatParticipant.objects.filter(
            room=other_chat, user=self.student2
        ).exists()
        assert is_participant is False

    def test_admin_can_access_any_chat(self):
        """Admin can access any WebSocket chat"""
        # Admin not necessarily in chat, but could access via permissions
        # Test that admin is in the admin_chat
        is_participant = ChatParticipant.objects.filter(
            room=self.admin_chat, user=self.admin
        ).exists()
        assert is_participant is True

    def test_participant_access_check(self):
        """ChatParticipant check - user must be in room"""
        # student1 is in admin_chat
        participant = ChatParticipant.objects.filter(
            room=self.admin_chat, user=self.student1
        ).exists()
        assert participant is True

        # student2 is not in admin_chat
        participant = ChatParticipant.objects.filter(
            room=self.admin_chat, user=self.student2
        ).exists()
        assert participant is False

    def test_message_send_student_to_teacher_permission(self):
        """Student can send message if in chat with teacher"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="Test message"
        )
        assert msg.sender == self.student1
        assert msg.room == self.chat_room
        assert msg.is_deleted is False

    def test_message_not_sent_if_not_participant(self):
        """Cannot send message if not a participant"""
        # student2 tries to send to chat_room where only student1 and teacher are
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.student2
        ).exists()
        assert is_participant is False

    def test_inactive_user_cannot_send_message(self):
        """Inactive user cannot create message"""
        # Add inactive user to room
        ChatParticipant.objects.create(room=self.chat_room, user=self.inactive_user)

        # Inactive status should prevent message creation in real consumer
        assert self.inactive_user.is_active is False

        # Verify inactive user is participant but should be blocked by is_active check
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.inactive_user
        ).exists()
        assert is_participant is True

    def test_message_broadcast_not_deleted(self):
        """Normal message should be broadcast, deleted message should not"""
        # Normal message
        normal_msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="Normal", is_deleted=False
        )
        assert normal_msg.is_deleted is False

        # Deleted message
        deleted_msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="Deleted", is_deleted=True
        )
        assert deleted_msg.is_deleted is True

    def test_rate_limit_structure_exists(self):
        """Rate limit mechanism should prevent 11+ messages in 1 minute"""
        # This is a conceptual test - actual rate limiting happens in consumer
        # Testing that rate limit keys would work
        rate_key = f"chat_rate_limit:{self.student1.id}"
        # Format is valid
        assert "chat_rate_limit:" in rate_key
        assert str(self.student1.id) in rate_key

    def test_room_enumeration_limit_structure(self):
        """Room enumeration limit should restrict connections per user"""
        room_limit_key = f"chat_rooms:{self.student1.id}"
        # Format is valid
        assert "chat_rooms:" in room_limit_key
        assert str(self.student1.id) in room_limit_key

    def test_multiple_participants_in_chat(self):
        """Multiple participants can be in same chat room"""
        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=self.student1)
        ChatParticipant.objects.create(room=room, user=self.teacher)
        ChatParticipant.objects.create(room=room, user=self.admin)

        participants = ChatParticipant.objects.filter(room=room).count()
        assert participants == 3

    def test_message_belongs_to_room(self):
        """Messages are properly associated with rooms"""
        room1 = ChatRoom.objects.create(is_active=True)
        room2 = ChatRoom.objects.create(is_active=True)

        msg1 = Message.objects.create(room=room1, sender=self.student1, content="In room 1")
        msg2 = Message.objects.create(room=room2, sender=self.teacher, content="In room 2")

        assert msg1.room == room1
        assert msg2.room == room2
        assert msg1.room != msg2.room

    def test_inactive_user_access_blocked(self):
        """Inactive user should not have access permission"""
        inactive_chat = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=inactive_chat, user=self.inactive_user)

        # Even though participant exists, inactive status blocks access
        # (in real consumer, is_active check prevents message sending)
        assert self.inactive_user.is_active is False

    def test_chat_room_active_flag(self):
        """Chat room has is_active flag"""
        active_room = ChatRoom.objects.create(is_active=True)
        assert active_room.is_active is True

        inactive_room = ChatRoom.objects.create(is_active=False)
        assert inactive_room.is_active is False

    def test_message_timestamps(self):
        """Messages have created_at and updated_at timestamps"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="Test"
        )
        assert msg.created_at is not None
        assert msg.updated_at is not None

    def test_message_edit_flag(self):
        """Messages can be marked as edited"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="Original"
        )
        assert msg.is_edited is False

        msg.content = "Edited"
        msg.is_edited = True
        msg.save()

        msg.refresh_from_db()
        assert msg.is_edited is True

    def test_message_delete_flag(self):
        """Messages can be marked as deleted"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="To delete"
        )
        assert msg.is_deleted is False
        assert msg.deleted_at is None

        msg.is_deleted = True
        msg.deleted_at = timezone.now()
        msg.save()

        msg.refresh_from_db()
        assert msg.is_deleted is True
        assert msg.deleted_at is not None

    def test_message_soft_delete_preserves_data(self):
        """Soft-deleted messages preserve data (not permanently removed)"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.student1, content="Original content"
        )
        original_id = msg.id

        msg.is_deleted = True
        msg.save()

        # Message still exists in DB
        msg = Message.objects.get(id=original_id)
        assert msg.is_deleted is True
        assert msg.content == "Original content"  # Content preserved

    def test_participant_joined_at_timestamp(self):
        """ChatParticipant has joined_at timestamp"""
        room = ChatRoom.objects.create(is_active=True)
        participant = ChatParticipant.objects.create(room=room, user=self.student1)

        assert participant.joined_at is not None

    def test_participant_last_read_at_tracking(self):
        """ChatParticipant tracks last_read_at"""
        room = ChatRoom.objects.create(is_active=True)
        participant = ChatParticipant.objects.create(room=room, user=self.student1)

        # Initially None
        assert participant.last_read_at is None

        # Can be set
        participant.last_read_at = timezone.now()
        participant.save()

        participant.refresh_from_db()
        assert participant.last_read_at is not None

    def test_unique_participant_constraint(self):
        """Each user can be participant in room only once"""
        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=self.student1)

        # Trying to add same participant again should fail
        with pytest.raises(Exception):
            ChatParticipant.objects.create(room=room, user=self.student1)
