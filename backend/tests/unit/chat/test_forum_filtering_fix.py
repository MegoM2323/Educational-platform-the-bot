"""
Unit tests for forum chat filtering fix (T715).

Verifies:
1. Teachers see ONLY forum chats for students they actually teach (enrollment-based)
2. Tutors see ONLY forum chats for students they are assigned to
3. No privacy violations (users can't see chats they shouldn't)
"""

import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from chat.models import ChatRoom
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for making authenticated requests"""
    return APIClient()


@pytest.mark.django_db
class TestForumChatFilteringFix:
    """Test suite for forum chat enrollment-based filtering"""

    def test_teacher_sees_only_enrolled_students_chats(
        self, api_client, student_user, teacher_user, tutor_user, subject
    ):
        """
        Test that teacher sees ONLY chats for students they teach.

        Privacy requirement: Teachers should not see chats for other teachers' students.
        """
        # Create another teacher and student
        other_teacher = User.objects.create_user(
            username='other_teacher',
            email='other_teacher@test.com',
            role='teacher',
            first_name='Other',
            last_name='Teacher'
        )
        other_student = User.objects.create_user(
            username='other_student',
            email='other_student@test.com',
            role='student',
            first_name='Other',
            last_name='Student'
        )

        # Create enrollments
        # teacher_user teaches student_user
        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # other_teacher teaches other_student
        enrollment2 = SubjectEnrollment.objects.create(
            student=other_student,
            subject=subject,
            teacher=other_teacher
        )

        # Verify forum chats were created
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment1
        ).exists()
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment2
        ).exists()

        # Authenticate as teacher_user
        token, _ = Token.objects.get_or_create(user=teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Get forum chats
        response = api_client.get('/api/chat/forum/')
        assert response.status_code == 200

        data = response.json()
        assert data['success'] is True

        # Teacher should see ONLY 1 chat (for student_user, not other_student)
        assert data['count'] == 1

        chat_names = [chat['name'] for chat in data['results']]
        assert any(student_user.get_full_name() in name for name in chat_names)
        assert not any(other_student.get_full_name() in name for name in chat_names)

    def test_tutor_sees_only_assigned_students_chats(
        self, api_client, student_user, teacher_user, tutor_user, subject
    ):
        """
        Test that tutor sees ONLY chats for students they are assigned to.

        Privacy requirement: Tutors should not see chats for students assigned to other tutors.
        """
        # Create another tutor and student
        other_tutor = User.objects.create_user(
            username='other_tutor',
            email='other_tutor@test.com',
            role='tutor',
            first_name='Other',
            last_name='Tutor'
        )
        other_student = User.objects.create_user(
            username='other_student',
            email='other_student@test.com',
            role='student',
            first_name='Other',
            last_name='Student'
        )

        # Assign tutors to students
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        other_student.student_profile.tutor = other_tutor
        other_student.student_profile.save()

        # Create enrollments (triggers forum chat creation)
        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=other_student,
            subject=subject,
            teacher=teacher_user
        )

        # Verify FORUM_TUTOR chats were created
        tutor_chats = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR
        )
        # Should have 2 tutor chats (one for each student-tutor pair)
        assert tutor_chats.count() == 2

        # Authenticate as tutor_user
        token, _ = Token.objects.get_or_create(user=tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Get forum chats
        response = api_client.get('/api/chat/forum/')
        assert response.status_code == 200

        data = response.json()
        assert data['success'] is True

        # Tutor should see ONLY chats with their assigned students
        # In this case: 1 FORUM_TUTOR chat with student_user
        chat_names = [chat['name'] for chat in data['results']]

        # Should see student_user's chat
        assert any(student_user.get_full_name() in name for name in chat_names)

        # Should NOT see other_student's chat
        assert not any(other_student.get_full_name() in name for name in chat_names)

    def test_student_sees_both_teacher_and_tutor_chats(
        self, api_client, student_user, teacher_user, tutor_user, subject
    ):
        """
        Test that student sees both FORUM_SUBJECT and FORUM_TUTOR chats.

        Students should see:
        - All FORUM_SUBJECT chats (with their teachers per subject)
        - FORUM_TUTOR chat (if tutor assigned)
        """
        # Assign tutor to student
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Create enrollment (triggers both forum chats)
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Verify both chat types were created
        subject_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )
        tutor_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        assert subject_chat.exists()
        assert tutor_chat.exists()

        # Authenticate as student
        token, _ = Token.objects.get_or_create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Get forum chats
        response = api_client.get('/api/chat/forum/')
        assert response.status_code == 200

        data = response.json()
        assert data['success'] is True

        # Student should see 2 chats (FORUM_SUBJECT + FORUM_TUTOR)
        assert data['count'] == 2

        # Verify chat types
        chat_types = [chat.get('type') for chat in data['results']]
        assert 'forum_subject' in chat_types
        assert 'forum_tutor' in chat_types

    def test_parent_sees_no_forum_chats(
        self, api_client, student_user, teacher_user, subject
    ):
        """
        Test that parent role has no access to forum chats.

        Privacy requirement: Parents should not see forum chats.
        """
        # Create parent user
        parent = User.objects.create_user(
            username='parent_user',
            email='parent@test.com',
            role='parent',
            first_name='Parent',
            last_name='User'
        )

        # Link student to parent
        student_user.student_profile.parent = parent
        student_user.student_profile.save()

        # Create enrollment (triggers forum chat)
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Verify forum chat exists
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT
        ).exists()

        # Authenticate as parent
        token, _ = Token.objects.get_or_create(user=parent)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Get forum chats
        response = api_client.get('/api/chat/forum/')
        assert response.status_code == 200

        data = response.json()
        assert data['success'] is True

        # Parent should see NO forum chats
        assert data['count'] == 0
        assert data['results'] == []
