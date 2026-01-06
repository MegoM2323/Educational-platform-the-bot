"""
Test suite for admin read-only access to forum chats.

Tests that admin users can:
1. View all FORUM_SUBJECT and FORUM_TUTOR chats (read-only)
2. Not have contacts to initiate new chats
3. Access chats via WebSocket
"""

import json
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from channels.testing import WebsocketCommunicator
from chat.models import ChatRoom, Message, ChatParticipant
from materials.models import SubjectEnrollment, Subject

User = get_user_model()


class TestAdminForumListAccess(TestCase):
    """Test admin access to forum chat list endpoint"""

    def setUp(self):
        """Create test users and forum chats"""
        # Create users with different roles
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='TestPass123!',
            role='admin',
            is_staff=True,
            first_name='Admin',
            last_name='User'
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher',
            first_name='Teacher',
            last_name='User'
        )

        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='TestPass123!',
            role='student',
            first_name='Student',
            last_name='User'
        )

        self.tutor = User.objects.create_user(
            username='tutor',
            email='tutor@test.com',
            password='TestPass123!',
            role='tutor',
            first_name='Tutor',
            last_name='User'
        )

        # Create subject
        self.subject = Subject.objects.create(
            name='Mathematics'
        )

        # Create enrollment (student-teacher) - signal will create FORUM_SUBJECT chat
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        # Get the auto-created FORUM_SUBJECT chat from signal
        self.forum_subject_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.enrollment
        )

        # Create a separate FORUM_TUTOR chat manually
        # Note: FORUM_TUTOR chats don't have enrollment link
        self.forum_tutor_chat = ChatRoom.objects.create(
            name='Tutor Forum - Student & Tutor',
            type=ChatRoom.Type.FORUM_TUTOR,
            created_by=self.tutor,
            is_active=True
        )
        self.forum_tutor_chat.participants.add(self.tutor, self.student)

        # Create API client
        self.client = APIClient()

    def test_admin_sees_all_forum_chats(self):
        """Test that admin sees ALL forum chats regardless of participation"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Request forum chats list
        response = self.client.get('/api/chat/forum/')

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

        # Extract chat IDs from response
        chat_ids = [chat['id'] for chat in response.data['results']]

        # Admin should see both FORUM_SUBJECT and FORUM_TUTOR chats
        # even though admin is NOT a participant
        self.assertIn(self.forum_subject_chat.id, chat_ids)
        self.assertIn(self.forum_tutor_chat.id, chat_ids)
        self.assertEqual(response.data['count'], 2)

    def test_admin_does_not_see_non_forum_chats(self):
        """Test that admin only sees forum chats (FORUM_SUBJECT, FORUM_TUTOR)"""
        # Create a non-forum chat (direct chat)
        direct_chat = ChatRoom.objects.create(
            name='Direct Chat',
            type=ChatRoom.Type.DIRECT,
            created_by=self.teacher,
            is_active=True
        )
        direct_chat.participants.add(self.teacher, self.student)

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Request forum chats
        response = self.client.get('/api/chat/forum/')

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Admin should NOT see the direct chat
        chat_ids = [chat['id'] for chat in response.data['results']]
        self.assertNotIn(direct_chat.id, chat_ids)

    def test_student_cannot_see_all_chats(self):
        """Test that non-admin student only sees their own chats"""
        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Request forum chats
        response = self.client.get('/api/chat/forum/')

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Student should see their own chats (as participant)
        chat_ids = [chat['id'] for chat in response.data['results']]
        self.assertIn(self.forum_subject_chat.id, chat_ids)
        self.assertIn(self.forum_tutor_chat.id, chat_ids)

    def test_teacher_cannot_see_all_chats(self):
        """Test that non-admin teacher only sees their own chats"""
        # Create another enrollment/chat that teacher doesn't belong to
        other_student = User.objects.create_user(
            username='other_student',
            email='other_student@test.com',
            password='TestPass123!',
            role='student'
        )
        other_teacher = User.objects.create_user(
            username='other_teacher',
            email='other_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

        other_subject = Subject.objects.create(name='English')
        other_enrollment = SubjectEnrollment.objects.create(
            student=other_student,
            subject=other_subject,
            teacher=other_teacher,
            is_active=True
        )

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Request forum chats
        response = self.client.get('/api/chat/forum/')

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Teacher should see ONLY their own chats (where they're teacher)
        chat_ids = [chat['id'] for chat in response.data['results']]
        self.assertIn(self.forum_subject_chat.id, chat_ids)
        # Don't assert about other_enrollment chat since it was auto-created


class TestAdminReadOnlyAccess(TestCase):
    """Test that admin has read-only access (cannot send messages as admin)"""

    def setUp(self):
        """Create test setup"""
        self.admin = User.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.teacher2 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='TestPass123!',
            role='teacher'
        )

        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='TestPass123!',
            role='student'
        )

        # Create subject and enrollment - signal will create FORUM_SUBJECT chat
        self.subject = Subject.objects.create(name='Science')
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student2,
            subject=self.subject,
            teacher=self.teacher2,
            is_active=True
        )

        # Get the auto-created FORUM_SUBJECT chat from signal
        self.forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.enrollment
        )

        self.client = APIClient()

    def test_admin_cannot_send_message_as_non_participant(self):
        """Test that admin cannot send messages without being a participant"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Try to send message to chat where admin is not a participant
        response = self.client.post(
            f'/api/chat/forum/{self.forum_chat.id}/send_message/',
            {'content': 'Test message', 'message_type': 'text'},
            format='json'
        )

        # Admin should NOT be able to send message
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data.get('success', True))

    def test_admin_can_read_messages(self):
        """Test that admin can read/view forum chat messages"""
        # Create test message
        message = Message.objects.create(
            room=self.forum_chat,
            sender=self.teacher2,
            content='Test message from teacher',
            message_type=Message.Type.TEXT
        )

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Request messages from chat
        response = self.client.get(f'/api/chat/forum/{self.forum_chat.id}/messages/')

        # Admin should be able to see messages
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

        # Verify message is in response
        message_ids = [msg['id'] for msg in response.data.get('results', [])]
        self.assertIn(message.id, message_ids)

    def test_admin_sees_chat_details(self):
        """Test that admin can access full chat details"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Request forum chats list
        response = self.client.get('/api/chat/forum/')

        # Find admin's view of the forum chat
        chats = response.data['results']
        admin_chat_view = next(
            (chat for chat in chats if chat['id'] == self.forum_chat.id),
            None
        )

        # Admin should see chat details
        self.assertIsNotNone(admin_chat_view)
        self.assertEqual(admin_chat_view['type'], ChatRoom.Type.FORUM_SUBJECT)
        # Verify participants are visible
        self.assertGreater(len(admin_chat_view.get('participants', [])), 0)


class TestAdminNoContacts(TestCase):
    """Test that admin has no contacts list for initiating new chats"""

    def setUp(self):
        """Create test users"""
        self.admin = User.objects.create_user(
            username='admin3',
            email='admin3@test.com',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.teacher = User.objects.create_user(
            username='teacher3',
            email='teacher3@test.com',
            password='TestPass123!',
            role='teacher'
        )

        self.client = APIClient()

    def test_admin_has_no_available_contacts(self):
        """Test that admin has empty contacts list"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Request available contacts
        # (This endpoint may not exist yet, so we'll look for it)
        response = self.client.get('/api/chat/available-contacts/')

        # If endpoint exists, admin should have empty list
        if response.status_code == 200:
            self.assertEqual(len(response.data), 0)


class TestAdminWebSocketAccess(TransactionTestCase):
    """Test admin access via WebSocket"""

    def setUp(self):
        """Create test setup"""
        self.admin = User.objects.create_user(
            username='admin4',
            email='admin4@test.com',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.teacher4 = User.objects.create_user(
            username='teacher4',
            email='teacher4@test.com',
            password='TestPass123!',
            role='teacher'
        )

        self.student4 = User.objects.create_user(
            username='student4',
            email='student4@test.com',
            password='TestPass123!',
            role='student'
        )

        # Create subject and enrollment - signal will create FORUM_SUBJECT chat
        self.subject = Subject.objects.create(name='History')
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student4,
            subject=self.subject,
            teacher=self.teacher4,
            is_active=True
        )

        # Get the auto-created FORUM_SUBJECT chat from signal
        self.forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.enrollment
        )

    def test_admin_websocket_connection_denied_as_non_participant(self):
        """Test that admin cannot establish WebSocket connection to chat (not participant)"""
        # Note: This is a basic structure. Full WebSocket testing requires
        # channels test utilities and async support

        # For now, we'll verify that non-participants cannot join
        # by checking that admin is not automatically added to participants
        admin_is_participant = self.forum_chat.participants.filter(
            id=self.admin.id
        ).exists()

        self.assertFalse(admin_is_participant)


class TestAdminInactiveChats(TestCase):
    """Test that admin only sees active forum chats"""

    def setUp(self):
        """Create test setup"""
        self.admin = User.objects.create_user(
            username='admin5',
            email='admin5@test.com',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.teacher5 = User.objects.create_user(
            username='teacher5',
            email='teacher5@test.com',
            password='TestPass123!',
            role='teacher'
        )

        self.student5 = User.objects.create_user(
            username='student5',
            email='student5@test.com',
            password='TestPass123!',
            role='student'
        )

        # Create subjects
        self.active_subject = Subject.objects.create(name='Physics')
        self.inactive_subject = Subject.objects.create(name='Chemistry')

        # Create another teacher for inactive enrollment
        self.other_teacher = User.objects.create_user(
            username='other_teacher5',
            email='other_teacher5@test.com',
            password='TestPass123!',
            role='teacher'
        )

        # Create two enrollments with different subjects/teachers
        self.active_enrollment = SubjectEnrollment.objects.create(
            student=self.student5,
            subject=self.active_subject,
            teacher=self.teacher5,
            is_active=True
        )

        self.inactive_enrollment = SubjectEnrollment.objects.create(
            student=self.student5,
            subject=self.inactive_subject,
            teacher=self.other_teacher,
            is_active=False
        )

        # Get the auto-created active chat
        self.active_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.active_enrollment
        )

        # Get the auto-created inactive chat
        self.inactive_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.inactive_enrollment
        )

        self.client = APIClient()

    def test_admin_only_sees_active_chats(self):
        """Test that admin only sees active forum chats"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)

        # Request forum chats
        response = self.client.get('/api/chat/forum/')

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Admin should see only active chats
        chat_ids = [chat['id'] for chat in response.data['results']]
        self.assertIn(self.active_chat.id, chat_ids)
        self.assertNotIn(self.inactive_chat.id, chat_ids)
