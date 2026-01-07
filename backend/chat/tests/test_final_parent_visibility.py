"""
Final E2E Test: Parent Message Visibility in Forum Chats

Tests T002, T004, T005 integration:
- T002: Parent synchronization (add/remove from chats)
- T004: Parent can see forum chat list
- T005: Parent can get messages from chats

Scenario:
1. Create student, teacher, parent
2. Assign parent to student
3. Create enrollment (forum auto-created)
4. Verify parent is added to chat
5. Create message in forum
6. Verify parent can see chat list
7. Verify parent can see messages
"""

import pytest
from uuid import uuid4
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile, ParentProfile
from chat.models import ChatRoom, Message, ChatParticipant
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestParentMessageVisibilityE2E:
    """E2E test for parent message visibility"""

    @pytest.fixture
    def parent(self):
        """Create parent user"""
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@e2e.test",
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)
        return parent

    @pytest.fixture
    def student(self, parent):
        """Create student with parent"""
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@e2e.test",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        profile = StudentProfile.objects.create(user=student, parent=parent)
        return student

    @pytest.fixture
    def teacher(self):
        """Create teacher user"""
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@e2e.test",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        return teacher

    @pytest.fixture
    def subject(self):
        """Create subject"""
        return Subject.objects.create(name=f"Math_E2E_{uuid4().hex[:8]}")

    @pytest.fixture
    def enrollment(self, student, teacher, subject):
        """Create enrollment (forum auto-created)"""
        return SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

    @pytest.fixture
    def forum(self, enrollment):
        """Get forum chat created by signal"""
        return ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

    def test_01_parent_added_to_forum_on_enrollment(
        self, student, teacher, subject, parent
    ):
        """
        T002: Parent is automatically added to forum when enrollment created.

        Scenario:
        1. Student with parent exists
        2. Create enrollment
        3. Verify parent is in forum participants
        """
        # Verify student-parent relationship
        assert student.student_profile.parent == parent

        # Create enrollment (signals fire)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        # Get forum created by signal
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Test: Parent should be in forum participants
        assert parent in forum.participants.all(), (
            "FAIL: Parent not in forum participants after enrollment"
        )

        # Test: ChatParticipant record should exist
        assert ChatParticipant.objects.filter(
            room=forum, user=parent
        ).exists(), (
            "FAIL: ChatParticipant record missing for parent"
        )

    def test_02_parent_sees_forum_list(self, student, teacher, subject, parent):
        """
        T004: Parent can see forum chat list via API.

        Scenario:
        1. Create enrollment (forum with parent)
        2. Parent calls GET /api/chat/forum/
        3. Verify forum is in response
        """
        # Create enrollment with parent already assigned
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Parent should be in forum
        assert parent in forum.participants.all()

        # API request as parent
        client = APIClient()
        client.force_authenticate(user=parent)

        response = client.get("/api/chat/forum/")

        # Test: Request should succeed
        assert response.status_code == status.HTTP_200_OK, (
            f"FAIL: API returned {response.status_code}, response: {response.data}"
        )

        # Test: Forum should be in response (response.data might be a dict with 'results' for paginated)
        if isinstance(response.data, dict):
            # Paginated response
            chat_list = response.data.get("results", [])
        else:
            # Direct list response
            chat_list = response.data

        assert len(chat_list) > 0, "FAIL: No forums in response"

        # Find our forum in response
        forum_ids = [chat["id"] for chat in chat_list]
        assert forum.id in forum_ids, (
            "FAIL: Forum not found in parent's chat list"
        )

    def test_03_parent_gets_messages_from_forum(
        self, student, teacher, subject, parent
    ):
        """
        T005: Parent can retrieve messages from forum chat.

        Scenario:
        1. Create enrollment (forum with parent)
        2. Create message in forum from teacher
        3. Parent calls GET /api/chat/forum/{id}/messages/
        4. Verify message is in response
        """
        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Create message from teacher (field is 'sender' not 'user')
        message = Message.objects.create(
            room=forum,
            sender=teacher,
            content="Hello from teacher!",
        )

        # API request as parent
        client = APIClient()
        client.force_authenticate(user=parent)

        response = client.get(f"/api/chat/forum/{forum.id}/messages/")

        # Test: Request should succeed
        assert response.status_code == status.HTTP_200_OK, (
            f"FAIL: API returned {response.status_code}, response: {response.data}"
        )

        # Test: Message should be in response (handle paginated or direct list)
        if isinstance(response.data, dict):
            message_list = response.data.get("results", [])
        else:
            message_list = response.data

        assert len(message_list) > 0, (
            "FAIL: No messages returned for parent"
        )

        # Verify message content
        message_ids = [msg["id"] for msg in message_list]
        assert message.id in message_ids, (
            "FAIL: Message not found in parent's view"
        )

    def test_04_parent_removed_from_chat_when_unassigned(
        self, student, teacher, subject, parent
    ):
        """
        T002: Parent is removed from chats when unassigned.

        Scenario:
        1. Student with parent, enrollment exists
        2. Unassign parent
        3. Verify parent removed from forum
        """
        # Create enrollment (parent auto-added)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent is in forum
        assert parent in forum.participants.all()

        # Unassign parent
        student.student_profile.parent = None
        student.student_profile.save()

        # Refresh forum
        forum.refresh_from_db()

        # Test: Parent should be removed
        assert parent not in forum.participants.all(), (
            "FAIL: Parent not removed from forum after unassignment"
        )

        # Test: ChatParticipant should be deleted
        assert not ChatParticipant.objects.filter(
            room=forum, user=parent
        ).exists(), (
            "FAIL: ChatParticipant record not deleted"
        )

    def test_05_parent_cannot_see_chat_when_unassigned(
        self, student, teacher, subject, parent
    ):
        """
        T005: Parent cannot see forum chat list after being unassigned.

        Scenario:
        1. Parent assigned, can see forum
        2. Unassign parent
        3. Parent calls API - should NOT see forum
        """
        # Create enrollment with parent
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent sees forum before unassignment
        client = APIClient()
        client.force_authenticate(user=parent)

        response_before = client.get("/api/chat/forum/")
        chat_list_before = response_before.data if isinstance(response_before.data, list) else response_before.data.get("results", [])
        forum_ids_before = [chat["id"] for chat in chat_list_before]
        assert forum.id in forum_ids_before

        # Unassign parent
        student.student_profile.parent = None
        student.student_profile.save()

        # Re-authenticate and check
        client.force_authenticate(user=parent)
        response_after = client.get("/api/chat/forum/")
        chat_list_after = response_after.data if isinstance(response_after.data, list) else response_after.data.get("results", [])
        forum_ids_after = [chat["id"] for chat in chat_list_after]

        # Test: Forum should NOT be in list
        assert forum.id not in forum_ids_after, (
            "FAIL: Parent still sees forum after unassignment"
        )


class TestParentMessageVisibilityDjangoTest:
    """Django TestCase version for consistency"""

    @pytest.mark.django_db(transaction=True)
    def test_full_parent_lifecycle(self):
        """
        Full lifecycle test:
        1. Create parent + student with parent
        2. Create enrollment -> forum created with parent
        3. Create message
        4. Verify parent can access via API
        5. Unassign parent
        6. Verify parent cannot access via API
        """
        # Create users
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@lifecycle.test",
            password="pass",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)

        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@lifecycle.test",
            password="pass",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student, parent=parent)

        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@lifecycle.test",
            password="pass",
            role=User.Role.TEACHER,
        )

        subject = Subject.objects.create(name=f"Subject_{uuid4().hex[:8]}")

        # Create enrollment -> forum auto-created with parent
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent in forum
        assert parent in forum.participants.all()

        # Create message (field is 'sender' not 'user')
        message = Message.objects.create(
            room=forum,
            sender=teacher,
            content="Test message",
        )

        # API check - parent can see forum
        client = APIClient()
        client.force_authenticate(user=parent)

        response = client.get("/api/chat/forum/")
        assert response.status_code == status.HTTP_200_OK
        chat_list = response.data if isinstance(response.data, list) else response.data.get("results", [])
        assert forum.id in [c["id"] for c in chat_list]

        # API check - parent can see message
        response = client.get(f"/api/chat/forum/{forum.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        msg_list = response.data if isinstance(response.data, list) else response.data.get("results", [])
        assert message.id in [m["id"] for m in msg_list]

        # Unassign parent
        student.student_profile.parent = None
        student.student_profile.save()

        # Forum should not have parent anymore
        forum.refresh_from_db()
        assert parent not in forum.participants.all()

        # API check - parent cannot see forum anymore
        client.force_authenticate(user=parent)
        response = client.get("/api/chat/forum/")
        chat_list = response.data if isinstance(response.data, list) else response.data.get("results", [])
        assert forum.id not in [c["id"] for c in chat_list]
