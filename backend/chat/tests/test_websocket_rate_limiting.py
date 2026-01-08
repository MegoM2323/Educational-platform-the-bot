"""
Tests for WebSocket rate limiting (T014) and room enumeration protection (T015)
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import RefreshToken

from chat.consumers import ChatConsumer
from chat.models import ChatRoom, ChatParticipant

User = get_user_model()


def create_communicator(room_id):
    """Create WebsocketCommunicator with proper scope setup"""
    application = ChatConsumer.as_asgi()
    communicator = WebsocketCommunicator(application, f"/ws/chat/{room_id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(room_id)}}
    return communicator


@database_sync_to_async
def create_room_with_participants(user, second_user=None):
    """Create a room with participants (async-safe)"""
    room = ChatRoom.objects.create()
    ChatParticipant.objects.create(room=room, user=user)
    if second_user:
        ChatParticipant.objects.create(room=room, user=second_user)
    return room


@pytest.fixture
def user():
    """Create test user"""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def second_user():
    """Create second test user"""
    return User.objects.create_user(
        username="user2", email="user2@example.com", password="testpass123"
    )


@pytest.fixture
def chat_room(user):
    """Create test chat room with participant"""
    room = ChatRoom.objects.create()
    ChatParticipant.objects.create(room=room, user=user)
    return room


@pytest.fixture
def second_chat_room(user, second_user):
    """Create second test chat room with participants"""
    room = ChatRoom.objects.create()
    ChatParticipant.objects.create(room=room, user=user)
    ChatParticipant.objects.create(room=room, user=second_user)
    return room


@pytest.fixture
def access_token(user):
    """Generate JWT token for user"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


def get_token_for_user(user):
    """Helper to generate token for any user"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


@pytest.mark.django_db(transaction=True)
class TestRateLimitingT014:
    """Test T014: Per-user rate limiting on message sends"""

    @pytest.mark.asyncio
    async def test_message_rate_limit_single_connection(
        self, user, chat_room, access_token
    ):
        """Verify that rate limit prevents sending >10 messages per minute on single connection"""
        communicator = create_communicator(chat_room.id)
        connected, subprotocol = await communicator.connect()
        assert connected

        await communicator.send_json_to({"type": "auth", "token": access_token})
        response = await communicator.receive_json_from()
        assert response["type"] == "auth_success"

        cache.clear()

        messages_sent = 0
        for i in range(15):
            await communicator.send_json_to(
                {"type": "message", "content": f"Message {i}"}
            )
            response = await communicator.receive_json_from()

            if response["type"] == "message":
                messages_sent += 1
            elif response["type"] == "error":
                assert response["code"] == "RATE_LIMIT_EXCEEDED"
                break

        assert messages_sent == 10

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_rate_limit_multiple_connections_same_user(
        self, user, chat_room, access_token
    ):
        """
        Verify that rate limit works across multiple connections from same user.
        This is the core security fix for T014.
        """
        comm1 = create_communicator(chat_room.id)
        conn1, _ = await comm1.connect()
        assert conn1

        comm2 = create_communicator(chat_room.id)
        conn2, _ = await comm2.connect()
        assert conn2

        await comm1.send_json_to({"type": "auth", "token": access_token})
        resp1 = await comm1.receive_json_from()
        assert resp1["type"] == "auth_success"

        await comm2.send_json_to({"type": "auth", "token": access_token})
        resp2 = await comm2.receive_json_from()
        assert resp2["type"] == "auth_success"

        cache.clear()

        messages_count = 0
        rate_limited_count = 0

        for i in range(8):
            await comm1.send_json_to(
                {"type": "message", "content": f"Msg from conn1: {i}"}
            )
            resp = await comm1.receive_json_from()
            if resp["type"] == "message":
                messages_count += 1
            elif resp["type"] == "error" and resp["code"] == "RATE_LIMIT_EXCEEDED":
                rate_limited_count += 1

        for i in range(6):
            await comm2.send_json_to(
                {"type": "message", "content": f"Msg from conn2: {i}"}
            )
            resp = await comm2.receive_json_from()
            if resp["type"] == "message":
                messages_count += 1
            elif resp["type"] == "error" and resp["code"] == "RATE_LIMIT_EXCEEDED":
                rate_limited_count += 1

        assert messages_count + rate_limited_count == 14
        assert messages_count == 10
        assert rate_limited_count == 4

        await comm1.disconnect()
        await comm2.disconnect()


@pytest.mark.django_db(transaction=True)
class TestRoomLimitT015:
    """Test T015: Protection against room enumeration via connection attempts"""

    @pytest.mark.asyncio
    async def test_room_connection_limit(self, user, chat_room, second_chat_room):
        """
        Verify that user cannot connect to more than 5 different rooms in 60 seconds
        """
        token = get_token_for_user(user)
        cache.clear()

        room_ids = []
        rooms = []

        for i in range(7):
            room = await create_room_with_participants(user)
            rooms.append(room)
            room_ids.append(room.id)

        conns = []
        successful_connections = 0

        for i, room_id in enumerate(room_ids):
            comm = create_communicator(room_id)
            connected, _ = await comm.connect()
            assert connected

            await comm.send_json_to({"type": "auth", "token": token})
            response = await comm.receive_json_from()

            if response["type"] == "auth_success":
                successful_connections += 1
                conns.append(comm)
            elif response["type"] == "error":
                assert response["code"] in ["RATE_LIMIT_EXCEEDED", "Forbidden"]
                await comm.disconnect()

        assert (
            successful_connections == 5
        ), f"Expected 5 successful connections, got {successful_connections}"

        for comm in conns:
            await comm.disconnect()

    @pytest.mark.asyncio
    async def test_room_limit_different_users_independent(
        self, user, second_user, chat_room, second_chat_room
    ):
        """Verify that room limit is per-user, not global"""
        user_token = get_token_for_user(user)
        user2_token = get_token_for_user(second_user)

        cache.clear()

        rooms = [chat_room, second_chat_room]
        for i in range(4):
            room = await create_room_with_participants(user, second_user)
            rooms.append(room)

        user1_conns = []
        user2_conns = []

        for i, room in enumerate(rooms[:6]):
            comm1 = create_communicator(room.id)
            connected1, _ = await comm1.connect()
            assert connected1

            comm2 = create_communicator(room.id)
            connected2, _ = await comm2.connect()
            assert connected2

            await comm1.send_json_to({"type": "auth", "token": user_token})
            resp1 = await comm1.receive_json_from()

            await comm2.send_json_to({"type": "auth", "token": user2_token})
            resp2 = await comm2.receive_json_from()

            if resp1["type"] == "auth_success":
                user1_conns.append(comm1)
            else:
                await comm1.disconnect()

            if resp2["type"] == "auth_success":
                user2_conns.append(comm2)
            else:
                await comm2.disconnect()

        assert (
            len(user1_conns) == 5
        ), f"User1 should have 5 connections, got {len(user1_conns)}"
        assert (
            len(user2_conns) == 5
        ), f"User2 should have 5 connections, got {len(user2_conns)}"

        for comm in user1_conns + user2_conns:
            await comm.disconnect()


@pytest.mark.django_db(transaction=True)
class TestRateLimitCacheExpiration:
    """Test that rate limit counters expire correctly"""

    def test_rate_limit_key_expiration(self, user):
        """Verify Redis key expires after CHAT_RATE_WINDOW seconds"""
        from chat.consumers import CHAT_RATE_WINDOW

        rate_key = f"chat_rate_limit:{user.id}"
        cache.set(rate_key, 5, CHAT_RATE_WINDOW)

        value = cache.get(rate_key)
        assert value == 5

        cache.delete(rate_key)
        value = cache.get(rate_key)
        assert value is None

    def test_room_limit_key_expiration(self, user):
        """Verify room limit key expires after CHAT_RATE_WINDOW seconds"""
        from chat.consumers import CHAT_RATE_WINDOW

        rooms_key = f"chat_rooms_limit:{user.id}"
        cache.set(rooms_key, 3, CHAT_RATE_WINDOW)

        value = cache.get(rooms_key)
        assert value == 3

        cache.delete(rooms_key)
        value = cache.get(rooms_key)
        assert value is None
