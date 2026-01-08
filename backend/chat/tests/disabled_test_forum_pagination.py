from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Q
from chat.models import ChatRoom, Message, ChatParticipant
from materials.models import SubjectEnrollment, Subject
import datetime

User = get_user_model()


class TestMessagePagination(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher_pagination",
            email="teacher_pagination@test.com",
            password="test123",
            role="teacher",
        )
        self.student = User.objects.create_user(
            username="student_pagination",
            email="student_pagination@test.com",
            password="test123",
            role="student",
        )

        self.subject = Subject.objects.create(name="Math Pagination Test")
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student, subject=self.subject, teacher=self.teacher
        )

        # Chat is created automatically via signal when enrollment is created
        # Get the existing chat room that was created
        self.chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        )

        # Create 100 messages with different times (in chronological order)
        for i in range(100):
            # Create messages with incrementing created_at
            Message.objects.create(
                room=self.chat,
                sender=self.teacher,
                content=f"Message {i}",
                message_type=Message.Type.TEXT,
                created_at=datetime.datetime(2024, 1, 1, 0, i % 60, i // 60),
            )

    def test_messages_chronological_order(self):
        """Messages are returned in chronological order (oldest first)"""
        # Get messages from database in order
        messages = Message.objects.filter(room=self.chat, is_deleted=False).order_by(
            "created_at"
        )

        # Should have our 100 test messages
        self.assertEqual(messages.count(), 100)

        # Check that messages are in chronological order (oldest first)
        messages_list = list(messages)
        for i in range(len(messages_list) - 1):
            current_time = messages_list[i].created_at
            next_time = messages_list[i + 1].created_at

            self.assertLessEqual(
                current_time,
                next_time,
                f"Message {i} time {current_time} should be <= message {i+1} time {next_time}",
            )

    def test_pagination_limit_and_offset(self):
        """Pagination with limit and offset returns correct messages"""
        # Get all messages
        all_messages = Message.objects.filter(
            room=self.chat, is_deleted=False
        ).order_by("created_at")

        # First page with limit=25, offset=0
        page1 = all_messages[0:25]
        ids1 = set(m.id for m in page1)

        # Second page with limit=25, offset=25
        page2 = all_messages[25:50]
        ids2 = set(m.id for m in page2)

        # Messages should not overlap
        intersection = ids1 & ids2
        self.assertEqual(
            len(intersection),
            0,
            f"Pages should not overlap. Found {len(intersection)} overlapping messages",
        )

        # Check that pages have expected sizes
        self.assertEqual(len(ids1), 25)
        self.assertEqual(len(ids2), 25)

    def test_pagination_no_duplicates_across_pages(self):
        """Duplicate messages should not appear across different pages"""
        all_messages = Message.objects.filter(
            room=self.chat, is_deleted=False
        ).order_by("created_at")

        all_ids = set()
        page_size = 20

        # Iterate through pages
        for offset in range(0, all_messages.count(), page_size):
            page = all_messages[offset : offset + page_size]
            page_ids = set(m.id for m in page)

            # Check that there are no duplicates between pages
            duplicates = all_ids & page_ids
            self.assertEqual(
                len(duplicates),
                0,
                f"Found {len(duplicates)} duplicate message IDs across pages at offset {offset}",
            )

            all_ids.update(page_ids)

        # Verify we got all messages
        self.assertEqual(len(all_ids), 100)

    def test_messages_have_correct_structure(self):
        """Check that messages in chatroom have correct structure"""
        # Get all messages from chat room
        messages = Message.objects.filter(room=self.chat, is_deleted=False)

        self.assertGreater(messages.count(), 0)

        # Check that each message has required fields
        for msg in messages:
            self.assertIsNotNone(msg.id)
            self.assertEqual(msg.content[: len("Message")], "Message")
            self.assertIsNotNone(msg.created_at)
            self.assertEqual(msg.sender, self.teacher)
            self.assertEqual(msg.room, self.chat)
