"""
Simple unit tests for GDPR data export (no database required).

Tests core export functionality:
- Token generation and verification
- File path generation
- Data structure validation
"""
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock
from django.utils import timezone
from django.conf import settings
from django.test import SimpleTestCase

from accounts.export import (
    UserDataExporter,
    ExportTokenGenerator,
    ExportFileManager
)


class TokenGeneratorTests(SimpleTestCase):
    """Test token generation and verification."""

    def test_token_is_64_char_hex(self):
        """Token should be 64-character hex string (SHA256)."""
        token = ExportTokenGenerator.generate(123, 'file.json')
        self.assertEqual(len(token), 64)
        # Verify it's valid hex
        int(token, 16)

    def test_token_verify_valid_token(self):
        """Valid token should verify successfully."""
        user_id = 123
        filename = 'export.json'
        timestamp = timezone.now().isoformat()

        token = ExportTokenGenerator.generate(user_id, filename)
        result = ExportTokenGenerator.verify(user_id, filename, token, timestamp)
        self.assertTrue(result)

    def test_token_verify_invalid_token(self):
        """Invalid token should not verify."""
        result = ExportTokenGenerator.verify(
            123,
            'file.json',
            'invalid' * 8,
            '2025-01-01T12:00:00'
        )
        self.assertFalse(result)

    def test_token_verify_wrong_user_id(self):
        """Token for one user shouldn't verify for another."""
        token = ExportTokenGenerator.generate(123, 'file.json')
        result = ExportTokenGenerator.verify(
            456,  # Different user
            'file.json',
            token,
            '2025-01-01T12:00:00'
        )
        self.assertFalse(result)

    def test_token_verify_wrong_filename(self):
        """Token for one file shouldn't verify for another."""
        token = ExportTokenGenerator.generate(123, 'file1.json')
        result = ExportTokenGenerator.verify(
            123,
            'file2.json',  # Different file
            token,
            '2025-01-01T12:00:00'
        )
        self.assertFalse(result)

    def test_token_expires_after_7_days(self):
        """Token should be invalid 8+ days after creation."""
        old_timestamp = (timezone.now() - timedelta(days=8)).isoformat()
        token = ExportTokenGenerator.generate(123, 'file.json')
        result = ExportTokenGenerator.verify(123, 'file.json', token, old_timestamp)
        self.assertFalse(result)

    def test_token_valid_within_7_days(self):
        """Token should be valid within 7 days."""
        recent_timestamp = (timezone.now() - timedelta(days=3)).isoformat()
        token = ExportTokenGenerator.generate(123, 'file.json')
        result = ExportTokenGenerator.verify(123, 'file.json', token, recent_timestamp)
        self.assertTrue(result)


class FileManagerTests(SimpleTestCase):
    """Test file path generation."""

    def test_export_path_includes_user_id(self):
        """Export path should include user ID."""
        path = ExportFileManager.get_export_path(123, 'json')
        self.assertIn('123', path)

    def test_export_path_json_extension(self):
        """JSON export path should end with .json."""
        path = ExportFileManager.get_export_path(123, 'json')
        self.assertTrue(path.endswith('.json'))

    def test_export_path_csv_extension(self):
        """CSV export path should end with .zip."""
        path = ExportFileManager.get_export_path(123, 'csv')
        self.assertTrue(path.endswith('.zip'))

    def test_export_path_includes_directory(self):
        """Export path should include user_exports directory."""
        path = ExportFileManager.get_export_path(123, 'json')
        self.assertIn('user_exports', path)

    def test_export_path_includes_timestamp(self):
        """Export path should include timestamp."""
        path = ExportFileManager.get_export_path(123, 'json')
        # Should match pattern: YYYYMMDD_HHMMSS
        self.assertRegex(path, r'\d{8}_\d{6}')


class UserDataExporterTests(SimpleTestCase):
    """Test user data export structure."""

    def setUp(self):
        """Create mock user."""
        self.user = Mock()
        self.user.id = 123
        self.user.username = 'testuser'
        self.user.email = 'test@example.com'
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.phone = '+1234567890'
        self.user.is_verified = True
        self.user.is_active = True
        self.user.role = 'student'
        self.user.created_at = timezone.now()
        self.user.updated_at = timezone.now()

    def test_user_profile_export_structure(self):
        """User profile export should have required fields."""
        exporter = UserDataExporter(self.user)
        profile = exporter._export_user_profile()

        expected_fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'phone', 'is_verified', 'is_active',
            'created_at', 'updated_at'
        ]
        for field in expected_fields:
            self.assertIn(field, profile)

    def test_user_profile_export_values(self):
        """User profile export should contain correct values."""
        exporter = UserDataExporter(self.user)
        profile = exporter._export_user_profile()

        self.assertEqual(profile['id'], 123)
        self.assertEqual(profile['username'], 'testuser')
        self.assertEqual(profile['email'], 'test@example.com')
        self.assertEqual(profile['role'], 'student')

    def test_role_profiles_export_empty_dict(self):
        """Role profiles should return empty dict if no profiles."""
        exporter = UserDataExporter(self.user)
        # User has no actual profile objects (mocked)
        profiles = exporter._export_role_profiles()
        self.assertIsInstance(profiles, dict)

    def test_export_to_json_valid_format(self):
        """JSON export should be valid JSON."""
        exporter = UserDataExporter(self.user)
        # Mock the data collection methods
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

        # Should parse as valid JSON
        data = json.loads(json_str)
        self.assertIn('user', data)
        self.assertIn('export_timestamp', data)

    def test_export_timestamp_iso_format(self):
        """Export timestamp should be in ISO format."""
        exporter = UserDataExporter(self.user)
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
        # This will raise ValueError if not ISO format
        datetime.fromisoformat(timestamp_str)

    def test_export_includes_all_sections(self):
        """Export should have all required sections."""
        exporter = UserDataExporter(self.user)
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

        sections = [
            'user', 'profile', 'notifications', 'messages',
            'assignments', 'payments', 'activity', 'export_timestamp'
        ]
        for section in sections:
            self.assertIn(section, data)


class DataMinimizationTests(SimpleTestCase):
    """Test that exports respect data minimization."""

    def test_user_profile_minimal_data(self):
        """User profile should only include essential fields."""
        user = Mock()
        user.id = 123
        user.username = 'testuser'
        user.email = 'test@example.com'
        user.first_name = 'Test'
        user.last_name = 'User'
        user.phone = ''
        user.is_verified = False
        user.is_active = True
        user.role = 'student'
        user.created_at = timezone.now()
        user.updated_at = timezone.now()

        exporter = UserDataExporter(user)
        profile = exporter._export_user_profile()

        # Should have essential fields only
        self.assertEqual(profile['id'], 123)
        self.assertEqual(profile['role'], 'student')

        # Should not include sensitive system fields
        self.assertNotIn('password', profile)
        self.assertNotIn('secret', profile)


class CSVExportTests(SimpleTestCase):
    """Test CSV export format."""

    def test_csv_export_is_dict(self):
        """CSV export should return dict of filename->content."""
        user = Mock()
        user.id = 123
        user.username = 'testuser'
        user.email = 'test@example.com'
        user.first_name = 'Test'
        user.last_name = 'User'
        user.phone = ''
        user.is_verified = False
        user.is_active = True
        user.role = 'student'
        user.created_at = timezone.now()
        user.updated_at = timezone.now()

        exporter = UserDataExporter(user)
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
        csv_files = exporter.to_csv()

        self.assertIsInstance(csv_files, dict)
        self.assertIn('user.csv', csv_files)
        self.assertIsInstance(csv_files['user.csv'], str)

    def test_csv_export_user_file_format(self):
        """User CSV should have header and data rows."""
        user = Mock()
        user.id = 123
        user.username = 'testuser'
        user.email = 'test@example.com'
        user.first_name = 'Test'
        user.last_name = 'User'
        user.phone = ''
        user.is_verified = False
        user.is_active = True
        user.role = 'student'
        user.created_at = timezone.now()
        user.updated_at = timezone.now()

        exporter = UserDataExporter(user)
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
        csv_files = exporter.to_csv()

        user_csv = csv_files['user.csv']
        lines = user_csv.strip().split('\n')

        # Should have header + at least 1 data row
        self.assertGreaterEqual(len(lines), 1)
        # Should contain testuser
        self.assertIn('testuser', user_csv)
