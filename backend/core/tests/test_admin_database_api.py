"""
Tests for Database Admin API endpoints (T_ADM_006.1)
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
import json

User = get_user_model()


class DatabaseAdminAPITestCase(TestCase):
    """Test Database Admin API endpoints"""

    def setUp(self):
        """Set up test client and admin user"""
        self.client = APIClient()

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User'
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='TestPass123!',
            first_name='Regular',
            last_name='User'
        )

    def test_database_status_view_admin_access(self):
        """Test GET /api/admin/system/database/ with admin"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/system/database/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)

        # Check required fields
        required_fields = [
            'database_type',
            'database_version',
            'database_name',
            'database_size_bytes',
            'database_size_human',
            'last_backup',
            'backup_status',
            'connection_pool'
        ]

        for field in required_fields:
            self.assertIn(field, data['data'])

        # Check connection_pool structure
        self.assertIn('active', data['data']['connection_pool'])
        self.assertIn('max', data['data']['connection_pool'])
        self.assertIn('available', data['data']['connection_pool'])

    def test_database_status_view_non_admin_denied(self):
        """Test GET /api/admin/system/database/ without admin"""
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get('/api/admin/system/database/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_database_status_view_unauthenticated_denied(self):
        """Test GET /api/admin/system/database/ without auth"""
        response = self.client.get('/api/admin/system/database/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_database_tables_view_admin_access(self):
        """Test GET /api/admin/system/database/tables/ with admin"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/system/database/tables/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)

        # Check pagination structure
        self.assertIn('count', data['data'])
        self.assertIn('page', data['data'])
        self.assertIn('page_size', data['data'])
        self.assertIn('total_pages', data['data'])
        self.assertIn('results', data['data'])

    def test_database_tables_view_pagination(self):
        """Test pagination parameters"""
        self.client.force_authenticate(user=self.admin_user)

        # Test with custom page size
        response = self.client.get('/api/admin/system/database/tables/?page=1&page_size=10')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['data']['page'], 1)
        self.assertEqual(data['data']['page_size'], 10)

    def test_database_tables_view_sorting(self):
        """Test sorting parameters"""
        self.client.force_authenticate(user=self.admin_user)

        # Test sorting by rows
        response = self.client.get('/api/admin/system/database/tables/?sort_by=rows')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Verify that results are returned
        self.assertIn('results', data['data'])

    def test_database_queries_view_admin_access(self):
        """Test GET /api/admin/system/database/queries/ with admin"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/system/database/queries/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('count', data['data'])
        self.assertIn('queries', data['data'])

        # Verify response is not paginated (max 10 items)
        self.assertLessEqual(len(data['data']['queries']), 10)

    def test_backup_list_view_admin_access(self):
        """Test GET /api/admin/system/database/backups/ with admin"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/system/database/backups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('count', data['data'])
        self.assertIn('backups', data['data'])

    def test_backup_create_view_admin_access(self):
        """Test POST /api/admin/system/database/backups/ with admin"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post('/api/admin/system/database/backups/', {
            'description': 'Test backup'
        }, format='json')

        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('backup_id', data['data'])
        self.assertIn('status', data['data'])

    def test_backup_restore_view_confirmation_required(self):
        """Test POST /api/admin/database/backup/TEST/restore/ requires confirmation"""
        self.client.force_authenticate(user=self.admin_user)

        # Try without confirmation
        response = self.client.post('/api/admin/database/backup/test_backup/restore/', {
            'confirm': False
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_backup_restore_view_invalid_backup(self):
        """Test POST /api/admin/database/backup/{id}/restore/ with invalid ID"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post('/api/admin/database/backup/nonexistent/restore/', {
            'confirm': True
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_backup_delete_view_invalid_backup(self):
        """Test DELETE /api/admin/database/backup/{id}/ with invalid ID"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.delete('/api/admin/database/backup/nonexistent/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_maintenance_task_create_valid_operation(self):
        """Test POST /api/admin/database/maintenance/ with valid operation"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post('/api/admin/database/maintenance/', {
            'operation': 'vacuum',
            'dry_run': False
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('task_id', data['data'])
        self.assertEqual(data['data']['operation'], 'vacuum')
        self.assertEqual(data['data']['status'], 'in-progress')
        self.assertIn('estimated_duration_seconds', data['data'])

    def test_maintenance_task_create_invalid_operation(self):
        """Test POST /api/admin/database/maintenance/ with invalid operation"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post('/api/admin/database/maintenance/', {
            'operation': 'invalid_operation',
            'dry_run': False
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_maintenance_status_view_valid_task(self):
        """Test GET /api/admin/database/maintenance/{task_id}/ with valid task"""
        self.client.force_authenticate(user=self.admin_user)

        # Create task first
        create_response = self.client.post('/api/admin/database/maintenance/', {
            'operation': 'vacuum'
        }, format='json')

        task_id = create_response.json()['data']['task_id']

        # Get task status
        response = self.client.get(f'/api/admin/database/maintenance/{task_id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertEqual(data['data']['task_id'], task_id)
        self.assertIn('status', data['data'])
        self.assertIn('progress_percent', data['data'])

    def test_maintenance_status_view_invalid_task(self):
        """Test GET /api/admin/database/maintenance/{task_id}/ with invalid task"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/database/maintenance/nonexistent/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_kill_query_view_requires_pid(self):
        """Test POST /api/admin/database/kill-query/ requires query_pid"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post('/api/admin/database/kill-query/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kill_query_view_invalid_pid(self):
        """Test POST /api/admin/database/kill-query/ with invalid PID"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post('/api/admin/database/kill-query/', {
            'query_pid': 99999
        }, format='json')

        # Should return 400 if PID not found
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_all_endpoints_require_admin(self):
        """Test that all endpoints require admin permission"""
        self.client.force_authenticate(user=self.regular_user)

        endpoints = [
            ('/api/admin/system/database/', 'get'),
            ('/api/admin/system/database/tables/', 'get'),
            ('/api/admin/system/database/queries/', 'get'),
            ('/api/admin/system/database/backups/', 'get'),
            ('/api/admin/system/database/backups/', 'post'),
            ('/api/admin/database/backup/test/restore/', 'post'),
            ('/api/admin/database/backup/test/', 'delete'),
            ('/api/admin/database/maintenance/', 'post'),
            ('/api/admin/database/kill-query/', 'post'),
        ]

        for endpoint, method in endpoints:
            if method == 'get':
                response = self.client.get(endpoint)
            elif method == 'post':
                response = self.client.post(endpoint, {}, format='json')
            elif method == 'delete':
                response = self.client.delete(endpoint)

            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Expected 403 for {method.upper()} {endpoint}"
            )


class DatabaseStatusResponseFormatTest(TestCase):
    """Test response format for database status endpoint"""

    def setUp(self):
        """Set up test client and admin user"""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User'
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_database_status_response_format(self):
        """Test that response follows correct format"""
        response = self.client.get('/api/admin/system/database/')

        data = response.json()

        # Top level structure
        self.assertIn('success', data)
        self.assertIsInstance(data['success'], bool)
        self.assertIn('data', data)

        # Data structure
        db_data = data['data']
        self.assertIsInstance(db_data['database_size_bytes'], int)
        self.assertIsInstance(db_data['database_size_human'], str)
        self.assertIsInstance(db_data['connection_pool'], dict)
        self.assertIsInstance(db_data['connection_pool']['active'], int)
        self.assertIsInstance(db_data['connection_pool']['max'], int)
        self.assertIsInstance(db_data['connection_pool']['available'], int)

    def test_backup_list_response_format(self):
        """Test that backup list follows correct format"""
        response = self.client.get('/api/admin/system/database/backups/')

        data = response.json()

        # Top level structure
        self.assertIn('success', data)
        self.assertIn('data', data)

        # Data structure
        self.assertIn('count', data['data'])
        self.assertIsInstance(data['data']['count'], int)
        self.assertIn('backups', data['data'])
        self.assertIsInstance(data['data']['backups'], list)

        # Each backup should have required fields
        for backup in data['data']['backups']:
            self.assertIn('id', backup)
            self.assertIn('filename', backup)
            self.assertIn('size_bytes', backup)
            self.assertIn('size_human', backup)
            self.assertIn('created_at', backup)
            self.assertIn('status', backup)
            self.assertIn('is_downloadable', backup)

    def test_maintenance_task_response_format(self):
        """Test that maintenance task response follows correct format"""
        response = self.client.post('/api/admin/database/maintenance/', {
            'operation': 'reindex'
        }, format='json')

        data = response.json()

        # Top level structure
        self.assertIn('success', data)
        self.assertIn('data', data)

        # Data structure
        task_data = data['data']
        self.assertIn('task_id', task_data)
        self.assertIsInstance(task_data['task_id'], str)
        self.assertIn('operation', task_data)
        self.assertIn('status', task_data)
        self.assertIn('estimated_duration_seconds', task_data)
        self.assertIn('progress_percent', task_data)
        self.assertIsInstance(task_data['progress_percent'], int)


class DatabaseEdgeCasesTest(TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        """Set up test client and admin user"""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User'
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_maintenance_dry_run_parameter(self):
        """Test dry_run parameter handling"""
        response = self.client.post('/api/admin/database/maintenance/', {
            'operation': 'cleanup',
            'dry_run': True
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()

        # Task should be created regardless of dry_run
        self.assertIn('task_id', data['data'])

    def test_backup_list_empty(self):
        """Test backup list when no backups exist"""
        response = self.client.get('/api/admin/system/database/backups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should return empty list, not error
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['count'], 0)

    def test_invalid_page_parameter(self):
        """Test handling of invalid page parameter"""
        response = self.client.get('/api/admin/system/database/tables/?page=invalid')

        # Should handle gracefully (either use default or return error)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ])

    def test_slow_queries_view_graceful_fallback(self):
        """Test slow queries view handles missing pg_stat_statements"""
        response = self.client.get('/api/admin/system/database/queries/')

        # Should return 200 even if pg_stat_statements not available
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['count'], 0)  # No queries if not available


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
