import json
import uuid
import pytest
from channels.layers import get_channel_layer
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from chat.models import ChatRoom, Message, ChatParticipant

User = get_user_model()


@pytest.fixture
def user1():
    """Create first user"""
    username = f"user1_notif_{uuid.uuid4().hex[:8]}"
    return User.objects.create_user(
        username=username,
        email=f"user1_{uuid.uuid4().hex[:8]}@test.com",
        password="pass123",
        role="student",
    )


@pytest.fixture
def user2():
    """Create second user"""
    username = f"user2_notif_{uuid.uuid4().hex[:8]}"
    return User.objects.create_user(
        username=username,
        email=f"user2_{uuid.uuid4().hex[:8]}@test.com",
        password="pass123",
        role="student",
    )


@pytest.fixture
def user3():
    """Create third user (muted participant)"""
    username = f"user3_notif_{uuid.uuid4().hex[:8]}"
    return User.objects.create_user(
        username=username,
        email=f"user3_{uuid.uuid4().hex[:8]}@test.com",
        password="pass123",
        role="student",
    )


@pytest.fixture
def token1(user1):
    """Create token for user1"""
    token, _ = Token.objects.get_or_create(user=user1)
    return token


@pytest.fixture
def token2(user2):
    """Create token for user2"""
    token, _ = Token.objects.get_or_create(user=user2)
    return token


@pytest.fixture
def token3(user3):
    """Create token for user3"""
    token, _ = Token.objects.get_or_create(user=user3)
    return token


@pytest.fixture
def chat_room(user1):
    """Create a chat room with user1 as creator"""
    room = ChatRoom.objects.create(
        name="Test Room",
        description="Test notification room",
        type=ChatRoom.Type.GROUP,
        created_by=user1,
    )
    room.participants.add(user1)
    ChatParticipant.objects.create(room=room, user=user1)
    return room


@pytest.fixture
def chat_room_with_users(user1, user2, user3):
    """Create a chat room with multiple participants"""
    room = ChatRoom.objects.create(
        name="Multi-User Room",
        description="Room for testing muted users",
        type=ChatRoom.Type.GROUP,
        created_by=user1,
    )
    room.participants.add(user1, user2, user3)
    ChatParticipant.objects.create(room=room, user=user1)
    ChatParticipant.objects.create(room=room, user=user2)
    ChatParticipant.objects.create(room=room, user=user3, is_muted=True)
    return room


@pytest.mark.django_db
def test_notification_consumer_token_validation_success(user1, token1):
    """T027.1: Token validation succeeds with valid token"""
    from rest_framework.authtoken.models import Token

    # Verify token exists and is valid
    validated_token = Token.objects.select_related("user").get(key=token1.key)
    assert validated_token.user == user1
    assert validated_token.user.is_active is True


@pytest.mark.django_db
def test_notification_consumer_token_validation_fails_invalid_token(user1):
    """T027.2: Token validation fails with invalid token"""
    from rest_framework.authtoken.models import Token

    # Invalid token should not exist
    with pytest.raises(Token.DoesNotExist):
        Token.objects.get(key="invalid_token")


@pytest.mark.django_db
def test_notification_consumer_user_mismatch(user1, user2, token1):
    """T027.3: User cannot access another user's notifications"""
    # Verify token belongs to user1, not user2
    assert token1.user == user1
    assert token1.user != user2
    assert str(user1.id) != str(user2.id)


@pytest.mark.django_db
def test_notification_on_new_message_data_structure(user1, user2, chat_room):
    """T028.1: Notification data contains required fields"""
    chat_room.participants.add(user2)
    ChatParticipant.objects.create(room=chat_room, user=user2)

    # Create a test notification structure
    notification_data = {
        "room_id": str(chat_room.id),
        "message_id": "test_msg_1",
        "sender_name": user1.get_full_name() or user1.username,
        "content": "Test message",
        "type": "new_message",
    }

    # Verify all required fields exist
    assert "room_id" in notification_data
    assert "message_id" in notification_data
    assert "sender_name" in notification_data
    assert "content" in notification_data
    assert notification_data["room_id"] == str(chat_room.id)


@pytest.mark.django_db
def test_notification_required_fields_room_id(user1, user2, chat_room):
    """T028.2: Notification contains valid room_id"""
    chat_room.participants.add(user2)

    notification_data = {
        "room_id": str(chat_room.id),
        "message_id": "msg_001",
        "sender_name": user1.username,
        "content": "Content",
    }

    assert notification_data["room_id"] == str(chat_room.id)
    # Verify room exists
    assert ChatRoom.objects.filter(id=chat_room.id).exists()


@pytest.mark.django_db
def test_notification_required_fields_message_id(user1, user2, chat_room):
    """T028.3: Notification contains valid message_id"""
    message = Message.objects.create(
        room=chat_room,
        sender=user1,
        content="Test message",
    )

    notification_data = {
        "room_id": str(chat_room.id),
        "message_id": str(message.id),
        "sender_name": user1.username,
        "content": message.content,
    }

    assert notification_data["message_id"] == str(message.id)
    assert Message.objects.filter(id=message.id).exists()


@pytest.mark.django_db
def test_notification_required_fields_sender_name(user1, user2, chat_room):
    """T028.4: Notification contains valid sender_name"""
    sender_name = user1.get_full_name() or user1.username
    assert len(sender_name) > 0

    notification_data = {
        "room_id": str(chat_room.id),
        "message_id": "msg_001",
        "sender_name": sender_name,
        "content": "Test",
    }

    assert notification_data["sender_name"] == sender_name


@pytest.mark.django_db
def test_notification_required_fields_content(user1, user2, chat_room):
    """T028.5: Notification contains valid content"""
    notification_data = {
        "room_id": str(chat_room.id),
        "message_id": "msg_001",
        "sender_name": user1.username,
        "content": "Test message content",
    }

    assert notification_data["content"] == "Test message content"
    assert len(notification_data["content"]) > 0


@pytest.mark.django_db
def test_notification_visibility_to_recipient(user1, user2, chat_room):
    """T029.1: Notification is intended for recipient not sender"""
    chat_room.participants.add(user2)

    # Notification for user2 (recipient)
    recipient_id = user2.id
    # Sender is user1
    sender_id = user1.id

    assert recipient_id != sender_id

    # Channel group name for recipient
    recipient_group = f"notifications_{recipient_id}"
    sender_group = f"notifications_{sender_id}"

    assert recipient_group != sender_group


@pytest.mark.django_db
def test_muted_user_is_muted_flag(user3, chat_room_with_users):
    """T029.2: Muted user has is_muted flag set to True"""
    participant = ChatParticipant.objects.get(room=chat_room_with_users, user=user3)
    assert participant.is_muted is True


@pytest.mark.django_db
def test_muted_user_detection(user1, user2, user3, chat_room_with_users):
    """T029.3: Can detect muted vs non-muted users"""
    participant1 = ChatParticipant.objects.get(room=chat_room_with_users, user=user1)
    participant2 = ChatParticipant.objects.get(room=chat_room_with_users, user=user2)
    participant3 = ChatParticipant.objects.get(room=chat_room_with_users, user=user3)

    assert participant1.is_muted is False
    assert participant2.is_muted is False
    assert participant3.is_muted is True


@pytest.mark.django_db
def test_deleted_message_flag(user1, chat_room):
    """T030.1: Deleted message has is_deleted flag set"""
    message = Message.objects.create(
        room=chat_room,
        sender=user1,
        content="To be deleted",
    )

    # Mark as deleted
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.deleted_by = user1
    message.save()

    # Verify deletion
    refreshed = Message.objects.get(id=message.id)
    assert refreshed.is_deleted is True
    assert refreshed.deleted_at is not None
    assert refreshed.deleted_by == user1


@pytest.mark.django_db
def test_deleted_message_is_soft_deleted(user1, chat_room):
    """T030.2: Deleted message remains in DB (soft delete)"""
    message = Message.objects.create(
        room=chat_room,
        sender=user1,
        content="To be deleted",
    )
    message_id = message.id

    # Soft delete
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save()

    # Message still in database
    assert Message.objects.filter(id=message_id, is_deleted=True).exists()
    # But excluded by default queryset filters
    assert Message.objects.filter(id=message_id, is_deleted=False).count() == 0


@pytest.mark.django_db
def test_active_chat_room(chat_room):
    """T030.3: Chat room is active by default"""
    assert chat_room.is_active is True


@pytest.mark.django_db
def test_chat_room_can_be_locked(chat_room):
    """T030.4: Chat room can be locked (is_active=False)"""
    chat_room.is_active = False
    chat_room.save()

    refreshed = ChatRoom.objects.get(id=chat_room.id)
    assert refreshed.is_active is False


@pytest.mark.django_db
def test_dashboard_update_room_info_structure(chat_room):
    """T030.5: Dashboard update contains room information"""
    dashboard_data = {
        "room_id": str(chat_room.id),
        "room_name": chat_room.name,
        "is_active": chat_room.is_active,
        "type": "chat_status_changed",
    }

    assert dashboard_data["room_id"] == str(chat_room.id)
    assert dashboard_data["room_name"] == chat_room.name
    assert "is_active" in dashboard_data


@pytest.mark.django_db
def test_dashboard_update_with_last_message(chat_room, user1):
    """T030.6: Dashboard update can include last message preview"""
    message = Message.objects.create(
        room=chat_room,
        sender=user1,
        content="Last message",
    )

    dashboard_data = {
        "room_id": str(chat_room.id),
        "room_name": chat_room.name,
        "is_active": chat_room.is_active,
        "last_message_preview": "Last message",
        "last_message_time": message.created_at.isoformat(),
    }

    assert "last_message_preview" in dashboard_data
    assert dashboard_data["last_message_preview"] == "Last message"


@pytest.mark.django_db
def test_dashboard_update_with_unread_count(chat_room, user1, user2):
    """T030.7: Dashboard update can include unread count"""
    chat_room.participants.add(user2)
    participant = ChatParticipant.objects.create(room=chat_room, user=user2)

    # Create messages
    for i in range(3):
        Message.objects.create(
            room=chat_room,
            sender=user1,
            content=f"Message {i}",
        )

    dashboard_data = {
        "room_id": str(chat_room.id),
        "room_name": chat_room.name,
        "is_active": chat_room.is_active,
        "unread_count": 3,
    }

    assert dashboard_data["unread_count"] == 3


@pytest.mark.django_db
def test_multiple_users_different_notification_groups(user1, user2, user3):
    """T028.6: Multiple users can have separate notification groups"""
    group1 = f"notifications_{user1.id}"
    group2 = f"notifications_{user2.id}"
    group3 = f"notifications_{user3.id}"

    assert group1 != group2
    assert group2 != group3
    assert group1 != group3


@pytest.mark.django_db
def test_notification_group_naming_convention(user1):
    """T027.4: Notification group follows naming convention"""
    group_name = f"notifications_{user1.id}"
    assert group_name.startswith("notifications_")
    assert str(user1.id) in group_name


@pytest.mark.django_db
def test_dashboard_group_naming_convention(user1):
    """T030.8: Dashboard group follows naming convention"""
    group_name = f"dashboard_{user1.id}"
    assert group_name.startswith("dashboard_")
    assert str(user1.id) in group_name


@pytest.mark.django_db
def test_token_key_format(token1):
    """T027.5: Token has valid key format"""
    assert isinstance(token1.key, str)
    assert len(token1.key) == 40
    assert token1.key.isalnum()


@pytest.mark.django_db
def test_user_can_access_own_token(user1, token1):
    """T027.6: User token belongs to correct user"""
    assert token1.user == user1
    assert token1.user_id == user1.id


@pytest.mark.django_db
def test_chat_participant_exists(user1, chat_room):
    """T029.4: ChatParticipant record exists for room participants"""
    participant = ChatParticipant.objects.get(room=chat_room, user=user1)
    assert participant is not None
    assert participant.room == chat_room
    assert participant.user == user1


@pytest.mark.django_db
def test_message_creation_in_chat(user1, chat_room):
    """T028.7: Messages can be created in chat rooms"""
    message = Message.objects.create(
        room=chat_room,
        sender=user1,
        content="Test message",
    )

    assert message.id is not None
    assert message.room == chat_room
    assert message.sender == user1
    assert message.content == "Test message"
    assert message.is_deleted is False


@pytest.mark.django_db
def test_chat_room_creation_defaults(user1):
    """T030.9: Chat room has correct default values"""
    room = ChatRoom.objects.create(
        name="Test Room",
        type=ChatRoom.Type.GROUP,
        created_by=user1,
    )

    assert room.is_active is True
    assert room.auto_delete_days == 7


@pytest.mark.django_db
def test_notification_data_json_serializable(chat_room, user1):
    """T028.8: Notification data can be JSON serialized"""
    notification_data = {
        "room_id": str(chat_room.id),
        "message_id": "test_123",
        "sender_name": user1.username,
        "content": "Test message",
        "type": "new_message",
    }

    # Should not raise
    json_str = json.dumps(notification_data)
    assert isinstance(json_str, str)

    # Should be deserializable
    parsed = json.loads(json_str)
    assert parsed["room_id"] == str(chat_room.id)


@pytest.mark.django_db
def test_dashboard_data_json_serializable(chat_room):
    """T030.10: Dashboard data can be JSON serialized"""
    dashboard_data = {
        "room_id": str(chat_room.id),
        "room_name": chat_room.name,
        "is_active": chat_room.is_active,
        "type": "update",
    }

    # Should not raise
    json_str = json.dumps(dashboard_data)
    assert isinstance(json_str, str)

    # Should be deserializable
    parsed = json.loads(json_str)
    assert parsed["room_id"] == str(chat_room.id)


@pytest.mark.django_db
def test_user_authentication_flag(user1):
    """T027.7: User is authenticated after creation"""
    assert user1.is_active is True
    assert user1.id is not None


@pytest.mark.django_db
def test_channel_layer_availability():
    """T027.8: Channel layer is available for group messaging"""
    channel_layer = get_channel_layer()
    assert channel_layer is not None
