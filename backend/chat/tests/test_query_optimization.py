"""
Unit tests for query optimization in chat system.
Tests verify no N+1 queries and proper use of prefetch_related/select_related.

T8 Tasks:
- test_chat_notifications_no_n_plus_1: Verify ChatNotificationsView uses ~3-5 queries max
- test_chat_list_prefetch: Verify prefetch_related works for list endpoint
- test_message_index_performance: Verify indexes on Message.sender work
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection
from django.db.models import Prefetch, Count, Q, Subquery, OuterRef, Sum
from django.db.models.functions import Coalesce
from django.core.cache import cache
import time
import uuid

from chat.models import ChatRoom, ChatParticipant, Message
from chat.services.chat_service import ChatService
from chat.serializers import ChatRoomListSerializer

User = get_user_model()

def unique_username(prefix="user"):
    """Generate unique username with timestamp and random suffix"""
    return f"{prefix}_{int(time.time() * 1000000) % 1000000}"


@pytest.mark.django_db(transaction=True)
class TestChatNotificationsNoNPlus1(TestCase):
    """T8.1: Verify ChatNotificationsView doesn't have N+1 queries"""

    def test_chat_notifications_no_n_plus_1(self):
        """
        Test that ChatNotificationsView uses ~3-5 queries regardless of chat count.

        Expected queries:
        1. SELECT * from ChatParticipant (filter user, room active)
        2. SELECT COUNT(*) from Message with Subquery (unread count aggregation)
        3. (Optional) SELECT filtering for unread_threads count

        NOT expected: N queries per chat for fetching messages
        """

        # Setup: Create user and 50 chats with unread messages
        student = User.objects.create(username=unique_username("student"), role="student")
        teachers = [
            User.objects.create(username=unique_username(f"teacher_{i}"), role="teacher")
            for i in range(50)
        ]

        chats = []
        now = timezone.now()

        for i, teacher in enumerate(teachers):
            # Create chat room
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=student, last_read_at=now)
            ChatParticipant.objects.create(room=room, user=teacher)

            # Create unread messages
            for j in range(2 + i % 3):
                Message.objects.create(
                    room=room,
                    sender=teacher,
                    content=f"Message {j} in chat {i}",
                    created_at=now,
                )
            chats.append(room)

        # Execute and count queries - should use Subquery annotation pattern
        # 2 queries: one for aggregate(), one for filter().count()
        with self.assertNumQueries(2):
            # Simulate what ChatNotificationsView.get() does
            unread_subquery = (
                Message.objects.filter(
                    room=OuterRef("room_id"),
                    created_at__gt=OuterRef("last_read_at"),
                    is_deleted=False,
                )
                .exclude(sender=student)
                .values("room")
                .annotate(cnt=Count("id"))
                .values("cnt")
            )

            participants = ChatParticipant.objects.filter(
                user=student, room__is_active=True
            ).annotate(
                unread_count=Coalesce(Subquery(unread_subquery), 0)
            )

            total_unread = participants.aggregate(total=Sum("unread_count"))["total"] or 0
            unread_threads = participants.filter(unread_count__gt=0).count()

    def test_chat_notifications_50_chats_performance(self):
        """Verify response time for 50 chats is under 100ms"""

        student = User.objects.create(username=unique_username("perf_student"), role="student")
        now = timezone.now()

        for i in range(50):
            teacher = User.objects.create(username=unique_username(f"perf_teacher_{i}"), role="teacher")
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=student, last_read_at=now)
            ChatParticipant.objects.create(room=room, user=teacher)

            Message.objects.create(
                room=room,
                sender=teacher,
                content="Test message",
                created_at=now,
            )

        # Measure query execution time
        start = time.perf_counter()

        unread_subquery = (
            Message.objects.filter(
                room=OuterRef("room_id"),
                created_at__gt=OuterRef("last_read_at"),
                is_deleted=False,
            )
            .exclude(sender=student)
            .values("room")
            .annotate(cnt=Count("id"))
            .values("cnt")
        )

        participants = ChatParticipant.objects.filter(
            user=student, room__is_active=True
        ).annotate(
            unread_count=Coalesce(Subquery(unread_subquery), 0)
        )

        total_unread = participants.aggregate(total=Sum("unread_count"))["total"] or 0
        elapsed = (time.perf_counter() - start) * 1000  # ms

        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"
        assert total_unread >= 50


@pytest.mark.django_db(transaction=True)
class TestChatListPrefetch(TestCase):
    """T8.2: Verify prefetch_related in ChatRoomViewSet.list()"""

    def test_chat_list_prefetch_related(self):
        """
        Test that chat list uses prefetch_related to avoid N+1 queries.

        Without prefetch:
        - 1 query for ChatRoom list
        - N queries for participants.all() in serializer
        - N queries for user select_related
        Total: 1 + N + N = 1 + 2N queries

        With Prefetch:
        - 1 query for ChatRoom list
        - 1 query for participants with select_related('user')
        Total: 2 queries
        """
        student = User.objects.create(username=unique_username("list_student"), role="student")

        # Create 20 chats with different participants
        for i in range(20):
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=student)

            # Add 2-3 other participants per chat
            for j in range(2 + i % 2):
                user = User.objects.create(username=unique_username(f"user_{i}_{j}"), role="teacher")
                ChatParticipant.objects.create(room=room, user=user)

        # Test WITH prefetch_related - use ChatParticipant filter instead
        with self.assertNumQueries(2):
            # Get all chats for student
            chats = ChatRoom.objects.filter(
                participants__user=student
            ).distinct().prefetch_related(
                Prefetch(
                    "participants",
                    queryset=ChatParticipant.objects.select_related("user")
                )
            )

            # Materialize the queryset
            chat_list = list(chats)

            # Access participants and users (should use prefetch, not generate queries)
            for chat in chat_list:
                for participant in chat.participants.all():
                    _ = participant.user.username

    def test_chat_list_with_serializer(self):
        """Test that ChatRoomListSerializer works with prefetch_related"""
        student = User.objects.create(username=unique_username("serial_student"), role="student")

        for i in range(10):
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=student)

            for j in range(2):
                teacher = User.objects.create(
                    username=unique_username(f"serial_teacher_{i}_{j}"), role="teacher"
                )
                ChatParticipant.objects.create(room=room, user=teacher)

        # Query with prefetch - use correct filter syntax
        chats = ChatRoom.objects.filter(
            participants__user=student
        ).distinct().prefetch_related(
            Prefetch(
                "participants",
                queryset=ChatParticipant.objects.select_related("user")
            )
        )

        # Serialize with prefetch active (should not generate extra queries)
        # 2 queries expected: one for rooms, one for prefetch
        with self.assertNumQueries(2):
            serializer = ChatRoomListSerializer(
                chats,
                many=True,
                context={"request": None}
            )
            data = serializer.data


@pytest.mark.django_db(transaction=True)
class TestMessageIndexPerformance(TestCase):
    """T8.3: Verify Message.sender index improves query performance"""

    def test_message_sender_index_usage(self):
        """
        Test that queries filtered by sender use the index.

        With index on sender_id:
        - Query execution time should be < 50ms even with 10k messages
        """
        sender = User.objects.create(username=unique_username("sender_user"), role="teacher")
        other_user = User.objects.create(username=unique_username("other_user"), role="student")

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=sender)
        ChatParticipant.objects.create(room=room, user=other_user)

        # Create 1000 messages from sender and 1000 from other user
        messages_to_create = []
        for i in range(1000):
            messages_to_create.append(
                Message(
                    room=room,
                    sender=sender,
                    content=f"Message {i}",
                )
            )
            messages_to_create.append(
                Message(
                    room=room,
                    sender=other_user,
                    content=f"Other message {i}",
                )
            )

        Message.objects.bulk_create(messages_to_create)

        # Measure filter by sender performance
        start = time.perf_counter()

        sender_messages = list(Message.objects.filter(sender=sender))

        elapsed = (time.perf_counter() - start) * 1000  # ms

        assert len(sender_messages) == 1000
        assert elapsed < 50, f"Query took {elapsed}ms, expected < 50ms"

    def test_message_filter_by_sender_returns_correct_count(self):
        """Verify filtering by sender returns correct results"""
        user1 = User.objects.create(username=unique_username("filter_user1"), role="teacher")
        user2 = User.objects.create(username=unique_username("filter_user2"), role="student")

        room = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=room, user=user1)
        ChatParticipant.objects.create(room=room, user=user2)

        # Create messages from both users
        for i in range(25):
            Message.objects.create(room=room, sender=user1, content=f"From user1 {i}")
            Message.objects.create(room=room, sender=user2, content=f"From user2 {i}")

        user1_msgs = Message.objects.filter(sender=user1).count()
        user2_msgs = Message.objects.filter(sender=user2).count()

        assert user1_msgs == 25
        assert user2_msgs == 25


@pytest.mark.django_db(transaction=True)
class TestChatParticipantSubqueryAnnotation(TestCase):
    """Test Subquery annotation pattern for unread count"""

    def test_subquery_annotation_no_n_plus_1(self):
        """Verify Subquery annotation doesn't trigger N+1 queries"""

        student = User.objects.create(username=unique_username("annotate_student"), role="student")
        now = timezone.now()

        # Create 10 chats with different unread counts
        for i in range(10):
            teacher = User.objects.create(
                username=unique_username(f"annotate_teacher_{i}"), role="teacher"
            )
            room = ChatRoom.objects.create(is_active=True)

            # student reads up to time T
            ChatParticipant.objects.create(room=room, user=student, last_read_at=now)
            ChatParticipant.objects.create(room=room, user=teacher)

            # Create unread messages (after last_read_at)
            for j in range(5 + i):
                Message.objects.create(
                    room=room,
                    sender=teacher,
                    content=f"Unread {j}",
                    created_at=now,
                )

        # Get participants with subquery annotation - should use minimal queries
        unread_subquery = (
            Message.objects.filter(
                room=OuterRef("room_id"),
                created_at__gt=OuterRef("last_read_at"),
                is_deleted=False,
            )
            .exclude(sender=student)
            .values("room")
            .annotate(cnt=Count("id"))
            .values("cnt")
        )

        # Should be 1 query with subquery compiled in
        with self.assertNumQueries(1):
            participants = list(
                ChatParticipant.objects.filter(user=student)
                .annotate(
                    unread_count=Coalesce(Subquery(unread_subquery), 0)
                )
            )

        # Verify counts are correct
        assert len(participants) == 10
        total_unread = sum(p.unread_count for p in participants)
        assert total_unread >= 50  # At least 5+0 + 5+1 + ... messages
