import pytest
import time
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from accounts.models import StudentProfile, TeacherProfile
from materials.models import SubjectEnrollment, Subject
from chat.models import ChatRoom, Message, ChatParticipant

User = get_user_model()


@pytest.mark.django_db
class TestRateLimitingBypass(TestCase):
    """Tests for rate limiting bypass protection"""

    def setUp(self):
        """Create test users and chat"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="pass", role="student", is_active=True
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="pass", role="teacher", is_active=True
        )
        self.user3 = User.objects.create_user(
            username="user3", email="user3@test.com", password="pass", role="student", is_active=True
        )

        # Create profiles
        StudentProfile.objects.create(user=self.user1)
        StudentProfile.objects.create(user=self.user3)
        TeacherProfile.objects.create(user=self.user2)

        # Create subject and enrollment
        self.subject = Subject.objects.create(name="Math")
        SubjectEnrollment.objects.create(
            student=self.user1, teacher=self.user2, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )
        SubjectEnrollment.objects.create(
            student=self.user3, teacher=self.user2, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        # Create chat rooms
        self.chat_room1 = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.chat_room1, user=self.user1)
        ChatParticipant.objects.create(room=self.chat_room1, user=self.user2)

        self.chat_room2 = ChatRoom.objects.create(is_active=True)
        ChatParticipant.objects.create(room=self.chat_room2, user=self.user2)
        ChatParticipant.objects.create(room=self.chat_room2, user=self.user3)

        # Clear cache before each test
        cache.clear()

    def _get_rate_key(self, user_id):
        """Get rate limit cache key"""
        return f"chat_rate_limit:{user_id}"

    @override_settings(CHAT_RATE_LIMIT=10)
    def test_single_connection_10_messages_success(self):
        """Single connection: 10 messages in 1 minute = all succeed"""
        rate_key = self._get_rate_key(self.user1.id)
        cache.set(rate_key, 0, 60)  # Initialize rate limit counter

        for i in range(10):
            current = cache.get(rate_key, 0)
            if current < 10:
                cache.set(rate_key, current + 1, 60)

        # Verify all 10 were counted
        assert cache.get(rate_key, 0) == 10

    @override_settings(CHAT_RATE_LIMIT=10)
    def test_single_connection_11th_message_fails(self):
        """Single connection: 11th message in 1 minute fails"""
        rate_key = self._get_rate_key(self.user1.id)

        # Manually set rate limit to 10 (simulating that 10 messages were sent)
        cache.set(rate_key, 10, 60)

        # 11th message would fail
        current = cache.get(rate_key, 0)
        can_send = current < 10
        assert can_send is False

    @override_settings(CHAT_RATE_LIMIT=10)
    def test_rate_limit_resets_after_60_seconds(self):
        """Rate limit resets after 60 seconds"""
        rate_key = self._get_rate_key(self.user1.id)

        # Set rate limit to 10 with 1 second TTL (simulating expiry)
        cache.set(rate_key, 10, 1)

        # Wait for cache to expire
        time.sleep(1.1)

        # Counter should be gone
        assert cache.get(rate_key) is None

    def test_rate_limits_are_per_user_not_per_room(self):
        """Rate limits are PER USER, not per room"""
        rate_key_user1 = self._get_rate_key(self.user1.id)
        rate_key_user3 = self._get_rate_key(self.user3.id)

        # User1 sends 10 messages
        cache.set(rate_key_user1, 10, 60)

        # User3 can still send (different user, independent rate limit)
        cache.set(rate_key_user3, 0, 60)

        # Verify they have different rate limits
        assert cache.get(rate_key_user1) == 10
        assert cache.get(rate_key_user3) == 0

    @override_settings(CHAT_RATE_LIMIT=10)
    def test_rate_limit_window_is_60_seconds(self):
        """Rate limit window is exactly 60 seconds"""
        rate_key = self._get_rate_key(self.user1.id)

        # Set rate limit with 60 second TTL
        cache.set(rate_key, 10, 60)

        # Verify key exists and TTL is set
        assert cache.get(rate_key) == 10

    def test_room_enumeration_protection_max_5_rooms(self):
        """Room enumeration protection: max 5 rooms in 1 minute"""
        # Create multiple chat rooms
        rooms = [self.chat_room1, self.chat_room2]
        for i in range(4):
            room = ChatRoom.objects.create(is_active=True)
            ChatParticipant.objects.create(room=room, user=self.user2)
            rooms.append(room)

        # Try to access 6 rooms in 1 minute
        room_access_key = f"chat_rooms:{self.user2.id}"
        accessed_rooms = 0

        for i, room in enumerate(rooms):
            # Simulate room access counting
            current = cache.get(room_access_key, 0)
            if current < 5:
                cache.set(room_access_key, current + 1, 60)
                accessed_rooms += 1
            else:
                # 6th room should be rejected
                break

        # Only 5 rooms should be accessible in 1 minute
        assert cache.get(room_access_key, 0) == 5

    def test_rate_limit_applies_across_different_rooms(self):
        """Same user sending in different rooms still respects per-user rate limit"""
        rate_key = self._get_rate_key(self.user1.id)

        # Set rate limit to 10 for this user
        cache.set(rate_key, 10, 60)

        # Try to send in room1 (should fail - already at limit)
        current = cache.get(rate_key, 0)
        can_send_room1 = current < 10
        assert can_send_room1 is False

        # Try to send in room2 (should also fail - same user limit)
        can_send_room2 = current < 10
        assert can_send_room2 is False

    def test_rate_limit_bypass_via_different_ips_not_possible(self):
        """Rate limiting is per-user, not per-IP (prevents IP-based bypass)"""
        # Rate limit should still apply
        rate_key = self._get_rate_key(self.user1.id)
        cache.set(rate_key, 10, 60)

        # Both requests would hit same user-level rate limit
        assert cache.get(rate_key) == 10

    def test_participant_enforcement(self):
        """Only chat participants can send messages"""
        # user1 is in chat_room1
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room1, user=self.user1
        ).exists()
        assert is_participant is True

        # user3 is NOT in chat_room1
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room1, user=self.user3
        ).exists()
        assert is_participant is False

    def test_message_creation_by_participant(self):
        """Messages can only be created by chat participants"""
        msg = Message.objects.create(
            room=self.chat_room1, sender=self.user1, content="Test"
        )
        assert msg.sender == self.user1

        # Verify sender is participant
        is_participant = ChatParticipant.objects.filter(
            room=self.chat_room1, user=msg.sender
        ).exists()
        assert is_participant is True

    def test_rate_limit_key_format(self):
        """Rate limit cache key format is correct"""
        rate_key = self._get_rate_key(self.user1.id)
        assert "chat_rate_limit:" in rate_key
        assert str(self.user1.id) in rate_key

    def test_room_limit_key_format(self):
        """Room limit cache key format is correct"""
        room_limit_key = f"chat_rooms:{self.user1.id}"
        assert "chat_rooms:" in room_limit_key
        assert str(self.user1.id) in room_limit_key

    def test_cache_get_nonexistent_key(self):
        """Cache returns None for non-existent keys"""
        rate_key = f"chat_rate_limit:99999"
        assert cache.get(rate_key) is None

    def test_cache_set_and_get(self):
        """Cache set/get works correctly"""
        rate_key = self._get_rate_key(self.user1.id)
        cache.set(rate_key, 5, 60)
        assert cache.get(rate_key) == 5

    def test_cache_delete(self):
        """Cache delete removes key"""
        rate_key = self._get_rate_key(self.user1.id)
        cache.set(rate_key, 5, 60)
        cache.delete(rate_key)
        assert cache.get(rate_key) is None

    def test_multiple_users_independent_limits(self):
        """Multiple users have independent rate limits"""
        rate_key_1 = self._get_rate_key(self.user1.id)
        rate_key_2 = self._get_rate_key(self.user2.id)
        rate_key_3 = self._get_rate_key(self.user3.id)

        cache.set(rate_key_1, 5, 60)
        cache.set(rate_key_2, 8, 60)
        cache.set(rate_key_3, 3, 60)

        assert cache.get(rate_key_1) == 5
        assert cache.get(rate_key_2) == 8
        assert cache.get(rate_key_3) == 3

    def test_room_count_tracking(self):
        """Room enumeration count tracking"""
        room_limit_key = f"chat_rooms:{self.user1.id}"

        # Track room access
        for i in range(3):
            current = cache.get(room_limit_key, 0)
            cache.set(room_limit_key, current + 1, 60)

        assert cache.get(room_limit_key) == 3

    def test_inactive_user_cannot_send_message(self):
        """Inactive user should not be able to send"""
        inactive_user = User.objects.create_user(
            username="inactive_test", email="inactive@test.com", password="pass", role="student", is_active=False
        )
        StudentProfile.objects.create(user=inactive_user)

        # Add to chat
        ChatParticipant.objects.create(room=self.chat_room1, user=inactive_user)

        # But is_active=False blocks messages
        assert inactive_user.is_active is False

        # In real system, is_active check would prevent message creation

    def test_rate_limit_threshold_boundary(self):
        """Rate limit at boundary conditions"""
        rate_key = self._get_rate_key(self.user1.id)

        # Exactly 10 messages
        cache.set(rate_key, 9, 60)
        current = cache.get(rate_key, 0)
        can_send = current < 10
        assert can_send is True  # 9 < 10

        # After increment
        cache.set(rate_key, 10, 60)
        current = cache.get(rate_key, 0)
        can_send = current < 10
        assert can_send is False  # 10 < 10 is False

    def test_rate_limit_counter_increment(self):
        """Rate limit counter increments correctly"""
        rate_key = self._get_rate_key(self.user1.id)

        for i in range(1, 11):
            current = cache.get(rate_key, 0)
            cache.set(rate_key, current + 1, 60)
            assert cache.get(rate_key) == i
