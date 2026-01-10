"""
Unit tests for Chat cascade and NULL handling (C3).
"""

import pytest
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.test import TestCase
from chat.models import ChatRoom, ChatParticipant, Message

User = get_user_model()


class ChatCascadeTests(TestCase):
    """Test Chat cascade constraints."""

    def setUp(self):
        """Create test fixtures."""
        self.room = ChatRoom.objects.create(is_active=True)
        self.user1 = User.objects.create(
            username="user1",
            first_name="Alice",
            last_name="Chat",
            role="student"
        )
        self.user2 = User.objects.create(
            username="user2",
            first_name="Bob",
            last_name="Chat",
            role="teacher"
        )

    def test_cannot_delete_user_with_chat_participants(self):
        """User cannot be deleted if they are a chat participant - ProtectedError."""
        participant = ChatParticipant.objects.create(
            room=self.room,
            user=self.user1
        )

        with self.assertRaises(ProtectedError):
            self.user1.delete()

        # Verify user and participant still exist
        self.assertTrue(User.objects.filter(id=self.user1.id).exists())
        self.assertTrue(ChatParticipant.objects.filter(id=participant.id).exists())

    def test_message_sender_can_be_null(self):
        """Message.sender can be NULL when sender is deleted (SET_NULL)."""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Hello",
            message_type="text"
        )

        message_id = message.id
        user_id = self.user1.id

        # Delete the user (no ProtectedError since Message uses SET_NULL)
        self.user1.delete()

        # User should be deleted
        self.assertFalse(User.objects.filter(id=user_id).exists())

        # Message should still exist with sender=None
        message.refresh_from_db()
        self.assertIsNone(message.sender)

    def test_deleted_user_messages_preserved(self):
        """Messages from deleted user are preserved."""
        messages = [
            Message.objects.create(
                room=self.room,
                sender=self.user1,
                content="Message {}".format(i),
                message_type="text"
            )
            for i in range(3)
        ]

        self.user1.delete()

        # All messages should still exist
        for i, msg in enumerate(messages):
            msg.refresh_from_db()
            self.assertIsNone(msg.sender)

    def test_message_str_handles_null_sender(self):
        """Message.__str__() handles null sender without error."""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Test message",
            message_type="text"
        )

        self.user1.delete()
        message.refresh_from_db()

        # Should not raise error
        message_str = str(message)
        self.assertIn("(Deleted User)", message_str)
        self.assertIn("Message", message_str)

    def test_deleting_room_deletes_all_messages(self):
        """ChatRoom deletion cascades to delete all messages."""
        msg1 = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Message 1"
        )
        msg2 = Message.objects.create(
            room=self.room,
            sender=self.user2,
            content="Message 2"
        )

        room_id = self.room.id
        self.room.delete()

        self.assertFalse(ChatRoom.objects.filter(id=room_id).exists())
        self.assertEqual(Message.objects.filter(room_id=room_id).count(), 0)
