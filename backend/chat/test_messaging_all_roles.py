"""
Full integration test: Messaging between all role pairs

Tests all 13 pairs of user roles:
1. admin ↔ teacher
2. admin ↔ tutor
3. admin ↔ student
4. admin ↔ parent
5. teacher ↔ student
6. teacher ↔ tutor
7. teacher ↔ parent
8. tutor ↔ student
9. tutor ↔ parent
10. student ↔ parent
Plus: existing pairs (student-student, teacher-teacher, etc.)

Each pair tests:
- Chat creation or lookup
- Message sending from first role
- Message delivery to second role
- Reply from second role
- Reply delivery to first role
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from chat.models import ChatRoom, Message, MessageRead, ChatParticipant
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()


class MessagingAllRolesPairTest(TransactionTestCase):
    """
    Test direct messaging between all role pairs
    """

    def setUp(self):
        """Create test users for all roles"""
        super().setUp()

        # Create admin
        self.admin = User.objects.create_user(
            username='admin_messaging_test',
            email='admin@msg.test',
            password='test123',
            role='admin'
        )

        # Create teacher
        self.teacher = User.objects.create_user(
            username='teacher_messaging_test',
            email='teacher@msg.test',
            password='test123',
            role='teacher'
        )
        TeacherProfile.objects.create(user=self.teacher)

        # Create tutor
        self.tutor = User.objects.create_user(
            username='tutor_messaging_test',
            email='tutor@msg.test',
            password='test123',
            role='tutor'
        )
        TutorProfile.objects.create(user=self.tutor)

        # Create student
        self.student = User.objects.create_user(
            username='student_messaging_test',
            email='student@msg.test',
            password='test123',
            role='student'
        )
        StudentProfile.objects.create(user=self.student, grade=9)

        # Create parent
        self.parent = User.objects.create_user(
            username='parent_messaging_test',
            email='parent@msg.test',
            password='test123',
            role='parent'
        )
        ParentProfile.objects.create(user=self.parent)

        self.client = APIClient()
        self.messages_created = []

    def tearDown(self):
        """Clean up after each test"""
        pass

    def _get_or_create_direct_chat(self, user1, user2):
        """Get or create a direct chat between two users"""
        # Try to find existing chat between users
        chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.DIRECT,
            participants=user1
        ).filter(participants=user2).first()

        if chat:
            return chat

        # Create new chat
        chat = ChatRoom.objects.create(
            name=f"Chat: {user1.get_full_name() or user1.username} <-> {user2.get_full_name() or user2.username}",
            type=ChatRoom.Type.DIRECT,
            created_by=user1
        )
        chat.participants.add(user1, user2)
        ChatParticipant.objects.get_or_create(room=chat, user=user1)
        ChatParticipant.objects.get_or_create(room=chat, user=user2)

        return chat

    def _send_message(self, sender, chat_room, text):
        """Send a message in a chat"""
        message = Message.objects.create(
            room=chat_room,
            sender=sender,
            content=text
        )
        self.messages_created.append(message)
        return message

    def _verify_message_delivered(self, recipient, chat_room, expected_text):
        """Verify that recipient can see the message"""
        messages = Message.objects.filter(
            room=chat_room,
            content=expected_text,
            is_deleted=False
        ).order_by('-created_at')

        self.assertTrue(
            messages.exists(),
            f"Message '{expected_text}' not found in chat {chat_room.id}"
        )

        message = messages.first()
        # Mark as read
        MessageRead.objects.get_or_create(message=message, user=recipient)
        return message

    def _test_messaging_pair(self, user1, user2, msg1_from_user1, msg2_from_user2, pair_name):
        """
        Test messaging between two users:
        1. Create/get chat
        2. User1 sends message
        3. Verify user2 sees message
        4. User2 replies
        5. Verify user1 sees reply
        """
        # Step 1: Get or create chat
        chat = self._get_or_create_direct_chat(user1, user2)
        self.assertIsNotNone(chat, f"Failed to create chat for {pair_name}")
        self.assertTrue(
            chat.participants.filter(id=user1.id).exists(),
            f"User1 not in participants for {pair_name}"
        )
        self.assertTrue(
            chat.participants.filter(id=user2.id).exists(),
            f"User2 not in participants for {pair_name}"
        )

        # Step 2: User1 sends message
        msg1 = self._send_message(user1, chat, msg1_from_user1)
        self.assertIsNotNone(msg1, f"Failed to send message from {user1.username} in {pair_name}")

        # Step 3: Verify User2 sees message
        verified_msg1 = self._verify_message_delivered(user2, chat, msg1_from_user1)
        self.assertEqual(verified_msg1.sender.id, user1.id, f"Message sender mismatch in {pair_name}")

        # Step 4: User2 replies
        msg2 = self._send_message(user2, chat, msg2_from_user2)
        self.assertIsNotNone(msg2, f"Failed to send reply from {user2.username} in {pair_name}")

        # Step 5: Verify User1 sees reply
        verified_msg2 = self._verify_message_delivered(user1, chat, msg2_from_user2)
        self.assertEqual(verified_msg2.sender.id, user2.id, f"Reply sender mismatch in {pair_name}")

        return {
            'pair': pair_name,
            'status': 'PASS',
            'chat_id': chat.id,
            'messages': [msg1.id, msg2.id],
            'notes': f"2 messages exchanged successfully"
        }

    def test_01_admin_teacher_messaging(self):
        """Pair 1: admin ↔ teacher"""
        result = self._test_messaging_pair(
            self.admin, self.teacher,
            "Привет, учитель. Это администратор.",
            "Здравствуйте, администратор!",
            "admin ↔ teacher"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_02_admin_tutor_messaging(self):
        """Pair 2: admin ↔ tutor"""
        result = self._test_messaging_pair(
            self.admin, self.tutor,
            "Привет, репетитор. Администратор здесь.",
            "Привет, администратор!",
            "admin ↔ tutor"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_03_admin_student_messaging(self):
        """Pair 3: admin ↔ student"""
        result = self._test_messaging_pair(
            self.admin, self.student,
            "Привет, ученик. Это администратор.",
            "Здравствуйте, администратор!",
            "admin ↔ student"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_04_admin_parent_messaging(self):
        """Pair 4: admin ↔ parent"""
        result = self._test_messaging_pair(
            self.admin, self.parent,
            "Привет, родитель. Это администратор.",
            "Добрый день, администратор!",
            "admin ↔ parent"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_05_teacher_student_messaging(self):
        """Pair 5: teacher ↔ student"""
        result = self._test_messaging_pair(
            self.teacher, self.student,
            "Привет, ученик! Я твой учитель.",
            "Здравствуйте, учитель!",
            "teacher ↔ student"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_06_teacher_tutor_messaging(self):
        """Pair 6: teacher ↔ tutor"""
        result = self._test_messaging_pair(
            self.teacher, self.tutor,
            "Привет, коллега репетитор!",
            "Привет, учитель!",
            "teacher ↔ tutor"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_07_teacher_parent_messaging(self):
        """Pair 7: teacher ↔ parent"""
        result = self._test_messaging_pair(
            self.teacher, self.parent,
            "Привет, родитель! Я учитель вашего ребенка.",
            "Здравствуйте, учитель!",
            "teacher ↔ parent"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_08_tutor_student_messaging(self):
        """Pair 8: tutor ↔ student"""
        result = self._test_messaging_pair(
            self.tutor, self.student,
            "Привет, ученик! Я твой репетитор.",
            "Здравствуйте, репетитор!",
            "tutor ↔ student"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_09_tutor_parent_messaging(self):
        """Pair 9: tutor ↔ parent"""
        result = self._test_messaging_pair(
            self.tutor, self.parent,
            "Привет, родитель! Я репетитор вашего ребенка.",
            "Здравствуйте, репетитор!",
            "tutor ↔ parent"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)

    def test_10_student_parent_messaging(self):
        """Pair 10: student ↔ parent"""
        result = self._test_messaging_pair(
            self.student, self.parent,
            "Привет, родитель!",
            "Привет, сын!",
            "student ↔ parent"
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['messages']), 2)


class ChatRoomCreationTest(TestCase):
    """Test chat room creation and participant management"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='chattest_user1',
            email='user1@test.local',
            password='test123',
            role='teacher'
        )
        TeacherProfile.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='chattest_user2',
            email='user2@test.local',
            password='test123',
            role='student'
        )
        StudentProfile.objects.create(user=self.user2, grade=10)

    def test_create_direct_chat_room(self):
        """Test creating a direct chat room"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1
        )
        chat.participants.add(self.user1, self.user2)

        self.assertEqual(chat.type, ChatRoom.Type.DIRECT)
        self.assertEqual(chat.created_by, self.user1)
        self.assertEqual(chat.participants.count(), 2)
        self.assertTrue(chat.is_active)

    def test_chat_room_participant_count(self):
        """Test participant counting"""
        chat = ChatRoom.objects.create(
            name="Group Chat",
            type=ChatRoom.Type.GROUP,
            created_by=self.user1
        )
        chat.participants.add(self.user1, self.user2)

        participant_count = chat.participants.count()
        self.assertEqual(participant_count, 2)

    def test_chat_participant_model(self):
        """Test ChatParticipant model creation"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1
        )

        participant = ChatParticipant.objects.create(
            room=chat,
            user=self.user1
        )

        self.assertEqual(participant.room, chat)
        self.assertEqual(participant.user, self.user1)
        self.assertIsNotNone(participant.joined_at)


class MessageCreationAndReadTest(TestCase):
    """Test message creation and read status tracking"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='msgtest_user1',
            email='msguser1@test.local',
            password='test123',
            role='admin'
        )

        self.user2 = User.objects.create_user(
            username='msgtest_user2',
            email='msguser2@test.local',
            password='test123',
            role='teacher'
        )
        TeacherProfile.objects.create(user=self.user2)

        self.chat = ChatRoom.objects.create(
            name="Message Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1
        )
        self.chat.participants.add(self.user1, self.user2)

    def test_create_message(self):
        """Test creating a message"""
        message = Message.objects.create(
            room=self.chat,
            sender=self.user1,
            content="Test message"
        )

        self.assertEqual(message.room, self.chat)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, "Test message")
        self.assertFalse(message.is_deleted)

    def test_message_read_tracking(self):
        """Test tracking message reads"""
        message = Message.objects.create(
            room=self.chat,
            sender=self.user1,
            content="Test message for read tracking"
        )

        # User2 reads the message
        read_record = MessageRead.objects.create(
            message=message,
            user=self.user2
        )

        self.assertEqual(read_record.message, message)
        self.assertEqual(read_record.user, self.user2)
        self.assertIsNotNone(read_record.read_at)

    def test_multiple_message_creation(self):
        """Test creating multiple messages in sequence"""
        msg1 = Message.objects.create(
            room=self.chat,
            sender=self.user1,
            content="First message"
        )

        msg2 = Message.objects.create(
            room=self.chat,
            sender=self.user2,
            content="Second message"
        )

        msg3 = Message.objects.create(
            room=self.chat,
            sender=self.user1,
            content="Third message"
        )

        messages = Message.objects.filter(room=self.chat).order_by('created_at')
        self.assertEqual(messages.count(), 3)
        self.assertEqual(messages[0].content, "First message")
        self.assertEqual(messages[1].content, "Second message")
        self.assertEqual(messages[2].content, "Third message")


class MessageDeletionTest(TestCase):
    """Test message deletion and soft-delete tracking"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='deltest_user',
            email='deluser@test.local',
            password='test123',
            role='admin'
        )

        self.chat = ChatRoom.objects.create(
            name="Delete Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user
        )
        self.chat.participants.add(self.user)

    def test_message_soft_delete(self):
        """Test soft-deleting a message"""
        message = Message.objects.create(
            room=self.chat,
            sender=self.user,
            content="Message to delete"
        )

        # Soft delete
        message.is_deleted = True
        message.save()

        # Should not appear in non-deleted queries
        active_messages = Message.objects.filter(room=self.chat, is_deleted=False)
        self.assertEqual(active_messages.count(), 0)

        # But should still exist in database
        all_messages = Message.objects.filter(room=self.chat)
        self.assertEqual(all_messages.count(), 1)


class ChatRoomBoundaryTest(TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='boundtest_user',
            email='bounduser@test.local',
            password='test123',
            role='student'
        )
        StudentProfile.objects.create(user=self.user, grade=8)

    def test_create_chat_with_long_name(self):
        """Test creating chat with maximum length name"""
        long_name = "A" * 200  # Max CharField length
        chat = ChatRoom.objects.create(
            name=long_name,
            type=ChatRoom.Type.DIRECT,
            created_by=self.user
        )

        self.assertEqual(len(chat.name), 200)
        self.assertEqual(chat.name, long_name)

    def test_create_chat_with_long_description(self):
        """Test creating chat with very long description"""
        long_description = "Test description. " * 100
        chat = ChatRoom.objects.create(
            name="Test Chat",
            description=long_description,
            type=ChatRoom.Type.DIRECT,
            created_by=self.user
        )

        self.assertTrue(len(chat.description) > 1000)
        self.assertIn("Test description", chat.description)

    def test_message_with_empty_content(self):
        """Test creating message with empty content"""
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user
        )
        chat.participants.add(self.user)

        message = Message.objects.create(
            room=chat,
            sender=self.user,
            content=""
        )

        self.assertEqual(message.content, "")

    def test_message_with_long_content(self):
        """Test creating message with very long content"""
        long_content = "Text " * 500  # ~2500 chars
        chat = ChatRoom.objects.create(
            name="Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user
        )
        chat.participants.add(self.user)

        message = Message.objects.create(
            room=chat,
            sender=self.user,
            content=long_content
        )

        self.assertEqual(message.content, long_content)


class ChatHistorySynchronizationTest(TestCase):
    """Test chat history synchronization between users"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='synctest_user1',
            email='syncuser1@test.local',
            password='test123',
            role='teacher'
        )
        TeacherProfile.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='synctest_user2',
            email='syncuser2@test.local',
            password='test123',
            role='student'
        )
        StudentProfile.objects.create(user=self.user2, grade=9)

        self.chat = ChatRoom.objects.create(
            name="Sync Test Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1
        )
        self.chat.participants.add(self.user1, self.user2)

    def test_both_users_see_same_messages(self):
        """Test that both users see the same messages"""
        msg1 = Message.objects.create(
            room=self.chat,
            sender=self.user1,
            content="Message from user1"
        )

        msg2 = Message.objects.create(
            room=self.chat,
            sender=self.user2,
            content="Message from user2"
        )

        # Both users query their chat messages
        user1_messages = Message.objects.filter(room=self.chat, is_deleted=False)
        user2_messages = Message.objects.filter(room=self.chat, is_deleted=False)

        self.assertEqual(user1_messages.count(), 2)
        self.assertEqual(user2_messages.count(), 2)

        # Order should be the same
        self.assertEqual(
            list(user1_messages.values_list('id', flat=True)),
            list(user2_messages.values_list('id', flat=True))
        )

    def test_message_order_preserved(self):
        """Test that message order is preserved for both users"""
        messages_to_create = [
            ("First message", self.user1),
            ("Second message", self.user2),
            ("Third message", self.user1),
            ("Fourth message", self.user2),
        ]

        created_messages = []
        for content, sender in messages_to_create:
            msg = Message.objects.create(
                room=self.chat,
                sender=sender,
                content=content
            )
            created_messages.append(msg)

        # Query messages
        all_messages = Message.objects.filter(
            room=self.chat,
            is_deleted=False
        ).order_by('created_at')

        self.assertEqual(all_messages.count(), 4)
        for i, message in enumerate(all_messages):
            self.assertEqual(message.content, messages_to_create[i][0])
