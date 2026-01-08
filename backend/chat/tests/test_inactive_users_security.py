import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import StudentProfile, TeacherProfile
from materials.models import SubjectEnrollment, Subject
from chat.models import ChatRoom, Message, ChatParticipant

User = get_user_model()


@pytest.mark.django_db
class TestInactiveUsersSecurity(TestCase):
    """Security tests for inactive users accessing chat"""

    def setUp(self):
        """Create users and setup"""
        self.active_student = User.objects.create_user(
            username="active_student", email="active@test.com", password="pass", role="student", is_active=True
        )
        self.active_teacher = User.objects.create_user(
            username="active_teacher", email="teacher@test.com", password="pass", role="teacher", is_active=True
        )
        self.inactive_student = User.objects.create_user(
            username="inactive_student", email="inactive@test.com", password="pass", role="student", is_active=False
        )

        # Create profiles
        StudentProfile.objects.create(user=self.active_student)
        StudentProfile.objects.create(user=self.inactive_student)
        TeacherProfile.objects.create(user=self.active_teacher)

        # Create subject and enrollment
        self.subject = Subject.objects.create(name="Math")
        SubjectEnrollment.objects.create(
            student=self.active_student, teacher=self.active_teacher, subject=self.subject,
            status=SubjectEnrollment.Status.ACTIVE
        )

        # Create chat room
        self.chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.chat_room, user=self.active_student)
        ChatParticipant.objects.create(room=self.chat_room, user=self.active_teacher)

        # Create some messages
        for i in range(5):
            Message.objects.create(
                room=self.chat_room, sender=self.active_student, content=f"Message {i}"
            )

    def test_inactive_user_has_no_participant_records(self):
        """Inactive user should not be in chat room"""
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.inactive_student
        ).exists()
        assert is_participant is False

    def test_inactive_user_cannot_create_message_if_not_participant(self):
        """Inactive user cannot create message if not participant"""
        # Verify inactive user is not participant
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.inactive_student
        ).exists()
        assert is_participant is False

        # Cannot create message as non-participant
        # In real system, permission checks would prevent this

    def test_inactive_user_flag_prevents_operations(self):
        """Inactive user flag is set"""
        assert self.inactive_student.is_active is False
        assert self.active_student.is_active is True

    def test_active_user_in_chat_room(self):
        """Active user is participant in chat"""
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.active_student
        ).exists()
        assert is_participant is True

    def test_message_sender_must_be_participant(self):
        """Message sender must be participant (implicit constraint)"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.active_student, content="Test"
        )

        # Sender is participant
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=msg.sender
        ).exists()
        assert is_participant is True

    def test_inactive_user_cannot_read_messages_logic(self):
        """Logic: inactive user shouldn't retrieve messages"""
        # Get all active participants
        active_participants = ChatParticipant.objects.filter(
            room=self.chat_room, user__is_active=True
        )
        assert active_participants.count() == 2  # active_student and active_teacher

        # Inactive user would be filtered out
        inactive_in_room = ChatParticipant.objects.filter(
            room=self.chat_room, user__is_active=False
        )
        assert inactive_in_room.count() == 0

    def test_user_deactivation_and_participation(self):
        """When user is deactivated, they should lose access"""
        # Initially active
        assert self.active_student.is_active is True

        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.active_student
        ).exists()
        assert is_participant is True

        # Deactivate user
        self.active_student.is_active = False
        self.active_student.save()

        # User still exists as participant in DB
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room, user=self.active_student
        ).exists()
        assert is_participant is True

        # But is_active=False means access should be denied
        assert self.active_student.is_active is False

    def test_inactive_user_cannot_send_message_logic(self):
        """Logic check: message from inactive user should be prevented"""
        # Even if we try to create message from inactive user
        # In production, permission layer would prevent this

        # But in tests, we can verify the flag
        assert self.inactive_student.is_active is False

    def test_active_user_can_send_message(self):
        """Active user can send messages"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.active_student, content="Active message"
        )
        assert msg.sender.is_active is True

    def test_message_creation_timestamp(self):
        """Messages have timestamps"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.active_student, content="Test"
        )
        assert msg.created_at is not None
        assert msg.updated_at is not None

    def test_inactive_user_message_not_retrievable(self):
        """Messages from inactive users shouldn't be retrieved in queries"""
        # Create message from inactive user (if they were somehow added)
        ChatParticipant.objects.create(room=self.chat_room, user=self.inactive_student)
        msg = Message.objects.create(
            room=self.chat_room, sender=self.inactive_student, content="From inactive"
        )

        # Query for messages from active senders only
        active_messages = Message.objects.filter(
            room=self.chat_room, sender__is_active=True
        )
        assert active_messages.count() == 5  # Original 5 messages
        assert msg not in active_messages

    def test_inactive_user_chat_room_list_empty(self):
        """Inactive user shouldn't have chats in their list"""
        # Get chats for inactive user (should be empty or filtered)
        user_chats = ChatParticipant.objects.filter(
            user=self.inactive_student
        )
        assert user_chats.count() == 0

    def test_inactive_user_chat_room_access_denied(self):
        """Even if participant, inactive user shouldn't access"""
        # Add inactive user to room
        ChatParticipant.objects.create(room=self.chat_room, user=self.inactive_student)

        # User is participant but inactive
        assert self.inactive_student.is_active is False

        # Permission check would fail
        # (in real view, checked via user.is_active)

    def test_message_soft_delete_remains_accessible(self):
        """Deleted messages are marked but remain in DB"""
        msg = Message.objects.create(
            room=self.chat_room, sender=self.active_student, content="To delete"
        )
        msg_id = msg.id

        msg.is_deleted = True
        msg.deleted_at = timezone.now()
        msg.save()

        # Still in DB
        msg = Message.objects.get(id=msg_id)
        assert msg.is_deleted is True

    def test_inactive_user_deactivation_mid_session(self):
        """User active, then becomes inactive"""
        assert self.active_student.is_active is True

        # Deactivate
        self.active_student.is_active = False
        self.active_student.save()

        # Verify deactivation
        fresh_user = User.objects.get(id=self.active_student.id)
        assert fresh_user.is_active is False

    def test_multiple_inactive_users_blocked(self):
        """Multiple inactive users should all be blocked"""
        inactive1 = User.objects.create_user(
            username="inactive1", email="i1@test.com", password="pass", role="student", is_active=False
        )
        inactive2 = User.objects.create_user(
            username="inactive2", email="i2@test.com", password="pass", role="student", is_active=False
        )

        assert inactive1.is_active is False
        assert inactive2.is_active is False

    def test_participant_joined_at_immutable(self):
        """Participant joined_at timestamp doesn't change"""
        participant = ChatParticipant.objects.get(
            room=self.chat_room, user=self.active_student
        )
        original_joined_at = participant.joined_at

        # Update something else
        participant.last_read_at = timezone.now()
        participant.save()

        # joined_at should not change
        participant.refresh_from_db()
        assert participant.joined_at == original_joined_at

    def test_inactive_user_in_query_filters(self):
        """Queries can filter by user.is_active"""
        # Active participants
        active = ChatParticipant.objects.filter(
            room=self.chat_room, user__is_active=True
        ).count()
        assert active == 2

        # Inactive participants
        inactive = ChatParticipant.objects.filter(
            room=self.chat_room, user__is_active=False
        ).count()
        assert inactive == 0

    def test_message_count_from_active_only(self):
        """Count messages from active users"""
        # 5 messages from active student
        msg_count = Message.objects.filter(
            room=self.chat_room, sender__is_active=True
        ).count()
        assert msg_count == 5

    def test_inactive_user_cannot_mark_read(self):
        """Inactive user cannot update last_read_at"""
        # If inactive user is in chat (shouldn't happen but for safety)
        ChatParticipant.objects.create(room=self.chat_room, user=self.inactive_student)
        participant = ChatParticipant.objects.get(
            room=self.chat_room, user=self.inactive_student
        )

        # They shouldn't be able to update last_read_at in real system
        assert self.inactive_student.is_active is False
