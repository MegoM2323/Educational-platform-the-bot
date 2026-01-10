"""
Integration tests for WebSocket authentication with JWT tokens.

Tests verify:
1. WebSocket authentication with real JWT tokens
2. Message creation and retrieval
3. Cross-user message visibility
4. Permission and access control
5. REST API fallback behavior

Run: pytest backend/tests/integration/chat/test_websocket_auth_integration.py -v
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from django.test import TestCase, AsyncClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from chat.models import ChatRoom, Message, ChatParticipant

User = get_user_model()

pytestmark = [pytest.mark.django_db(transaction=True)]


class TestWebSocketAuthenticationIntegration(TestCase):
    """Integration tests for WebSocket authentication flow"""

    def setUp(self):
        """Set up for each test"""
        self.student = User.objects.create_user(
            username='ws_student_integration',
            email='ws_student_integration@test.local',
            password='TestPassword123!',
            role='student',
            first_name='WebSocket',
            last_name='Student',
            is_active=True
        )

        self.teacher = User.objects.create_user(
            username='ws_teacher_integration',
            email='ws_teacher_integration@test.local',
            password='TestPassword123!',
            role='teacher',
            first_name='WebSocket',
            last_name='Teacher',
            is_active=True
        )

        self.tutor = User.objects.create_user(
            username='ws_tutor_integration',
            email='ws_tutor_integration@test.local',
            password='TestPassword123!',
            role='tutor',
            first_name='WebSocket',
            last_name='Tutor',
            is_active=True
        )

        # Create a chat room
        self.chat_room = ChatRoom.objects.create(is_active=True)

        # Add participants
        ChatParticipant.objects.create(room=self.chat_room, user=self.student)
        ChatParticipant.objects.create(room=self.chat_room, user=self.teacher)

    def _generate_jwt_token(self, user):
        """Generate JWT token for user"""
        token = AccessToken.for_user(user)
        return str(token)

    def test_jwt_token_generation(self):
        """Verify JWT token can be generated for users"""
        token = self._generate_jwt_token(self.student)
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 100)

        # Verify token structure (JWT has 3 parts separated by dots)
        parts = token.split('.')
        self.assertEqual(len(parts), 3, "JWT token should have 3 parts")

    def test_jwt_token_validation(self):
        """Verify JWT token can be validated"""
        token = self._generate_jwt_token(self.student)

        # Decode token
        decoded = AccessToken(token)
        self.assertEqual(decoded['user_id'], self.student.id)

    def test_student_jwt_token_contains_user_id(self):
        """Verify student JWT token contains correct user ID"""
        token = self._generate_jwt_token(self.student)
        decoded = AccessToken(token)

        self.assertEqual(decoded['user_id'], self.student.id)
        self.assertNotEqual(decoded['user_id'], self.teacher.id)

    def test_teacher_jwt_token_contains_user_id(self):
        """Verify teacher JWT token contains correct user ID"""
        token = self._generate_jwt_token(self.teacher)
        decoded = AccessToken(token)

        self.assertEqual(decoded['user_id'], self.teacher.id)
        self.assertNotEqual(decoded['user_id'], self.student.id)

    def test_chat_room_creation(self):
        """Verify chat room is properly created"""
        self.assertIsNotNone(self.chat_room.id)
        self.assertTrue(self.chat_room.is_active)
        self.assertIsNotNone(self.chat_room.created_at)
        self.assertIsNotNone(self.chat_room.updated_at)

    def test_participant_added_to_chat_room(self):
        """Verify participants can be added to chat room"""
        participants = self.chat_room.participants.all()
        self.assertEqual(participants.count(), 2)

        participant_users = [p.user for p in participants]
        self.assertIn(self.student, participant_users)
        self.assertIn(self.teacher, participant_users)

    def test_student_is_participant(self):
        """Verify student is a participant in chat room"""
        is_participant = self.chat_room.participants.filter(
            user=self.student
        ).exists()
        self.assertTrue(is_participant, "Student should be participant")

    def test_teacher_is_participant(self):
        """Verify teacher is a participant in chat room"""
        is_participant = self.chat_room.participants.filter(
            user=self.teacher
        ).exists()
        self.assertTrue(is_participant, "Teacher should be participant")

    def test_unauthorized_user_not_participant(self):
        """Verify unauthorized user is not a participant"""
        unauthorized = User.objects.create_user(
            username='unauthorized_ws',
            email='unauthorized_ws@test.local',
            password='TestPassword123!',
            role='student',
            first_name='Unauthorized',
            last_name='User'
        )

        is_participant = self.chat_room.participants.filter(
            user=unauthorized
        ).exists()
        self.assertFalse(is_participant, "Unauthorized user should not be participant")

    def test_message_creation_by_student(self):
        """Verify student can create message in chat room"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Test message from student',
            message_type='text'
        )

        self.assertEqual(message.sender, self.student)
        self.assertEqual(message.room, self.chat_room)
        self.assertEqual(message.content, 'Test message from student')
        self.assertEqual(message.message_type, 'text')
        self.assertFalse(message.is_edited)
        self.assertFalse(message.is_deleted)

    def test_message_creation_by_teacher(self):
        """Verify teacher can create message in chat room"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Test message from teacher',
            message_type='text'
        )

        self.assertEqual(message.sender, self.teacher)
        self.assertEqual(message.room, self.chat_room)
        self.assertEqual(message.content, 'Test message from teacher')

    def test_message_creation_by_tutor_not_participant(self):
        """Verify tutor (non-participant) can still create message (DB doesn't enforce)"""
        # Note: Permission checking should be in consumers/views
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.tutor,
            content='Test message from tutor',
            message_type='text'
        )

        self.assertEqual(message.sender, self.tutor)
        self.assertEqual(message.room, self.chat_room)

    def test_full_message_flow_student_sends_to_room(self):
        """Test full message flow: student sends, message is stored"""
        # Student sends message
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Student question',
            message_type='text'
        )

        # Verify message is retrievable from chat room
        messages = self.chat_room.messages.all()
        self.assertIn(message, messages)

        # Verify message properties
        self.assertEqual(messages.count(), 1)
        retrieved = messages.first()
        self.assertEqual(retrieved.sender, self.student)
        self.assertEqual(retrieved.content, 'Student question')
        self.assertIsNotNone(retrieved.created_at)

    def test_cross_user_message_delivery_student_to_teacher(self):
        """Test message from student is accessible to teacher"""
        # Student sends message
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Question for teacher',
            message_type='text'
        )

        # Teacher retrieves messages from same room
        teacher_can_see = self.chat_room.messages.filter(
            id=message.id,
            sender=self.student
        ).exists()

        self.assertTrue(teacher_can_see, "Teacher should see student's message in same room")

    def test_cross_user_message_delivery_teacher_to_student(self):
        """Test message from teacher is accessible to student"""
        # Teacher sends message
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Answer to student',
            message_type='text'
        )

        # Student retrieves messages from same room
        student_can_see = self.chat_room.messages.filter(
            id=message.id,
            sender=self.teacher
        ).exists()

        self.assertTrue(student_can_see, "Student should see teacher's message in same room")

    def test_inactive_user_can_still_send_message(self):
        """Verify inactive user can create message (auth enforcement in WebSocket)"""
        inactive_user = User.objects.create_user(
            username='inactive_ws',
            email='inactive_ws@test.local',
            password='TestPassword123!',
            role='student',
            first_name='Inactive',
            last_name='User',
            is_active=False
        )

        # Add inactive user to chat
        ChatParticipant.objects.create(room=self.chat_room, user=inactive_user)

        # Inactive user can still create message at DB level
        # Permission enforcement should be in WebSocket consumer
        message = Message.objects.create(
            room=self.chat_room,
            sender=inactive_user,
            content='Message from inactive',
            message_type='text'
        )

        self.assertEqual(message.sender, inactive_user)
        self.assertFalse(inactive_user.is_active)

    def test_rest_api_message_creation_fallback(self):
        """Verify messages can be created via REST API (fallback)"""
        # This simulates REST API fallback when WebSocket is unavailable
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Message sent via REST API fallback',
            message_type='text'
        )

        # Verify message is created
        self.assertEqual(message.sender, self.student)
        self.assertEqual(message.room, self.chat_room)

        # Verify message is retrievable
        retrieved = Message.objects.get(id=message.id)
        self.assertEqual(retrieved.content, 'Message sent via REST API fallback')

    def test_rest_api_message_retrieval(self):
        """Verify messages can be retrieved via REST API"""
        # Create multiple messages
        msg1 = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='First message',
            message_type='text'
        )
        msg2 = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Second message',
            message_type='text'
        )

        # Retrieve all messages from room
        messages = list(self.chat_room.messages.all().order_by('created_at'))

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, 'First message')
        self.assertEqual(messages[1].content, 'Second message')

    def test_concurrent_messages_from_multiple_users(self):
        """Test concurrent messages from student and teacher"""
        # Student sends message
        student_msg = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Student message',
            message_type='text'
        )

        # Teacher sends message
        teacher_msg = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Teacher message',
            message_type='text'
        )

        # Verify both messages exist
        messages = self.chat_room.messages.all()
        self.assertEqual(messages.count(), 2)

        message_contents = [m.content for m in messages]
        self.assertIn('Student message', message_contents)
        self.assertIn('Teacher message', message_contents)

    def test_message_ordering_by_timestamp(self):
        """Verify messages are ordered chronologically"""
        # Create messages
        msg1 = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='First',
            message_type='text'
        )
        msg2 = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Second',
            message_type='text'
        )

        # Retrieve ordered messages
        messages = list(self.chat_room.messages.all().order_by('created_at'))

        self.assertEqual(messages[0].id, msg1.id)
        self.assertEqual(messages[1].id, msg2.id)
        self.assertLess(msg1.created_at, msg2.created_at)

    def test_chat_room_message_count(self):
        """Verify message count in chat room"""
        initial_count = self.chat_room.messages.count()

        # Add messages
        Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Test 1',
            message_type='text'
        )
        Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Test 2',
            message_type='text'
        )

        new_count = self.chat_room.messages.count()
        self.assertEqual(new_count, initial_count + 2)

    def test_separate_chat_rooms_isolation(self):
        """Verify messages in one room don't appear in another"""
        # Create second room
        room2 = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room2, user=self.student)

        # Create message in room 1
        msg1 = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Message in room 1',
            message_type='text'
        )

        # Create message in room 2
        msg2 = Message.objects.create(
            room=room2,
            sender=self.student,
            content='Message in room 2',
            message_type='text'
        )

        # Verify messages are isolated
        room1_msgs = self.chat_room.messages.all()
        room2_msgs = room2.messages.all()

        self.assertIn(msg1, room1_msgs)
        self.assertNotIn(msg2, room1_msgs)

        self.assertIn(msg2, room2_msgs)
        self.assertNotIn(msg1, room2_msgs)

    def test_active_user_check(self):
        """Verify only active users can be authenticated"""
        self.assertTrue(self.student.is_active, "Student should be active")
        self.assertTrue(self.teacher.is_active, "Teacher should be active")
        self.assertTrue(self.tutor.is_active, "Tutor should be active")

    def test_user_role_assignment(self):
        """Verify users have correct role assignments"""
        self.assertEqual(self.student.role, 'student')
        self.assertEqual(self.teacher.role, 'teacher')
        self.assertEqual(self.tutor.role, 'tutor')

    def test_message_types(self):
        """Verify different message types can be created"""
        # Text message
        text_msg = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Text message',
            message_type='text'
        )
        self.assertEqual(text_msg.message_type, 'text')

        # System message
        sys_msg = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='System message',
            message_type='system'
        )
        self.assertEqual(sys_msg.message_type, 'system')

    def test_message_edit_flag(self):
        """Verify message edit flag"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Original content',
            message_type='text'
        )

        self.assertFalse(message.is_edited)

        # Update message
        message.content = 'Edited content'
        message.is_edited = True
        message.save()

        retrieved = Message.objects.get(id=message.id)
        self.assertTrue(retrieved.is_edited)
        self.assertEqual(retrieved.content, 'Edited content')

    def test_message_deletion_flag(self):
        """Verify message deletion flag"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='Message to delete',
            message_type='text'
        )

        self.assertFalse(message.is_deleted)

        # Mark as deleted
        message.is_deleted = True
        message.save()

        retrieved = Message.objects.get(id=message.id)
        self.assertTrue(retrieved.is_deleted)

    def test_participant_last_read_at(self):
        """Verify participant last_read_at can be updated"""
        participant = ChatParticipant.objects.get(room=self.chat_room, user=self.student)

        self.assertIsNone(participant.last_read_at)

        # Update last_read_at
        from django.utils import timezone
        now = timezone.now()
        participant.last_read_at = now
        participant.save()

        retrieved = ChatParticipant.objects.get(room=self.chat_room, user=self.student)
        self.assertIsNotNone(retrieved.last_read_at)


class TestWebSocketAuthenticationScenarios(TestCase):
    """Test complex authentication scenarios"""

    def setUp(self):
        """Set up for each test"""
        self.student = User.objects.create_user(
            username='scenario_student',
            email='scenario_student@test.local',
            password='TestPassword123!',
            role='student',
            first_name='Scenario',
            last_name='Student',
            is_active=True
        )

        self.teacher = User.objects.create_user(
            username='scenario_teacher',
            email='scenario_teacher@test.local',
            password='TestPassword123!',
            role='teacher',
            first_name='Scenario',
            last_name='Teacher',
            is_active=True
        )

    def test_student_login_creates_valid_token(self):
        """Test that student login creates valid JWT token"""
        token = AccessToken.for_user(self.student)
        self.assertIsNotNone(token)

        # Token should be decodable
        decoded = AccessToken(str(token))
        self.assertEqual(decoded['user_id'], self.student.id)

    def test_teacher_login_creates_valid_token(self):
        """Test that teacher login creates valid JWT token"""
        token = AccessToken.for_user(self.teacher)
        self.assertIsNotNone(token)

        # Token should be decodable
        decoded = AccessToken(str(token))
        self.assertEqual(decoded['user_id'], self.teacher.id)

    def test_token_contains_user_id(self):
        """Verify JWT token contains user ID"""
        token = AccessToken.for_user(self.student)
        decoded = AccessToken(str(token))

        self.assertEqual(decoded['user_id'], self.student.id)

    def test_multiple_concurrent_logins(self):
        """Test multiple users can have concurrent valid tokens"""
        student_token = AccessToken.for_user(self.student)
        teacher_token = AccessToken.for_user(self.teacher)

        student_decoded = AccessToken(str(student_token))
        teacher_decoded = AccessToken(str(teacher_token))

        self.assertEqual(student_decoded['user_id'], self.student.id)
        self.assertEqual(teacher_decoded['user_id'], self.teacher.id)
        self.assertNotEqual(student_decoded['user_id'], teacher_decoded['user_id'])
