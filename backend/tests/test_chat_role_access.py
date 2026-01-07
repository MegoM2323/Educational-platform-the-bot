"""
Test suite for Chat Room role-based access control.

Tests for:
- T003: Connection access to chat rooms
- T004: Role-based access control (Student, Teacher, Parent, Admin, Tutor)

WebSocket access verification using channels.testing.WebsocketCommunicator
"""

import os
import django
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.urls import re_path
from rest_framework.authtoken.models import Token

from chat.models import ChatRoom
from chat.consumers import ChatConsumer
from materials.models import Subject, SubjectEnrollment
from accounts.models import StudentProfile

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

if not django.apps.apps.ready:
    django.setup()

User = get_user_model()


def get_chat_application():
    """Helper to create URLRouter with ChatConsumer for testing"""
    return URLRouter([
        re_path(
            r'^ws/chat/(?P<room_id>\w+)/$',
            ChatConsumer.as_asgi(),
            name='chat'
        ),
    ])


class TestStudentChatAccess(TransactionTestCase):
    """Test student access to class and forum chats"""

    def setUp(self):
        """Create test users and chat rooms"""
        # Create teacher
        self.teacher = User.objects.create_user(
            username='teacher_t003',
            email='teacher@test.com',
            password='pass123',
            role=User.Role.TEACHER,
            is_active=True
        )

        # Create student
        self.student = User.objects.create_user(
            username='student_t003',
            email='student@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=self.student)

        # Create subject
        self.subject = Subject.objects.create(name='Math')

        # Create enrollment
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        # Create class chat
        self.class_chat = ChatRoom.objects.create(
            name='Math Class Chat',
            type=ChatRoom.Type.CLASS,
            created_by=self.teacher,
            enrollment=self.enrollment
        )
        self.class_chat.participants.add(self.student, self.teacher)

        # Get or get the auto-created forum subject chat
        self.forum_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.enrollment
        ).first()

        # Get token
        self.token = Token.objects.create(user=self.student)

    @async_to_sync
    async def test_student_can_access_class_chat(self):
        """T003: Student can access class chat"""
        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.class_chat.id}/?token={self.token.key}',
            headers=[(b'origin', b'http://localhost')]
        )
        communicator.scope['user'] = self.student

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Student should connect to class chat')
        await communicator.disconnect()

    @async_to_sync
    async def test_student_can_access_forum_subject_chat(self):
        """T003: Student can access forum subject chat"""
        if not self.forum_chat:
            self.skipTest('Forum chat not created by signal')

        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.forum_chat.id}/?token={self.token.key}',
            headers=[(b'origin', b'http://localhost')]
        )
        communicator.scope['user'] = self.student

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Student should connect to forum chat')
        await communicator.disconnect()


class TestTeacherChatAccess(TransactionTestCase):
    """Test teacher access to class and forum chats"""

    def setUp(self):
        """Create test users and chat rooms"""
        self.teacher = User.objects.create_user(
            username='teacher_t004',
            email='teacher@test.com',
            password='pass123',
            role=User.Role.TEACHER,
            is_active=True
        )

        self.student = User.objects.create_user(
            username='student_t004',
            email='student@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=self.student)

        self.subject = Subject.objects.create(name='English')

        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        # Class chat with enrollment
        self.class_chat = ChatRoom.objects.create(
            name='English Class',
            type=ChatRoom.Type.CLASS,
            created_by=self.teacher,
            enrollment=self.enrollment
        )
        self.class_chat.participants.add(self.student, self.teacher)

        # Get the auto-created forum subject chat
        self.forum_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.enrollment
        ).first()

        self.token = Token.objects.create(user=self.teacher)

    @async_to_sync
    async def test_teacher_can_access_own_class_chat(self):
        """T004: Teacher can access their own class chat"""
        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.class_chat.id}/?token={self.token.key}',
            headers=[(b'origin', b'http://localhost')]
        )
        communicator.scope['user'] = self.teacher

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Teacher should access their class chat')
        await communicator.disconnect()


class TestParentChatAccess(TransactionTestCase):
    """Test parent access control for chat rooms"""

    def setUp(self):
        """Create test users and relationships"""
        # Create parent
        self.parent = User.objects.create_user(
            username='parent_t004',
            email='parent@test.com',
            password='pass123',
            role=User.Role.PARENT,
            is_active=True
        )

        # Create child student
        self.student = User.objects.create_user(
            username='student_child',
            email='student_child@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )

        # Link parent to student
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            parent=self.parent
        )

        # Create teacher
        self.teacher = User.objects.create_user(
            username='teacher_parent',
            email='teacher_parent@test.com',
            password='pass123',
            role=User.Role.TEACHER,
            is_active=True
        )

        # Create enrollment
        self.subject = Subject.objects.create(name='Science')
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        # Class chat with student
        self.class_chat = ChatRoom.objects.create(
            name='Science Class',
            type=ChatRoom.Type.CLASS,
            created_by=self.teacher,
            enrollment=self.enrollment
        )
        self.class_chat.participants.add(self.student, self.teacher)

        self.token = Token.objects.create(user=self.parent)

    @async_to_sync
    async def test_parent_can_access_childs_class_chat(self):
        """T004: Parent can access class chat with their child"""
        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.class_chat.id}/?token={self.token.key}',
            headers=[(b'origin', b'http://localhost')]
        )
        communicator.scope['user'] = self.parent

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Parent should access child\'s class chat')
        await communicator.disconnect()


class TestAdminChatAccess(TransactionTestCase):
    """Test admin access to all chat rooms"""

    def setUp(self):
        """Create test admin and various chats"""
        # Create admin
        self.admin = User.objects.create_user(
            username='admin_t004',
            email='admin@test.com',
            password='pass123',
            role=User.Role.ADMIN,
            is_staff=True,
            is_active=True
        )

        # Create teacher and student
        self.teacher = User.objects.create_user(
            username='teacher_admin',
            email='teacher_admin@test.com',
            password='pass123',
            role=User.Role.TEACHER,
            is_active=True
        )

        self.student = User.objects.create_user(
            username='student_admin',
            email='student_admin@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=self.student)

        # Create subject and enrollment
        self.subject = Subject.objects.create(name='Physics')
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        # Create different types of chats
        self.class_chat = ChatRoom.objects.create(
            name='Physics Class',
            type=ChatRoom.Type.CLASS,
            created_by=self.teacher,
            enrollment=self.enrollment
        )
        self.class_chat.participants.add(self.student, self.teacher)

        # Get the auto-created forum subject chat
        self.forum_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=self.enrollment
        ).first()

        self.direct_chat = ChatRoom.objects.create(
            name='Direct Chat',
            type=ChatRoom.Type.DIRECT,
            created_by=self.teacher
        )
        self.direct_chat.participants.add(self.teacher)

        self.token = Token.objects.create(user=self.admin)

    @async_to_sync
    async def test_admin_can_access_class_chat(self):
        """T004: Admin can access class chat"""
        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.class_chat.id}/?token={self.token.key}',
            headers=[(b'origin', b'http://localhost')]
        )
        communicator.scope['user'] = self.admin

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Admin should access class chat')
        await communicator.disconnect()


class TestTutorChatAccess(TransactionTestCase):
    """Test tutor access to forum chats"""

    def setUp(self):
        """Create test tutor and student relationships"""
        # Create tutor
        self.tutor = User.objects.create_user(
            username='tutor_t004',
            email='tutor@test.com',
            password='pass123',
            role=User.Role.TUTOR,
            is_active=True
        )

        # Create teacher
        self.teacher = User.objects.create_user(
            username='teacher_tutor',
            email='teacher_tutor@test.com',
            password='pass123',
            role=User.Role.TEACHER,
            is_active=True
        )

        # Create assigned student
        self.student = User.objects.create_user(
            username='student_tutor',
            email='student_tutor@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )

        # Link student to tutor
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            tutor=self.tutor
        )

        # Create subject and enrollment
        self.subject = Subject.objects.create(name='Chemistry')
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        # Get the auto-created FORUM_TUTOR chat
        self.tutor_forum = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=self.enrollment
        ).first()

        self.token = Token.objects.create(user=self.tutor)

    @async_to_sync
    async def test_tutor_can_access_assigned_forum(self):
        """T004: Tutor can access forum with assigned student"""
        if not self.tutor_forum:
            self.skipTest('Tutor forum chat not created by signal')

        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.tutor_forum.id}/?token={self.token.key}',
            headers=[(b'origin', b'http://localhost')]
        )
        communicator.scope['user'] = self.tutor

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Tutor should access forum with assigned student')
        await communicator.disconnect()


class TestConnectionWithoutAuthentication(TransactionTestCase):
    """Test that unauthenticated connections are rejected"""

    def setUp(self):
        """Create test chat"""
        teacher = User.objects.create_user(
            username='teacher_unauth',
            email='teacher_unauth@test.com',
            password='pass123',
            role=User.Role.TEACHER,
            is_active=True
        )

        student = User.objects.create_user(
            username='student_unauth',
            email='student_unauth@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=student)

        subject = Subject.objects.create(name='Test')
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        self.chat = ChatRoom.objects.create(
            name='Test Chat',
            type=ChatRoom.Type.CLASS,
            created_by=teacher,
            enrollment=enrollment
        )
        self.chat.participants.add(student, teacher)

    @async_to_sync
    async def test_connection_rejected_without_token(self):
        """T003: Connection rejected without authentication token"""
        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.chat.id}/',
            headers=[(b'origin', b'http://localhost')]
        )

        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected, 'Connection should be rejected without token')

    @async_to_sync
    async def test_connection_rejected_with_invalid_token(self):
        """T003: Connection rejected with invalid token"""
        communicator = WebsocketCommunicator(
            get_chat_application(),
            f'/ws/chat/{self.chat.id}/?token=invalid_token_12345',
            headers=[(b'origin', b'http://localhost')]
        )

        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected, 'Connection should be rejected with invalid token')
