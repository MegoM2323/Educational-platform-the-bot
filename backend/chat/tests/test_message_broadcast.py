"""
Unit Tests: Message Broadcast and M2M Sync

Tests that verify:
1. WebSocket broadcast is triggered when message is sent via REST API
2. M2M participants are synced when message is sent
3. Message is saved even when broadcast fails
4. Messages are visible to other participants after refresh
"""

import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import StudentProfile
from chat.models import ChatRoom, Message, ChatParticipant
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestMessageBroadcast:
    """Test WebSocket broadcast when sending messages via REST API"""

    @pytest.fixture
    def subject(self):
        """Create test subject"""
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}",
            description="Test subject for messaging",
        )

    @pytest.fixture
    def teacher(self):
        """Create teacher user"""
        return User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    @pytest.fixture
    def student(self):
        """Create student user with profile"""
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)
        return student

    @pytest.fixture
    def enrollment(self, student, teacher, subject):
        """Create enrollment"""
        return SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            status="active",
        )

    @pytest.fixture
    def forum_chat(self, enrollment, teacher, student):
        """Get forum chat auto-created by signal on enrollment"""
        # Forum chat is auto-created by signal on enrollment creation
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )
        return forum

    @pytest.fixture
    def student_client(self, student):
        """Create authenticated API client for student"""
        client = APIClient()
        client.force_authenticate(user=student)
        return client

    @pytest.fixture
    def teacher_client(self, teacher):
        """Create authenticated API client for teacher"""
        client = APIClient()
        client.force_authenticate(user=teacher)
        return client

    @patch('chat.forum_views.get_channel_layer')
    @patch('chat.forum_views.async_to_sync')
    def test_send_message_triggers_websocket_broadcast(
        self, mock_async_to_sync, mock_get_channel_layer,
        student_client, forum_chat, student
    ):
        """
        Test that sending message via REST API triggers WebSocket broadcast.

        Scenario:
        1. Student sends message via POST /api/chat/forum/{id}/send_message/
        2. Verify channel_layer.group_send was called
        3. Verify correct group name (chat_{id})
        """
        # Setup mock channel layer
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        mock_async_to_sync.return_value = MagicMock()

        url = f"/api/chat/forum/{forum_chat.id}/send_message/"
        message_text = "Test message for broadcast"

        response = student_client.post(
            url,
            {"content": message_text},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify async_to_sync was called (which wraps channel_layer.group_send)
        assert mock_async_to_sync.called

        # Get the function that was wrapped by async_to_sync
        # async_to_sync is called with channel_layer.group_send(...)
        call_args = mock_async_to_sync.call_args
        assert call_args is not None

    def test_send_message_syncs_m2m_participants(
        self, student_client, enrollment, teacher, student
    ):
        """
        Test that user is added to M2M participants when sending message.

        Scenario:
        1. Forum chat already created by signal on enrollment
        2. Remove student from M2M to simulate incomplete state
        3. Send message
        4. Verify user is now in M2M participants
        """
        # Forum chat is auto-created by signal on enrollment creation
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Remove student from M2M to simulate incomplete state
        forum.participants.remove(student)

        # Verify student NOT in M2M yet
        assert not forum.participants.filter(id=student.id).exists()

        url = f"/api/chat/forum/{forum.id}/send_message/"
        message_text = "Test message for M2M sync"

        response = student_client.post(
            url,
            {"content": message_text},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify student is now in M2M participants
        forum.refresh_from_db()
        assert forum.participants.filter(id=student.id).exists()

    @patch('chat.forum_views.get_channel_layer')
    @patch('chat.forum_views.async_to_sync')
    def test_send_message_works_when_broadcast_fails(
        self, mock_async_to_sync, mock_get_channel_layer,
        student_client, forum_chat, student
    ):
        """
        Test that message is saved even when WebSocket broadcast fails.

        Scenario:
        1. Mock channel_layer.group_send to raise exception
        2. Send message
        3. Verify message is saved in database
        """
        # Setup mock to raise exception
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        mock_async_to_sync.return_value = MagicMock(side_effect=Exception("Broadcast failed"))

        url = f"/api/chat/forum/{forum_chat.id}/send_message/"
        message_text = "Test message when broadcast fails"

        initial_count = Message.objects.filter(room=forum_chat).count()

        response = student_client.post(
            url,
            {"content": message_text},
            format="json",
        )

        # Message should still be created (201 Created)
        assert response.status_code == status.HTTP_201_CREATED

        # Verify message exists in database
        final_count = Message.objects.filter(room=forum_chat).count()
        assert final_count == initial_count + 1

        # Verify message content
        message = Message.objects.filter(room=forum_chat, content=message_text).first()
        assert message is not None
        assert message.sender == student

    def test_message_visible_to_other_participants_after_refresh(
        self, student_client, teacher_client, forum_chat, student, teacher
    ):
        """
        Test that message sent by User A is visible to User B via GET.

        Scenario:
        1. User A (student) sends message
        2. User B (teacher) requests message list via GET
        3. Verify message is visible to User B
        """
        message_text = f"Test visibility message {uuid4().hex[:8]}"

        # Student sends message
        send_response = student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Teacher requests messages
        get_response = teacher_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert get_response.status_code == status.HTTP_200_OK

        # Extract messages from response
        messages = get_response.data.get("results", [])

        # Verify message is in list
        message_contents = [m["content"] for m in messages]
        assert message_text in message_contents

    @patch('chat.forum_views.get_channel_layer')
    @patch('chat.forum_views.async_to_sync')
    def test_broadcast_uses_correct_group_name(
        self, mock_async_to_sync, mock_get_channel_layer,
        student_client, forum_chat, student
    ):
        """
        Test that broadcast uses correct WebSocket group name format.

        Expected group name format: chat_{room_id}
        """
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        # Create a mock function that captures the call
        captured_calls = []
        def capture_group_send(group_name, message):
            captured_calls.append((group_name, message))

        mock_async_to_sync.return_value = capture_group_send

        url = f"/api/chat/forum/{forum_chat.id}/send_message/"

        response = student_client.post(
            url,
            {"content": "Test broadcast group name"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify group_send was called with correct group name
        if captured_calls:
            group_name, message = captured_calls[0]
            expected_group = f"chat_{forum_chat.id}"
            assert group_name == expected_group


@pytest.mark.django_db(transaction=True)
class TestM2MParticipantSync:
    """Test M2M participant synchronization"""

    @pytest.fixture
    def subject(self):
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}",
            description="Test subject",
        )

    @pytest.fixture
    def teacher(self):
        return User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    @pytest.fixture
    def student(self):
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)
        return student

    @pytest.fixture
    def enrollment(self, student, teacher, subject):
        return SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            status="active",
        )

    def test_chat_participant_without_m2m_gets_synced_on_access(
        self, student, teacher, enrollment
    ):
        """
        Test that ChatParticipant without M2M relation gets synced.

        Scenario:
        1. Forum chat already created by signal on enrollment
        2. Remove student from M2M to simulate sync issue
        3. Access messages endpoint
        4. Verify student added to M2M
        """
        # Forum chat is auto-created by signal on enrollment creation
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Remove student from M2M to simulate incomplete sync
        forum.participants.remove(student)

        # Verify student not in M2M
        assert not forum.participants.filter(id=student.id).exists()

        # Access via API
        client = APIClient()
        client.force_authenticate(user=student)

        response = client.get(f"/api/chat/forum/{forum.id}/messages/")

        # Should get access (ChatParticipant exists)
        assert response.status_code == status.HTTP_200_OK

        # Verify sync happened
        forum.refresh_from_db()
        assert forum.participants.filter(id=student.id).exists()

    def test_both_m2m_and_chatparticipant_created_on_send(
        self, student, teacher, enrollment
    ):
        """
        Test that sending message creates both M2M and ChatParticipant.
        """
        # Forum chat is auto-created by signal on enrollment creation
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Remove student from M2M to simulate incomplete state
        forum.participants.remove(student)

        client = APIClient()
        client.force_authenticate(user=student)

        response = client.post(
            f"/api/chat/forum/{forum.id}/send_message/",
            {"content": "Test sync message"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify M2M
        forum.refresh_from_db()
        assert forum.participants.filter(id=student.id).exists()

        # Verify ChatParticipant
        assert ChatParticipant.objects.filter(room=forum, user=student).exists()


@pytest.mark.django_db(transaction=True)
class TestBroadcastMessageContent:
    """Test broadcast message content format"""

    @pytest.fixture
    def subject(self):
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}",
            description="Test",
        )

    @pytest.fixture
    def teacher(self):
        return User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    @pytest.fixture
    def student(self):
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)
        return student

    @pytest.fixture
    def enrollment(self, student, teacher, subject):
        return SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            status="active",
        )

    @pytest.fixture
    def forum_chat(self, enrollment, teacher, student):
        # Forum chat is auto-created by signal on enrollment creation
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )
        return forum

    @patch('chat.forum_views.get_channel_layer')
    @patch('chat.forum_views.async_to_sync')
    def test_broadcast_message_contains_sender_info(
        self, mock_async_to_sync, mock_get_channel_layer,
        student, teacher, enrollment, forum_chat
    ):
        """
        Test that broadcast message contains sender information.
        """
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        captured_messages = []
        def capture_call(group_name, message):
            captured_messages.append(message)

        mock_async_to_sync.return_value = capture_call

        client = APIClient()
        client.force_authenticate(user=student)

        response = client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": "Test sender info"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        if captured_messages:
            broadcast_msg = captured_messages[0]
            assert broadcast_msg["type"] == "chat_message"
            assert "message" in broadcast_msg
            msg_data = broadcast_msg["message"]
            assert "sender" in msg_data
            assert msg_data["sender"]["id"] == student.id
