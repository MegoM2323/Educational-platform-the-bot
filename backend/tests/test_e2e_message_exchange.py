"""
End-to-End Message Exchange Test

Tests bidirectional message exchange between two different users (student and teacher)
on the production database. Verifies:

1. ChatRoom creation without IntegrityError
2. Messages can be sent between users
3. Conversations are bidirectional
4. Message history is preserved
5. Both users see the same messages
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from accounts.models import User, StudentProfile, TeacherProfile
from chat.models import ChatRoom, ChatParticipant, Message

User = get_user_model()


class EndToEndMessageExchangeTest(TestCase):
    """Test complete message exchange workflow between two users"""

    @classmethod
    def setUpTestData(cls):
        """Create test users with profiles"""
        # Create student
        cls.student = User.objects.create_user(
            email='student_e2e@test.com',
            username='student_e2e@test.com',
            password='TestPass123!',
            first_name='Ivan',
            last_name='Sokolov',
            role=User.Role.STUDENT,
            is_active=True,
            is_verified=True
        )
        StudentProfile.objects.create(
            user=cls.student,
            grade='9',
            goal='Test learning'
        )

        # Create teacher
        cls.teacher = User.objects.create_user(
            email='teacher_e2e@test.com',
            username='teacher_e2e@test.com',
            password='TestPass123!',
            first_name='Petr',
            last_name='Ivanov',
            role=User.Role.TEACHER,
            is_active=True,
            is_verified=True
        )
        TeacherProfile.objects.create(
            user=cls.teacher,
            subject='Mathematics',
            experience_years=5
        )

    def test_01_chatroom_creation(self):
        """Step 1: Create ChatRoom without IntegrityError"""
        with transaction.atomic():
            chat_room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=chat_room, user=self.student)
            ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        self.assertIsNotNone(chat_room.id)
        self.assertEqual(chat_room.participants.count(), 2)
        self.assertTrue(chat_room.is_active)

    def test_02_student_sends_message(self):
        """Step 2: Student initiates chat by sending message"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Student sends message
        message = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )

        self.assertIsNotNone(message.id)
        self.assertEqual(message.sender, self.student)
        self.assertEqual(message.content, 'Hello from Student')
        self.assertEqual(message.message_type, 'text')
        self.assertFalse(message.is_deleted)

    def test_03_message_visible_to_teacher(self):
        """Step 3: Message appears in teacher's view"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Student sends message
        message = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )

        # Teacher views message
        teacher_messages = Message.objects.filter(
            room=chat_room,
            sender=self.student,
            is_deleted=False
        )
        self.assertEqual(teacher_messages.count(), 1)
        self.assertEqual(teacher_messages.first().content, 'Hello from Student')

    def test_04_teacher_sends_reply(self):
        """Step 4: Teacher sends reply message"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Student sends message
        Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )

        # Teacher sends reply
        reply = Message.objects.create(
            room=chat_room,
            sender=self.teacher,
            content='Hello from Teacher',
            message_type='text'
        )

        self.assertIsNotNone(reply.id)
        self.assertEqual(reply.sender, self.teacher)
        self.assertEqual(reply.content, 'Hello from Teacher')

    def test_05_student_receives_reply(self):
        """Step 5: Student can receive teacher's reply"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Student sends message
        Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )

        # Teacher sends reply
        Message.objects.create(
            room=chat_room,
            sender=self.teacher,
            content='Hello from Teacher',
            message_type='text'
        )

        # Student receives reply
        student_received = Message.objects.filter(
            room=chat_room,
            sender=self.teacher,
            is_deleted=False
        )
        self.assertEqual(student_received.count(), 1)
        self.assertEqual(student_received.first().content, 'Hello from Teacher')

    def test_06_student_sends_another_message(self):
        """Step 6: Student sends second message"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # First exchange
        Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )
        Message.objects.create(
            room=chat_room,
            sender=self.teacher,
            content='Hello from Teacher',
            message_type='text'
        )

        # Student sends another message
        message2 = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Test message 2',
            message_type='text'
        )

        self.assertIsNotNone(message2.id)
        self.assertEqual(message2.content, 'Test message 2')

    def test_07_bidirectional_conversation(self):
        """Step 7: Conversation is bidirectional"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Student sends first
        Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )

        # Teacher replies
        Message.objects.create(
            room=chat_room,
            sender=self.teacher,
            content='Hello from Teacher',
            message_type='text'
        )

        # Student sends another
        Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Test message 2',
            message_type='text'
        )

        # Verify message counts match for both users
        all_messages = Message.objects.filter(room=chat_room, is_deleted=False)
        student_messages = all_messages.filter(sender=self.student)
        teacher_messages = all_messages.filter(sender=self.teacher)

        self.assertEqual(all_messages.count(), 3)
        self.assertEqual(student_messages.count(), 2)
        self.assertEqual(teacher_messages.count(), 1)

    def test_08_complete_conversation_history(self):
        """Step 8: Complete conversation history is preserved"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Build conversation
        msg1 = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )
        msg2 = Message.objects.create(
            room=chat_room,
            sender=self.teacher,
            content='Hello from Teacher',
            message_type='text'
        )
        msg3 = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Test message 2',
            message_type='text'
        )

        # Retrieve complete history
        history = Message.objects.filter(
            room=chat_room,
            is_deleted=False
        ).order_by('created_at')

        self.assertEqual(history.count(), 3)
        self.assertEqual(history[0].content, 'Hello from Student')
        self.assertEqual(history[1].content, 'Hello from Teacher')
        self.assertEqual(history[2].content, 'Test message 2')

    def test_09_both_users_see_same_messages(self):
        """Step 9: Both users see the same messages"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Create messages
        messages_to_create = [
            (self.student, 'Hello from Student'),
            (self.teacher, 'Hello from Teacher'),
            (self.student, 'Test message 2'),
        ]

        for sender, content in messages_to_create:
            Message.objects.create(
                room=chat_room,
                sender=sender,
                content=content,
                message_type='text'
            )

        # Both users query same room
        student_view = Message.objects.filter(
            room=chat_room,
            is_deleted=False
        ).count()
        teacher_view = Message.objects.filter(
            room=chat_room,
            is_deleted=False
        ).count()

        self.assertEqual(student_view, 3)
        self.assertEqual(teacher_view, 3)
        self.assertEqual(student_view, teacher_view)

    def test_10_message_order_preserved(self):
        """Step 10: Message ordering is preserved (FIFO)"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Create messages with specific order
        messages = [
            Message.objects.create(
                room=chat_room,
                sender=self.student,
                content='Message 1',
                message_type='text'
            ),
            Message.objects.create(
                room=chat_room,
                sender=self.teacher,
                content='Message 2',
                message_type='text'
            ),
            Message.objects.create(
                room=chat_room,
                sender=self.student,
                content='Message 3',
                message_type='text'
            ),
        ]

        # Retrieve in order
        ordered_messages = list(
            Message.objects.filter(room=chat_room, is_deleted=False).order_by('created_at')
        )

        self.assertEqual(len(ordered_messages), 3)
        self.assertEqual(ordered_messages[0].content, 'Message 1')
        self.assertEqual(ordered_messages[1].content, 'Message 2')
        self.assertEqual(ordered_messages[2].content, 'Message 3')

    def test_11_messages_not_duplicated(self):
        """Step 11: Messages are not duplicated in database"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Create message
        message = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )

        # Count occurrences
        count = Message.objects.filter(
            room=chat_room,
            content='Hello from Student',
            is_deleted=False
        ).count()

        self.assertEqual(count, 1)

    def test_12_deleted_messages_excluded(self):
        """Step 12: Soft-deleted messages are excluded from conversation"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        # Create and delete a message
        message = Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Hello from Student',
            message_type='text'
        )
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save()

        # Count active messages
        active_count = Message.objects.filter(
            room=chat_room,
            is_deleted=False
        ).count()

        self.assertEqual(active_count, 0)

    def test_13_chatroom_timestamp_tracking(self):
        """Step 13: ChatRoom timestamps are updated correctly"""
        # Create room
        chat_room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=chat_room, user=self.student)
        ChatParticipant.objects.create(room=chat_room, user=self.teacher)

        created_at = chat_room.created_at
        updated_at_before = chat_room.updated_at

        # Send message (should not auto-update ChatRoom.updated_at in this model)
        Message.objects.create(
            room=chat_room,
            sender=self.student,
            content='Test',
            message_type='text'
        )

        chat_room.refresh_from_db()
        self.assertEqual(chat_room.created_at, created_at)

    def test_14_multiple_conversations_isolated(self):
        """Step 14: Multiple conversations are properly isolated"""
        # Create user for second conversation
        student2 = User.objects.create_user(
            email='student2_e2e@test.com',
            username='student2_e2e@test.com',
            password='TestPass123!',
            first_name='Alexander',
            last_name='Petrov',
            role=User.Role.STUDENT
        )

        # Create first conversation
        room1 = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room1, user=self.student)
        ChatParticipant.objects.create(room=room1, user=self.teacher)

        # Create second conversation
        room2 = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room2, user=student2)
        ChatParticipant.objects.create(room=room2, user=self.teacher)

        # Add messages to both
        Message.objects.create(
            room=room1,
            sender=self.student,
            content='Message in room 1',
            message_type='text'
        )
        Message.objects.create(
            room=room2,
            sender=student2,
            content='Message in room 2',
            message_type='text'
        )

        # Verify isolation
        room1_messages = Message.objects.filter(room=room1).count()
        room2_messages = Message.objects.filter(room=room2).count()

        self.assertEqual(room1_messages, 1)
        self.assertEqual(room2_messages, 1)
        self.assertNotEqual(room1.id, room2.id)
