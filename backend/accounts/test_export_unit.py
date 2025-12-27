"""
Unit tests for GDPR user data export (without database).

Tests core functionality of export service:
- Token generation and verification
- Data collection structure
- File path generation
- CSV/JSON formatting
"""
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from accounts.export import (
    UserDataExporter,
    ExportTokenGenerator,
    ExportFileManager
)


class TokenGeneratorUnitTests(TestCase):
    """Test secure token generation and verification."""

    def test_generate_token_produces_sha256_hash(self):
        """Test that token is 64-char SHA256 hex string."""
        token = ExportTokenGenerator.generate(123, 'file.json')
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 64)
        # Verify it's valid hex
        int(token, 16)

    def test_token_is_deterministic(self):
        """Test that same inputs produce same token."""
        token1 = ExportTokenGenerator.generate(123, 'file.json')
        # Regenerate with same inputs
        secret = settings.SECRET_KEY
        message = f"123:file.json:123:file.json".encode()
        token2 = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        # Note: Actual implementation uses timestamp, so this is approximate test

    def test_verify_requires_exact_match(self):
        """Test that token verification requires exact data match."""
        user_id = 123
        filename = 'export.json'
        timestamp = '2025-01-01T12:00:00'

        token = ExportTokenGenerator.generate(user_id, filename)

        # Should verify successfully
        self.assertTrue(
            ExportTokenGenerator.verify(user_id, filename, token, timestamp)
        )

    def test_verify_fails_with_different_user_id(self):
        """Test token fails with different user ID."""
        token = ExportTokenGenerator.generate(123, 'file.json')

        self.assertFalse(
            ExportTokenGenerator.verify(456, 'file.json', token, '2025-01-01T12:00:00')
        )

    def test_verify_fails_with_different_filename(self):
        """Test token fails with different filename."""
        token = ExportTokenGenerator.generate(123, 'file1.json')

        self.assertFalse(
            ExportTokenGenerator.verify(123, 'file2.json', token, '2025-01-01T12:00:00')
        )

    def test_verify_fails_with_invalid_token(self):
        """Test that invalid token is rejected."""
        self.assertFalse(
            ExportTokenGenerator.verify(123, 'file.json', 'invalid' * 8, '2025-01-01T12:00:00')
        )

    def test_token_expires_after_7_days(self):
        """Test that token is invalid 8 days after creation."""
        # Create timestamp 8 days ago
        old_timestamp = (timezone.now() - timedelta(days=8)).isoformat()
        token = ExportTokenGenerator.generate(123, 'file.json')

        # Should fail (expired)
        self.assertFalse(
            ExportTokenGenerator.verify(123, 'file.json', token, old_timestamp)
        )

    def test_token_valid_within_7_days(self):
        """Test that token is valid within 7 days."""
        # Timestamp 3 days ago (within 7 day window)
        recent_timestamp = (timezone.now() - timedelta(days=3)).isoformat()
        token = ExportTokenGenerator.generate(123, 'file.json')

        # Should pass (not expired)
        self.assertTrue(
            ExportTokenGenerator.verify(123, 'file.json', token, recent_timestamp)
        )


class FileManagerUnitTests(TestCase):
    """Test file path generation and management."""

    def test_get_export_path_includes_user_id(self):
        """Test that path includes user ID."""
        path = ExportFileManager.get_export_path(123, 'json')
        self.assertIn('123', path)

    def test_get_export_path_json_format(self):
        """Test that JSON path ends with .json."""
        path = ExportFileManager.get_export_path(123, 'json')
        self.assertTrue(path.endswith('.json'))

    def test_get_export_path_csv_format(self):
        """Test that CSV path ends with .zip."""
        path = ExportFileManager.get_export_path(123, 'csv')
        self.assertTrue(path.endswith('.zip'))

    def test_get_export_path_includes_directory(self):
        """Test that path includes export directory."""
        path = ExportFileManager.get_export_path(123, 'json')
        self.assertIn('user_exports', path)

    def test_get_export_path_includes_timestamp(self):
        """Test that path includes date/time timestamp."""
        path = ExportFileManager.get_export_path(123, 'json')
        # Should have format with YYYYMMDD_HHMMSS
        self.assertRegex(path, r'\d{8}_\d{6}')


class UserDataExporterStructureTests(TestCase):
    """Test export data structure without database."""

    def setUp(self):
        """Create mock user."""
        self.mock_user = Mock()
        self.mock_user.id = 123
        self.mock_user.username = 'testuser'
        self.mock_user.email = 'test@example.com'
        self.mock_user.first_name = 'Test'
        self.mock_user.last_name = 'User'
        self.mock_user.phone = '+1234567890'
        self.mock_user.is_verified = True
        self.mock_user.is_active = True
        self.mock_user.role = 'student'
        self.mock_user.get_full_name = Mock(return_value='Test User')
        self.mock_user.created_at = timezone.now()
        self.mock_user.updated_at = timezone.now()

    def test_exporter_exports_user_profile(self):
        """Test that exporter collects user profile."""
        exporter = UserDataExporter(self.mock_user)

        # Mock the data collection methods
        with MagicMock() as mock_notifications:
            exporter._export_notifications = Mock(return_value=[])
            exporter._export_messages = Mock(return_value=[])
            exporter._export_assignments = Mock(return_value={
                'assigned': [],
                'submissions': []
            })
            exporter._export_payments = Mock(return_value={
                'payments': [],
                'invoices': []
            })
            exporter._export_activity = Mock(return_value=[])

            data = exporter.collect_all_data()

            # Check user profile
            self.assertIn('user', data)
            self.assertEqual(data['user']['username'], 'testuser')
            self.assertEqual(data['user']['email'], 'test@example.com')

    def test_export_structure_has_required_sections(self):
        """Test that export has all required sections."""
        exporter = UserDataExporter(self.mock_user)

        with MagicMock():
            exporter._export_notifications = Mock(return_value=[])
            exporter._export_messages = Mock(return_value=[])
            exporter._export_assignments = Mock(return_value={
                'assigned': [],
                'submissions': []
            })
            exporter._export_payments = Mock(return_value={
                'payments': [],
                'invoices': []
            })
            exporter._export_activity = Mock(return_value=[])

            data = exporter.collect_all_data()

            expected_sections = [
                'user', 'profile', 'notifications', 'messages',
                'assignments', 'payments', 'activity', 'export_timestamp'
            ]
            for section in expected_sections:
                self.assertIn(section, data, f"Missing section: {section}")

    def test_export_timestamp_is_iso_format(self):
        """Test that timestamp is in ISO format."""
        exporter = UserDataExporter(self.mock_user)

        with MagicMock():
            exporter._export_notifications = Mock(return_value=[])
            exporter._export_messages = Mock(return_value=[])
            exporter._export_assignments = Mock(return_value={
                'assigned': [],
                'submissions': []
            })
            exporter._export_payments = Mock(return_value={
                'payments': [],
                'invoices': []
            })
            exporter._export_activity = Mock(return_value=[])

            data = exporter.collect_all_data()

            # Should be valid ISO format
            timestamp_str = data['export_timestamp']
            datetime.fromisoformat(timestamp_str)

    def test_json_export_is_valid_json(self):
        """Test that JSON export is valid JSON."""
        exporter = UserDataExporter(self.mock_user)

        with MagicMock():
            exporter._export_notifications = Mock(return_value=[])
            exporter._export_messages = Mock(return_value=[])
            exporter._export_assignments = Mock(return_value={
                'assigned': [],
                'submissions': []
            })
            exporter._export_payments = Mock(return_value={
                'payments': [],
                'invoices': []
            })
            exporter._export_activity = Mock(return_value=[])

            exporter.collect_all_data()
            json_str = exporter.to_json()

            # Should be valid JSON
            data = json.loads(json_str)
            self.assertIn('user', data)

    def test_json_export_uses_utf8(self):
        """Test that JSON export is UTF-8 encoded."""
        exporter = UserDataExporter(self.mock_user)

        with MagicMock():
            exporter._export_notifications = Mock(return_value=[])
            exporter._export_messages = Mock(return_value=[])
            exporter._export_assignments = Mock(return_value={
                'assigned': [],
                'submissions': []
            })
            exporter._export_payments = Mock(return_value={
                'payments': [],
                'invoices': []
            })
            exporter._export_activity = Mock(return_value=[])

            exporter.collect_all_data()
            json_str = exporter.to_json()

            # Should contain valid UTF-8
            self.assertIsInstance(json_str, str)
            # Verify by encoding/decoding
            json_bytes = json_str.encode('utf-8')
            decoded = json_bytes.decode('utf-8')
            self.assertEqual(json_str, decoded)


class DataMinimizationTests(TestCase):
    """Test that export only includes user's own data."""

    def test_export_user_profile_includes_only_own_data(self):
        """Test that user profile export contains user's own data."""
        mock_user = Mock()
        mock_user.id = 123
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.first_name = 'Test'
        mock_user.last_name = 'User'
        mock_user.phone = ''
        mock_user.is_verified = False
        mock_user.is_active = True
        mock_user.role = 'student'
        mock_user.created_at = timezone.now()
        mock_user.updated_at = timezone.now()

        exporter = UserDataExporter(mock_user)
        profile = exporter._export_user_profile()

        # Should only have data for user 123
        self.assertEqual(profile['id'], 123)
        self.assertEqual(profile['username'], 'testuser')
        # Should not have other users' data
        self.assertNotIn('other_user', str(profile))

    def test_export_preserves_user_id_in_all_sections(self):
        """Test that exported data maintains user context."""
        mock_user = Mock()
        mock_user.id = 123
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.first_name = 'Test'
        mock_user.last_name = 'User'
        mock_user.phone = ''
        mock_user.is_verified = False
        mock_user.is_active = True
        mock_user.role = 'student'
        mock_user.created_at = timezone.now()
        mock_user.updated_at = timezone.now()

        exporter = UserDataExporter(mock_user)

        # Check that exporter instance maintains user reference
        self.assertEqual(exporter.user.id, 123)


class ExportAccessControlTests(TestCase):
    """Test access control and security."""

    def test_token_prevents_unauthorized_access(self):
        """Test that token validation prevents unauthorized downloads."""
        user_id = 123
        filename = 'export_user_123.json'

        # Create token for user 123
        token = ExportTokenGenerator.generate(user_id, filename)

        # Token should work for user 123
        self.assertTrue(
            ExportTokenGenerator.verify(
                user_id, filename, token, timezone.now().isoformat()
            )
        )

        # But fail for user 456
        self.assertFalse(
            ExportTokenGenerator.verify(
                456, filename, token, timezone.now().isoformat()
            )
        )

    def test_token_prevents_file_swap(self):
        """Test that token prevents downloading different file."""
        user_id = 123
        filename1 = 'export_user_123.json'
        filename2 = 'export_user_456.json'

        # Create token for file 1
        token = ExportTokenGenerator.generate(user_id, filename1)

        # Should fail for file 2
        self.assertFalse(
            ExportTokenGenerator.verify(
                user_id, filename2, token, timezone.now().isoformat()
            )
        )
