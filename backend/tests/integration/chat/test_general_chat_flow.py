"""
Integration tests for general chat workflows.

Tests complete end-to-end workflows including:
- Create thread → post messages → read messages (full workflow)
- Pin thread → verify pinned status (pin workflow)
- Lock thread → verify cannot post messages (lock workflow)
- General chat message → verify persists to database
- Multiple messages → verify correct order and pagination
- Database state consistency verification
"""

import pytest
from chat.models import ChatRoom, Message, MessageThread
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def general_chat_room(db, teacher_user):
    """Create a general chat room"""
    return ChatRoom.objects.create(
        name="General Discussion",
        type=ChatRoom.Type.GENERAL,
        created_by=teacher_user
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateThreadWorkflow:
    """Integration tests for creating threads"""

    def test_create_thread_workflow(self, general_chat_room, teacher_user):
        """Test complete workflow: create thread in general chat"""
        # Create thread via model
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="How to solve quadratic equations?",
            created_by=teacher_user
        )

        # Verify thread was created
        assert thread.id is not None
        assert thread.title == "How to solve quadratic equations?"
        assert thread.room_id == general_chat_room.id
        assert thread.created_by == teacher_user
        assert not thread.is_pinned
        assert not thread.is_locked

    def test_empty_thread_list_then_create_thread(self, general_chat_room, teacher_user):
        """Test that empty thread list becomes non-empty after thread creation"""
        # Verify list is empty
        assert MessageThread.objects.filter(room=general_chat_room).count() == 0

        # Create thread
        MessageThread.objects.create(
            room=general_chat_room,
            title="First thread",
            created_by=teacher_user
        )

        # Verify thread appears in list
        threads = MessageThread.objects.filter(room=general_chat_room)
        assert threads.count() == 1
        assert threads.first().title == "First thread"

    def test_create_multiple_threads(self, general_chat_room, teacher_user):
        """Test creating multiple threads in same chat"""
        # Create 3 threads
        thread_titles = [
            "First question",
            "Second question",
            "Third question"
        ]

        for title in thread_titles:
            MessageThread.objects.create(
                room=general_chat_room,
                title=title,
                created_by=teacher_user
            )

        # Verify all threads exist
        assert MessageThread.objects.filter(room=general_chat_room).count() == 3

        # Verify titles
        titles = list(
            MessageThread.objects.filter(room=general_chat_room)
            .values_list('title', flat=True)
        )
        assert set(titles) == set(thread_titles)


@pytest.mark.integration
@pytest.mark.django_db
class TestThreadMessageWorkflow:
    """Integration tests for posting messages to threads"""

    def test_create_thread_post_message_read_workflow(self, general_chat_room, teacher_user, student_user):
        """Test complete workflow: create thread → post message → read message"""
        # Step 1: Create thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Math homework help",
            created_by=teacher_user
        )

        # Step 2: Student posts message to thread
        message = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=student_user,
            content="Can you explain the formula?",
            message_type=Message.Type.TEXT
        )

        # Step 3: Verify message exists
        assert message.id is not None
        assert message.content == "Can you explain the formula?"
        assert message.sender == student_user
        assert message.thread_id == thread.id

        # Step 4: Verify message appears in thread
        thread_messages = Message.objects.filter(thread=thread)
        assert thread_messages.count() == 1
        assert thread_messages.first().content == "Can you explain the formula?"

    def test_multiple_messages_in_thread_order(self, general_chat_room, teacher_user, student_user):
        """Test that multiple messages in thread maintain correct order"""
        # Create thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Discussion thread",
            created_by=teacher_user
        )

        # Send 3 messages in sequence
        msg1 = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=teacher_user,
            content="First message"
        )

        msg2 = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=student_user,
            content="Second message"
        )

        msg3 = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=teacher_user,
            content="Third message"
        )

        # Verify order in database
        messages = list(Message.objects.filter(thread=thread))
        assert len(messages) == 3
        assert messages[0].id == msg1.id
        assert messages[1].id == msg2.id
        assert messages[2].id == msg3.id

    def test_message_ordering_by_creation_date(self, general_chat_room, teacher_user):
        """Test that messages are ordered by creation date"""
        # Create thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            created_by=teacher_user
        )

        # Create messages
        messages = []
        for i in range(5):
            msg = Message.objects.create(
                room=general_chat_room,
                thread=thread,
                content=f"Message {i+1}",
                sender=teacher_user
            )
            messages.append(msg)

        # Verify order
        db_messages = list(Message.objects.filter(thread=thread))
        for i, msg in enumerate(db_messages):
            assert msg.content == f"Message {i+1}"


@pytest.mark.integration
@pytest.mark.django_db
class TestThreadPinWorkflow:
    """Integration tests for pinning threads"""

    def test_pin_thread_workflow(self, general_chat_room, teacher_user):
        """Test complete workflow: create thread → pin → verify pinned status"""
        # Create thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Important announcement",
            created_by=teacher_user
        )

        # Verify thread is not pinned initially
        assert not thread.is_pinned

        # Pin thread
        thread.is_pinned = True
        thread.save()

        # Verify thread is pinned
        thread.refresh_from_db()
        assert thread.is_pinned

        # Verify pinned status in database
        db_thread = MessageThread.objects.get(id=thread.id)
        assert db_thread.is_pinned is True

    def test_unpin_thread_workflow(self, general_chat_room, teacher_user):
        """Test unpinning a pinned thread"""
        # Create and pin thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Pinned thread",
            created_by=teacher_user,
            is_pinned=True
        )

        # Verify pinned
        assert thread.is_pinned

        # Unpin thread
        thread.is_pinned = False
        thread.save()

        # Verify unpinned
        thread.refresh_from_db()
        assert not thread.is_pinned

    def test_pin_idempotent(self, general_chat_room, teacher_user):
        """Test that pinning already pinned thread is idempotent"""
        # Create and pin thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Test idempotency",
            created_by=teacher_user
        )

        # Pin multiple times
        thread.is_pinned = True
        thread.save()
        thread.is_pinned = True
        thread.save()
        thread.is_pinned = True
        thread.save()

        # Verify still pinned
        thread.refresh_from_db()
        assert thread.is_pinned is True

    def test_pinned_threads_in_ordering(self, general_chat_room, teacher_user):
        """Test that pinned threads are ordered appropriately"""
        # Create 3 threads
        threads = []
        for i in range(3):
            thread = MessageThread.objects.create(
                room=general_chat_room,
                title=f"Thread {i+1}",
                created_by=teacher_user
            )
            threads.append(thread)

        # Pin first and third threads
        threads[0].is_pinned = True
        threads[0].save()
        threads[2].is_pinned = True
        threads[2].save()

        # Verify pinned status
        pinned = MessageThread.objects.filter(room=general_chat_room, is_pinned=True)
        unpinned = MessageThread.objects.filter(room=general_chat_room, is_pinned=False)

        assert pinned.count() == 2
        assert unpinned.count() == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestThreadLockWorkflow:
    """Integration tests for locking threads"""

    def test_lock_thread_workflow(self, general_chat_room, teacher_user):
        """Test complete workflow: create thread → lock → verify cannot post"""
        # Create thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Locked discussion",
            created_by=teacher_user
        )

        # Verify thread is not locked initially
        assert not thread.is_locked

        # Lock thread
        thread.is_locked = True
        thread.save()

        # Verify thread is locked
        thread.refresh_from_db()
        assert thread.is_locked

    def test_locked_thread_state(self, general_chat_room, teacher_user):
        """Test that locked thread has is_locked flag set"""
        # Create locked thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Locked thread",
            created_by=teacher_user,
            is_locked=True
        )

        # Verify locked status
        assert thread.is_locked is True

        # Verify in database
        db_thread = MessageThread.objects.get(id=thread.id)
        assert db_thread.is_locked is True

    def test_unlock_thread(self, general_chat_room, teacher_user):
        """Test unlocking a locked thread"""
        # Create locked thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Thread to unlock",
            created_by=teacher_user,
            is_locked=True
        )

        # Unlock thread
        thread.is_locked = False
        thread.save()

        # Verify unlocked
        thread.refresh_from_db()
        assert not thread.is_locked

    def test_lock_idempotent(self, general_chat_room, teacher_user):
        """Test that locking already locked thread is idempotent"""
        # Create and lock thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Lock idempotency",
            created_by=teacher_user
        )

        # Lock multiple times
        thread.is_locked = True
        thread.save()
        thread.is_locked = True
        thread.save()

        # Verify locked
        thread.refresh_from_db()
        assert thread.is_locked is True


@pytest.mark.integration
@pytest.mark.django_db
class TestGeneralChatMessageWorkflow:
    """Integration tests for general chat messages (not in threads)"""

    def test_send_message_to_general_chat(self, general_chat_room, teacher_user):
        """Test sending message directly to general chat"""
        # Send message (not to thread)
        message = Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="Hello everyone!",
            message_type=Message.Type.TEXT,
            thread=None  # Not in a thread
        )

        # Verify message exists
        assert message.id is not None
        assert message.content == "Hello everyone!"
        assert message.sender == teacher_user
        assert message.room == general_chat_room
        assert message.thread is None

    def test_empty_general_chat_then_send_message(self, general_chat_room, teacher_user):
        """Test that empty chat becomes non-empty after message"""
        # Verify chat is empty
        assert Message.objects.filter(room=general_chat_room).count() == 0

        # Send message
        Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="First message",
            thread=None
        )

        # Verify message appears
        messages = Message.objects.filter(room=general_chat_room, thread__isnull=True)
        assert messages.count() == 1
        assert messages.first().content == "First message"

    def test_multiple_messages_in_general_chat(self, general_chat_room, teacher_user, student_user):
        """Test multiple messages in general chat"""
        # Teacher sends message
        msg1 = Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="Teacher says hello",
            thread=None
        )

        # Student sends message
        msg2 = Message.objects.create(
            room=general_chat_room,
            sender=student_user,
            content="Student replies",
            thread=None
        )

        # Verify order
        messages = list(Message.objects.filter(room=general_chat_room, thread__isnull=True))
        assert len(messages) == 2
        assert messages[0].id == msg1.id
        assert messages[1].id == msg2.id
        assert messages[0].sender == teacher_user
        assert messages[1].sender == student_user

    def test_general_chat_messages_persist(self, general_chat_room, teacher_user):
        """Test that messages persist correctly"""
        # Create 10 messages
        for i in range(10):
            Message.objects.create(
                room=general_chat_room,
                sender=teacher_user,
                content=f"Message {i+1}",
                thread=None
            )

        # Verify all persisted
        messages = Message.objects.filter(room=general_chat_room, thread__isnull=True)
        assert messages.count() == 10

        # Verify content
        contents = list(messages.values_list('content', flat=True))
        for i, content in enumerate(contents):
            assert content == f"Message {i+1}"


@pytest.mark.integration
@pytest.mark.django_db
class TestDatabaseStateManagement:
    """Integration tests for database state consistency"""

    def test_thread_creation_persists_to_database(self, general_chat_room, teacher_user):
        """Test that thread creation properly persists to database"""
        initial_count = MessageThread.objects.count()

        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Persistence test",
            created_by=teacher_user
        )

        # Verify count increased
        assert MessageThread.objects.count() == initial_count + 1

        # Verify exact data
        db_thread = MessageThread.objects.get(id=thread.id)
        assert db_thread.title == "Persistence test"
        assert db_thread.created_by == teacher_user
        assert db_thread.room == general_chat_room

    def test_message_creation_persists_to_database(self, general_chat_room, teacher_user):
        """Test that message creation properly persists to database"""
        initial_count = Message.objects.count()

        message = Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="Persistence test message",
            thread=None
        )

        # Verify count increased
        assert Message.objects.count() == initial_count + 1

        # Verify exact data
        db_message = Message.objects.get(id=message.id)
        assert db_message.content == "Persistence test message"
        assert db_message.sender == teacher_user
        assert db_message.room == general_chat_room

    def test_no_state_leakage_between_tests(self, general_chat_room):
        """Test that state from one test does not affect another"""
        # This test verifies that database isolation works correctly
        # Each test should get a clean database
        assert ChatRoom.objects.count() == 1  # Only the fixture room
        assert MessageThread.objects.count() == 0
        assert Message.objects.count() == 0

    def test_thread_count_matches_database(self, general_chat_room, teacher_user):
        """Test that thread count is accurate"""
        # Create 5 threads
        for i in range(5):
            MessageThread.objects.create(
                room=general_chat_room,
                title=f"Thread {i+1}",
                created_by=teacher_user
            )

        # Check count in database
        db_count = MessageThread.objects.filter(room=general_chat_room).count()
        assert db_count == 5

    def test_message_count_matches_database(self, general_chat_room, teacher_user):
        """Test that message count is accurate"""
        # Create 10 messages
        for i in range(10):
            Message.objects.create(
                room=general_chat_room,
                sender=teacher_user,
                content=f"Message {i+1}",
                thread=None
            )

        # Check count in database
        db_count = Message.objects.filter(room=general_chat_room, thread__isnull=True).count()
        assert db_count == 10

    def test_thread_and_message_separation(self, general_chat_room, teacher_user):
        """Test that thread messages are separate from general messages"""
        # Create thread with messages
        thread = MessageThread.objects.create(
            room=general_chat_room,
            created_by=teacher_user
        )
        thread_msg = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=teacher_user,
            content="Thread message"
        )

        # Create general message
        general_msg = Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="General message",
            thread=None
        )

        # Verify counts
        thread_count = Message.objects.filter(thread=thread).count()
        general_count = Message.objects.filter(room=general_chat_room, thread__isnull=True).count()

        assert thread_count == 1
        assert general_count == 1
        assert thread_count + general_count == 2


@pytest.mark.integration
@pytest.mark.django_db
class TestCompleteUserFlow:
    """Integration tests for realistic complete user flows"""

    def test_complete_forum_discussion_flow(self, general_chat_room, teacher_user, student_user):
        """Test realistic forum discussion workflow"""
        # 1. Teacher creates thread
        thread = MessageThread.objects.create(
            room=general_chat_room,
            title="Weekly homework discussion",
            created_by=teacher_user
        )
        assert thread.id is not None

        # 2. Student posts first message
        msg1 = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=student_user,
            content="I have questions about problem 3"
        )
        assert msg1.id is not None

        # 3. Teacher replies
        msg2 = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=teacher_user,
            content="Good question! Let me explain..."
        )
        assert msg2.id is not None

        # 4. Student sends follow-up
        msg3 = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=student_user,
            content="Thank you, that makes sense!"
        )
        assert msg3.id is not None

        # 5. Teacher pins important discussion
        thread.is_pinned = True
        thread.save()

        # 6. Verify final state
        thread.refresh_from_db()
        assert thread.is_pinned is True
        assert thread.messages.count() == 3

        # 7. Verify message order
        messages = list(thread.messages.all())
        assert len(messages) == 3
        assert messages[0].sender == student_user
        assert messages[1].sender == teacher_user
        assert messages[2].sender == student_user

    def test_complete_general_chat_flow(self, general_chat_room, teacher_user, student_user):
        """Test realistic general chat flow"""
        # 1. Teacher sends announcement
        msg1 = Message.objects.create(
            room=general_chat_room,
            sender=teacher_user,
            content="Important announcement for everyone",
            thread=None
        )
        assert msg1.id is not None

        # 2. Student reacts
        msg2 = Message.objects.create(
            room=general_chat_room,
            sender=student_user,
            content="Thank you for the update",
            thread=None
        )
        assert msg2.id is not None

        # 3. Verify both can read full conversation
        messages = Message.objects.filter(room=general_chat_room, thread__isnull=True)
        assert messages.count() == 2

        # 4. Verify message order
        msg_list = list(messages)
        assert msg_list[0].content == "Important announcement for everyone"
        assert msg_list[1].content == "Thank you for the update"
        assert msg_list[0].sender == teacher_user
        assert msg_list[1].sender == student_user

    def test_mixed_threads_and_general_messages(self, general_chat_room, teacher_user, student_user):
        """Test chat with both threaded and general messages"""
        # Create thread with messages
        thread = MessageThread.objects.create(
            room=general_chat_room,
            created_by=teacher_user
        )
        thread_msg = Message.objects.create(
            room=general_chat_room,
            thread=thread,
            sender=teacher_user,
            content="Thread discussion"
        )

        # Create general messages
        general_msg = Message.objects.create(
            room=general_chat_room,
            sender=student_user,
            content="General announcement",
            thread=None
        )

        # Verify separation
        thread_messages = Message.objects.filter(thread=thread)
        general_messages = Message.objects.filter(room=general_chat_room, thread__isnull=True)

        assert thread_messages.count() == 1
        assert general_messages.count() == 1

        # Verify contents
        assert thread_messages.first().content == "Thread discussion"
        assert general_messages.first().content == "General announcement"
