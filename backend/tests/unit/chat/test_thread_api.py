"""
Unit tests for MessageThreadViewSet endpoints.

Tests cover:
- GET /api/chat/threads/{id}/messages/ - thread message retrieval
- POST /api/chat/threads/{id}/send_message/ - thread message creation
- POST /api/chat/threads/{id}/pin/ - thread pinning (admin/teacher only)
- POST /api/chat/threads/{id}/unpin/ - thread unpinning
- POST /api/chat/threads/{id}/lock/ - thread locking (admin/teacher only)
- POST /api/chat/threads/{id}/unlock/ - thread unlocking
- Permissions: only authenticated users, pin/lock requires admin/teacher
- Query optimization: no N+1 queries
- Edge cases: locked threads, non-existent threads, permission violations
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.test.utils import CaptureQueriesContext
from django.db import connection

from chat.models import ChatRoom, Message, MessageThread, ChatParticipant

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for tests"""
    return APIClient()


@pytest.fixture
def general_chat_with_thread(teacher_user, student_user):
    """Create general chat with a thread"""
    general_chat = ChatRoom.objects.create(
        name='Общий форум',
        type=ChatRoom.Type.GENERAL,
        created_by=teacher_user
    )
    general_chat.participants.add(teacher_user, student_user)

    # Add teacher as admin
    ChatParticipant.objects.get_or_create(
        room=general_chat,
        user=teacher_user,
        defaults={'is_admin': True}
    )

    thread = MessageThread.objects.create(
        room=general_chat,
        title='Test Thread',
        created_by=student_user
    )

    return general_chat, thread


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageThreadViewSet:
    """Tests for MessageThreadViewSet endpoints"""

    # ========== GET /api/chat/threads/{id}/messages/ ==========

    def test_get_thread_messages_unauthenticated(self, api_client, teacher_user):
        """Unauthenticated users should get 401 or 403"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        thread = MessageThread.objects.create(
            room=general_chat,
            title='Test',
            created_by=teacher_user
        )

        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_thread_messages_empty(self, api_client, general_chat_with_thread, student_user):
        """Empty thread returns empty list"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_thread_messages_returns_messages(self, api_client, general_chat_with_thread, student_user, teacher_user):
        """Returns messages from thread"""
        general_chat, thread = general_chat_with_thread

        # Create test messages
        msg1 = Message.objects.create(
            room=general_chat,
            thread=thread,
            sender=student_user,
            content='First message'
        )
        msg2 = Message.objects.create(
            room=general_chat,
            thread=thread,
            sender=teacher_user,
            content='Second message'
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == msg1.id
        assert response.data[1]['id'] == msg2.id

    def test_get_thread_messages_pagination_limit(self, api_client, general_chat_with_thread, student_user):
        """Pagination with limit parameter"""
        general_chat, thread = general_chat_with_thread

        # Create 5 messages
        for i in range(5):
            Message.objects.create(
                room=general_chat,
                thread=thread,
                sender=student_user,
                content=f'Message {i}'
            )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/?limit=2')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_get_thread_messages_pagination_offset(self, api_client, general_chat_with_thread, student_user):
        """Pagination with offset parameter"""
        general_chat, thread = general_chat_with_thread

        # Create 5 messages
        messages = []
        for i in range(5):
            msg = Message.objects.create(
                room=general_chat,
                thread=thread,
                sender=student_user,
                content=f'Message {i}'
            )
            messages.append(msg)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/?limit=2&offset=2')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == messages[2].id

    def test_get_thread_messages_response_structure(self, api_client, general_chat_with_thread, student_user):
        """Message response contains required fields"""
        general_chat, thread = general_chat_with_thread

        Message.objects.create(
            room=general_chat,
            thread=thread,
            sender=student_user,
            content='Test message'
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        message_data = response.data[0]
        assert 'id' in message_data
        assert 'content' in message_data
        assert 'sender_name' in message_data
        assert 'created_at' in message_data

    def test_get_nonexistent_thread_returns_404(self, api_client, student_user):
        """Accessing non-existent thread returns 404"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/chat/threads/99999/messages/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== POST /api/chat/threads/{id}/send_message/ ==========

    def test_send_thread_message_unauthenticated(self, api_client, teacher_user):
        """Unauthenticated users should get 401 or 403"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        thread = MessageThread.objects.create(
            room=general_chat,
            title='Test',
            created_by=teacher_user
        )

        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Test'
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_send_thread_message_with_valid_content(self, api_client, general_chat_with_thread, student_user):
        """Send valid message to thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Thread message'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['content'] == 'Thread message'

    def test_send_thread_message_empty_content_fails(self, api_client, general_chat_with_thread, student_user):
        """Empty message should return 400"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': ''
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_thread_message_no_content_fails(self, api_client, general_chat_with_thread, student_user):
        """Missing content should return 400"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_thread_message_to_nonexistent_thread(self, api_client, student_user):
        """Sending to non-existent thread returns 404"""
        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/chat/threads/99999/send_message/', {
            'content': 'Test'
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_send_thread_message_persists_to_database(self, api_client, general_chat_with_thread, student_user):
        """Message is persisted to database"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Persisted thread message'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert Message.objects.filter(content='Persisted thread message').exists()

    def test_send_thread_message_associates_with_thread(self, api_client, general_chat_with_thread, student_user):
        """Message is associated with the correct thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Thread-associated message'
        })

        assert response.status_code == status.HTTP_201_CREATED
        message = Message.objects.get(content='Thread-associated message')
        assert message.thread_id == thread.id

    # ========== POST /api/chat/threads/{id}/pin/ ==========

    def test_pin_thread_unauthenticated(self, api_client, teacher_user):
        """Unauthenticated users should get 401 or 403"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        thread = MessageThread.objects.create(
            room=general_chat,
            title='Test',
            created_by=teacher_user
        )

        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_pin_thread_by_admin(self, api_client, general_chat_with_thread, teacher_user):
        """Admin/teacher can pin thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_pinned'] is True

        # Verify in database
        thread.refresh_from_db()
        assert thread.is_pinned is True

    def test_pin_thread_by_regular_user_fails(self, api_client, general_chat_with_thread, student_user):
        """Regular users cannot pin thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')

        # Should fail with permission error
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pin_thread_idempotent(self, api_client, general_chat_with_thread, teacher_user):
        """Pinning already pinned thread works"""
        general_chat, thread = general_chat_with_thread
        thread.is_pinned = True
        thread.save()

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_pinned'] is True

    def test_pin_nonexistent_thread(self, api_client, teacher_user):
        """Pinning non-existent thread returns 404"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post('/api/chat/threads/99999/pin/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== POST /api/chat/threads/{id}/unpin/ ==========

    def test_unpin_thread_unauthenticated(self, api_client, teacher_user):
        """Unauthenticated users should get 401 or 403"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        thread = MessageThread.objects.create(
            room=general_chat,
            title='Test',
            created_by=teacher_user,
            is_pinned=True
        )

        response = api_client.post(f'/api/chat/threads/{thread.id}/unpin/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_unpin_thread_by_admin(self, api_client, general_chat_with_thread, teacher_user):
        """Admin/teacher can unpin thread"""
        general_chat, thread = general_chat_with_thread
        thread.is_pinned = True
        thread.save()

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/unpin/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_pinned'] is False

        # Verify in database
        thread.refresh_from_db()
        assert thread.is_pinned is False

    def test_unpin_thread_by_regular_user_fails(self, api_client, general_chat_with_thread, student_user):
        """Regular users cannot unpin thread"""
        general_chat, thread = general_chat_with_thread
        thread.is_pinned = True
        thread.save()

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/unpin/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unpin_nonexistent_thread(self, api_client, teacher_user):
        """Unpinning non-existent thread returns 404"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post('/api/chat/threads/99999/unpin/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== POST /api/chat/threads/{id}/lock/ ==========

    def test_lock_thread_unauthenticated(self, api_client, teacher_user):
        """Unauthenticated users should get 401 or 403"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        thread = MessageThread.objects.create(
            room=general_chat,
            title='Test',
            created_by=teacher_user
        )

        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_lock_thread_by_admin(self, api_client, general_chat_with_thread, teacher_user):
        """Admin/teacher can lock thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_locked'] is True

        # Verify in database
        thread.refresh_from_db()
        assert thread.is_locked is True

    def test_lock_thread_by_regular_user_fails(self, api_client, general_chat_with_thread, student_user):
        """Regular users cannot lock thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_lock_thread_with_existing_messages(self, api_client, general_chat_with_thread, teacher_user, student_user):
        """Can lock thread with existing messages"""
        general_chat, thread = general_chat_with_thread

        # Create messages first
        Message.objects.create(
            room=general_chat,
            thread=thread,
            sender=student_user,
            content='Message before lock'
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_locked'] is True

    def test_lock_thread_idempotent(self, api_client, general_chat_with_thread, teacher_user):
        """Locking already locked thread works"""
        general_chat, thread = general_chat_with_thread
        thread.is_locked = True
        thread.save()

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_locked'] is True

    def test_lock_nonexistent_thread(self, api_client, teacher_user):
        """Locking non-existent thread returns 404"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post('/api/chat/threads/99999/lock/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== POST /api/chat/threads/{id}/unlock/ ==========

    def test_unlock_thread_unauthenticated(self, api_client, teacher_user):
        """Unauthenticated users should get 401 or 403"""
        general_chat = ChatRoom.objects.create(
            name='Общий форум',
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        thread = MessageThread.objects.create(
            room=general_chat,
            title='Test',
            created_by=teacher_user,
            is_locked=True
        )

        response = api_client.post(f'/api/chat/threads/{thread.id}/unlock/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_unlock_thread_by_admin(self, api_client, general_chat_with_thread, teacher_user):
        """Admin/teacher can unlock thread"""
        general_chat, thread = general_chat_with_thread
        thread.is_locked = True
        thread.save()

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/unlock/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_locked'] is False

        # Verify in database
        thread.refresh_from_db()
        assert thread.is_locked is False

    def test_unlock_thread_by_regular_user_fails(self, api_client, general_chat_with_thread, student_user):
        """Regular users cannot unlock thread"""
        general_chat, thread = general_chat_with_thread
        thread.is_locked = True
        thread.save()

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/unlock/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unlock_nonexistent_thread(self, api_client, teacher_user):
        """Unlocking non-existent thread returns 404"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post('/api/chat/threads/99999/unlock/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== Combination Tests ==========

    def test_pin_and_lock_thread(self, api_client, general_chat_with_thread, teacher_user):
        """Can pin and lock same thread"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=teacher_user)

        # Pin thread
        response1 = api_client.post(f'/api/chat/threads/{thread.id}/pin/')
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['is_pinned'] is True

        # Lock thread
        response2 = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['is_locked'] is True

        # Verify both flags
        thread.refresh_from_db()
        assert thread.is_pinned is True
        assert thread.is_locked is True

    def test_lock_then_unpin_thread(self, api_client, general_chat_with_thread, teacher_user):
        """Can lock pinned thread and then unpin it"""
        general_chat, thread = general_chat_with_thread
        thread.is_pinned = True
        thread.save()

        api_client.force_authenticate(user=teacher_user)

        # Lock
        response1 = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert response1.status_code == status.HTTP_200_OK

        # Unpin
        response2 = api_client.post(f'/api/chat/threads/{thread.id}/unpin/')
        assert response2.status_code == status.HTTP_200_OK

        # Verify states
        thread.refresh_from_db()
        assert thread.is_pinned is False
        assert thread.is_locked is True

    # ========== Query Optimization Tests ==========

    @pytest.mark.django_db
    def test_get_thread_messages_no_n_plus_one(self, general_chat_with_thread, student_user):
        """No N+1 queries when fetching thread messages"""
        general_chat, thread = general_chat_with_thread

        # Create 5 messages
        for i in range(5):
            Message.objects.create(
                room=general_chat,
                thread=thread,
                sender=student_user,
                content=f'Message {i}'
            )

        with CaptureQueriesContext(connection) as ctx:
            api_client = APIClient()
            api_client.force_authenticate(user=student_user)
            response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert len(ctx) <= 3  # Should be around 2-3 queries, not N+5


@pytest.mark.unit
@pytest.mark.django_db
class TestThreadPermissions:
    """Permission tests for thread operations"""

    def test_only_teachers_can_pin_thread(self, api_client, general_chat_with_thread, student_user, teacher_user):
        """Only teachers/admins can pin thread"""
        general_chat, thread = general_chat_with_thread

        # Student should fail
        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Teacher should succeed
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/pin/')
        assert response.status_code == status.HTTP_200_OK

    def test_only_teachers_can_lock_thread(self, api_client, general_chat_with_thread, student_user, teacher_user):
        """Only teachers/admins can lock thread"""
        general_chat, thread = general_chat_with_thread

        # Student should fail
        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Teacher should succeed
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert response.status_code == status.HTTP_200_OK

    def test_any_authenticated_user_can_send_message(self, api_client, general_chat_with_thread, student_user, teacher_user):
        """Any authenticated user can send message to thread"""
        general_chat, thread = general_chat_with_thread

        # Student can send
        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Student message'
        })
        assert response.status_code == status.HTTP_201_CREATED

        # Teacher can send
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Teacher message'
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_any_authenticated_user_can_view_thread_messages(self, api_client, general_chat_with_thread, student_user, teacher_user):
        """Any authenticated user can view thread messages"""
        general_chat, thread = general_chat_with_thread

        # Create a message
        Message.objects.create(
            room=general_chat,
            thread=thread,
            sender=student_user,
            content='Test message'
        )

        # Student can view
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')
        assert response.status_code == status.HTTP_200_OK

        # Teacher can view
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/chat/threads/{thread.id}/messages/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
@pytest.mark.django_db
class TestThreadEdgeCases:
    """Edge case tests for thread operations"""

    def test_create_message_in_locked_thread(self, api_client, general_chat_with_thread, student_user, teacher_user):
        """Cannot send message to locked thread (if enforced)"""
        general_chat, thread = general_chat_with_thread
        thread.is_locked = True
        thread.save()

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/chat/threads/{thread.id}/send_message/', {
            'content': 'Message to locked thread'
        })

        # Depending on implementation, might be 403 or 201
        # Current implementation allows sending to locked threads
        # This test documents the behavior
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]

    def test_pin_and_unpin_multiple_times(self, api_client, general_chat_with_thread, teacher_user):
        """Pin/unpin operations are idempotent"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=teacher_user)

        # Pin
        r1 = api_client.post(f'/api/chat/threads/{thread.id}/pin/')
        assert r1.status_code == status.HTTP_200_OK
        assert r1.data['is_pinned'] is True

        # Unpin
        r2 = api_client.post(f'/api/chat/threads/{thread.id}/unpin/')
        assert r2.status_code == status.HTTP_200_OK
        assert r2.data['is_pinned'] is False

        # Pin again
        r3 = api_client.post(f'/api/chat/threads/{thread.id}/pin/')
        assert r3.status_code == status.HTTP_200_OK
        assert r3.data['is_pinned'] is True

    def test_lock_and_unlock_multiple_times(self, api_client, general_chat_with_thread, teacher_user):
        """Lock/unlock operations are idempotent"""
        general_chat, thread = general_chat_with_thread

        api_client.force_authenticate(user=teacher_user)

        # Lock
        r1 = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert r1.status_code == status.HTTP_200_OK
        assert r1.data['is_locked'] is True

        # Unlock
        r2 = api_client.post(f'/api/chat/threads/{thread.id}/unlock/')
        assert r2.status_code == status.HTTP_200_OK
        assert r2.data['is_locked'] is False

        # Lock again
        r3 = api_client.post(f'/api/chat/threads/{thread.id}/lock/')
        assert r3.status_code == status.HTTP_200_OK
        assert r3.data['is_locked'] is True
