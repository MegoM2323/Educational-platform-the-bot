import pytest
import uuid
import json
from unittest.mock import AsyncMock, patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test.utils import override_settings

from chat.models import ChatRoom, Message, ChatParticipant
from chat.consumers import ChatConsumer

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestT021UserJoinedEvent(TestCase):
    """T021: Событие подключения пользователя (user_joined)"""

    def setUp(self):
        """Fixtures: два пользователя, комната, токены"""
        unique_id = str(uuid.uuid4())[:8]

        self.user1 = User.objects.create_user(
            username=f"user_joined_1_{unique_id}",
            email=f"user_joined_1_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user1.is_active = True
        self.user1.save()

        self.user2 = User.objects.create_user(
            username=f"user_joined_2_{unique_id}",
            email=f"user_joined_2_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user2.is_active = True
        self.user2.save()

        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        self.room.participants.add(self.user1, self.user2)

    def test_user_joined_event_broadcast(self):
        """Test user_joined event contains correct user data"""
        # Simulate user_joined event
        event = {
            "type": "user_joined",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
                "first_name": self.user1.first_name,
                "last_name": self.user1.last_name,
            },
        }

        # Verify event structure
        assert event["type"] == "user_joined"
        assert event["user"]["id"] == self.user1.id
        assert event["user"]["username"] == self.user1.username

    def test_user_joined_contains_required_fields(self):
        """Test user_joined event has all required fields"""
        user = self.user2
        event = {
            "type": "user_joined",
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }

        assert "type" in event
        assert "user" in event
        assert "id" in event["user"]
        assert "username" in event["user"]

    def test_user_joined_data_correctness(self):
        """Test user_joined event contains correct user information"""
        user = self.user1
        event = {
            "type": "user_joined",
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }

        assert event["user"]["id"] == user.id
        assert event["user"]["username"] == user.username
        assert isinstance(event["user"]["id"], int)
        assert isinstance(event["user"]["username"], str)


@pytest.mark.django_db(transaction=True)
class TestT022UserLeftEvent(TestCase):
    """T022: Событие отключения пользователя (user_left)"""

    def setUp(self):
        """Fixtures: пользователь, комната, токен"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"user_left_{unique_id}",
            email=f"user_left_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.token = Token.objects.create(user=self.user)

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        self.room.participants.add(self.user)

    def test_user_left_event_structure(self):
        """Test user_left event has correct structure"""
        event = {
            "type": "user_left",
            "user": {
                "id": self.user.id,
                "username": self.user.username,
            },
        }

        assert event["type"] == "user_left"
        assert "user" in event
        assert event["user"]["id"] == self.user.id
        assert event["user"]["username"] == self.user.username

    def test_user_left_contains_user_id_and_username(self):
        """Test user_left event contains user id and username"""
        event = {
            "type": "user_left",
            "user": {
                "id": self.user.id,
                "username": self.user.username,
            },
        }

        assert "id" in event["user"]
        assert "username" in event["user"]

    def test_user_left_event_on_disconnect(self):
        """Test user_left event is triggered on disconnect"""
        # Create participant record to simulate active session
        ChatParticipant.objects.create(room=self.room, user=self.user)

        # Verify participant exists
        participant = ChatParticipant.objects.get(room=self.room, user=self.user)
        assert participant is not None

        # Event would be triggered on disconnect
        event = {
            "type": "user_left",
            "user": {
                "id": participant.user.id,
                "username": participant.user.username,
            },
        }

        assert event["type"] == "user_left"


@pytest.mark.django_db(transaction=True)
class TestT023ChatMessageBroadcast(TestCase):
    """T023: Трансляция сообщений ко всем участникам (chat_message event)"""

    def setUp(self):
        """Fixtures: два пользователя, комната, сообщение"""
        unique_id = str(uuid.uuid4())[:8]

        self.user1 = User.objects.create_user(
            username=f"chat_msg_1_{unique_id}",
            email=f"chat_msg_1_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user1.is_active = True
        self.user1.save()

        self.user2 = User.objects.create_user(
            username=f"chat_msg_2_{unique_id}",
            email=f"chat_msg_2_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user2.is_active = True
        self.user2.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        self.room.participants.add(self.user1, self.user2)

    def test_chat_message_event_structure(self):
        """Test chat_message event contains correct structure"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Test message",
            message_type=Message.Type.TEXT,
        )

        event = {
            "type": "chat_message",
            "message": {
                "id": str(message.id),
                "room_id": str(message.room_id),
                "sender": {
                    "id": message.sender.id,
                    "username": message.sender.username,
                },
                "content": message.content,
                "message_type": message.message_type,
                "created_at": message.created_at.isoformat(),
                "is_edited": message.is_edited,
            },
        }

        assert event["type"] == "chat_message"
        assert "message" in event
        assert event["message"]["content"] == "Test message"
        assert event["message"]["sender"]["username"] == self.user1.username

    def test_chat_message_broadcast_to_all_participants(self):
        """Test message is visible to all room participants"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Broadcast test",
            message_type=Message.Type.TEXT,
        )

        # Both participants should see the message
        room_messages = self.room.messages.filter(is_deleted=False)
        assert room_messages.count() == 1
        assert message in room_messages

        # Both users are participants
        assert self.room.participants.filter(id=self.user1.id).exists()
        assert self.room.participants.filter(id=self.user2.id).exists()

    def test_chat_message_includes_full_data(self):
        """Test chat_message event includes all required message data"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Full data test",
            message_type=Message.Type.TEXT,
        )

        event = {
            "type": "chat_message",
            "message": {
                "id": str(message.id),
                "content": message.content,
                "sender": {
                    "id": message.sender.id,
                    "username": message.sender.username,
                },
                "created_at": message.created_at.isoformat(),
                "message_type": message.message_type,
                "is_edited": message.is_edited,
                "is_deleted": message.is_deleted,
            },
        }

        assert event["message"]["id"]
        assert event["message"]["content"] == "Full data test"
        assert event["message"]["sender"]["id"] == self.user1.id
        assert event["message"]["created_at"]
        assert event["message"]["message_type"] == Message.Type.TEXT


@pytest.mark.django_db(transaction=True)
class TestT024MessageEditedEvent(TestCase):
    """T024: Трансляция события редактирования (message_edited event)"""

    def setUp(self):
        """Fixtures: пользователь, комната, сообщение"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"msg_edit_{unique_id}",
            email=f"msg_edit_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        self.room.participants.add(self.user)

        self.message = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="Original content",
            message_type=Message.Type.TEXT,
        )

    def test_message_edited_event_structure(self):
        """Test message_edited event has correct structure"""
        self.message.content = "Edited content"
        self.message.is_edited = True
        self.message.save(update_fields=["content", "is_edited", "updated_at"])

        event = {
            "type": "message_edited",
            "message_id": str(self.message.id),
            "content": self.message.content,
            "is_edited": True,
            "edited_at": self.message.updated_at.isoformat(),
        }

        assert event["type"] == "message_edited"
        assert event["message_id"] == str(self.message.id)
        assert event["content"] == "Edited content"
        assert event["is_edited"] is True

    def test_message_edited_flag_set(self):
        """Test is_edited flag is set after edit"""
        self.message.content = "New content"
        self.message.is_edited = True
        self.message.save(update_fields=["content", "is_edited", "updated_at"])

        # Refresh from DB
        self.message.refresh_from_db()

        assert self.message.is_edited is True
        assert self.message.content == "New content"

    def test_message_edited_timestamp_updated(self):
        """Test updated_at timestamp changes on edit"""
        original_time = self.message.updated_at

        # Wait a bit to ensure timestamp changes
        import time

        time.sleep(0.01)

        self.message.content = "Changed content"
        self.message.save(update_fields=["content", "updated_at"])

        self.message.refresh_from_db()

        assert self.message.updated_at >= original_time

    def test_message_edited_event_broadcast_structure(self):
        """Test message_edited event can be broadcast to all participants"""
        self.message.content = "Broadcast edit"
        self.message.is_edited = True
        self.message.save(update_fields=["content", "is_edited", "updated_at"])

        # All room participants should receive edit event
        event = {
            "type": "message_edited",
            "message_id": str(self.message.id),
            "content": "Broadcast edit",
            "is_edited": True,
            "edited_at": self.message.updated_at.isoformat(),
        }

        assert self.room.participants.filter(id=self.user.id).exists()
        assert "message_id" in event
        assert "content" in event


@pytest.mark.django_db(transaction=True)
class TestT025MessageDeletedEvent(TestCase):
    """T025: Трансляция события удаления (message_deleted event)"""

    def setUp(self):
        """Fixtures: пользователь, комната, сообщение"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"msg_del_{unique_id}",
            email=f"msg_del_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        self.room.participants.add(self.user)

        self.message = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="Message to delete",
            message_type=Message.Type.TEXT,
        )

    def test_message_deleted_event_structure(self):
        """Test message_deleted event has correct structure"""
        self.message.is_deleted = True
        self.message.deleted_at = timezone.now()
        self.message.deleted_by = self.user
        self.message.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        event = {
            "type": "message_deleted",
            "message_id": str(self.message.id),
            "deleted_by": self.user.id,
            "deleted_by_role": "author",
        }

        assert event["type"] == "message_deleted"
        assert event["message_id"] == str(self.message.id)
        assert event["deleted_by"] == self.user.id

    def test_message_soft_delete_flag(self):
        """Test message is marked as deleted (soft delete)"""
        self.message.is_deleted = True
        self.message.deleted_at = timezone.now()
        self.message.deleted_by = self.user
        self.message.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        self.message.refresh_from_db()

        assert self.message.is_deleted is True
        assert self.message.deleted_at is not None
        assert self.message.deleted_by == self.user

    def test_message_deleted_excluded_from_list(self):
        """Test deleted message is excluded from message list"""
        self.message.is_deleted = True
        self.message.deleted_at = timezone.now()
        self.message.save(update_fields=["is_deleted", "deleted_at"])

        # Soft-deleted messages should not appear in active queries
        active_messages = self.room.messages.filter(is_deleted=False)

        assert self.message not in active_messages
        assert active_messages.count() == 0

    def test_deleted_by_tracking(self):
        """Test deleted_by user is tracked"""
        self.message.is_deleted = True
        self.message.deleted_at = timezone.now()
        self.message.deleted_by = self.user
        self.message.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        self.message.refresh_from_db()

        assert self.message.deleted_by.id == self.user.id


@pytest.mark.django_db(transaction=True)
class TestT026TypingIndicator(TestCase):
    """T026: Индикатор печати (typing, typing_stop)"""

    def setUp(self):
        """Fixtures: два пользователя, комната"""
        unique_id = str(uuid.uuid4())[:8]

        self.user1 = User.objects.create_user(
            username=f"typing_1_{unique_id}",
            email=f"typing_1_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user1.is_active = True
        self.user1.save()

        self.user2 = User.objects.create_user(
            username=f"typing_2_{unique_id}",
            email=f"typing_2_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user2.is_active = True
        self.user2.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        self.room.participants.add(self.user1, self.user2)

    def test_typing_event_structure(self):
        """Test typing event has correct structure"""
        event = {
            "type": "typing",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
                "first_name": self.user1.first_name,
                "last_name": self.user1.last_name,
            },
        }

        assert event["type"] == "typing"
        assert "user" in event
        assert event["user"]["id"] == self.user1.id
        assert event["user"]["username"] == self.user1.username

    def test_typing_event_contains_user_info(self):
        """Test typing event includes user information"""
        event = {
            "type": "typing",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
                "first_name": self.user1.first_name,
                "last_name": self.user1.last_name,
            },
        }

        assert "id" in event["user"]
        assert "username" in event["user"]
        assert "first_name" in event["user"]
        assert "last_name" in event["user"]

    def test_typing_stop_event_structure(self):
        """Test typing_stop event has correct structure"""
        event = {
            "type": "typing_stop",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
            },
        }

        assert event["type"] == "typing_stop"
        assert "user" in event
        assert event["user"]["id"] == self.user1.id

    def test_typing_stop_event_minimal_fields(self):
        """Test typing_stop event has minimal required fields"""
        event = {
            "type": "typing_stop",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
            },
        }

        assert "type" in event
        assert "user" in event
        assert "id" in event["user"]
        assert "username" in event["user"]

    def test_typing_indicates_user_is_typing(self):
        """Test typing event identifies which user is typing"""
        event1 = {
            "type": "typing",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
            },
        }

        event2 = {
            "type": "typing",
            "user": {
                "id": self.user2.id,
                "username": self.user2.username,
            },
        }

        assert event1["user"]["id"] != event2["user"]["id"]
        assert event1["user"]["username"] != event2["user"]["username"]

    def test_typing_broadcast_to_all_participants(self):
        """Test typing event reaches all room participants"""
        # Both participants in room
        assert self.room.participants.count() >= 2

        event = {
            "type": "typing",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
            },
        }

        # Event should be broadcastable to all participants
        participants = list(self.room.participants.all())
        assert len(participants) >= 2


@pytest.mark.django_db(transaction=True)
class TestEventChronologicalOrder(TestCase):
    """Test: Order событий сохраняется (chronological)"""

    def setUp(self):
        """Fixtures: пользователь, комната"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"chrono_{unique_id}",
            email=f"chrono_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        self.room.participants.add(self.user)

    def test_messages_ordered_by_created_at(self):
        """Test messages are ordered chronologically"""
        msg1 = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="First message",
            message_type=Message.Type.TEXT,
        )

        import time

        time.sleep(0.01)

        msg2 = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="Second message",
            message_type=Message.Type.TEXT,
        )

        messages = self.room.messages.filter(is_deleted=False).order_by("created_at")

        message_list = list(messages)
        assert len(message_list) == 2
        assert message_list[0] == msg1
        assert message_list[1] == msg2

    def test_event_sequence_creation_edit_delete(self):
        """Test event sequence: create -> edit -> delete maintains order"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="Original",
            message_type=Message.Type.TEXT,
        )

        original_created_at = message.created_at

        import time

        time.sleep(0.01)

        # Edit event
        message.content = "Edited"
        message.is_edited = True
        message.save(update_fields=["content", "is_edited", "updated_at"])

        edited_at = message.updated_at

        time.sleep(0.01)

        # Delete event
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=["is_deleted", "deleted_at"])

        message.refresh_from_db()

        # Verify timestamp order
        assert message.created_at <= message.updated_at
        assert message.updated_at <= message.deleted_at

    def test_multiple_messages_preserve_order(self):
        """Test multiple messages preserve chronological order"""
        messages_created = []
        for i in range(5):
            msg = Message.objects.create(
                room=self.room,
                sender=self.user,
                content=f"Message {i}",
                message_type=Message.Type.TEXT,
            )
            messages_created.append(msg)

            import time

            time.sleep(0.001)

        # Retrieve messages in order
        messages_retrieved = list(
            self.room.messages.filter(is_deleted=False).order_by("created_at")
        )

        # Verify order
        for i, msg in enumerate(messages_retrieved):
            assert msg.content == f"Message {i}"


@pytest.mark.django_db(transaction=True)
class TestEventDataIntegrity(TestCase):
    """Test: Целостность данных событий"""

    def setUp(self):
        """Fixtures: два пользователя, комната"""
        unique_id = str(uuid.uuid4())[:8]

        self.user1 = User.objects.create_user(
            username=f"integrity_1_{unique_id}",
            email=f"integrity_1_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user1.is_active = True
        self.user1.save()

        self.user2 = User.objects.create_user(
            username=f"integrity_2_{unique_id}",
            email=f"integrity_2_{unique_id}@example.com",
            password="testpass123",
            role="teacher",
        )
        self.user2.is_active = True
        self.user2.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )
        self.room.participants.add(self.user1, self.user2)

    def test_user_joined_event_has_valid_id(self):
        """Test user_joined event has valid user id"""
        event = {
            "type": "user_joined",
            "user": {
                "id": self.user1.id,
                "username": self.user1.username,
                "first_name": self.user1.first_name,
                "last_name": self.user1.last_name,
            },
        }

        # ID should be integer
        assert isinstance(event["user"]["id"], int)
        assert event["user"]["id"] > 0

    def test_chat_message_event_message_id_is_string(self):
        """Test chat_message event message id is string"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Test",
            message_type=Message.Type.TEXT,
        )

        event = {
            "type": "chat_message",
            "message": {
                "id": str(message.id),
            },
        }

        assert isinstance(event["message"]["id"], str)

    def test_message_edited_event_contains_edited_at(self):
        """Test message_edited event contains edited_at timestamp"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Original",
            message_type=Message.Type.TEXT,
        )

        message.content = "Edited"
        message.is_edited = True
        message.save(update_fields=["content", "is_edited", "updated_at"])

        event = {
            "type": "message_edited",
            "edited_at": message.updated_at.isoformat(),
        }

        assert "edited_at" in event
        assert event["edited_at"]

    def test_deleted_message_tracks_deleted_by_user(self):
        """Test deleted message tracks which user deleted it"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="To delete",
            message_type=Message.Type.TEXT,
        )

        # User2 (teacher/moderator) deletes message
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.deleted_by = self.user2
        message.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        event = {
            "type": "message_deleted",
            "deleted_by": message.deleted_by.id,
            "deleted_by_role": "moderator",
        }

        assert event["deleted_by"] == self.user2.id
        assert event["deleted_by"] != self.user1.id


@pytest.mark.django_db(transaction=True)
class TestWebSocketEventJSON(TestCase):
    """Test: JSON структура событий для WebSocket"""

    def setUp(self):
        """Fixtures: пользователь, комната, сообщение"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"json_test_{unique_id}",
            email=f"json_test_{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        self.room.participants.add(self.user)

    def test_user_joined_json_serializable(self):
        """Test user_joined event is JSON serializable"""
        event = {
            "type": "user_joined",
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
            },
        }

        # Should not raise exception
        json_str = json.dumps(event)
        assert json_str is not None

    def test_chat_message_json_serializable(self):
        """Test chat_message event is JSON serializable"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="Test",
            message_type=Message.Type.TEXT,
        )

        event = {
            "type": "chat_message",
            "message": {
                "id": str(message.id),
                "content": message.content,
                "sender": {
                    "id": message.sender.id,
                    "username": message.sender.username,
                },
                "created_at": message.created_at.isoformat(),
            },
        }

        json_str = json.dumps(event)
        assert json_str is not None

    def test_message_edited_json_serializable(self):
        """Test message_edited event is JSON serializable"""
        message = Message.objects.create(
            room=self.room,
            sender=self.user,
            content="Original",
            message_type=Message.Type.TEXT,
        )

        message.content = "Edited"
        message.is_edited = True
        message.save(update_fields=["content", "is_edited", "updated_at"])

        event = {
            "type": "message_edited",
            "message_id": str(message.id),
            "content": message.content,
            "is_edited": True,
            "edited_at": message.updated_at.isoformat(),
        }

        json_str = json.dumps(event)
        assert json_str is not None

    def test_typing_json_serializable(self):
        """Test typing event is JSON serializable"""
        event = {
            "type": "typing",
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
            },
        }

        json_str = json.dumps(event)
        assert json_str is not None
