"""
Integration tests for Telegram linking feature.
Tests the complete flow: generate link -> verify token -> unlink
"""
import json
from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.test import TestCase, Client
from django.utils import timezone
from django.conf import settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import User, TelegramLinkToken
from accounts.telegram_link_service import TelegramLinkService


class TelegramLinkServiceTests(TestCase):
    """Unit tests for TelegramLinkService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

    def test_generate_link_token_success(self):
        """Test successful token generation"""
        result = TelegramLinkService.generate_link_token(self.user)

        self.assertIn("token", result)
        self.assertIn("link", result)
        self.assertIn("expires_at", result)
        self.assertIn("ttl_minutes", result)
        self.assertTrue(result["link"].startswith("https://t.me/"))
        self.assertIn("link_", result["link"])

    def test_generate_link_token_creates_db_entry(self):
        """Test that token is created in database"""
        result = TelegramLinkService.generate_link_token(self.user)
        token_obj = TelegramLinkToken.objects.get(token=result["token"])

        self.assertEqual(token_obj.user, self.user)
        self.assertFalse(token_obj.is_used)
        self.assertIsNone(token_obj.used_at)

    def test_generate_link_token_removes_old_tokens(self):
        """Test that old unused tokens are removed"""
        # Create first token
        TelegramLinkService.generate_link_token(self.user)
        first_count = TelegramLinkToken.objects.filter(user=self.user).count()

        # Create second token
        TelegramLinkService.generate_link_token(self.user)
        second_count = TelegramLinkToken.objects.filter(user=self.user).count()

        # Should still have only 1 unused token
        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)

    def test_generate_link_token_rate_limit(self):
        """Test rate limit enforcement (5 tokens per 10 minutes)"""
        # Generate 5 tokens
        for i in range(5):
            TelegramLinkService.generate_link_token(self.user)

        # 6th token should fail
        with self.assertRaises(ValueError):
            TelegramLinkService.generate_link_token(self.user)

    def test_confirm_link_success(self):
        """Test successful Telegram link confirmation"""
        result = TelegramLinkService.generate_link_token(self.user)
        token = result["token"]
        telegram_id = 123456789

        confirm_result = TelegramLinkService.confirm_link(token, telegram_id)

        self.assertTrue(confirm_result["success"])
        self.assertEqual(confirm_result["user_id"], str(self.user.id))
        self.assertEqual(confirm_result["email"], self.user.email)

    def test_confirm_link_updates_user(self):
        """Test that confirm_link updates user's telegram_id"""
        result = TelegramLinkService.generate_link_token(self.user)
        token = result["token"]
        telegram_id = 123456789

        TelegramLinkService.confirm_link(token, telegram_id)

        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_id, telegram_id)

    def test_confirm_link_marks_token_used(self):
        """Test that token is marked as used"""
        result = TelegramLinkService.generate_link_token(self.user)
        token = result["token"]

        TelegramLinkService.confirm_link(token, 123456789)

        token_obj = TelegramLinkToken.objects.get(token=token)
        self.assertTrue(token_obj.is_used)
        self.assertIsNotNone(token_obj.used_at)

    def test_confirm_link_invalid_token(self):
        """Test confirmation with invalid token"""
        result = TelegramLinkService.confirm_link("invalid_token", 123456789)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_confirm_link_expired_token(self):
        """Test confirmation with expired token"""
        result = TelegramLinkService.generate_link_token(self.user)
        token = result["token"]

        # Mark token as expired
        token_obj = TelegramLinkToken.objects.get(token=token)
        token_obj.expires_at = timezone.now() - timedelta(minutes=1)
        token_obj.save()

        confirm_result = TelegramLinkService.confirm_link(token, 123456789)
        self.assertFalse(confirm_result["success"])
        self.assertIn("expired", confirm_result["error"].lower())

    def test_confirm_link_duplicate_telegram_id(self):
        """Test that same telegram_id can't be linked twice"""
        user1 = self.user
        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        # Link telegram_id to user1
        result1 = TelegramLinkService.generate_link_token(user1)
        telegram_id = 123456789
        TelegramLinkService.confirm_link(result1["token"], telegram_id)

        # Try to link same telegram_id to user2
        result2 = TelegramLinkService.generate_link_token(user2)
        confirm_result = TelegramLinkService.confirm_link(result2["token"], telegram_id)

        self.assertFalse(confirm_result["success"])
        self.assertIn("already linked", confirm_result["error"].lower())

    def test_unlink_telegram_success(self):
        """Test successful unlinking of Telegram"""
        result = TelegramLinkService.generate_link_token(self.user)
        TelegramLinkService.confirm_link(result["token"], 123456789)

        unlink_result = TelegramLinkService.unlink_telegram(self.user)

        self.assertTrue(unlink_result["success"])
        self.user.refresh_from_db()
        self.assertIsNone(self.user.telegram_id)

    def test_unlink_telegram_not_linked(self):
        """Test unlinking when telegram not linked"""
        result = TelegramLinkService.unlink_telegram(self.user)

        self.assertFalse(result["success"])
        self.assertIn("not linked", result["error"].lower())

    def test_get_user_by_telegram_id_found(self):
        """Test getting user by telegram_id"""
        result = TelegramLinkService.generate_link_token(self.user)
        telegram_id = 123456789
        TelegramLinkService.confirm_link(result["token"], telegram_id)

        found_user = TelegramLinkService.get_user_by_telegram_id(telegram_id)

        self.assertEqual(found_user.id, self.user.id)

    def test_get_user_by_telegram_id_not_found(self):
        """Test getting user by invalid telegram_id"""
        found_user = TelegramLinkService.get_user_by_telegram_id(999999999)

        self.assertIsNone(found_user)

    def test_is_telegram_linked_true(self):
        """Test is_telegram_linked returns True when linked"""
        result = TelegramLinkService.generate_link_token(self.user)
        TelegramLinkService.confirm_link(result["token"], 123456789)

        is_linked = TelegramLinkService.is_telegram_linked(self.user)

        self.assertTrue(is_linked)

    def test_is_telegram_linked_false(self):
        """Test is_telegram_linked returns False when not linked"""
        is_linked = TelegramLinkService.is_telegram_linked(self.user)

        self.assertFalse(is_linked)


class GenerateTelegramLinkViewTests(APITestCase):
    """Tests for GenerateTelegramLinkView endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.client = APIClient()

    def test_generate_link_requires_authentication(self):
        """Test that endpoint requires authentication"""
        response = self.client.post("/api/profile/telegram/generate-link/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_generate_link_authenticated_success(self):
        """Test successful link generation for authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/profile/telegram/generate-link/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("link", data)

    def test_generate_link_rate_limit_response(self):
        """Test rate limit error response"""
        self.client.force_authenticate(user=self.user)

        # Generate 5 tokens
        for i in range(5):
            response = self.client.post("/api/profile/telegram/generate-link/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 6th request should be rate limited
        response = self.client.post("/api/profile/telegram/generate-link/")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class ConfirmTelegramLinkViewTests(APITestCase):
    """Tests for ConfirmTelegramLinkView endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.client = APIClient()
        self.valid_secret = "test_secret"
        settings.TELEGRAM_BOT_SECRET = self.valid_secret

    def test_confirm_link_requires_bot_secret(self):
        """Test that missing X-Bot-Secret returns 401"""
        result = TelegramLinkService.generate_link_token(self.user)
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": result["token"],
                "telegram_id": 123456789,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_confirm_link_invalid_bot_secret(self):
        """Test that invalid X-Bot-Secret returns 401"""
        result = TelegramLinkService.generate_link_token(self.user)
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": result["token"],
                "telegram_id": 123456789,
            },
            format="json",
            HTTP_X_BOT_SECRET="wrong_secret",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_confirm_link_valid_bot_secret(self):
        """Test successful confirmation with valid secret"""
        result = TelegramLinkService.generate_link_token(self.user)
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": result["token"],
                "telegram_id": 123456789,
            },
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])

    def test_confirm_link_missing_token(self):
        """Test that missing token returns 400"""
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {"telegram_id": 123456789},
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_link_missing_telegram_id(self):
        """Test that missing telegram_id returns 400"""
        result = TelegramLinkService.generate_link_token(self.user)
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {"token": result["token"]},
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_link_invalid_telegram_id_format(self):
        """Test that non-numeric telegram_id returns 400"""
        result = TelegramLinkService.generate_link_token(self.user)
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": result["token"],
                "telegram_id": "not_a_number",
            },
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UnlinkTelegramViewTests(APITestCase):
    """Tests for UnlinkTelegramView endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.client = APIClient()

    def test_unlink_requires_authentication(self):
        """Test that endpoint requires authentication"""
        response = self.client.delete("/api/profile/telegram/unlink/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unlink_success(self):
        """Test successful unlinking"""
        # First, link telegram
        result = TelegramLinkService.generate_link_token(self.user)
        TelegramLinkService.confirm_link(result["token"], 123456789)

        self.client.force_authenticate(user=self.user)
        response = self.client.delete("/api/profile/telegram/unlink/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])

    def test_unlink_not_linked(self):
        """Test unlinking when telegram not linked"""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete("/api/profile/telegram/unlink/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])


class TelegramStatusViewTests(APITestCase):
    """Tests for TelegramStatusView endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.client = APIClient()

    def test_status_requires_authentication(self):
        """Test that endpoint requires authentication"""
        response = self.client.get("/api/profile/telegram/status/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_not_linked(self):
        """Test status response when telegram not linked"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/profile/telegram/status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_linked"])
        self.assertIsNone(data["telegram_id"])

    def test_status_linked(self):
        """Test status response when telegram is linked"""
        result = TelegramLinkService.generate_link_token(self.user)
        telegram_id = 123456789
        TelegramLinkService.confirm_link(result["token"], telegram_id)

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/profile/telegram/status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["is_linked"])
        self.assertEqual(data["telegram_id"], telegram_id)


class TelegramEndToEndTests(APITestCase):
    """End-to-end tests for complete Telegram linking workflow"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.client = APIClient()
        self.valid_secret = "test_secret"
        settings.TELEGRAM_BOT_SECRET = self.valid_secret

    def test_complete_flow_link_and_unlink(self):
        """Test complete flow: generate link -> confirm -> unlink"""
        # Step 1: Generate link token
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/profile/telegram/generate-link/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.json()["token"]

        # Step 2: Verify token is not used yet
        token_obj = TelegramLinkToken.objects.get(token=token)
        self.assertFalse(token_obj.is_used)

        # Step 3: Confirm link (simulate bot request)
        telegram_id = 123456789
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": token,
                "telegram_id": telegram_id,
            },
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

        # Step 4: Check status
        response = self.client.get("/api/profile/telegram/status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["is_linked"])
        self.assertEqual(data["telegram_id"], telegram_id)

        # Step 5: Unlink
        response = self.client.delete("/api/profile/telegram/unlink/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 6: Verify unlinked
        response = self.client.get("/api/profile/telegram/status/")
        data = response.json()
        self.assertFalse(data["is_linked"])
        self.assertIsNone(data["telegram_id"])

    def test_token_reuse_not_allowed(self):
        """Test that used token can't be confirmed again"""
        # Generate and confirm link
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/profile/telegram/generate-link/")
        token = response.json()["token"]

        telegram_id_1 = 123456789
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": token,
                "telegram_id": telegram_id_1,
            },
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to reuse same token
        telegram_id_2 = 987654321
        response = self.client.post(
            "/api/profile/telegram/confirm/",
            {
                "token": token,
                "telegram_id": telegram_id_2,
            },
            format="json",
            HTTP_X_BOT_SECRET=self.valid_secret,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
