"""
Unit tests for GeneralChatViewSet endpoints.

Tests cover:
- GET /api/chat/general/ - get_or_create_general_chat()
- GET /api/chat/general/messages/ - fetch general chat messages with pagination
- POST /api/chat/general/send_message/ - create messages with validation
- GET /api/chat/general/threads/ - list threads with pagination
- POST /api/chat/general/create_thread/ - create threads with validation
- Permissions: only authenticated users
- Query optimization: no N+1 queries
- Edge cases: empty messages, non-existent resources, permission violations
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from chat.models import ChatRoom, Message, MessageThread, ChatParticipant

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for tests"""
    return APIClient()


@pytest.mark.unit
@pytest.mark.django_db
class TestGeneralChatViewSet:
    """Tests for GeneralChatViewSet endpoints"""

    # ========== GET /api/chat/general/ ==========

    def test_get_general_chat_unauthenticated(self, api_client):
        """Unauthenticated users should get 401 or 403"""
        response = api_client.get('/api/chat/general/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_general_chat_authenticated_creates_if_needed(self, api_client, student_user):
        """Authenticated users get general chat, creating if needed"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == ChatRoom.Type.GENERAL
        assert response.data['name'] == 'Общий форум'

    def test_get_general_chat_returns_existing_chat(self, api_client, teacher_user):
        """Subsequent calls return the same general chat"""
        # Create general chat
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(teacher_user)

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/chat/general/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == general_chat.id

    def test_get_general_chat_response_structure(self, api_client, student_user):
        """Response contains required fields"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/')

        assert 'id' in response.data
        assert 'name' in response.data
        assert 'type' in response.data
        assert 'description' in response.data
        assert 'created_at' in response.data
        assert 'updated_at' in response.data
        assert 'is_active' in response.data

    # ========== GET /api/chat/general/messages/ ==========

    def test_get_general_messages_unauthenticated(self, api_client):
        """Unauthenticated users should get 401 or 403"""
        response = api_client.get('/api/chat/general/messages/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_general_messages_empty_chat(self, api_client, student_user, teacher_user):
        """Empty general chat returns empty list"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_general_messages_returns_messages(self, api_client, student_user, teacher_user):
        """Returns messages from general chat"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        # Create test messages
        msg1 = Message.objects.create(
            room=general_chat,
            sender=student_user,
            content='First message'
        )
        msg2 = Message.objects.create(
            room=general_chat,
            sender=teacher_user,
            content='Second message'
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == msg1.id
        assert response.data[1]['id'] == msg2.id

    def test_get_general_messages_pagination_limit(self, api_client, student_user, teacher_user):
        """Pagination with limit parameter"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        # Create 5 messages
        for i in range(5):
            Message.objects.create(
                room=general_chat,
                sender=student_user,
                content=f'Message {i}'
            )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/messages/?limit=2')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_get_general_messages_pagination_offset(self, api_client, student_user, teacher_user):
        """Pagination with offset parameter"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        # Create 5 messages
        messages = []
        for i in range(5):
            msg = Message.objects.create(
                room=general_chat,
                sender=student_user,
                content=f'Message {i}'
            )
            messages.append(msg)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/messages/?limit=2&offset=2')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == messages[2].id

    def test_get_general_messages_response_structure(self, api_client, student_user, teacher_user):
        """Message response contains required fields"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        Message.objects.create(
            room=general_chat,
            sender=student_user,
            content='Test message'
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/messages/')

        assert response.status_code == status.HTTP_200_OK
        message_data = response.data[0]
        assert 'id' in message_data
        assert 'content' in message_data
        assert 'sender_name' in message_data
        assert 'created_at' in message_data
        assert 'message_type' in message_data

    # ========== POST /api/chat/general/send_message/ ==========

    def test_send_message_unauthenticated(self, api_client):
        """Unauthenticated users should get 401 or 403"""
        response = api_client.post('/api/chat/general/send_message/', {'content': 'Test'})
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_send_message_with_valid_content(self, api_client, student_user, teacher_user):
        """Send valid message to general chat"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Test message'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['content'] == 'Test message'
        assert response.data['sender_name'] == student_user.get_full_name()

    def test_send_message_empty_content_fails(self, api_client, student_user, teacher_user):
        """Empty message should return 400"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': ''
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_send_message_no_content_field_fails(self, api_client, student_user, teacher_user):
        """Missing content field should return 400"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_message_with_file(self, api_client, student_user, teacher_user):
        """Send message with file attachment"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        test_file = SimpleUploadedFile(
            'test.pdf',
            b'file content',
            content_type='application/pdf'
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Here is a file',
            'file': test_file
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message_type'] == Message.Type.FILE

    def test_send_message_with_image(self, api_client, student_user, teacher_user):
        """Send message with image attachment"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        # Create a simple image file
        test_image = SimpleUploadedFile(
            'test.jpg',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
            content_type='image/jpeg'
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Here is an image',
            'image': test_image
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message_type'] == Message.Type.IMAGE

    def test_send_message_message_type_field(self, api_client, student_user, teacher_user):
        """Message type is set correctly"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Text message',
            'message_type': Message.Type.TEXT
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message_type'] == Message.Type.TEXT

    def test_send_message_persists_to_database(self, api_client, student_user, teacher_user):
        """Message is persisted to database"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Persisted message'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert Message.objects.filter(content='Persisted message').exists()

    # ========== GET /api/chat/general/threads/ ==========

    def test_get_threads_unauthenticated(self, api_client):
        """Unauthenticated users should get 401 or 403"""
        response = api_client.get('/api/chat/general/threads/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_threads_empty(self, api_client, student_user, teacher_user):
        """Empty threads list"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_threads_returns_threads(self, api_client, student_user, teacher_user):
        """Returns threads from general chat"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        # Create test threads
        thread1 = MessageThread.objects.create(
            room=general_chat,
            title='First thread',
            created_by=student_user
        )
        thread2 = MessageThread.objects.create(
            room=general_chat,
            title='Second thread',
            created_by=teacher_user
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == thread1.id
        assert response.data[1]['id'] == thread2.id

    def test_get_threads_pagination_limit(self, api_client, student_user, teacher_user):
        """Pagination with limit parameter"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        # Create 5 threads
        for i in range(5):
            MessageThread.objects.create(
                room=general_chat,
                title=f'Thread {i}',
                created_by=student_user
            )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/?limit=2')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_get_threads_pagination_offset(self, api_client, student_user, teacher_user):
        """Pagination with offset parameter"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        # Create 5 threads
        threads = []
        for i in range(5):
            thread = MessageThread.objects.create(
                room=general_chat,
                title=f'Thread {i}',
                created_by=student_user
            )
            threads.append(thread)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/?limit=2&offset=2')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == threads[2].id

    def test_get_threads_response_structure(self, api_client, student_user, teacher_user):
        """Thread response contains required fields"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        MessageThread.objects.create(
            room=general_chat,
            title='Test thread',
            created_by=student_user
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/')

        assert response.status_code == status.HTTP_200_OK
        thread_data = response.data[0]
        assert 'id' in thread_data
        assert 'title' in thread_data
        assert 'created_by' in thread_data
        assert 'is_pinned' in thread_data
        assert 'is_locked' in thread_data
        assert 'created_at' in thread_data

    def test_get_threads_pinned_first(self, api_client, student_user, teacher_user):
        """Pinned threads appear first"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        # Create threads
        unpinned = MessageThread.objects.create(
            room=general_chat,
            title='Unpinned thread',
            created_by=student_user,
            is_pinned=False
        )
        pinned = MessageThread.objects.create(
            room=general_chat,
            title='Pinned thread',
            created_by=teacher_user,
            is_pinned=True
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/general/threads/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['id'] == pinned.id
        assert response.data[1]['id'] == unpinned.id

    # ========== POST /api/chat/general/create_thread/ ==========

    def test_create_thread_unauthenticated(self, api_client):
        """Unauthenticated users should get 401 or 403"""
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': 'Test thread'
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_thread_with_title(self, api_client, student_user, teacher_user):
        """Create thread with valid title"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': 'New thread'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New thread'
        assert response.data['created_by']['id'] == student_user.id

    def test_create_thread_no_title_fails(self, api_client, student_user, teacher_user):
        """Missing title should return 400"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/create_thread/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_create_thread_empty_title_fails(self, api_client, student_user, teacher_user):
        """Empty title should return 400"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': ''
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_thread_persists_to_database(self, api_client, student_user, teacher_user):
        """Thread is persisted to database"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': 'Persisted thread'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert MessageThread.objects.filter(title='Persisted thread').exists()

    def test_create_thread_creates_general_chat_if_needed(self, api_client, student_user):
        """Creating thread auto-creates general chat if needed"""
        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': 'First thread'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).exists()

    def test_create_thread_response_structure(self, api_client, student_user, teacher_user):
        """Thread response contains required fields"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': 'Test thread'
        })

        assert response.status_code == status.HTTP_201_CREATED
        thread_data = response.data
        assert 'id' in thread_data
        assert 'title' in thread_data
        assert 'created_by' in thread_data
        assert 'is_pinned' in thread_data
        assert 'is_locked' in thread_data
        assert 'created_at' in thread_data

    # ========== Query Optimization Tests ==========

    @pytest.mark.django_db
    def test_get_messages_no_n_plus_one(self, student_user, teacher_user):
        """No N+1 queries when fetching messages"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        # Create 5 messages
        for i in range(5):
            Message.objects.create(
                room=general_chat,
                sender=student_user,
                content=f'Message {i}'
            )

        # Reset query counter and fetch messages
        from django.test import override_settings
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            api_client = APIClient()
            api_client.force_authenticate(user=student_user)
            response = api_client.get('/api/chat/general/messages/')

        # Should be 1 query (get general chat) + 1 query (get messages)
        # Not N+1 (5 queries for 5 messages)
        assert response.status_code == status.HTTP_200_OK
        assert len(ctx) <= 3  # Reasonable limit

    @pytest.mark.django_db
    def test_get_threads_no_n_plus_one(self, student_user, teacher_user):
        """No N+1 queries when fetching threads"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user, teacher_user)

        # Create 5 threads
        for i in range(5):
            MessageThread.objects.create(
                room=general_chat,
                title=f'Thread {i}',
                created_by=student_user
            )

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            api_client = APIClient()
            api_client.force_authenticate(user=student_user)
            response = api_client.get('/api/chat/general/threads/')

        assert response.status_code == status.HTTP_200_OK
        assert len(ctx) <= 3  # Reasonable limit


@pytest.mark.unit
@pytest.mark.django_db
class TestGeneralChatPermissions:
    """Permission tests for general chat endpoints"""

    def test_only_authenticated_can_list_general_chat(self, api_client):
        """Unauthenticated users cannot list general chat"""
        response = api_client.get('/api/chat/general/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_only_authenticated_can_view_messages(self, api_client):
        """Unauthenticated users cannot view messages"""
        response = api_client.get('/api/chat/general/messages/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_only_authenticated_can_send_message(self, api_client):
        """Unauthenticated users cannot send messages"""
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Test'
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_only_authenticated_can_view_threads(self, api_client):
        """Unauthenticated users cannot view threads"""
        response = api_client.get('/api/chat/general/threads/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_only_authenticated_can_create_thread(self, api_client):
        """Unauthenticated users cannot create threads"""
        response = api_client.post('/api/chat/general/create_thread/', {
            'title': 'Test'
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_authenticated_users_can_send_messages(self, api_client, student_user, teacher_user):
        """Authenticated users can send messages"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_chat.participants.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/general/send_message/', {
            'content': 'Test message'
        })

        assert response.status_code == status.HTTP_201_CREATED
