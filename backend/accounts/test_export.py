"""
Tests for GDPR-compliant user data export functionality.

Tests:
- Export endpoint (POST /api/accounts/export/)
- Export status endpoint (GET /api/accounts/export/status/<job_id>/)
- Download endpoint with token verification
- JSON and CSV export formats
- Data minimization (only user's own data)
- Token expiration (7 days)
- Management command
"""
import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from io import StringIO

from accounts.export import (
    UserDataExporter,
    ExportTokenGenerator,
    ExportFileManager
)
from accounts.models import StudentProfile, TeacherProfile

User = get_user_model()


class UserDataExporterTestCase(TestCase):
    """Test data collection and export generation."""

    def setUp(self):
        """Create test user with profile."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123',
            role='student'
        )

        # Create student profile
        self.student_profile = StudentProfile.objects.create(
            user=self.user,
            grade='10',
            goal='Learn programming',
            progress_percentage=50,
            streak_days=5,
            total_points=100,
            accuracy_percentage=85
        )

    def test_collect_all_data_includes_user_profile(self):
        """Test that export includes user profile data."""
        exporter = UserDataExporter(self.user)
        data = exporter.collect_all_data()

        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertEqual(data['user']['first_name'], 'Test')
        self.assertEqual(data['user']['last_name'], 'User')
        self.assertEqual(data['user']['role'], 'student')

    def test_collect_all_data_includes_role_profiles(self):
        """Test that export includes role-specific profile."""
        exporter = UserDataExporter(self.user)
        data = exporter.collect_all_data()

        self.assertIn('profile', data)
        self.assertIn('student', data['profile'])
        self.assertEqual(data['profile']['student']['grade'], '10')
        self.assertEqual(data['profile']['student']['goal'], 'Learn programming')
        self.assertEqual(data['profile']['student']['progress_percentage'], 50)

    def test_collect_all_data_includes_sections(self):
        """Test that export includes all data sections."""
        exporter = UserDataExporter(self.user)
        data = exporter.collect_all_data()

        expected_sections = [
            'user', 'profile', 'notifications', 'messages',
            'assignments', 'payments', 'activity', 'export_timestamp'
        ]
        for section in expected_sections:
            self.assertIn(section, data)

    def test_export_to_json(self):
        """Test JSON export format."""
        exporter = UserDataExporter(self.user)
        exporter.collect_all_data()
        json_str = exporter.to_json()

        # Verify it's valid JSON
        data = json.loads(json_str)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_export_to_csv(self):
        """Test CSV export format."""
        exporter = UserDataExporter(self.user)
        exporter.collect_all_data()
        csv_files = exporter.to_csv()

        # Should have user.csv
        self.assertIn('user.csv', csv_files)
        self.assertIsInstance(csv_files['user.csv'], str)

        # Verify CSV content
        lines = csv_files['user.csv'].strip().split('\n')
        self.assertEqual(len(lines), 2)  # Header + 1 data row
        self.assertIn('testuser', csv_files['user.csv'])

    def test_data_minimization_no_other_users_data(self):
        """Test that export doesn't include other users' data."""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        exporter = UserDataExporter(self.user)
        data = exporter.collect_all_data()

        # Messages should only be from current user (empty in this test)
        self.assertIsInstance(data['messages'], list)

    def test_export_timestamp_included(self):
        """Test that export includes timestamp."""
        exporter = UserDataExporter(self.user)
        data = exporter.collect_all_data()

        self.assertIn('export_timestamp', data)
        # Verify ISO format
        datetime.fromisoformat(data['export_timestamp'])


class ExportTokenGeneratorTestCase(TestCase):
    """Test secure token generation and verification."""

    def setUp(self):
        """Set up test data."""
        self.user_id = 123
        self.filename = 'export_user_123_20251227.json'
        self.timestamp = timezone.now().isoformat()

    def test_generate_token(self):
        """Test token generation."""
        token = ExportTokenGenerator.generate(self.user_id, self.filename)

        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 64)  # SHA256 hex is 64 chars

    def test_verify_valid_token(self):
        """Test verification of valid token."""
        token = ExportTokenGenerator.generate(self.user_id, self.filename)

        is_valid = ExportTokenGenerator.verify(
            self.user_id,
            self.filename,
            token,
            self.timestamp
        )
        self.assertTrue(is_valid)

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = 'invalid' * 10

        is_valid = ExportTokenGenerator.verify(
            self.user_id,
            self.filename,
            invalid_token,
            self.timestamp
        )
        self.assertFalse(is_valid)

    def test_verify_wrong_user_id(self):
        """Test that token fails with wrong user ID."""
        token = ExportTokenGenerator.generate(self.user_id, self.filename)

        is_valid = ExportTokenGenerator.verify(
            self.user_id + 1,  # Different user
            self.filename,
            token,
            self.timestamp
        )
        self.assertFalse(is_valid)

    def test_verify_wrong_filename(self):
        """Test that token fails with wrong filename."""
        token = ExportTokenGenerator.generate(self.user_id, self.filename)

        is_valid = ExportTokenGenerator.verify(
            self.user_id,
            'different_filename.json',
            token,
            self.timestamp
        )
        self.assertFalse(is_valid)

    def test_token_expires_after_7_days(self):
        """Test that token expires after 7 days."""
        token = ExportTokenGenerator.generate(self.user_id, self.filename)

        # Timestamp 8 days ago
        old_timestamp = (timezone.now() - timedelta(days=8)).isoformat()

        is_valid = ExportTokenGenerator.verify(
            self.user_id,
            self.filename,
            token,
            old_timestamp
        )
        self.assertFalse(is_valid)

    def test_token_valid_within_7_days(self):
        """Test that token is valid within 7 days."""
        # Timestamp 5 days ago
        old_timestamp = (timezone.now() - timedelta(days=5)).isoformat()
        token = ExportTokenGenerator.generate(self.user_id, self.filename)

        is_valid = ExportTokenGenerator.verify(
            self.user_id,
            self.filename,
            token,
            old_timestamp
        )
        self.assertTrue(is_valid)


class ExportFileManagerTestCase(TestCase):
    """Test file storage and cleanup."""

    def setUp(self):
        """Set up test data."""
        self.user_id = 123

    def test_get_export_path_json(self):
        """Test path generation for JSON export."""
        path = ExportFileManager.get_export_path(self.user_id, 'json')

        self.assertIn('user_exports', path)
        self.assertIn('export_user_123', path)
        self.assertTrue(path.endswith('.json'))

    def test_get_export_path_csv(self):
        """Test path generation for CSV export."""
        path = ExportFileManager.get_export_path(self.user_id, 'csv')

        self.assertIn('user_exports', path)
        self.assertIn('export_user_123', path)
        self.assertTrue(path.endswith('.zip'))

    def test_export_path_format(self):
        """Test that export path includes timestamp."""
        path = ExportFileManager.get_export_path(self.user_id, 'json')

        # Should have format: user_exports/export_user_123_YYYYMMDD_HHMMSS.json
        parts = path.split('/')
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], 'user_exports')
        self.assertIn('export_user_123', parts[1])


class ExportAPITestCase(APITestCase):
    """Test export API endpoints."""

    def setUp(self):
        """Create test user and authentication token."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = Client()

    def test_export_endpoint_requires_authentication(self):
        """Test that export endpoint requires authentication."""
        response = self.client.post('/api/accounts/export/')

        self.assertEqual(response.status_code, 401)

    def test_export_endpoint_with_token(self):
        """Test export endpoint with valid token."""
        headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        response = self.client.post(
            '/api/accounts/export/',
            **headers
        )

        # Should return 202 Accepted
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertIn('job_id', data)
        self.assertEqual(data['status'], 'queued')
        self.assertEqual(data['format'], 'json')

    def test_export_endpoint_csv_format(self):
        """Test export endpoint with CSV format."""
        headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        response = self.client.post(
            '/api/accounts/export/?format=csv',
            **headers
        )

        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data['format'], 'csv')

    def test_export_endpoint_invalid_format(self):
        """Test export endpoint with invalid format."""
        headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        response = self.client.post(
            '/api/accounts/export/?format=xml',
            **headers
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    @patch('accounts.views.generate_user_export.delay')
    def test_export_status_endpoint(self, mock_task):
        """Test export status endpoint."""
        mock_result = MagicMock()
        mock_result.id = 'test-job-id'
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'success': True,
            'file_path': 'user_exports/export_user_123_20251227.json',
            'file_size': 10000,
            'format': 'json',
            'message': 'Export generated successfully'
        }
        mock_task.return_value = mock_result

        headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        response = self.client.post(
            '/api/accounts/export/',
            **headers
        )
        data = response.json()
        job_id = data['job_id']

        # Check status with mocked task
        with patch('accounts.views.AsyncResult') as mock_async:
            mock_async.return_value = mock_result
            response = self.client.get(
                f'/api/accounts/export/status/{job_id}/',
                **headers
            )

            self.assertEqual(response.status_code, 200)
            status_data = response.json()
            self.assertEqual(status_data['status'], 'completed')
            self.assertIn('file_path', status_data)

    def test_export_status_pending(self):
        """Test export status for pending job."""
        headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        with patch('accounts.views.AsyncResult') as mock_async:
            mock_task = MagicMock()
            mock_task.state = 'PENDING'
            mock_async.return_value = mock_task

            response = self.client.get(
                '/api/accounts/export/status/test-job-id/',
                **headers
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'pending')

    def test_download_export_requires_token(self):
        """Test that download requires valid token."""
        response = self.client.get(
            '/api/accounts/export/download/invalid-token/?ts=2025-01-01&fn=file.json'
        )

        self.assertEqual(response.status_code, 403)

    def test_download_export_missing_timestamp(self):
        """Test download with missing timestamp."""
        headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        response = self.client.get(
            '/api/accounts/export/download/token/?fn=file.json',
            **headers
        )

        self.assertEqual(response.status_code, 400)


class ExportManagementCommandTestCase(TestCase):
    """Test management command for data export."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student'
        )

    def test_export_command_requires_user_id(self):
        """Test that command requires --user_id."""
        with self.assertRaises(SystemExit):
            call_command('export_user_data')

    def test_export_command_nonexistent_user(self):
        """Test command with nonexistent user."""
        with self.assertRaises(SystemExit):
            call_command('export_user_data', '--user_id=99999')

    def test_export_command_json_format(self):
        """Test command with JSON format."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            out = StringIO()
            call_command(
                'export_user_data',
                user_id=self.user.id,
                format='json',
                output=tmpdir,
                stdout=out
            )

            output = out.getvalue()
            self.assertIn('Export completed successfully', output)

            # Check file was created
            files = os.listdir(tmpdir)
            self.assertTrue(any(f.endswith('.json') for f in files))

    def test_export_command_csv_format(self):
        """Test command with CSV format."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            out = StringIO()
            call_command(
                'export_user_data',
                user_id=self.user.id,
                format='csv',
                output=tmpdir,
                stdout=out
            )

            output = out.getvalue()
            self.assertIn('Export completed successfully', output)

            # Check ZIP file was created
            files = os.listdir(tmpdir)
            self.assertTrue(any(f.endswith('.zip') for f in files))

    def test_export_command_invalid_output_dir(self):
        """Test command with invalid output directory."""
        with self.assertRaises(SystemExit):
            call_command(
                'export_user_data',
                user_id=self.user.id,
                output='/nonexistent/directory/'
            )
