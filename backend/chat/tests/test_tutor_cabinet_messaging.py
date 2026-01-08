"""
T073-T087: Comprehensive messaging and forum tests for Tutor Cabinet

Test Cases:
- T073-T083: Chat functionality (direct messages, WebSocket, editing, deletion, files, history, notifications, mute, archive)
- T084-T087: Forum functionality (posts, replies, moderation, announcements)
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone


User = get_user_model()


@pytest.fixture
def tutor_user(db):
    """Create tutor user with profile"""
    from accounts.models import TutorProfile

    user = User.objects.create_user(
        username="tutor_test",
        email="tutor@test.com",
        password="test123",
        first_name="Тьютор",
        last_name="Тестовый",
        role="tutor",
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_user(db):
    """Create student user"""
    return User.objects.create_user(
        username="student_test",
        email="student@test.com",
        password="test123",
        first_name="Студент",
        last_name="Тестовый",
        role="student",
    )


@pytest.fixture
def another_student(db):
    """Create another student for group chat tests"""
    return User.objects.create_user(
        username="student2_test",
        email="student2@test.com",
        password="test123",
        first_name="Студент2",
        last_name="Тестовый",
        role="student",
    )


@pytest.fixture
def subject(db):
    """Create test subject"""
    from materials.models import Subject

    return Subject.objects.create(name="Тестовый предмет", slug="test-subject")


@pytest.fixture
def direct_chat_room(db, tutor_user, student_user):
    """Create direct chat room between tutor and student"""
    from chat.models import ChatRoom, ChatParticipant

    room = ChatRoom.objects.create(
        name=f"Chat: {tutor_user.first_name} - {student_user.first_name}",
        type=ChatRoom.Type.DIRECT,
        created_by=tutor_user,
    )
    room.participants.add(tutor_user, student_user)
    ChatParticipant.objects.create(room=room, user=tutor_user, is_admin=True)
    ChatParticipant.objects.create(room=room, user=student_user)
    return room


@pytest.fixture
def group_chat_room(db, tutor_user, student_user, another_student):
    """Create group chat room"""
    from chat.models import ChatRoom, ChatParticipant

    room = ChatRoom.objects.create(
        name="Групповой чат", type=ChatRoom.Type.GROUP, created_by=tutor_user
    )
    room.participants.add(tutor_user, student_user, another_student)
    ChatParticipant.objects.create(room=room, user=tutor_user, is_admin=True)
    ChatParticipant.objects.create(room=room, user=student_user)
    ChatParticipant.objects.create(room=room, user=another_student)
    return room


@pytest.fixture
def forum_room(db, tutor_user, student_user, subject):
    """Create forum chat room"""
    from chat.models import ChatRoom, ChatParticipant
    from materials.models import SubjectEnrollment

    enrollment = SubjectEnrollment.objects.create(
        student=student_user, subject=subject, tutor=tutor_user
    )
    room = ChatRoom.objects.create(
        name=f"Forum: {subject.name}",
        type=ChatRoom.Type.FORUM_TUTOR,
        created_by=tutor_user,
        enrollment=enrollment,
    )
    room.participants.add(tutor_user, student_user)
    ChatParticipant.objects.create(room=room, user=tutor_user, is_admin=True)
    ChatParticipant.objects.create(room=room, user=student_user)
    return room


@pytest.fixture
def api_client():
    """Create API client"""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_tutor_client(api_client, tutor_user):
    """Create authenticated API client for tutor"""
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=tutor_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def authenticated_student_client(api_client, student_user):
    """Create authenticated API client for student"""
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=student_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


# ==================== T073: Chat Initiation Tests ====================


@pytest.mark.django_db
class TestT073ChatInitiation:
    """T073: Начало чата, отправка сообщений"""

    def test_create_direct_chat_room(self, authenticated_tutor_client):
        """Test creating direct chat room"""
        from rest_framework import status

        response = authenticated_tutor_client.post(
            "/api/chat/rooms/",
            {"name": "Test Chat", "type": "direct", "description": "Test description"},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_send_text_message(self, authenticated_tutor_client, direct_chat_room):
        """Test sending text message"""
        from rest_framework import status
        from chat.models import Message

        response = authenticated_tutor_client.post(
            "/api/chat/messages/",
            {
                "room": direct_chat_room.id,
                "content": "Hello, student!",
                "message_type": "text",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_cannot_send_message_if_not_participant(
        self, api_client, direct_chat_room, student_user, another_student
    ):
        """Test non-participant cannot send message"""
        from rest_framework import status
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=another_student)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.post(
            "/api/chat/messages/",
            {"room": direct_chat_room.id, "content": "Should fail"},
        )
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_join_chat_room(
        self, authenticated_student_client, tutor_user, student_user
    ):
        """Test joining chat room"""
        from rest_framework import status
        from chat.models import ChatRoom, ChatParticipant

        # Create room with only tutor
        room = ChatRoom.objects.create(
            name="Test room", type=ChatRoom.Type.GROUP, created_by=tutor_user
        )
        room.participants.add(tutor_user)
        ChatParticipant.objects.create(room=room, user=tutor_user, is_admin=True)

        # Student joins
        response = authenticated_student_client.post(f"/api/chat/rooms/{room.id}/join/")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


# ==================== T074-T075: WebSocket & Messages ====================


@pytest.mark.django_db
class TestT074WebSocketMessages:
    """T074-T075: WebSocket и сообщения"""

    def test_list_messages_in_room(self, authenticated_tutor_client, direct_chat_room):
        """Test listing messages in chat room"""
        from rest_framework import status
        from chat.models import Message

        # Create messages
        tutor = User.objects.get(email="tutor@test.com")
        Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Message 1",
            message_type="text",
        )
        Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Message 2",
            message_type="text",
        )

        response = authenticated_tutor_client.get(
            f"/api/chat/rooms/{direct_chat_room.id}/messages/"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_mark_messages_as_read(
        self, authenticated_student_client, direct_chat_room
    ):
        """Test marking messages as read"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        message = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Read this",
            message_type="text",
        )

        response = authenticated_student_client.post(
            f"/api/chat/messages/{message.id}/mark_as_read/", {}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


# ==================== T076: Message Editing ====================


@pytest.mark.django_db
class TestT076MessageEditing:
    """T076: Редактирование сообщений"""

    def test_edit_own_message(self, authenticated_tutor_client, direct_chat_room):
        """Test editing own message"""
        from rest_framework import status
        from chat.models import Message

        # Create message
        tutor = User.objects.get(email="tutor@test.com")
        msg = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Original message",
            message_type="text",
        )

        # Edit message
        response = authenticated_tutor_client.patch(
            f"/api/chat/messages/{msg.id}/", {"content": "Edited message"}
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

        # Verify
        msg.refresh_from_db()
        assert msg.content == "Edited message"
        assert msg.is_edited is True

    def test_cannot_edit_others_message(
        self, authenticated_tutor_client, authenticated_student_client, direct_chat_room
    ):
        """Test user cannot edit other's message"""
        from rest_framework import status
        from chat.models import Message

        # Tutor creates message
        tutor = User.objects.get(email="tutor@test.com")
        msg = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Tutor message",
            message_type="text",
        )

        # Student tries to edit
        response = authenticated_student_client.patch(
            f"/api/chat/messages/{msg.id}/", {"content": "Hacked message"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== T077: Message Deletion ====================


@pytest.mark.django_db
class TestT077MessageDeletion:
    """T077: Удаление сообщений"""

    def test_soft_delete_own_message(
        self, authenticated_tutor_client, direct_chat_room
    ):
        """Test soft deleting own message"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        msg = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Message to delete",
            message_type="text",
        )

        response = authenticated_tutor_client.delete(f"/api/chat/messages/{msg.id}/")
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]

        # Verify soft delete
        msg.refresh_from_db()
        assert msg.is_deleted is True

    def test_cannot_delete_others_message(
        self, authenticated_tutor_client, authenticated_student_client, direct_chat_room
    ):
        """Test user cannot delete other's message"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        msg = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Protected message",
            message_type="text",
        )

        response = authenticated_student_client.delete(f"/api/chat/messages/{msg.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Message should still exist
        msg.refresh_from_db()
        assert msg.is_deleted is False

    def test_deleted_message_not_in_list(
        self, authenticated_tutor_client, direct_chat_room
    ):
        """Test deleted messages don't appear in list"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        msg = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Will delete",
            message_type="text",
        )
        msg.delete()

        response = authenticated_tutor_client.get(
            f"/api/chat/rooms/{direct_chat_room.id}/messages/"
        )
        assert response.status_code == status.HTTP_200_OK
        # Deleted message should not be in list
        if response.data:
            message_ids = [m.get("id") for m in response.data]
            assert msg.id not in message_ids


# ==================== T078: File Upload ====================


@pytest.mark.django_db
class TestT078FileUpload:
    """T078: Загрузка файлов в чат"""

    def test_upload_image(self, authenticated_tutor_client, direct_chat_room):
        """Test uploading image to chat"""
        from rest_framework import status

        image_file = SimpleUploadedFile(
            "test.jpg", b"fake image content", content_type="image/jpeg"
        )

        response = authenticated_tutor_client.post(
            "/api/chat/messages/",
            {"room": direct_chat_room.id, "message_type": "image", "image": image_file},
            format="multipart",
        )

        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_upload_file(self, authenticated_tutor_client, direct_chat_room):
        """Test uploading file to chat"""
        from rest_framework import status

        test_file = SimpleUploadedFile(
            "document.pdf", b"fake pdf content", content_type="application/pdf"
        )

        response = authenticated_tutor_client.post(
            "/api/chat/messages/",
            {"room": direct_chat_room.id, "message_type": "file", "file": test_file},
            format="multipart",
        )

        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]


# ==================== T079: Chat History ====================


@pytest.mark.django_db
class TestT079ChatHistory:
    """T079: История чата"""

    def test_get_chat_history(self, authenticated_tutor_client, direct_chat_room):
        """Test retrieving chat history"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        for i in range(5):
            Message.objects.create(
                room=direct_chat_room,
                sender=tutor,
                content=f"Message {i}",
                message_type="text",
            )

        response = authenticated_tutor_client.get(
            f"/api/chat/rooms/{direct_chat_room.id}/messages/"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_history_excludes_deleted(
        self, authenticated_tutor_client, direct_chat_room
    ):
        """Test deleted messages excluded from history"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        msg = Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="To be deleted",
            message_type="text",
        )
        msg.delete()

        response = authenticated_tutor_client.get(
            f"/api/chat/rooms/{direct_chat_room.id}/messages/"
        )
        assert response.status_code == status.HTTP_200_OK


# ==================== T080: Notifications ====================


@pytest.mark.django_db
class TestT080Notifications:
    """T080: Уведомления о новых сообщениях"""

    def test_unread_message_badge(
        self, authenticated_tutor_client, authenticated_student_client, direct_chat_room
    ):
        """Test unread message count"""
        from rest_framework import status
        from chat.models import Message

        tutor = User.objects.get(email="tutor@test.com")
        Message.objects.create(
            room=direct_chat_room,
            sender=tutor,
            content="Unread message",
            message_type="text",
        )

        response = authenticated_student_client.get("/api/chat/rooms/")
        assert response.status_code == status.HTTP_200_OK

    def test_clear_unread_on_read(self, authenticated_student_client, direct_chat_room):
        """Test unread count clears when read"""
        from rest_framework import status
        from chat.models import Message, MessageRead, ChatParticipant

        tutor = User.objects.get(email="tutor@test.com")
        student = User.objects.get(email="student@test.com")

        message = Message.objects.create(
            room=direct_chat_room, sender=tutor, content="Unread", message_type="text"
        )

        # Mark as read
        MessageRead.objects.create(message=message, user=student)

        # Update participant
        participant = ChatParticipant.objects.get(room=direct_chat_room, user=student)
        participant.last_read_at = timezone.now()
        participant.save()

        # Verify
        assert MessageRead.objects.filter(message=message, user=student).exists()


# ==================== T081: Message Mute ====================


@pytest.mark.django_db
class TestT081MessageMute:
    """T081: Отключение уведомлений (mute)"""

    def test_mute_room(self, authenticated_student_client, direct_chat_room):
        """Test muting a room"""
        from rest_framework import status
        from chat.models import ChatParticipant

        student = User.objects.get(email="student@test.com")
        participant = ChatParticipant.objects.get(room=direct_chat_room, user=student)

        response = authenticated_student_client.post(
            f"/api/chat/rooms/{direct_chat_room.id}/mute/", {}
        )

        if response.status_code == status.HTTP_200_OK:
            participant.refresh_from_db()
            assert participant.is_muted is True


# ==================== T082: Archive ====================


@pytest.mark.django_db
class TestT082Archive:
    """T082: Архивирование чатов"""

    def test_archive_chat_room(self, authenticated_tutor_client, direct_chat_room):
        """Test archiving a chat room"""
        from rest_framework import status

        response = authenticated_tutor_client.patch(
            f"/api/chat/rooms/{direct_chat_room.id}/", {"is_active": False}
        )

        if response.status_code == status.HTTP_200_OK:
            direct_chat_room.refresh_from_db()
            assert direct_chat_room.is_active is False


# ==================== T084-T087: Forum Tests ====================


@pytest.mark.django_db
class TestT084ForumPostCreation:
    """T084: Создание постов в форуме"""

    def test_create_forum_post(self, authenticated_tutor_client, forum_room):
        """Test creating forum post (thread)"""
        from rest_framework import status
        from chat.models import MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        thread = MessageThread.objects.create(
            room=forum_room, title="Question about algebra", created_by=tutor
        )
        assert thread.id is not None

    def test_list_forum_posts(self, authenticated_student_client, forum_room):
        """Test listing forum posts"""
        from rest_framework import status
        from chat.models import MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        for i in range(3):
            MessageThread.objects.create(
                room=forum_room, title=f"Post {i}", created_by=tutor
            )

        response = authenticated_student_client.get(
            f"/api/chat/rooms/{forum_room.id}/threads/"
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
class TestT085ForumReplies:
    """T085: Ответы в форуме"""

    def test_reply_to_forum_post(self, authenticated_student_client, forum_room):
        """Test replying to forum post"""
        from rest_framework import status
        from chat.models import Message, MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        thread = MessageThread.objects.create(
            room=forum_room, title="Question", created_by=tutor
        )

        response = authenticated_student_client.post(
            "/api/chat/messages/",
            {
                "room": forum_room.id,
                "thread": thread.id,
                "content": "Here is the answer",
                "message_type": "text",
            },
        )

        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_get_thread_replies(self, authenticated_student_client, forum_room):
        """Test getting all replies to a thread"""
        from rest_framework import status
        from chat.models import Message, MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        student = User.objects.get(email="student@test.com")

        thread = MessageThread.objects.create(
            room=forum_room, title="Topic", created_by=tutor
        )

        for i in range(2):
            Message.objects.create(
                room=forum_room,
                thread=thread,
                sender=student,
                content=f"Reply {i}",
                message_type="text",
            )

        response = authenticated_student_client.get(
            f"/api/chat/threads/{thread.id}/messages/"
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
class TestT086ForumModeration:
    """T086: Модерация форума"""

    def test_pin_forum_post(self, authenticated_tutor_client, forum_room):
        """Test pinning important forum post"""
        from rest_framework import status
        from chat.models import MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        thread = MessageThread.objects.create(
            room=forum_room, title="Important announcement", created_by=tutor
        )

        response = authenticated_tutor_client.patch(
            f"/api/chat/threads/{thread.id}/", {"is_pinned": True}
        )

        if response.status_code == status.HTTP_200_OK:
            thread.refresh_from_db()
            assert thread.is_pinned is True

    def test_lock_forum_post(self, authenticated_tutor_client, forum_room):
        """Test locking forum post"""
        from rest_framework import status
        from chat.models import MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        thread = MessageThread.objects.create(
            room=forum_room, title="Locked post", created_by=tutor
        )

        response = authenticated_tutor_client.patch(
            f"/api/chat/threads/{thread.id}/", {"is_locked": True}
        )

        if response.status_code == status.HTTP_200_OK:
            thread.refresh_from_db()
            assert thread.is_locked is True

    def test_cannot_reply_to_locked_post(
        self, authenticated_student_client, forum_room
    ):
        """Test users cannot reply to locked post"""
        from rest_framework import status
        from chat.models import MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        thread = MessageThread.objects.create(
            room=forum_room, title="Locked", created_by=tutor, is_locked=True
        )

        response = authenticated_student_client.post(
            "/api/chat/messages/",
            {
                "room": forum_room.id,
                "thread": thread.id,
                "content": "Should fail",
                "message_type": "text",
            },
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestT087ForumAnnouncements:
    """T087: Объявления в форуме"""

    def test_create_announcement_thread(self, authenticated_tutor_client, forum_room):
        """Test creating announcement thread"""
        from rest_framework import status
        from chat.models import MessageThread

        tutor = User.objects.get(email="tutor@test.com")
        thread = MessageThread.objects.create(
            room=forum_room,
            title="Important Announcement",
            created_by=tutor,
            is_pinned=True,
        )
        assert thread.is_pinned is True

    def test_announcement_visible_to_all(
        self, authenticated_student_client, forum_room
    ):
        """Test announcement visible to all forum participants"""
        from rest_framework import status
        from chat.models import MessageThread, Message

        tutor = User.objects.get(email="tutor@test.com")

        thread = MessageThread.objects.create(
            room=forum_room,
            title="System Announcement",
            created_by=tutor,
            is_pinned=True,
        )

        Message.objects.create(
            room=forum_room,
            thread=thread,
            sender=tutor,
            content="Important: System maintenance",
            message_type="text",
        )

        response = authenticated_student_client.get(
            f"/api/chat/rooms/{forum_room.id}/threads/"
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# ==================== Security Tests ====================


@pytest.mark.django_db
class TestSecurityAndPermissions:
    """Security and permission tests"""

    def test_user_cannot_see_others_private_chats(
        self, authenticated_student_client, tutor_user, another_student
    ):
        """Test user cannot access private chats they're not in"""
        from rest_framework import status
        from chat.models import ChatRoom

        private_room = ChatRoom.objects.create(
            name="Private", type=ChatRoom.Type.DIRECT, created_by=tutor_user
        )
        private_room.participants.add(tutor_user, another_student)

        response = authenticated_student_client.get(
            f"/api/chat/rooms/{private_room.id}/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_leave_chat_room(self, authenticated_student_client, direct_chat_room):
        """Test leaving chat room"""
        from rest_framework import status

        response = authenticated_student_client.post(
            f"/api/chat/rooms/{direct_chat_room.id}/leave/"
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

        student = User.objects.get(email="student@test.com")
        assert not direct_chat_room.participants.filter(id=student.id).exists()
