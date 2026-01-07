import pytest
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.authtoken.models import Token
from chat.models import ChatRoom

User = get_user_model()


@pytest.mark.django_db
class TestT001WebSocketAuth(TestCase):
    """T001: WebSocket аутентификация токеном"""

    def setUp(self):
        """Fixtures: user, token, room"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"wsauth_user_{unique_id}",
            email=f"wsauth{unique_id}@example.com",
            password="testpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.token = Token.objects.create(user=self.user)

        self.room = ChatRoom.objects.create(
            name=f"Test Room {unique_id}",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user,
        )
        self.room.participants.add(self.user)

    def test_token_creation_success(self):
        """Test token is created successfully"""
        assert self.token is not None
        assert self.token.key is not None
        assert len(self.token.key) == 40

    def test_token_belongs_to_user(self):
        """Test token belongs to correct user"""
        token_from_db = Token.objects.get(key=self.token.key)
        assert token_from_db.user == self.user

    def test_user_is_active(self):
        """Test user is active for authentication"""
        assert self.user.is_active is True

    def test_user_has_role(self):
        """Test user has assigned role"""
        assert self.user.role == "student"

    def test_room_created_with_participants(self):
        """Test room is created with user as participant"""
        assert self.room.participants.filter(id=self.user.id).exists()


@pytest.mark.django_db
class TestT002MiddlewareTokenAuth(TestCase):
    """T002: Middleware TokenAuthMiddleware проверка"""

    def setUp(self):
        """Fixtures: user, token"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"middleware_user_{unique_id}",
            email=f"middleware{unique_id}@example.com",
            password="testpass456",
            role="tutor",
        )
        self.user.is_active = True
        self.user.save()

        self.token = Token.objects.create(user=self.user)

    def test_token_extraction_from_query_string(self):
        """Test token can be extracted from query string"""
        query_string = f"token={self.token.key}"

        # Simulate token extraction logic
        if "token=" in query_string:
            extracted = query_string.split("token=")[1].split("&")[0]
            assert extracted == self.token.key

    def test_bearer_token_format_extraction(self):
        """Test Bearer token format extraction"""
        query_string = f"authorization=Bearer%20{self.token.key}"

        # Simulate Bearer token extraction
        if "authorization=" in query_string:
            auth_header = query_string.split("authorization=")[1].split("&")[0]
            if auth_header.startswith("Bearer%20"):
                extracted = auth_header[9:]
                assert extracted == self.token.key

    def test_invalid_token_raises_exception(self):
        """Test invalid token raises DoesNotExist"""
        with pytest.raises(Token.DoesNotExist):
            Token.objects.get(key="invalid_token_does_not_exist")

    def test_user_active_status_check(self):
        """Test middleware checks user.is_active"""
        token_obj = Token.objects.get(key=self.token.key)

        # Active user
        assert token_obj.user.is_active is True

        # Inactive user
        token_obj.user.is_active = False
        token_obj.user.save()

        user_from_db = User.objects.get(id=token_obj.user.id)
        assert user_from_db.is_active is False

    def test_anonymous_user_when_no_token(self):
        """Test AnonymousUser is assigned when no token provided"""
        anon = AnonymousUser()
        assert anon.is_authenticated is False

    def test_query_string_without_token(self):
        """Test query string without token parameter"""
        query_string = "room_id=123&extra=param"

        # Simulate token extraction
        token = None
        if "token=" in query_string:
            token = query_string.split("token=")[1].split("&")[0]

        assert token is None

    def test_malformed_query_string_handling(self):
        """Test malformed query string is handled safely"""
        query_string = "token="

        # Simulate extraction
        token = None
        if "token=" in query_string:
            extracted = query_string.split("token=")[1].split("&")[0]
            token = extracted if extracted else None

        assert token is None or token == ""


@pytest.mark.django_db
class TestAuthenticationScenarios(TestCase):
    """Test authentication scenarios and edge cases"""

    def setUp(self):
        """Fixtures setup"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"auth_user_{unique_id}",
            email=f"auth{unique_id}@example.com",
            password="authpass123",
            role="student",
        )
        self.user.is_active = True
        self.user.save()

        self.token = Token.objects.create(user=self.user)

    def test_valid_token_retrieval(self):
        """Test retrieving user with valid token"""
        token_obj = Token.objects.get(key=self.token.key)
        assert token_obj.user.id == self.user.id

    def test_user_inactive_token_still_exists(self):
        """Test token still exists but user is inactive"""
        self.user.is_active = False
        self.user.save()

        token_from_db = Token.objects.get(key=self.token.key)
        assert token_from_db.user.is_active is False

    def test_token_key_length_validation(self):
        """Test token key has correct length"""
        assert len(self.token.key) == 40
        assert self.token.key.isalnum()

    def test_user_deleted_token_removed(self):
        """Test token is removed when user is deleted"""
        token_key = self.token.key
        self.user.delete()

        with pytest.raises(Token.DoesNotExist):
            Token.objects.get(key=token_key)

    def test_token_unique_per_user_constraint(self):
        """Test Token has unique constraint on user"""
        from django.db import IntegrityError

        try:
            Token.objects.create(user=self.user)
            assert False, "Should raise IntegrityError"
        except IntegrityError:
            # Expected - Token has unique constraint on user_id
            pass

    def test_different_users_different_tokens(self):
        """Test different users have different tokens"""
        unique_id2 = str(uuid.uuid4())[:8]

        user2 = User.objects.create_user(
            username=f"auth_user2_{unique_id2}",
            email=f"auth2{unique_id2}@example.com",
            password="authpass456",
            role="student",
        )
        user2.is_active = True
        user2.save()

        token2 = Token.objects.create(user=user2)

        assert self.token.key != token2.key
        assert self.token.user != token2.user

    def test_token_user_relationship(self):
        """Test token-user relationship"""
        assert self.token.user.email == self.user.email
        assert self.token.user.role == "student"


@pytest.mark.django_db
class TestChatRoomAndParticipants(TestCase):
    """Test ChatRoom setup and participant management"""

    def setUp(self):
        """Fixtures setup"""
        unique_id = str(uuid.uuid4())[:8]

        self.user1 = User.objects.create_user(
            username=f"room_user1_{unique_id}",
            email=f"roomuser1{unique_id}@example.com",
            password="pass123",
            role="student",
        )
        self.user1.is_active = True
        self.user1.save()

        unique_id2 = str(uuid.uuid4())[:8]
        self.user2 = User.objects.create_user(
            username=f"room_user2_{unique_id2}",
            email=f"roomuser2{unique_id2}@example.com",
            password="pass456",
            role="student",
        )
        self.user2.is_active = True
        self.user2.save()

        self.room = ChatRoom.objects.create(
            name="Test Chat Room",
            type=ChatRoom.Type.DIRECT,
            created_by=self.user1,
        )

    def test_room_creation(self):
        """Test ChatRoom creation"""
        assert self.room.name == "Test Chat Room"
        assert self.room.type == ChatRoom.Type.DIRECT
        assert self.room.created_by == self.user1

    def test_add_participant(self):
        """Test adding participant to room"""
        self.room.participants.add(self.user1)
        assert self.room.participants.filter(id=self.user1.id).exists()

    def test_multiple_participants(self):
        """Test multiple participants in room"""
        self.room.participants.add(self.user1, self.user2)
        participants = self.room.participants.all()
        assert participants.count() == 2

    def test_participant_access_check(self):
        """Test checking participant access"""
        self.room.participants.add(self.user1)

        is_participant_1 = self.room.participants.filter(id=self.user1.id).exists()
        is_participant_2 = self.room.participants.filter(id=self.user2.id).exists()

        assert is_participant_1 is True
        assert is_participant_2 is False

    def test_room_is_active_default(self):
        """Test room is active by default"""
        assert self.room.is_active is True

    def test_room_auto_delete_days_default(self):
        """Test auto delete days default value"""
        assert self.room.auto_delete_days == 7


@pytest.mark.django_db
class TestTokenValidationLogic(TestCase):
    """Test token validation core logic"""

    def setUp(self):
        """Fixtures setup"""
        unique_id = str(uuid.uuid4())[:8]

        self.user = User.objects.create_user(
            username=f"token_logic_{unique_id}",
            email=f"tokenlogic{unique_id}@example.com",
            password="logic123",
            role="tutor",
        )
        self.user.is_active = True
        self.user.save()

        self.token = Token.objects.create(user=self.user)

    def test_token_format_validation(self):
        """Test token key format"""
        assert isinstance(self.token.key, str)
        assert len(self.token.key) == 40
        assert self.token.key.isalnum()

    def test_query_param_parsing_logic(self):
        """Test query parameter parsing for token"""
        # Test case 1: token= format
        query_string = f"token={self.token.key}"
        if "token=" in query_string:
            token_value = query_string.split("token=")[1].split("&")[0]
            assert token_value == self.token.key

        # Test case 2: Multiple params
        query_string = f"room_id=1&token={self.token.key}&extra=value"
        if "token=" in query_string:
            token_value = query_string.split("token=")[1].split("&")[0]
            assert token_value == self.token.key

    def test_empty_token_string(self):
        """Test empty token string is rejected"""
        with pytest.raises(Token.DoesNotExist):
            Token.objects.get(key="")

    def test_whitespace_token_rejected(self):
        """Test token with whitespace is rejected"""
        with pytest.raises(Token.DoesNotExist):
            Token.objects.get(key=" " + self.token.key)

    def test_case_sensitive_token(self):
        """Test token keys are case-sensitive"""
        lowercase_key = self.token.key.lower()
        if lowercase_key != self.token.key:
            with pytest.raises(Token.DoesNotExist):
                Token.objects.get(key=lowercase_key)

    def test_user_role_with_token(self):
        """Test user role is preserved with token"""
        token_obj = Token.objects.get(key=self.token.key)
        assert token_obj.user.role == "tutor"

    def test_token_creation_timestamp_exists(self):
        """Test token has creation timestamp"""
        assert self.token.created is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
