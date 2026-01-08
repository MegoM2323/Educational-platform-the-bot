"""
Integration tests for Chat API endpoints.
Tests complete workflows through REST API and WebSocket.
"""
import pytest
import json
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from django.utils import timezone

from chat.models import ChatRoom, ChatParticipant, Message
from chat.services.chat_service import ChatService
from chat.services.message_service import MessageService


@pytest.mark.django_db
class TestChatAPIList:
    """Tests for GET /api/chat/ endpoint"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(
            username='api_student',
            password='testpass',
            role='student'
        )
        self.teacher = User.objects.create(
            username='api_teacher',
            password='testpass',
            role='teacher'
        )

    def test_list_chats_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.get('/api/chat/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_chats_empty(self):
        """Test listing chats when user has none"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/chat/')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 0
        assert response.json()['results'] == []

    def test_list_chats_with_chats(self):
        """Test listing user's chats"""
        self.client.force_authenticate(user=self.student)

        # Create chat
        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=self.student)
        ChatParticipant.objects.create(room=room, user=self.teacher)

        response = self.client.get('/api/chat/')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 1
        assert len(response.json()['results']) == 1

    def test_list_chats_pagination(self):
        """Test chat list pagination"""
        self.client.force_authenticate(user=self.student)

        # Create multiple chats
        for i in range(25):
            teacher = User.objects.create(username=f'teacher{i}', role='teacher')
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=self.student)
            ChatParticipant.objects.create(room=room, user=teacher)

        # First page
        response = self.client.get('/api/chat/?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 25
        assert response.json()['page'] == 1
        assert response.json()['page_size'] == 10
        assert len(response.json()['results']) == 10

    def test_list_chats_orders_by_recent(self):
        """Test that chats are ordered by most recent"""
        self.client.force_authenticate(user=self.student)

        # Create first chat and send message
        room1 = ChatRoom.objects.create(is_active=True)
        teacher1 = User.objects.create(username='teacher_a', role='teacher')
        ChatParticipant.objects.create(room=room1, user=self.student)
        ChatParticipant.objects.create(room=room1, user=teacher1)
        MessageService.send_message(self.student, room1, "Old message")

        # Create second chat and send message
        room2 = ChatRoom.objects.create(is_active=True)
        teacher2 = User.objects.create(username='teacher_b', role='teacher')
        ChatParticipant.objects.create(room=room2, user=self.student)
        ChatParticipant.objects.create(room=room2, user=teacher2)
        MessageService.send_message(self.student, room2, "New message")

        response = self.client.get('/api/chat/')

        assert response.status_code == status.HTTP_200_OK
        results = response.json()['results']
        assert results[0]['id'] == room2.id
        assert results[1]['id'] == room1.id


@pytest.mark.django_db
class TestChatAPICreate:
    """Tests for POST /api/chat/ endpoint"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(
            username='api_student2',
            password='testpass',
            role='student'
        )
        self.teacher = User.objects.create(
            username='api_teacher2',
            password='testpass',
            role='teacher'
        )

    def test_create_chat_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.post('/api/chat/', {'recipient_id': self.teacher.id})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_chat_missing_recipient(self):
        """Test that missing recipient_id is rejected"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/chat/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'recipient_id' in response.json()['error']['message']

    def test_create_chat_invalid_recipient(self):
        """Test that invalid recipient_id is rejected"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/chat/', {'recipient_id': 99999})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_chat_success(self):
        """Test successful chat creation"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/chat/', {'recipient_id': self.teacher.id})

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert 'id' in response.json()

    def test_create_chat_returns_existing(self):
        """Test that repeated creation returns existing chat"""
        self.client.force_authenticate(user=self.student)

        response1 = self.client.post('/api/chat/', {'recipient_id': self.teacher.id})
        room_id_1 = response1.json()['id']

        response2 = self.client.post('/api/chat/', {'recipient_id': self.teacher.id})
        room_id_2 = response2.json()['id']

        assert room_id_1 == room_id_2


@pytest.mark.django_db
class TestChatAPIDetail:
    """Tests for GET /api/chat/{id}/ endpoint"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(username='api_student3', role='student')
        self.teacher = User.objects.create(username='api_teacher3', role='teacher')

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.student)
        ChatParticipant.objects.create(room=self.room, user=self.teacher)

    def test_get_chat_detail_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.get(f'/api/chat/{self.room.id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_chat_detail_not_found(self):
        """Test that non-existent chat returns 404"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/chat/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_chat_detail_forbidden(self):
        """Test that non-participant cannot access chat"""
        other_user = User.objects.create(username='other_user', role='student')
        self.client.force_authenticate(user=other_user)

        response = self.client.get(f'/api/chat/{self.room.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_chat_detail_success(self):
        """Test successful chat detail retrieval"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/chat/{self.room.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == self.room.id
        assert 'participants' in response.json()


@pytest.mark.django_db
class TestChatAPIMessages:
    """Tests for message endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(username='api_student4', role='student')
        self.teacher = User.objects.create(username='api_teacher4', role='teacher')

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.student)
        ChatParticipant.objects.create(room=self.room, user=self.teacher)

    def test_get_messages_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.get(f'/api/chat/{self.room.id}/messages/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_messages_empty(self):
        """Test getting messages from empty chat"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/chat/{self.room.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['results'] == []

    def test_get_messages_with_content(self):
        """Test getting messages with content"""
        self.client.force_authenticate(user=self.student)

        MessageService.send_message(self.student, self.room, "Test message 1")
        MessageService.send_message(self.teacher, self.room, "Test message 2")

        response = self.client.get(f'/api/chat/{self.room.id}/messages/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 2

    def test_send_message_unauthorized(self):
        """Test that unauthenticated message send is rejected"""
        response = self.client.post(
            f'/api/chat/{self.room.id}/messages/',
            {'content': 'Hello!'}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_send_message_empty_fails(self):
        """Test that empty message is rejected"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f'/api/chat/{self.room.id}/messages/',
            {'content': '   '}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_message_success(self):
        """Test successful message send"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f'/api/chat/{self.room.id}/messages/',
            {'content': 'Hello!'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['content'] == 'Hello!'
        assert response.json()['sender']['id'] == self.student.id

    def test_send_message_to_inactive_chat_fails(self):
        """Test that message cannot be sent to inactive chat"""
        self.client.force_authenticate(user=self.student)
        self.room.is_active = False
        self.room.save()

        response = self.client.post(
            f'/api/chat/{self.room.id}/messages/',
            {'content': 'Hello!'}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestChatAPIMessageEdit:
    """Tests for PATCH /api/chat/{id}/messages/{msg_id}/ endpoint"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(username='api_student5', role='student')
        self.teacher = User.objects.create(username='api_teacher5', role='teacher')

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.student)
        ChatParticipant.objects.create(room=self.room, user=self.teacher)

        self.message = MessageService.send_message(
            self.student, self.room, "Original"
        )

    def test_edit_message_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.patch(
            f'/api/chat/{self.room.id}/messages/{self.message.id}/',
            {'content': 'Edited'}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_edit_message_not_author(self):
        """Test that non-author cannot edit message"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(
            f'/api/chat/{self.room.id}/messages/{self.message.id}/',
            {'content': 'Hacked!'}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_edit_message_success(self):
        """Test successful message edit"""
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f'/api/chat/{self.room.id}/messages/{self.message.id}/',
            {'content': 'Edited'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['content'] == 'Edited'
        assert response.json()['is_edited'] is True


@pytest.mark.django_db
class TestChatAPIMessageDelete:
    """Tests for DELETE /api/chat/{id}/messages/{msg_id}/ endpoint"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(username='api_student6', role='student')
        self.teacher = User.objects.create(username='api_teacher6', role='teacher')

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.student)
        ChatParticipant.objects.create(room=self.room, user=self.teacher)

        self.message = MessageService.send_message(
            self.student, self.room, "To delete"
        )

    def test_delete_message_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.delete(
            f'/api/chat/{self.room.id}/messages/{self.message.id}/'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_message_not_author(self):
        """Test that non-author cannot delete message"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.delete(
            f'/api/chat/{self.room.id}/messages/{self.message.id}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_message_success(self):
        """Test successful message deletion"""
        self.client.force_authenticate(user=self.student)
        response = self.client.delete(
            f'/api/chat/{self.room.id}/messages/{self.message.id}/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete
        self.message.refresh_from_db()
        assert self.message.is_deleted is True


@pytest.mark.django_db
class TestChatAPIRead:
    """Tests for POST /api/chat/{id}/read/ endpoint"""

    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create(username='api_student7', role='student')
        self.teacher = User.objects.create(username='api_teacher7', role='teacher')

        self.room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.room, user=self.student)
        ChatParticipant.objects.create(room=self.room, user=self.teacher)

    def test_mark_as_read_unauthorized(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.post(f'/api/chat/{self.room.id}/read/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_mark_as_read_success(self):
        """Test marking chat as read"""
        self.client.force_authenticate(user=self.student)

        # Add message
        MessageService.send_message(self.teacher, self.room, "New message")

        # Mark as read
        response = self.client.post(f'/api/chat/{self.room.id}/read/')

        assert response.status_code == status.HTTP_200_OK
        assert 'last_read_at' in response.json()

        # Verify
        participant = ChatParticipant.objects.get(room=self.room, user=self.student)
        assert participant.last_read_at is not None


@pytest.mark.django_db
class TestChatAPICompleteWorkflow:
    """Integration tests for complete chat workflow"""

    def test_full_chat_workflow(self):
        """Test complete chat workflow: create, send, edit, delete messages"""
        client = APIClient()
        student = User.objects.create(username='workflow_student', role='student')
        teacher = User.objects.create(username='workflow_teacher', role='teacher')

        client.force_authenticate(user=student)

        # 1. Create chat
        response = client.post('/api/chat/', {'recipient_id': teacher.id})
        assert response.status_code in [200, 201]
        room_id = response.json()['id']

        # 2. List chats
        response = client.get('/api/chat/')
        assert response.status_code == 200
        assert response.json()['count'] == 1

        # 3. Send message
        response = client.post(
            f'/api/chat/{room_id}/messages/',
            {'content': 'Hello teacher!'}
        )
        assert response.status_code == 201
        message_id = response.json()['id']

        # 4. Get messages
        response = client.get(f'/api/chat/{room_id}/messages/')
        assert response.status_code == 200
        assert len(response.json()['results']) == 1

        # 5. Edit message
        response = client.patch(
            f'/api/chat/{room_id}/messages/{message_id}/',
            {'content': 'Hello teacher! (updated)'}
        )
        assert response.status_code == 200
        assert response.json()['is_edited'] is True

        # 6. Mark as read
        response = client.post(f'/api/chat/{room_id}/read/')
        assert response.status_code == 200

        # 7. Delete message
        response = client.delete(f'/api/chat/{room_id}/messages/{message_id}/')
        assert response.status_code == 204

        # 8. Verify deletion
        response = client.get(f'/api/chat/{room_id}/messages/')
        assert response.status_code == 200
        assert len(response.json()['results']) == 0
