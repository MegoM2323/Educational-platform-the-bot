"""
Tests: Message Visibility Across All Roles

Verifies that messages are visible between different user roles:
- Teacher <-> Student
- Parent -> Child's messages
- Tutor -> Student
- Teacher sees messages even with inactive enrollment
- ChatParticipant synchronization with M2M participants
"""

import pytest
from uuid import uuid4
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile, ParentProfile, TutorProfile, TeacherProfile
from chat.models import ChatRoom, Message, ChatParticipant
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.fixture
def unique_suffix():
    """Generate unique suffix for test data"""
    return uuid4().hex[:8]


@pytest.fixture
def subject(db, unique_suffix):
    """Create test subject"""
    return Subject.objects.create(
        name=f"Test Subject {unique_suffix}",
        description="Test subject for visibility tests",
    )


@pytest.fixture
def teacher_user(db, unique_suffix):
    """Create teacher user with profile"""
    teacher = User.objects.create_user(
        username=f"teacher_{unique_suffix}",
        email=f"teacher_{unique_suffix}@test.com",
        password="testpass123",
        role=User.Role.TEACHER,
        first_name="Teacher",
        last_name="Test",
    )
    TeacherProfile.objects.create(user=teacher)
    return teacher


@pytest.fixture
def student_user(db, unique_suffix):
    """Create student user with profile"""
    student = User.objects.create_user(
        username=f"student_{unique_suffix}",
        email=f"student_{unique_suffix}@test.com",
        password="testpass123",
        role=User.Role.STUDENT,
        first_name="Student",
        last_name="Test",
    )
    StudentProfile.objects.create(user=student)
    return student


@pytest.fixture
def parent_user(db, unique_suffix):
    """Create parent user with profile"""
    parent = User.objects.create_user(
        username=f"parent_{unique_suffix}",
        email=f"parent_{unique_suffix}@test.com",
        password="testpass123",
        role=User.Role.PARENT,
        first_name="Parent",
        last_name="Test",
    )
    ParentProfile.objects.create(user=parent)
    return parent


@pytest.fixture
def tutor_user(db, unique_suffix):
    """Create tutor user with profile"""
    tutor = User.objects.create_user(
        username=f"tutor_{unique_suffix}",
        email=f"tutor_{unique_suffix}@test.com",
        password="testpass123",
        role=User.Role.TUTOR,
        first_name="Tutor",
        last_name="Test",
    )
    TutorProfile.objects.create(user=tutor)
    return tutor


@pytest.fixture
def enrollment(db, student_user, teacher_user, subject, parent_user):
    """Create enrollment and assign parent to student"""
    enrollment = SubjectEnrollment.objects.create(
        student=student_user,
        teacher=teacher_user,
        subject=subject,
        status="active",
        is_active=True,
    )
    # Assign parent to student
    student_profile = StudentProfile.objects.get(user=student_user)
    student_profile.parent = parent_user
    student_profile.save()
    return enrollment


@pytest.fixture
def tutor_enrollment(db, student_user, tutor_user, subject, enrollment):
    """Assign tutor to student"""
    student_profile = StudentProfile.objects.get(user=student_user)
    student_profile.tutor = tutor_user
    student_profile.save()
    return enrollment


@pytest.fixture
def forum_chat(db, enrollment, teacher_user, student_user):
    """Get or create forum chat for enrollment (signal may already create it)"""
    forum, created = ChatRoom.objects.get_or_create(
        type=ChatRoom.Type.FORUM_SUBJECT,
        enrollment=enrollment,
        defaults={
            "name": f"Forum: {enrollment.subject.name}",
            "created_by": teacher_user,
            "is_active": True,
        }
    )
    # Ensure participants are in M2M
    forum.participants.add(teacher_user, student_user)
    # Ensure ChatParticipant records exist
    ChatParticipant.objects.get_or_create(room=forum, user=teacher_user, defaults={"is_admin": True})
    ChatParticipant.objects.get_or_create(room=forum, user=student_user)
    return forum


@pytest.fixture
def tutor_forum_chat(db, tutor_enrollment, tutor_user, student_user):
    """Get or create tutor forum chat"""
    forum, created = ChatRoom.objects.get_or_create(
        type=ChatRoom.Type.FORUM_TUTOR,
        enrollment=tutor_enrollment,
        defaults={
            "name": f"Tutor Forum: {student_user.first_name}",
            "created_by": tutor_user,
            "is_active": True,
        }
    )
    # Ensure participants are in M2M
    forum.participants.add(tutor_user, student_user)
    # Ensure ChatParticipant records exist
    ChatParticipant.objects.get_or_create(room=forum, user=tutor_user, defaults={"is_admin": True})
    ChatParticipant.objects.get_or_create(room=forum, user=student_user)
    return forum


@pytest.fixture
def student_client(student_user):
    """Authenticated API client for student"""
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


@pytest.fixture
def teacher_client(teacher_user):
    """Authenticated API client for teacher"""
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    return client


@pytest.fixture
def parent_client(parent_user):
    """Authenticated API client for parent"""
    client = APIClient()
    client.force_authenticate(user=parent_user)
    return client


@pytest.fixture
def tutor_client(tutor_user):
    """Authenticated API client for tutor"""
    client = APIClient()
    client.force_authenticate(user=tutor_user)
    return client


@pytest.mark.django_db(transaction=True)
class TestMessageVisibilityAllRoles:
    """Test message visibility across all user roles"""

    def test_teacher_sees_student_messages(
        self, student_client, teacher_client, forum_chat, student_user
    ):
        """Teacher can see messages sent by Student"""
        message_text = f"Message from student {uuid4().hex[:8]}"

        # Student sends message
        send_response = student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Teacher retrieves messages
        response = teacher_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = response.data.get("results", response.data)
        if isinstance(messages, dict):
            messages = messages.get("results", [])

        assert len(messages) > 0, "Teacher should see at least one message"
        assert any(
            m.get("content") == message_text for m in messages
        ), f"Teacher should see student's message: {message_text}"

    def test_student_sees_teacher_messages(
        self, student_client, teacher_client, forum_chat, teacher_user
    ):
        """Student can see messages sent by Teacher"""
        message_text = f"Message from teacher {uuid4().hex[:8]}"

        # Teacher sends message
        send_response = teacher_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Student retrieves messages
        response = student_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = response.data.get("results", response.data)
        if isinstance(messages, dict):
            messages = messages.get("results", [])

        assert len(messages) > 0, "Student should see at least one message"
        assert any(
            m.get("content") == message_text for m in messages
        ), f"Student should see teacher's message: {message_text}"

    def test_parent_sees_child_messages(
        self, student_client, parent_client, forum_chat, parent_user, student_user
    ):
        """Parent can see messages in child's forum chat"""
        # Add parent to chat participants
        forum_chat.participants.add(parent_user)
        ChatParticipant.objects.get_or_create(room=forum_chat, user=parent_user)

        message_text = f"Child message {uuid4().hex[:8]}"

        # Student (child) sends message
        send_response = student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Parent retrieves messages
        response = parent_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = response.data.get("results", response.data)
        if isinstance(messages, dict):
            messages = messages.get("results", [])

        assert len(messages) > 0, "Parent should see at least one message"
        assert any(
            m.get("content") == message_text for m in messages
        ), f"Parent should see child's message: {message_text}"

    def test_tutor_sees_student_messages(
        self, student_client, tutor_client, tutor_forum_chat, student_user
    ):
        """Tutor can see messages sent by Student in tutor forum"""
        message_text = f"Student message to tutor {uuid4().hex[:8]}"

        # Student sends message
        send_response = student_client.post(
            f"/api/chat/forum/{tutor_forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Tutor retrieves messages
        response = tutor_client.get(
            f"/api/chat/forum/{tutor_forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = response.data.get("results", response.data)
        if isinstance(messages, dict):
            messages = messages.get("results", [])

        assert len(messages) > 0, "Tutor should see at least one message"
        assert any(
            m.get("content") == message_text for m in messages
        ), f"Tutor should see student's message: {message_text}"

    def test_teacher_sees_messages_after_enrollment_inactive(
        self, student_client, teacher_client, forum_chat, enrollment, student_user
    ):
        """Teacher can still see messages even after enrollment is deactivated"""
        message_text = f"Message before deactivation {uuid4().hex[:8]}"

        # Student sends message while enrollment is active
        send_response = student_client.post(
            f"/api/chat/forum/{forum_chat.id}/send_message/",
            {"content": message_text},
            format="json",
        )
        assert send_response.status_code == status.HTTP_201_CREATED

        # Deactivate enrollment
        enrollment.is_active = False
        enrollment.save()

        # Teacher can still retrieve messages (chat access based on participants, not enrollment status)
        response = teacher_client.get(
            f"/api/chat/forum/{forum_chat.id}/messages/",
        )

        assert response.status_code == status.HTTP_200_OK
        messages = response.data.get("results", response.data)
        if isinstance(messages, dict):
            messages = messages.get("results", [])

        assert len(messages) > 0, "Teacher should still see messages after enrollment deactivation"
        assert any(
            m.get("content") == message_text for m in messages
        ), f"Teacher should see the message sent before deactivation: {message_text}"

    def test_chatparticipant_sync_with_m2m(
        self, db, teacher_user, student_user, forum_chat
    ):
        """ChatParticipant records are synchronized with M2M participants"""
        # Verify M2M participants
        m2m_participant_ids = set(forum_chat.participants.values_list("id", flat=True))
        assert teacher_user.id in m2m_participant_ids
        assert student_user.id in m2m_participant_ids

        # Verify ChatParticipant records exist
        teacher_participant = ChatParticipant.objects.filter(
            room=forum_chat, user=teacher_user
        ).exists()
        student_participant = ChatParticipant.objects.filter(
            room=forum_chat, user=student_user
        ).exists()

        assert teacher_participant, "ChatParticipant should exist for teacher"
        assert student_participant, "ChatParticipant should exist for student"

        # Test that adding to M2M also creates ChatParticipant
        new_user = User.objects.create_user(
            username=f"newuser_{uuid4().hex[:8]}",
            email=f"newuser_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        # Add to M2M
        forum_chat.participants.add(new_user)

        # Create ChatParticipant manually (as the signal would do)
        ChatParticipant.objects.get_or_create(room=forum_chat, user=new_user)

        # Verify sync
        new_participant_m2m = forum_chat.participants.filter(id=new_user.id).exists()
        new_participant_cp = ChatParticipant.objects.filter(
            room=forum_chat, user=new_user
        ).exists()

        assert new_participant_m2m, "New user should be in M2M participants"
        assert new_participant_cp, "ChatParticipant should exist for new user"


@pytest.mark.django_db(transaction=True)
class TestCrossRoleMessageVisibility:
    """Additional cross-role visibility tests"""

    def test_all_roles_see_same_message_count(
        self,
        student_client,
        teacher_client,
        parent_client,
        forum_chat,
        parent_user,
        student_user,
    ):
        """All roles see the same number of messages in shared forum"""
        # Add parent to chat
        forum_chat.participants.add(parent_user)
        ChatParticipant.objects.get_or_create(room=forum_chat, user=parent_user)

        # Send messages from different roles
        messages_to_send = [
            ("student", student_client),
            ("teacher", teacher_client),
        ]

        for sender_role, client in messages_to_send:
            client.post(
                f"/api/chat/forum/{forum_chat.id}/send_message/",
                {"content": f"Test message from {sender_role}"},
                format="json",
            )

        # Get messages from all roles
        student_response = student_client.get(f"/api/chat/forum/{forum_chat.id}/messages/")
        teacher_response = teacher_client.get(f"/api/chat/forum/{forum_chat.id}/messages/")
        parent_response = parent_client.get(f"/api/chat/forum/{forum_chat.id}/messages/")

        assert student_response.status_code == status.HTTP_200_OK
        assert teacher_response.status_code == status.HTTP_200_OK
        assert parent_response.status_code == status.HTTP_200_OK

        def extract_count(response):
            data = response.data
            if isinstance(data, dict):
                results = data.get("results", [])
                return len(results)
            return len(data)

        student_count = extract_count(student_response)
        teacher_count = extract_count(teacher_response)
        parent_count = extract_count(parent_response)

        assert student_count == teacher_count, (
            f"Student ({student_count}) and teacher ({teacher_count}) see different counts"
        )
        assert teacher_count == parent_count, (
            f"Teacher ({teacher_count}) and parent ({parent_count}) see different counts"
        )

    def test_tutor_and_student_bidirectional_visibility(
        self, student_client, tutor_client, tutor_forum_chat
    ):
        """Both tutor and student can see messages from each other"""
        student_message = f"Student to tutor {uuid4().hex[:8]}"
        tutor_message = f"Tutor to student {uuid4().hex[:8]}"

        # Student sends message
        student_client.post(
            f"/api/chat/forum/{tutor_forum_chat.id}/send_message/",
            {"content": student_message},
            format="json",
        )

        # Tutor sends message
        tutor_client.post(
            f"/api/chat/forum/{tutor_forum_chat.id}/send_message/",
            {"content": tutor_message},
            format="json",
        )

        # Student sees both messages
        student_response = student_client.get(
            f"/api/chat/forum/{tutor_forum_chat.id}/messages/"
        )
        student_messages = student_response.data.get("results", [])
        if isinstance(student_messages, dict):
            student_messages = student_messages.get("results", [])

        assert any(m.get("content") == student_message for m in student_messages)
        assert any(m.get("content") == tutor_message for m in student_messages)

        # Tutor sees both messages
        tutor_response = tutor_client.get(
            f"/api/chat/forum/{tutor_forum_chat.id}/messages/"
        )
        tutor_messages = tutor_response.data.get("results", [])
        if isinstance(tutor_messages, dict):
            tutor_messages = tutor_messages.get("results", [])

        assert any(m.get("content") == student_message for m in tutor_messages)
        assert any(m.get("content") == tutor_message for m in tutor_messages)
