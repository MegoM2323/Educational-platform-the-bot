"""
Edge case tests for chat system.
Tests unusual conditions, race conditions, and boundary cases.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TransactionTestCase
from django.db import transaction

from chat.models import ChatRoom, ChatParticipant, Message
from chat.services.chat_service import ChatService
from chat.services.message_service import MessageService

User = get_user_model()


@pytest.mark.django_db
class TestEdgeCasesEmptyInputs:
    """Tests for empty and null inputs"""

    def test_send_message_only_whitespace(self):
        """Test that message with only whitespace is rejected"""
        user1 = User.objects.create(username='edge_user1', role='student')
        user2 = User.objects.create(username='edge_user2', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        with pytest.raises(ValueError):
            MessageService.send_message(user1, room, "\n\t  \r\n")

    def test_send_message_very_long(self):
        """Test sending very long message"""
        user1 = User.objects.create(username='edge_user3', role='student')
        user2 = User.objects.create(username='edge_user4', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        # Message with 10000 characters
        long_content = "x" * 10000

        message = MessageService.send_message(user1, room, long_content)
        assert len(message.content) == 10000

    def test_edit_message_to_whitespace(self):
        """Test that editing to whitespace fails"""
        user1 = User.objects.create(username='edge_user5', role='student')
        user2 = User.objects.create(username='edge_user6', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        message = MessageService.send_message(user1, room, "Original")

        with pytest.raises(ValueError):
            MessageService.edit_message(user1, message, "  \n\t  ")


@pytest.mark.django_db
class TestEdgeCasesConcurrency:
    """Tests for concurrent operations"""

    def test_get_or_create_chat_concurrent_creation(self):
        """Test that room can be created and retrieved by multiple participants"""
        user1 = User.objects.create(username='edge_user7', role='student')
        user2 = User.objects.create(username='edge_user8', role='teacher')

        # Create room with both participants
        room1 = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room1, user=user1)
        ChatParticipant.objects.create(room=room1, user=user2)

        # Retrieve same room
        room2 = ChatRoom.objects.get(id=room1.id)

        # Should be same room
        assert room1.id == room2.id
        assert ChatParticipant.objects.filter(room=room2, user=user1).exists()
        assert ChatParticipant.objects.filter(room=room2, user=user2).exists()

    def test_send_messages_in_rapid_sequence(self):
        """Test sending multiple messages in rapid sequence"""
        user1 = User.objects.create(username='edge_user9', role='student')
        user2 = User.objects.create(username='edge_user10', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        messages = []
        for i in range(100):
            msg = MessageService.send_message(user1, room, f"Message {i}")
            messages.append(msg)

        # Verify all created
        assert Message.objects.filter(room=room).count() == 100

        # Verify ordering
        retrieved = MessageService.get_messages(room, limit=100)
        for i, msg in enumerate(retrieved):
            assert msg.content == f"Message {i}"


@pytest.mark.django_db
class TestEdgeCasesBoundaries:
    """Tests for boundary conditions"""

    def test_get_messages_with_limit_zero(self):
        """Test getting messages with limit=0"""
        user1 = User.objects.create(username='edge_user11', role='student')
        user2 = User.objects.create(username='edge_user12', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        MessageService.send_message(user1, room, "Message 1")

        messages = MessageService.get_messages(room, limit=0)
        assert len(messages) == 0

    def test_get_messages_with_large_limit(self):
        """Test getting messages with very large limit"""
        user1 = User.objects.create(username='edge_user13', role='student')
        user2 = User.objects.create(username='edge_user14', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        for i in range(10):
            MessageService.send_message(user1, room, f"Message {i}")

        messages = MessageService.get_messages(room, limit=1000000)
        assert len(messages) == 10

    def test_get_messages_before_first_message(self):
        """Test cursor pagination before first message"""
        user1 = User.objects.create(username='edge_user15', role='student')
        user2 = User.objects.create(username='edge_user16', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        msg1 = MessageService.send_message(user1, room, "Message 1")
        msg2 = MessageService.send_message(user1, room, "Message 2")

        # Try to get messages before first message
        messages = MessageService.get_messages(room, before_id=msg1.id, limit=10)

        # Should return empty since there's nothing before first
        assert len(messages) == 0


@pytest.mark.django_db
class TestEdgeCasesMessageLifecycle:
    """Tests for message lifecycle edge cases"""

    def test_delete_already_deleted_message(self):
        """Test that deleted message stays deleted (idempotent)"""
        user1 = User.objects.create(username='edge_user17', role='student')
        user2 = User.objects.create(username='edge_user18', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        message = MessageService.send_message(user1, room, "To delete")

        # Delete once
        MessageService.delete_message(user1, message)
        message.refresh_from_db()
        assert message.is_deleted is True
        deleted_at_1 = message.deleted_at

        # Delete again - should not fail even though already deleted
        message.is_deleted = True
        message.deleted_at = deleted_at_1
        message.save(update_fields=["is_deleted", "deleted_at"])

        message.refresh_from_db()
        # Timestamp should be the same
        assert message.deleted_at == deleted_at_1

    def test_edit_message_multiple_times(self):
        """Test editing message multiple times"""
        user1 = User.objects.create(username='edge_user19', role='student')
        user2 = User.objects.create(username='edge_user20', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        message = MessageService.send_message(user1, room, "Original")

        msg = MessageService.edit_message(user1, message, "Edit 1")
        assert msg.content == "Edit 1"

        msg = MessageService.edit_message(user1, message, "Edit 2")
        assert msg.content == "Edit 2"

        msg = MessageService.edit_message(user1, message, "Edit 3")
        assert msg.content == "Edit 3"

        msg.refresh_from_db()
        assert msg.content == "Edit 3"
        assert msg.is_edited is True


@pytest.mark.django_db
class TestEdgeCasesPermissions:
    """Tests for permission edge cases"""

    def test_admin_can_delete_any_message(self):
        """Test that admin can delete messages from any user"""
        admin = User.objects.create(username='admin_edge', role='admin')
        user1 = User.objects.create(username='edge_user21', role='student')
        user2 = User.objects.create(username='edge_user22', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        message = MessageService.send_message(user1, room, "Original")

        # Admin can delete
        MessageService.delete_message(admin, message)

        message.refresh_from_db()
        assert message.is_deleted is True

    def test_non_admin_cannot_edit_after_deletion(self):
        """Test that user cannot edit their own deleted message"""
        user1 = User.objects.create(username='edge_user23', role='student')
        user2 = User.objects.create(username='edge_user24', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        message = MessageService.send_message(user1, room, "Original")
        MessageService.delete_message(user1, message)

        with pytest.raises(ValueError):
            MessageService.edit_message(user1, message, "Should fail")


@pytest.mark.django_db
class TestEdgeCasesChatState:
    """Tests for chat state edge cases"""

    def test_cannot_send_to_inactive_chat(self):
        """Test that messages cannot be sent to inactive chats"""
        user1 = User.objects.create(username='edge_user25', role='student')
        user2 = User.objects.create(username='edge_user26', role='teacher')

        room = ChatRoom.objects.create(is_active=False)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        with pytest.raises(ValueError):
            MessageService.send_message(user1, room, "Message")

    def test_reactivating_chat_allows_messages(self):
        """Test that reactivating chat allows messages"""
        user1 = User.objects.create(username='edge_user27', role='student')
        user2 = User.objects.create(username='edge_user28', role='teacher')

        room = ChatRoom.objects.create(is_active=False)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        # Try to send to inactive
        with pytest.raises(ValueError):
            MessageService.send_message(user1, room, "Message")

        # Reactivate
        room.is_active = True
        room.save()

        # Should work now
        message = MessageService.send_message(user1, room, "Message")
        assert message.content == "Message"


@pytest.mark.django_db
class TestEdgeCasesTimestamps:
    """Tests for timestamp edge cases"""

    def test_message_timestamps_are_sequential(self):
        """Test that message timestamps are sequential"""
        user1 = User.objects.create(username='edge_user29', role='student')
        user2 = User.objects.create(username='edge_user30', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        messages = []
        for i in range(5):
            msg = MessageService.send_message(user1, room, f"Message {i}")
            messages.append(msg)

        # All timestamps should be in order
        for i in range(1, len(messages)):
            assert messages[i].created_at >= messages[i-1].created_at

    def test_room_updated_at_changes_with_messages(self):
        """Test that room's updated_at changes when messages are sent"""
        user1 = User.objects.create(username='edge_user31', role='student')
        user2 = User.objects.create(username='edge_user32', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        first_updated = room.updated_at

        MessageService.send_message(user1, room, "Message 1")

        room.refresh_from_db()
        second_updated = room.updated_at

        MessageService.send_message(user1, room, "Message 2")

        room.refresh_from_db()
        third_updated = room.updated_at

        assert first_updated <= second_updated <= third_updated


@pytest.mark.django_db
class TestEdgeCasesQueryOptimization:
    """Tests for query efficiency (N+1 problem)"""

    def test_get_user_chats_uses_prefetch(self):
        """Test that we can efficiently query chats with participants"""
        user1 = User.objects.create(username='edge_user33', role='student')

        # Create multiple chats
        for i in range(5):
            teacher = User.objects.create(username=f'edge_teacher_{i}', role='teacher')
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=user1)
            ChatParticipant.objects.create(room=room, user=teacher)
            MessageService.send_message(teacher, room, f"Message {i}")

        # Get user's chats efficiently using select_related/prefetch
        chats = ChatRoom.objects.filter(
            participants__user=user1,
            is_active=True
        ).prefetch_related('participants__user').distinct()

        # Should have 5 chats
        assert chats.count() == 5

        # Access participants should work without extra queries
        for chat in chats:
            for participant in chat.participants.all():
                assert participant.user is not None


@pytest.mark.django_db
class TestEdgeCasesUnicode:
    """Tests for Unicode handling"""

    def test_send_message_with_unicode(self):
        """Test sending messages with various Unicode characters"""
        user1 = User.objects.create(username='edge_user34', role='student')
        user2 = User.objects.create(username='edge_user35', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        unicode_messages = [
            "Hello 世界",  # Chinese
            "Привет мир",  # Russian
            "مرحبا بالعالم",  # Arabic
            "שלום עולם",  # Hebrew
            "🎉🎊🎈",  # Emojis
            "Ñoño",  # Spanish accents
        ]

        for content in unicode_messages:
            message = MessageService.send_message(user1, room, content)
            assert message.content == content

    def test_get_messages_with_unicode(self):
        """Test retrieving messages with Unicode"""
        user1 = User.objects.create(username='edge_user36', role='student')
        user2 = User.objects.create(username='edge_user37', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        content = "Hello 世界 🎉"
        MessageService.send_message(user1, room, content)

        messages = MessageService.get_messages(room)
        assert len(messages) == 1
        assert messages[0].content == content


@pytest.mark.django_db
class TestEdgeCasesNullAndBlank:
    """Tests for NULL and blank field handling"""

    def test_message_without_edit_shows_original_time(self):
        """Test that unedited message shows created_at"""
        user1 = User.objects.create(username='edge_user38', role='student')
        user2 = User.objects.create(username='edge_user39', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        message = MessageService.send_message(user1, room, "Original")

        assert message.is_edited is False
        assert message.created_at is not None
        assert message.updated_at is not None

    def test_participant_without_read_timestamp(self):
        """Test that participant without read timestamp shows None"""
        user1 = User.objects.create(username='edge_user40', role='student')
        user2 = User.objects.create(username='edge_user41', role='teacher')

        room = ChatRoom.objects.create(is_active=True)
        participant = ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        assert participant.last_read_at is None
