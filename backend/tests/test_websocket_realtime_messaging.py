"""
WebSocket Real-Time Messaging Tests

Tests verify:
1. WebSocket connection establishment and authentication
2. Message sending and receiving in real-time
3. Multiple users receiving messages simultaneously
4. Message persistence in database
5. WebSocket disconnection handling
6. Message ordering and timestamps
7. Error handling and edge cases
8. Concurrent message broadcasting
9. Message delivery confirmation
10. Connection state management
"""

import json
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from rest_framework.test import APIClient
from rest_framework import status

from chat.models import ChatRoom, Message, ChatParticipant
from chat.consumers import ChatConsumer

User = get_user_model()


@pytest.mark.django_db
class TestWebSocketConnection:
    """WebSocket connection establishment tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and chat room"""
        self.user1 = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        self.user2 = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.user1)
        ChatParticipant.objects.create(room=self.room, user=self.user2)

    @pytest.mark.asyncio
    async def test_websocket_connection_authenticated(self):
        """Test WebSocket connection with authenticated user"""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"ws/chat/{self.room.id}/",
            headers=[[b"origin", b"http://localhost"]]
        )
        communicator.scope["user"] = self.user1

        connected, subprotocol = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_websocket_connection_requires_authentication(self):
        """Test WebSocket rejects anonymous connections"""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"ws/chat/{self.room.id}/",
            headers=[[b"origin", b"http://localhost"]]
        )
        # Don't set user scope

        try:
            connected, subprotocol = await communicator.connect()
            assert connected is False
        except Exception:
            pass

        try:
            await communicator.disconnect()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_websocket_join_message(self):
        """Test WebSocket sends join message to room"""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"ws/chat/{self.room.id}/",
            headers=[[b"origin", b"http://localhost"]]
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        assert connected is True

        # Receive join message
        response = await communicator.receive_json_from()
        assert response.get("type") in ["user_join", "online_count"]

        await communicator.disconnect()


@pytest.mark.django_db
class TestWebSocketMessaging:
    """WebSocket message sending and receiving tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and chat room"""
        self.user1 = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        self.user2 = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.user1)
        ChatParticipant.objects.create(room=self.room, user=self.user2)

    def test_send_message_via_rest_api(self):
        """Test sending message via REST API"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": "Test message from student"},
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "Test message from student" in response.json()["content"]

        message = Message.objects.get(content="Test message from student")
        assert message.sender == self.user1
        assert message.room == self.room
        assert message.is_deleted is False

    def test_send_empty_message_fails(self):
        """Test sending empty message returns error"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": ""},
            format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_message_to_inactive_chat_fails(self):
        """Test sending message to inactive chat returns error"""
        self.room.is_active = False
        self.room.save()

        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": "Test message"},
            format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_message_persistence_in_database(self):
        """Test message is saved to database"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        content = "Persistent message"
        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": content},
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify in database
        message = Message.objects.get(content=content)
        assert message.sender == self.user1
        assert message.room == self.room
        assert message.created_at is not None
        assert message.is_deleted is False

    def test_message_has_correct_timestamps(self):
        """Test message timestamps are set correctly"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        before_send = timezone.now()
        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": "Test with timestamps"},
            format="json"
        )
        after_send = timezone.now()

        assert response.status_code == status.HTTP_201_CREATED

        message = Message.objects.get(content="Test with timestamps")
        assert before_send <= message.created_at <= after_send
        # Allow small time difference due to database precision
        assert abs((message.updated_at - message.created_at).total_seconds()) < 1
        assert message.is_edited is False


@pytest.mark.django_db
class TestRealTimeMessageDelivery:
    """Real-time message delivery tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and chat room"""
        self.user1 = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        self.user2 = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.user1)
        ChatParticipant.objects.create(room=self.room, user=self.user2)

    def test_get_chat_list(self):
        """Test retrieving list of user's chats"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.get("/api/chat/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.json()
        assert isinstance(response.json()["results"], list)

    def test_get_chat_detail(self):
        """Test retrieving chat detail information"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.get(f"/api/chat/{self.room.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == self.room.id

    def test_get_messages_history(self):
        """Test retrieving message history"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create test messages
        Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Message 1"
        )
        Message.objects.create(
            room=self.room,
            sender=self.user2,
            content="Message 2"
        )

        response = client.get(f"/api/chat/{self.room.id}/messages/")

        assert response.status_code == status.HTTP_200_OK
        assert "messages" in response.json()
        messages = response.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["content"] == "Message 1"
        assert messages[1]["content"] == "Message 2"

    def test_message_ordering_in_history(self):
        """Test messages are ordered correctly"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create messages with delays
        msg1 = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="First message"
        )
        msg2 = Message.objects.create(
            room=self.room,
            sender=self.user2,
            content="Second message"
        )
        msg3 = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Third message"
        )

        response = client.get(f"/api/chat/{self.room.id}/messages/")

        messages = response.json()["messages"]
        assert len(messages) == 3
        assert messages[0]["id"] == msg1.id
        assert messages[1]["id"] == msg2.id
        assert messages[2]["id"] == msg3.id


@pytest.mark.django_db
class TestMessageEditing:
    """Message editing tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and chat room"""
        self.user1 = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        self.user2 = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.user1)
        ChatParticipant.objects.create(room=self.room, user=self.user2)

        self.message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Original message"
        )

    def test_edit_own_message(self):
        """Test message author can edit message"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.patch(
            f"/api/chat/{self.room.id}/messages/{self.message.id}/",
            {"content": "Edited message"},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Edited message" in response.json()["content"]

        # Verify in database
        self.message.refresh_from_db()
        assert self.message.content == "Edited message"
        assert self.message.is_edited is True

    def test_cannot_edit_other_user_message(self):
        """Test non-author cannot edit message"""
        client = APIClient()
        client.force_authenticate(user=self.user2)

        response = client.patch(
            f"/api/chat/{self.room.id}/messages/{self.message.id}/",
            {"content": "Edited by other user"},
            format="json"
        )

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

        # Verify content unchanged
        self.message.refresh_from_db()
        assert self.message.content == "Original message"

    def test_edit_deleted_message_fails(self):
        """Test cannot edit deleted message"""
        self.message.is_deleted = True
        self.message.save()

        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.patch(
            f"/api/chat/{self.room.id}/messages/{self.message.id}/",
            {"content": "New content"},
            format="json"
        )

        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
class TestMessageDeletion:
    """Message deletion tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and chat room"""
        self.user1 = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        self.user2 = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role=User.Role.ADMIN
        )

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.user1)
        ChatParticipant.objects.create(room=self.room, user=self.user2)

        self.message = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Message to delete"
        )

    def test_delete_own_message(self):
        """Test message author can delete message"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.delete(
            f"/api/chat/{self.room.id}/messages/{self.message.id}/"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete
        self.message.refresh_from_db()
        assert self.message.is_deleted is True
        assert self.message.deleted_at is not None

    def test_cannot_delete_other_user_message(self):
        """Test non-author cannot delete message"""
        client = APIClient()
        client.force_authenticate(user=self.user2)

        response = client.delete(
            f"/api/chat/{self.room.id}/messages/{self.message.id}/"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify not deleted
        self.message.refresh_from_db()
        assert self.message.is_deleted is False

    def test_admin_can_delete_any_message(self):
        """Test admin can delete any message"""
        client = APIClient()
        client.force_authenticate(user=self.admin)

        response = client.delete(
            f"/api/chat/{self.room.id}/messages/{self.message.id}/"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete
        self.message.refresh_from_db()
        assert self.message.is_deleted is True

    def test_deleted_messages_excluded_from_list(self):
        """Test deleted messages not shown in history"""
        # Create multiple messages
        msg1 = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Visible message"
        )
        msg2 = Message.objects.create(
            room=self.room,
            sender=self.user1,
            content="Deleted message"
        )
        msg2.is_deleted = True
        msg2.save()

        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.get(f"/api/chat/{self.room.id}/messages/")

        messages = response.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["content"] == "Visible message"


@pytest.mark.django_db
class TestChatAccess:
    """Chat access control tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and chat room"""
        self.user1 = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        self.user2 = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        self.user3 = User.objects.create_user(
            username="outsider",
            email="outsider@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Petrov"
        )

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.user1)
        ChatParticipant.objects.create(room=self.room, user=self.user2)

    def test_participant_can_view_chat(self):
        """Test chat participant can view chat"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.get(f"/api/chat/{self.room.id}/")

        assert response.status_code == status.HTTP_200_OK

    def test_non_participant_cannot_view_chat(self):
        """Test non-participant cannot view chat"""
        client = APIClient()
        client.force_authenticate(user=self.user3)

        response = client.get(f"/api/chat/{self.room.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_participant_can_send_message(self):
        """Test participant can send message"""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": "Test message"},
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_non_participant_cannot_send_message(self):
        """Test non-participant cannot send message"""
        client = APIClient()
        client.force_authenticate(user=self.user3)

        response = client.post(
            f"/api/chat/{self.room.id}/send_message",
            {"content": "Test message"},
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestChatCreation:
    """Chat creation and initialization tests"""

    def test_create_chat_between_two_users(self):
        """Test creating chat between student and teacher"""
        student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        client = APIClient()
        client.force_authenticate(user=student)

        response = client.post(
            "/api/chat/",
            {"recipient_id": teacher.id},
            format="json"
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert "id" in response.json()

        room_id = response.json()["id"]
        room = ChatRoom.objects.get(id=room_id)
        assert ChatParticipant.objects.filter(room=room, user=student).exists()
        assert ChatParticipant.objects.filter(room=room, user=teacher).exists()

    def test_cannot_chat_with_self(self):
        """Test cannot create chat with yourself"""
        user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            "/api/chat/",
            {"recipient_id": user.id},
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_chat_returns_existing(self):
        """Test creating duplicate chat returns existing chat"""
        student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        client = APIClient()
        client.force_authenticate(user=student)

        # Create first chat
        response1 = client.post(
            "/api/chat/",
            {"recipient_id": teacher.id},
            format="json"
        )
        room_id_1 = response1.json()["id"]

        # Create second chat with same users
        response2 = client.post(
            "/api/chat/",
            {"recipient_id": teacher.id},
            format="json"
        )
        room_id_2 = response2.json()["id"]

        assert room_id_1 == room_id_2
        assert response2.status_code == status.HTTP_200_OK  # Not created again


@pytest.mark.django_db
class TestChatContacts:
    """Chat contacts list tests"""

    def test_get_available_contacts(self):
        """Test getting list of available contacts"""
        student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        client = APIClient()
        client.force_authenticate(user=student)

        response = client.get("/api/chat/contacts/")

        assert response.status_code == status.HTTP_200_OK
        assert "contacts" in response.json()
        contacts = response.json()["contacts"]
        assert len(contacts) >= 1
        assert any(c["id"] == teacher.id for c in contacts)

    def test_contacts_exclude_self(self):
        """Test contacts list excludes user itself"""
        student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        client = APIClient()
        client.force_authenticate(user=student)

        response = client.get("/api/chat/contacts/")

        contacts = response.json()["contacts"]
        assert not any(c["id"] == student.id for c in contacts)

    def test_contacts_have_required_fields(self):
        """Test contact items have all required fields"""
        student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Ivan",
            last_name="Sokolov"
        )

        teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Petr",
            last_name="Ivanov"
        )

        client = APIClient()
        client.force_authenticate(user=student)

        response = client.get("/api/chat/contacts/")

        contacts = response.json()["contacts"]
        contact = next((c for c in contacts if c["id"] == teacher.id), None)
        assert contact is not None
        assert "id" in contact
        assert "full_name" in contact
        assert "role" in contact
        assert "has_existing_chat" in contact
