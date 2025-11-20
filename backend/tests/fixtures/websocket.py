"""
WebSocket test fixtures and utilities for Django Channels
"""
import pytest
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def channel_layer():
    """Get channel layer for testing"""
    return get_channel_layer()


@pytest.fixture
async def websocket_communicator():
    """
    Create a WebSocket communicator for testing.
    Usage:
        async def test_websocket(websocket_communicator):
            communicator = websocket_communicator('/ws/chat/')
            connected, subprotocol = await communicator.connect()
            assert connected
            await communicator.disconnect()
    """
    from config.asgi import application

    def _create_communicator(path, user=None, headers=None):
        """Create WebSocket communicator with optional authentication"""
        communicator = WebsocketCommunicator(application, path)

        # Add user to scope if provided
        if user:
            communicator.scope['user'] = user

        # Add headers if provided
        if headers:
            communicator.scope['headers'] = headers

        return communicator

    return _create_communicator


@pytest.fixture
def mock_websocket_send():
    """Mock WebSocket send method"""
    mock_send = AsyncMock()
    return mock_send


@pytest.fixture
def mock_websocket_receive():
    """Mock WebSocket receive method"""
    mock_receive = AsyncMock()
    mock_receive.return_value = {
        'type': 'websocket.receive',
        'text': '{"message": "test message"}'
    }
    return mock_receive


@pytest.fixture
def mock_channel_layer():
    """Mock channel layer for testing without Redis"""
    mock_layer = MagicMock()

    # Mock group_send
    mock_layer.group_send = AsyncMock()

    # Mock group_add
    mock_layer.group_add = AsyncMock()

    # Mock group_discard
    mock_layer.group_discard = AsyncMock()

    # Mock send
    mock_layer.send = AsyncMock()

    return mock_layer


@pytest.fixture
async def authenticated_websocket(websocket_communicator, student_user):
    """
    WebSocket communicator with authenticated student user.
    Usage:
        async def test_chat(authenticated_websocket):
            communicator = await authenticated_websocket('/ws/chat/1/')
            connected, _ = await communicator.connect()
            assert connected
    """
    @database_sync_to_async
    def get_user():
        return student_user

    async def _create_authenticated_communicator(path):
        user = await get_user()
        return websocket_communicator(path, user=user)

    return _create_authenticated_communicator


@pytest.fixture
def websocket_message():
    """Sample WebSocket message"""
    return {
        'type': 'chat.message',
        'message': {
            'id': 1,
            'text': 'Test message',
            'sender': 'Test User',
            'timestamp': '2024-01-01T00:00:00Z'
        }
    }


@pytest.fixture
def websocket_connect_message():
    """WebSocket connect message"""
    return {
        'type': 'websocket.connect'
    }


@pytest.fixture
def websocket_disconnect_message():
    """WebSocket disconnect message"""
    return {
        'type': 'websocket.disconnect',
        'code': 1000
    }


@pytest.fixture
def websocket_receive_text():
    """WebSocket receive text message"""
    return {
        'type': 'websocket.receive',
        'text': '{"action": "send_message", "data": {"text": "Hello"}}'
    }


@pytest.fixture
def websocket_receive_bytes():
    """WebSocket receive bytes message"""
    return {
        'type': 'websocket.receive',
        'bytes': b'binary data'
    }


@pytest.fixture(autouse=True)
async def clear_channel_layers():
    """Clear channel layers after each test"""
    yield
    # Cleanup code here if needed
    channel_layer = get_channel_layer()
    if channel_layer:
        await channel_layer.flush()


@pytest.fixture
def mock_consumer():
    """Mock WebSocket consumer"""
    mock = MagicMock()
    mock.accept = AsyncMock()
    mock.send = AsyncMock()
    mock.receive = AsyncMock()
    mock.close = AsyncMock()
    mock.channel_layer = MagicMock()
    mock.channel_name = 'test-channel-name'
    return mock


@pytest.fixture
async def chat_room_communicator(websocket_communicator, student_user):
    """
    Pre-configured chat room WebSocket communicator.
    Usage:
        async def test_chat_room(chat_room_communicator):
            communicator, room_id = await chat_room_communicator()
            # Use communicator for testing
    """
    @database_sync_to_async
    def get_user():
        return student_user

    async def _create_chat_communicator(room_id=1):
        user = await get_user()
        path = f'/ws/chat/{room_id}/'
        return websocket_communicator(path, user=user), room_id

    return _create_chat_communicator


@pytest.fixture
def websocket_url_pattern():
    """WebSocket URL pattern for testing"""
    return 'ws/chat/<int:room_id>/'


@pytest.fixture(autouse=True)
def use_in_memory_channel_layer(settings):
    """
    Use InMemoryChannelLayer for tests instead of Redis.
    This makes tests faster and doesn't require Redis to be running.
    """
    settings.CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }
