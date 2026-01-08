"""
Unit Tests: Forum Message Visibility Logic

Tests that verify message visibility for Student, Teacher, and Parent
using local database and test fixtures.

Coverage:
- Student can send and receive messages
- Teacher can receive student messages
- Parent can see all messages in forum
- Message filtering by chat and role
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
class TestMessageVisibility:
    """Test message visibility across roles"""

    @pytest.fixture
    def subject(self):
        """Create test subject"""
        return Subject.objects.create(
            name="Test Subject",
            description="Test subject for messaging",
        )

    @pytest.fixture
    def teacher(self):
        """Create teacher user"""
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        return teacher

    @pytest.fixture
    def student(self):
        """Create student user"""
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)
        return student

    @pytest.fixture
    def parent(self):
        """Create parent user"""
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)
        return parent

    @pytest.fixture
    def enrollment(self, student, teacher, subject, parent):
        """Create enrollment and assign parent"""
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            status="active",
        )
        # Assign parent to student
        student_profile = StudentProfile.objects.get(user=student)
        student_profile.parent = parent
        student_profile.save()
        return enrollment

    @pytest.fixture
    def forum_chat(self, enrollment, teacher):
        """Get or create forum chat from enrollment"""
        forums = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )
        if forums.exists():
            return forums.first()

        # Create forum if it doesn't exist
        forum = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
            name=f"Forum: {enrollment.subject.name}",
            created_by=teacher,
        )

        # Add participants
        for user in [enrollment.student, enrollment.teacher]:
            ChatParticipant.objects.get_or_create(
                room=forum,
                user=user,
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

    @pytest.fixture
    def parent_client(self, parent):
        """Create authenticated API client for parent"""
        client = APIClient()
        client.force_authenticate(user=parent)
        return client

    def test_student_can_send_message(
        self, student_client, forum_chat, student, teacher
    ):
        """Student can send message to forum"""
        url = f"/api/chat/forum/{forum_chat.id}/send_message/"
        message_text = "Test message from student"

        response = student_client.post(
            url,
            {"content": message_text},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        # Response may be wrapped in 'message' key
        message_data = response.data.get("message", response.data)
        assert message_data["content"] == message_text
        assert message_data["sender"]["id"] == student.id

    def test_student_can_receive_own_message(self, student_client, forum_chat, student):
        """Student can see their own message in message list"""
        message_text = "Test message from student"

        # Send message
        student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )

        # Get messages
        response = student_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        assert len(messages) > 0
        assert any(m["content"] == message_text for m in messages)

    def test_teacher_can_receive_student_message(
        self, student_client, teacher_client, forum_chat, student, teacher
    ):
        """Teacher can see student's message"""
        message_text = "Test message from student to teacher"

        # Student sends message
        send_response = student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Teacher gets messages
        response = teacher_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        assert len(messages) > 0, "Teacher message list is empty"
        assert any(
            m["content"] == message_text for m in messages
        ), f"Message '{message_text}' not found in teacher's message list"

    def test_student_can_receive_teacher_message(
        self, student_client, teacher_client, forum_chat, student, teacher
    ):
        """Student can see teacher's message"""
        message_text = "Test message from teacher to student"

        # Teacher sends message
        send_response = teacher_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Student gets messages
        response = student_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        assert len(messages) > 0, "Student message list is empty"
        assert any(
            m["content"] == message_text for m in messages
        ), f"Message '{message_text}' not found in student's message list"

    def test_parent_can_see_forum_list(self, parent_client, forum_chat, parent):
        """Parent can see forum chat list"""
        response = parent_client.get("/api/chat/forum/")

        assert response.status_code == status.HTTP_200_OK
        forums = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        assert len(forums) > 0, "Parent has no forums"

    def test_parent_can_see_forum_messages(
        self, student_client, teacher_client, parent_client, forum_chat, parent
    ):
        """Parent can see messages in forum"""
        # Add parent to chat if not already added
        ChatParticipant.objects.get_or_create(
            room=forum_chat,
            user=parent,
        )

        # Send a message first
        message_text = "Test message for parent visibility"
        student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )

        # Parent gets messages
        response = parent_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        assert len(messages) > 0, "Parent message list is empty"
        assert any(
            m["content"] == message_text for m in messages
        ), f"Message not found in parent's message list"

    def test_parent_added_to_chat_on_assignment(
        self, student, teacher, parent, subject
    ):
        """When parent assigned to student, parent added to existing chats"""
        # Create enrollment first
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            status="active",
        )

        # Get or create forum (signals will create it)
        forum, _ = ChatRoom.objects.get_or_create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
            defaults={"name": f"Forum: {subject.name}", "created_by": teacher},
        )

        # Ensure student and teacher are in forum
        ChatParticipant.objects.get_or_create(room=forum, user=student)
        ChatParticipant.objects.get_or_create(room=forum, user=teacher)

        # Now assign parent to student
        student_profile = StudentProfile.objects.get(user=student)
        student_profile.parent = parent
        student_profile.save()

        # Verify parent is in chat participants
        parent_in_chat = ChatParticipant.objects.filter(
            room=forum,
            user=parent,
        ).exists()

        assert parent_in_chat, "Parent not added to chat after assignment"

    def test_multiple_students_dont_see_each_other_messages(self, teacher, subject):
        """Different students shouldn't see each other's forum messages"""
        # Create two students and enrollments
        student1 = User.objects.create_user(
            username=f"student1_{uuid4().hex[:8]}",
            email=f"student1_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student1)

        student2 = User.objects.create_user(
            username=f"student2_{uuid4().hex[:8]}",
            email=f"student2_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student2)

        # Create separate enrollments
        enroll1 = SubjectEnrollment.objects.create(
            student=student1,
            teacher=teacher,
            subject=subject,
            status="active",
        )
        enroll2 = SubjectEnrollment.objects.create(
            student=student2,
            teacher=teacher,
            subject=subject,
            status="active",
        )

        # Get or create forums (signals will create them)
        forum1, _ = ChatRoom.objects.get_or_create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enroll1,
            defaults={"name": f"Forum: {subject.name}", "created_by": teacher},
        )
        forum2, _ = ChatRoom.objects.get_or_create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enroll2,
            defaults={"name": f"Forum: {subject.name}", "created_by": teacher},
        )

        # Ensure participants are added
        ChatParticipant.objects.get_or_create(room=forum1, user=student1)
        ChatParticipant.objects.get_or_create(room=forum1, user=teacher)
        ChatParticipant.objects.get_or_create(room=forum2, user=student2)
        ChatParticipant.objects.get_or_create(room=forum2, user=teacher)

        # Student1 sends message to their forum
        client1 = APIClient()
        client1.force_authenticate(user=student1)
        message_text = "Student1 message"
        client1.post(
            f"/api/chat/forum/{forum1.id}/send_message/",
            {"content": message_text},
            format="json",
        )

        # Student2 gets their own forum messages
        client2 = APIClient()
        client2.force_authenticate(user=student2)
        response = client2.get(
            f"/api/chat/forum/{forum2.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )

        # Student2 shouldn't see Student1's message
        assert not any(
            m["content"] == message_text for m in messages
        ), "Student2 can see Student1's message"

    def test_message_count_consistency_across_roles(
        self, student_client, teacher_client, parent_client, forum_chat, parent
    ):
        """All roles see the same message count"""
        # Add parent to chat
        ChatParticipant.objects.get_or_create(
            room=forum_chat,
            user=parent,
        )

        # Send multiple messages
        messages_to_send = [
            "Message 1",
            "Message 2",
            "Message 3",
        ]

        for msg_text in messages_to_send:
            student_client.post(
                f"/api/chat/forum/{forum_chat.id}/send_message/",
                {"content": msg_text},
                format="json",
            )

        # Get messages from all roles
        student_response = student_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )
        teacher_response = teacher_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )
        parent_response = parent_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        # Extract counts
        student_messages = (
            student_response.data
            if isinstance(student_response.data, list)
            else student_response.data.get("results", [])
        )
        teacher_messages = (
            teacher_response.data
            if isinstance(teacher_response.data, list)
            else teacher_response.data.get("results", [])
        )
        parent_messages = (
            parent_response.data
            if isinstance(parent_response.data, list)
            else parent_response.data.get("results", [])
        )

        student_count = len(student_messages)
        teacher_count = len(teacher_messages)
        parent_count = len(parent_messages)

        # All should have same count
        assert (
            student_count == teacher_count == parent_count
        ), f"Message counts differ: student={student_count}, teacher={teacher_count}, parent={parent_count}"

    def test_message_serialization_includes_sender_info(
        self, student_client, forum_chat, student
    ):
        """Message includes sender information"""
        message_text = "Test message with sender info"

        response = student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        # Response may be wrapped in 'message' key
        message = response.data.get("message", response.data)

        assert "sender" in message
        assert message["sender"]["id"] == student.id
        assert "content" in message
        assert "created_at" in message
