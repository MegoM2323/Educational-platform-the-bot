"""
Core functionality tests for Forum (Chat) module.
Tests WebSocket, Messages, Chat operations.
"""
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from accounts.models import User
from chat.models import ChatRoom, Message


class ChatRoomModelTests(TestCase):
    """Tests for ChatRoom model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    def test_create_direct_chat(self):
        """Test creating a direct chat room"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )

        self.assertEqual(chat.name, "Test Chat")
        self.assertEqual(chat.type, ChatRoom.Type.DIRECT)
        self.assertEqual(chat.created_by, self.user)
        self.assertTrue(chat.is_active)

    def test_create_group_chat(self):
        """Test creating a group chat room"""
        chat = ChatRoom.objects.create(
            name="Group Chat",
            type=ChatRoom.Type.GROUP,
            created_by=self.user,
            description="Test group",
        )

        self.assertEqual(chat.type, ChatRoom.Type.GROUP)
        self.assertEqual(chat.description, "Test group")

    def test_add_participants(self):
        """Test adding participants to chat"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        chat.participants.add(self.user, user2)

        self.assertEqual(chat.participants.count(), 2)
        self.assertIn(self.user, chat.participants.all())
        self.assertIn(user2, chat.participants.all())

    def test_auto_delete_days_default(self):
        """Test default auto_delete_days value"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )

        self.assertEqual(chat.auto_delete_days, 7)

    def test_auto_delete_days_custom(self):
        """Test custom auto_delete_days value"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
            auto_delete_days=30,
        )

        self.assertEqual(chat.auto_delete_days, 30)

    def test_chat_timestamps(self):
        """Test chat room timestamps"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )

        self.assertIsNotNone(chat.created_at)
        self.assertIsNotNone(chat.updated_at)
        self.assertEqual(chat.created_at, chat.updated_at)


class MessageModelTests(TestCase):
    """Tests for Message model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )

    def test_create_message(self):
        """Test creating a chat message"""
        message = Message.objects.create(
            chat_room=self.chat,
            author=self.user,
            content="Hello, world!",
        )

        self.assertEqual(message.content, "Hello, world!")
        self.assertEqual(message.author, self.user)
        self.assertEqual(message.chat_room, self.chat)

    def test_message_timestamps(self):
        """Test message timestamps"""
        message = Message.objects.create(
            chat_room=self.chat,
            author=self.user,
            content="Test message",
        )

        self.assertIsNotNone(message.created_at)
        self.assertIsNotNone(message.updated_at)

    def test_message_default_read_status(self):
        """Test message read status defaults to False"""
        message = Message.objects.create(
            chat_room=self.chat,
            author=self.user,
            content="Test message",
        )

        self.assertFalse(message.is_read)

    def test_mark_message_as_read(self):
        """Test marking message as read"""
        message = Message.objects.create(
            chat_room=self.chat,
            author=self.user,
            content="Test message",
        )
        message.is_read = True
        message.save()

        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_message_with_emoji(self):
        """Test message with emoji"""
        message = Message.objects.create(
            chat_room=self.chat,
            author=self.user,
            content="Hello 👋 This is a test 🎉",
        )

        self.assertIn("👋", message.content)
        self.assertIn("🎉", message.content)

    def test_message_with_long_content(self):
        """Test message with long content"""
        long_content = "A" * 5000
        message = Message.objects.create(
            chat_room=self.chat,
            author=self.user,
            content=long_content,
        )

        self.assertEqual(len(message.content), 5000)


class ChatOperationsTests(TestCase):
    """Tests for common chat operations"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        self.chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        self.chat.participants.add(self.user1, self.user2)

    def test_get_chat_messages_ordered(self):
        """Test that messages are ordered by creation time"""
        msg1 = Message.objects.create(
            chat_room=self.chat,
            author=self.user1,
            content="First message",
        )
        msg2 = Message.objects.create(
            chat_room=self.chat,
            author=self.user2,
            content="Second message",
        )

        messages = Message.objects.filter(chat_room=self.chat).order_by("created_at")
        self.assertEqual(list(messages), [msg1, msg2])

    def test_count_unread_messages(self):
        """Test counting unread messages"""
        Message.objects.create(
            chat_room=self.chat,
            author=self.user1,
            content="Message 1",
        )
        Message.objects.create(
            chat_room=self.chat,
            author=self.user1,
            content="Message 2",
        )
        read_msg = Message.objects.create(
            chat_room=self.chat,
            author=self.user1,
            content="Message 3",
        )
        read_msg.is_read = True
        read_msg.save()

        unread_count = Message.objects.filter(
            chat_room=self.chat,
            is_read=False,
        ).count()

        self.assertEqual(unread_count, 2)

    def test_delete_old_messages(self):
        """Test deleting messages older than auto_delete_days"""
        # Create messages with different timestamps
        old_date = timezone.now() - timedelta(days=10)
        recent_date = timezone.now() - timedelta(days=3)

        # Create old message
        old_msg = Message.objects.create(
            chat_room=self.chat,
            author=self.user1,
            content="Old message",
        )
        old_msg.created_at = old_date
        old_msg.save()

        # Create recent message
        recent_msg = Message.objects.create(
            chat_room=self.chat,
            author=self.user2,
            content="Recent message",
        )

        # Simulate auto-delete
        cutoff_date = timezone.now() - timedelta(days=self.chat.auto_delete_days)
        deleted_count, _ = Message.objects.filter(
            chat_room=self.chat,
            created_at__lt=cutoff_date,
        ).delete()

        remaining = Message.objects.filter(chat_room=self.chat)
        self.assertEqual(remaining.count(), 1)
        self.assertEqual(remaining.first().id, recent_msg.id)

    def test_get_participants_list(self):
        """Test getting participants list"""
        participants = list(self.chat.participants.all())

        self.assertEqual(len(participants), 2)
        self.assertIn(self.user1, participants)
        self.assertIn(self.user2, participants)

    def test_remove_participant(self):
        """Test removing participant from chat"""
        self.chat.participants.remove(self.user1)

        self.assertEqual(self.chat.participants.count(), 1)
        self.assertNotIn(self.user1, self.chat.participants.all())
        self.assertIn(self.user2, self.chat.participants.all())

    def test_deactivate_chat(self):
        """Test deactivating a chat"""
        self.chat.is_active = False
        self.chat.save()

        self.chat.refresh_from_db()
        self.assertFalse(self.chat.is_active)

    def test_active_chats_filter(self):
        """Test filtering active chats"""
        inactive_chat = ChatRoom.objects.create(
            name="Inactive Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
            is_active=False,
        )

        active_chats = ChatRoom.objects.filter(is_active=True)

        self.assertEqual(active_chats.count(), 1)
        self.assertIn(self.chat, active_chats)
        self.assertNotIn(inactive_chat, active_chats)


class ChatDataIsolationTests(TestCase):
    """Tests for data isolation between users"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.user3 = User.objects.create_user(
            username="user3",
            email="user3@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    def test_user_sees_only_their_chats(self):
        """Test that users only see their chats"""
        chat1 = ChatRoom.objects.create(
            name="Chat 1",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        chat1.participants.add(self.user1, self.user2)

        chat2 = ChatRoom.objects.create(
            name="Chat 2",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user3,
        )
        chat2.participants.add(self.user3)

        user1_chats = self.user1.chat_rooms.all()
        user3_chats = self.user3.chat_rooms.all()

        self.assertIn(chat1, user1_chats)
        self.assertNotIn(chat2, user1_chats)
        self.assertNotIn(chat1, user3_chats)
        self.assertIn(chat2, user3_chats)

    def test_user_sees_only_their_messages(self):
        """Test that users can read all messages in their chat"""
        chat = ChatRoom.objects.create(
            name="Shared Chat",
            type=ChatRoom.Type.GROUP,
            created_by=self.user1,
        )
        chat.participants.add(self.user1, self.user2, self.user3)

        Message.objects.create(
            chat_room=chat,
            author=self.user1,
            content="User1 message",
        )
        Message.objects.create(
            chat_room=chat,
            author=self.user2,
            content="User2 message",
        )
        Message.objects.create(
            chat_room=chat,
            author=self.user3,
            content="User3 message",
        )

        chat_messages = Message.objects.filter(chat_room=chat)
        self.assertEqual(chat_messages.count(), 3)

    def test_unlinked_user_cannot_see_chat(self):
        """Test that non-participants can't access chat"""
        chat = ChatRoom.objects.create(
            name="Private Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        chat.participants.add(self.user1, self.user2)

        # user3 is not a participant
        self.assertNotIn(self.user3, chat.participants.all())
        self.assertNotIn(chat, self.user3.chat_rooms.all())
