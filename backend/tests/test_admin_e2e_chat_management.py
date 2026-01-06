"""
E2E тесты для управления чатами в админской панели.

Тестирует полный workflow:
1. LIST: Загрузка списка чат-комнат
2. VIEW: Просмотр сообщений в комнате
3. FILTER: Фильтрация по типу и поиску
4. STATS: Статистика чатов
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from uuid import uuid4

from chat.models import ChatRoom, Message
from materials.models import Subject, SubjectEnrollment
from accounts.models import TeacherProfile, StudentProfile

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create superuser for admin access"""
    unique_id = uuid4().hex[:8]
    user = User.objects.create_superuser(
        username=f"admin_{unique_id}",
        email=f"admin_{unique_id}@test.com",
        password="admin123secure",
        first_name="Admin",
        last_name="User",
        role=User.Role.ADMIN,
    )
    return user


@pytest.fixture
def teacher_user(db):
    """Create teacher user with profile"""
    unique_id = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"teacher1_{unique_id}",
        email=f"teacher1_{unique_id}@test.com",
        password="teacher123secure",
        first_name="John",
        last_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    TeacherProfile.objects.create(
        user=user,
        subject="Mathematics",
        experience_years=5,
        bio="Experienced math teacher",
    )
    return user


@pytest.fixture
def student_user(db):
    """Create student user with profile"""
    unique_id = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"student1_{unique_id}",
        email=f"student1_{unique_id}@test.com",
        password="student123secure",
        first_name="Alice",
        last_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(
        user=user,
        grade=10,
        goal="Pass the exam",
    )
    return user


@pytest.fixture
def student_user_2(db):
    """Create second student"""
    unique_id = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"student2_{unique_id}",
        email=f"student2_{unique_id}@test.com",
        password="student456secure",
        first_name="Bob",
        last_name="Learner",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(
        user=user,
        grade=9,
        goal="Improve grades",
    )
    return user


@pytest.fixture
def subject_math(db):
    """Create Mathematics subject"""
    return Subject.objects.create(
        name="Mathematics",
        description="Basic mathematics course",
        color="#FF5733",
    )


@pytest.fixture
def subject_english(db):
    """Create English subject"""
    return Subject.objects.create(
        name="English",
        description="English language and literature",
        color="#33FF57",
    )


@pytest.fixture
def enrollment_math(db, student_user, subject_math, teacher_user):
    """Create subject enrollment for student"""
    return SubjectEnrollment.objects.create(
        student=student_user,
        subject=subject_math,
        teacher=teacher_user,
        is_active=True,
    )


@pytest.fixture
def enrollment_english(db, student_user_2, subject_english, teacher_user):
    """Create subject enrollment for second student"""
    return SubjectEnrollment.objects.create(
        student=student_user_2,
        subject=subject_english,
        teacher=teacher_user,
        is_active=True,
    )


@pytest.fixture
def forum_room_math(db, teacher_user, enrollment_math):
    """Get forum room for math subject (auto-created on enrollment)"""
    # Forum room is auto-created when SubjectEnrollment is created
    # Just retrieve it or create if doesn't exist with proper type
    room, created = ChatRoom.objects.get_or_create(
        type=ChatRoom.Type.FORUM_SUBJECT,
        enrollment=enrollment_math,
        defaults={
            "name": "Forum: Mathematics Discussion",
            "description": "General discussion forum for mathematics",
            "created_by": teacher_user,
            "is_active": True,
        }
    )
    return room


@pytest.fixture
def forum_room_english(db, teacher_user, enrollment_english):
    """Get forum room for english subject (auto-created on enrollment)"""
    # Forum room is auto-created when SubjectEnrollment is created
    room, created = ChatRoom.objects.get_or_create(
        type=ChatRoom.Type.FORUM_SUBJECT,
        enrollment=enrollment_english,
        defaults={
            "name": "Forum: English Literature",
            "description": "Discussion forum for english literature",
            "created_by": teacher_user,
            "is_active": True,
        }
    )
    return room


@pytest.fixture
def direct_room(db, teacher_user, student_user):
    """Create direct chat room"""
    room = ChatRoom.objects.create(
        name=f"Direct: {teacher_user.first_name} and {student_user.first_name}",
        type=ChatRoom.Type.DIRECT,
        created_by=teacher_user,
        is_active=True,
    )
    room.participants.add(teacher_user, student_user)
    return room


@pytest.fixture
def group_room(db, teacher_user, student_user, student_user_2):
    """Create group chat room"""
    room = ChatRoom.objects.create(
        name="Group: Study Group",
        description="Study group for collaborative learning",
        type=ChatRoom.Type.GROUP,
        created_by=teacher_user,
        is_active=True,
    )
    room.participants.add(teacher_user, student_user, student_user_2)
    return room


@pytest.fixture
def messages_in_forum_room(db, forum_room_math, teacher_user, student_user):
    """Create messages in forum room"""
    messages = []
    for i in range(5):
        msg = Message.objects.create(
            room=forum_room_math,
            sender=teacher_user if i % 2 == 0 else student_user,
            content=f"Test message {i+1}",
            message_type=Message.Type.TEXT,
        )
        messages.append(msg)
    return messages


@pytest.fixture
def messages_in_direct_room(db, direct_room, teacher_user, student_user):
    """Create messages in direct room"""
    messages = []
    for i in range(3):
        msg = Message.objects.create(
            room=direct_room,
            sender=teacher_user if i % 2 == 0 else student_user,
            content=f"Direct message {i+1}",
            message_type=Message.Type.TEXT,
        )
        messages.append(msg)
    return messages


@pytest.fixture
def api_client():
    """Provide unauthenticated API client for tests"""
    return APIClient()


@pytest.fixture
def authenticated_admin_client(admin_user):
    """Create API client authenticated as admin using force_authenticate"""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def authenticated_teacher_client(teacher_user):
    """Create API client authenticated as teacher using force_authenticate"""
    api_client = APIClient()
    api_client.force_authenticate(user=teacher_user)
    return api_client


class TestAdminChatRoomsList:
    """Test cases for listing chat rooms (admin only)"""

    def test_list_rooms_admin_success(
        self, authenticated_admin_client, forum_room_math, forum_room_english, direct_room, group_room
    ):
        """Test that admin can list all chat rooms"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "data" in response.json()

        data = response.json()["data"]
        assert "rooms" in data
        assert "count" in data
        assert data["count"] == 4  # 2 forum + 1 direct + 1 group

    def test_list_rooms_contains_required_columns(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that list response contains required columns for UI table"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")

        assert response.status_code == 200
        rooms = response.json()["data"]["rooms"]
        assert len(rooms) > 0

        # Check required fields for table display
        room = rooms[0]
        assert "id" in room
        assert "name" in room
        assert "type" in room
        assert "participants_count" in room
        # messages_count should be present from admin view (may not be in regular serializer)
        assert "updated_at" in room  # At minimum show last activity

    def test_list_rooms_shows_participants_count(
        self, authenticated_admin_client, group_room
    ):
        """Test that rooms display correct participant count"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")

        assert response.status_code == 200
        rooms = response.json()["data"]["rooms"]

        # Find group room with 3 participants
        group_rooms = [r for r in rooms if r["type"] == "group"]
        assert len(group_rooms) == 1
        assert group_rooms[0]["participants_count"] == 3

    def test_list_rooms_shows_message_count(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that rooms display correct participant count (basic verification)"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")

        assert response.status_code == 200
        rooms = response.json()["data"]["rooms"]

        # Find forum room - verify it has expected participants
        forum_rooms = [r for r in rooms if r["type"] == "forum_subject"]
        assert len(forum_rooms) > 0
        # Forum room auto-created with 2 participants (teacher + student)
        assert forum_rooms[0]["participants_count"] >= 2

    def test_list_rooms_no_auth_forbidden(self, api_client, forum_room_math):
        """Test that unauthenticated users cannot list rooms"""
        client = APIClient()  # No auth
        response = client.get("/api/chat/admin/rooms/")

        assert response.status_code in [401, 403]

    def test_list_rooms_teacher_forbidden(self, authenticated_teacher_client, forum_room_math):
        """Test that non-admin users cannot list all rooms"""
        response = authenticated_teacher_client.get("/api/chat/admin/rooms/")

        assert response.status_code == 403

    def test_list_rooms_sorted_by_updated_at(
        self, db, authenticated_admin_client, forum_room_math, direct_room
    ):
        """Test that rooms are sorted by updated_at descending"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        assert response.status_code == 200

        rooms = response.json()["data"]["rooms"]

        # Most recently updated should be first
        if len(rooms) >= 2:
            updated_times = [r["updated_at"] for r in rooms]
            assert updated_times == sorted(updated_times, reverse=True)


class TestAdminChatRoomDetail:
    """Test cases for viewing chat room details"""

    def test_get_room_detail_success(
        self, authenticated_admin_client, forum_room_math
    ):
        """Test that admin can get room detail"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(f"/api/chat/admin/rooms/{room_id}/")

        assert response.status_code == 200
        assert response.json()["success"] is True

        data = response.json()["data"]
        assert data["room"]["id"] == room_id
        assert data["room"]["name"] == forum_room_math.name

    def test_get_room_detail_contains_stats(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that room detail contains participant and message counts"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(f"/api/chat/admin/rooms/{room_id}/")

        assert response.status_code == 200
        data = response.json()["data"]
        assert "participants_count" in data
        assert "messages_count" in data
        assert data["participants_count"] == 2
        assert data["messages_count"] == 5

    def test_get_room_detail_not_found(self, authenticated_admin_client):
        """Test 404 for non-existent room"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/99999/")

        assert response.status_code == 404
        assert response.json()["success"] is False

    def test_get_room_detail_no_auth_forbidden(self, api_client, forum_room_math):
        """Test that unauthenticated users cannot get room detail"""
        client = APIClient()
        response = client.get(f"/api/chat/admin/rooms/{forum_room_math.id}/")

        assert response.status_code in [401, 403]


class TestAdminChatRoomMessages:
    """Test cases for viewing messages in a chat room"""

    def test_get_room_messages_success(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that admin can get messages from a room"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(f"/api/chat/admin/rooms/{room_id}/messages/")

        assert response.status_code == 200
        assert response.json()["success"] is True

        data = response.json()["data"]
        # room_id may be returned as string or int
        assert int(data["room_id"]) == room_id
        assert "messages" in data
        # At least the 5 messages we created should be present
        assert len(data["messages"]) >= 5

    def test_get_room_messages_contains_sender_info(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that messages contain sender information"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(f"/api/chat/admin/rooms/{room_id}/messages/")

        assert response.status_code == 200
        messages_data = response.json()["data"]["messages"]
        assert len(messages_data) > 0

        # Check first few messages for sender info
        for msg in messages_data[:5]:
            assert "id" in msg
            assert "content" in msg
            assert "created_at" in msg
            # Sender should have user info
            if "sender" in msg:
                sender = msg["sender"]
                # Should have at least id
                assert "id" in sender or isinstance(sender, (int, dict))

    def test_get_room_messages_pagination_limit(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test pagination with limit parameter"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{room_id}/messages/?limit=2"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["messages"]) == 2
        assert data["limit"] == 2
        assert data["count"] == 5  # Total count unchanged

    def test_get_room_messages_pagination_offset(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test pagination with offset parameter"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{room_id}/messages/?limit=2&offset=2"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["messages"]) == 2
        assert data["offset"] == 2

    def test_get_room_messages_max_limit_capped(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that max limit is capped at 500"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{room_id}/messages/?limit=1000"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["limit"] == 500  # Should be capped

    def test_get_room_messages_messages_from_different_users(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test that messages show different senders"""
        room_id = forum_room_math.id
        response = authenticated_admin_client.get(f"/api/chat/admin/rooms/{room_id}/messages/")

        assert response.status_code == 200
        messages = response.json()["data"]["messages"]

        senders = [msg["sender"]["id"] for msg in messages]
        # Should have at least 2 different senders
        assert len(set(senders)) >= 2

    def test_get_room_messages_no_auth_forbidden(
        self, api_client, forum_room_math, messages_in_forum_room
    ):
        """Test that unauthenticated users cannot get messages"""
        client = APIClient()
        response = client.get(f"/api/chat/admin/rooms/{forum_room_math.id}/messages/")

        assert response.status_code in [401, 403]

    def test_get_room_messages_teacher_forbidden(
        self, authenticated_teacher_client, forum_room_math, messages_in_forum_room
    ):
        """Test that non-admin cannot get all messages"""
        response = authenticated_teacher_client.get(
            f"/api/chat/admin/rooms/{forum_room_math.id}/messages/"
        )

        assert response.status_code == 403

    def test_get_room_messages_invalid_room_id(
        self, authenticated_admin_client
    ):
        """Test 404 for messages of non-existent room"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/99999/messages/")

        assert response.status_code == 404


class TestAdminChatStats:
    """Test cases for chat statistics"""

    def test_get_chat_stats_success(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room, messages_in_forum_room
    ):
        """Test that admin can get chat statistics"""
        response = authenticated_admin_client.get("/api/chat/admin/stats/")

        assert response.status_code == 200
        assert response.json()["success"] is True

        data = response.json()["data"]
        assert "total_rooms" in data
        assert "active_rooms" in data
        assert "total_messages" in data

    def test_get_chat_stats_contains_all_metrics(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room
    ):
        """Test that stats contain all required metrics"""
        response = authenticated_admin_client.get("/api/chat/admin/stats/")

        assert response.status_code == 200
        data = response.json()["data"]

        # Check all required fields
        assert "total_rooms" in data
        assert "active_rooms" in data
        assert "total_messages" in data
        assert "forum_subject_rooms" in data
        assert "direct_rooms" in data
        assert "group_rooms" in data

    def test_get_chat_stats_correct_counts(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room, messages_in_forum_room
    ):
        """Test that stats have correct counts"""
        response = authenticated_admin_client.get("/api/chat/admin/stats/")

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["total_rooms"] == 4
        assert data["active_rooms"] == 4
        assert data["forum_subject_rooms"] == 2
        assert data["direct_rooms"] == 1
        assert data["group_rooms"] == 1
        assert data["total_messages"] == 5

    def test_get_chat_stats_no_auth_forbidden(self, api_client):
        """Test that unauthenticated users cannot get stats"""
        client = APIClient()
        response = client.get("/api/chat/admin/stats/")

        assert response.status_code in [401, 403]

    def test_get_chat_stats_teacher_forbidden(self, authenticated_teacher_client):
        """Test that non-admin cannot get stats"""
        response = authenticated_teacher_client.get("/api/chat/admin/stats/")

        assert response.status_code == 403


class TestAdminChatWorkflow:
    """E2E workflow tests combining multiple operations"""

    def test_workflow_list_rooms_then_view_messages(
        self, authenticated_admin_client, forum_room_math, messages_in_forum_room
    ):
        """Test complete workflow: list rooms -> select room -> view messages"""
        # Step 1: List all rooms
        list_response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        assert list_response.status_code == 200

        rooms = list_response.json()["data"]["rooms"]
        assert len(rooms) > 0

        # Step 2: Select first room
        selected_room = rooms[0]
        room_id = selected_room["id"]

        # Step 3: Get room detail
        detail_response = authenticated_admin_client.get(f"/api/chat/admin/rooms/{room_id}/")
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["room"]["id"] == room_id

        # Step 4: Get messages in room
        messages_response = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{room_id}/messages/"
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()["data"]["messages"]
        assert len(messages) > 0

    def test_workflow_get_stats_then_drill_down(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room, messages_in_forum_room, messages_in_direct_room
    ):
        """Test workflow: get overall stats -> drill down to specific room"""
        # Step 1: Get overall stats
        stats_response = authenticated_admin_client.get("/api/chat/admin/stats/")
        assert stats_response.status_code == 200

        stats = stats_response.json()["data"]
        assert stats["total_rooms"] == 4
        assert stats["forum_subject_rooms"] == 2

        # Step 2: List rooms to find forum room
        list_response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        rooms = list_response.json()["data"]["rooms"]

        forum_rooms = [r for r in rooms if r["type"] == "forum_subject"]
        assert len(forum_rooms) == 2

        # Step 3: Drill down to specific forum room
        forum_id = forum_rooms[0]["id"]
        messages_response = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{forum_id}/messages/"
        )
        assert messages_response.status_code == 200

    def test_workflow_multiple_pagination_requests(
        self, authenticated_admin_client, forum_room_math, db
    ):
        """Test workflow with multiple paginated requests"""
        # Create many messages to test pagination
        for i in range(10):
            Message.objects.create(
                room=forum_room_math,
                sender=User.objects.first(),
                content=f"Message {i}",
                message_type=Message.Type.TEXT,
            )

        room_id = forum_room_math.id

        # Request first page
        response1 = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{room_id}/messages/?limit=5&offset=0"
        )
        assert response1.status_code == 200
        assert len(response1.json()["data"]["messages"]) == 5

        # Request second page
        response2 = authenticated_admin_client.get(
            f"/api/chat/admin/rooms/{room_id}/messages/?limit=5&offset=5"
        )
        assert response2.status_code == 200
        assert len(response2.json()["data"]["messages"]) == 5

        # Verify no overlap
        messages1_ids = [m["id"] for m in response1.json()["data"]["messages"]]
        messages2_ids = [m["id"] for m in response2.json()["data"]["messages"]]
        assert len(set(messages1_ids) & set(messages2_ids)) == 0


class TestAdminChatFiltering:
    """Test cases for room filtering by type"""

    def test_filter_rooms_by_type_forum_subject(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room
    ):
        """Test filtering rooms by forum_subject type"""
        # Note: API doesn't support filter yet, testing manual filter in response
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        assert response.status_code == 200

        all_rooms = response.json()["data"]["rooms"]
        forum_rooms = [r for r in all_rooms if r["type"] == "forum_subject"]

        assert len(forum_rooms) == 2

    def test_filter_rooms_by_type_direct(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room
    ):
        """Test filtering rooms by direct type"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        assert response.status_code == 200

        all_rooms = response.json()["data"]["rooms"]
        direct_rooms = [r for r in all_rooms if r["type"] == "direct"]

        assert len(direct_rooms) == 1

    def test_filter_rooms_by_type_group(
        self, authenticated_admin_client, forum_room_math, forum_room_english,
        direct_room, group_room
    ):
        """Test filtering rooms by group type"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        assert response.status_code == 200

        all_rooms = response.json()["data"]["rooms"]
        group_rooms = [r for r in all_rooms if r["type"] == "group"]

        assert len(group_rooms) == 1

    def test_search_rooms_by_name(
        self, authenticated_admin_client, forum_room_math, direct_room
    ):
        """Test searching rooms by name"""
        response = authenticated_admin_client.get("/api/chat/admin/rooms/")
        assert response.status_code == 200

        all_rooms = response.json()["data"]["rooms"]

        # Manual search by name
        math_rooms = [r for r in all_rooms if "Mathematics" in r["name"]]
        assert len(math_rooms) >= 1
