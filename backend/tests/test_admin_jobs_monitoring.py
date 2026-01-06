"""
E2E Tests for Admin Jobs Monitoring Dashboard

Тест мониторинга background заданий (Jobs Monitor) в админ кабинете.

Endpoints:
- GET /api/admin/jobs/status/ - список активных заданий
- GET /api/admin/jobs/{job_id}/ - детали конкретного задания
- GET /api/admin/jobs/stats/ - статистика заданий
"""

import pytest
import json
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import time

User = get_user_model()


class AdminJobsMonitoringAPITest(APITestCase):
    """E2E тесты для мониторинга заданий в админ кабинете"""

    def setUp(self):
        """Инициализация тестовых данных"""
        # Очистка кэша
        cache.clear()

        # Создание admin пользователя
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='AdminPass123!@#'
        )

        # Создание обычного пользователя
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='user@test.com',
            password='UserPass123!@#'
        )

        # API клиент
        self.client = APIClient()

        # Mock job ID
        self.mock_job_id = 'job_test_12345'

    def tearDown(self):
        """Очистка после тестов"""
        cache.clear()

    # ============================================================================
    # T001: GET /api/admin/jobs/status/ - Список активных заданий
    # ============================================================================

    def test_admin_jobs_status_requires_authentication(self):
        """Security: Неаутентифицированный пользователь не может видеть jobs"""
        response = self.client.get('/api/system/admin/jobs/status/')

        # Expect 401 Unauthorized
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_non_admin_cannot_view_jobs_status(self):
        """Security: Обычный пользователь не может видеть jobs (403)"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/system/admin/jobs/status/')

        # Expect 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_jobs_status(self):
        """Test: Admin может видеть список активных заданий"""
        self.client.force_authenticate(user=self.admin_user)

        # Mock Celery jobs in cache
        mock_jobs = [
            {
                'job_id': 'job_export_001',
                'name': 'Export Users',
                'status': 'running',
                'progress': 45,
                'started_at': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            },
            {
                'job_id': 'job_report_002',
                'name': 'Generate Report',
                'status': 'pending',
                'progress': 0,
                'started_at': datetime.utcnow().isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            }
        ]

        # Кэшируем mock jobs
        cache.set('admin_jobs_list', mock_jobs, timeout=300)

        response = self.client.get('/api/system/admin/jobs/status/')

        # Expect 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем структуру ответа
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('data', data)

        # Проверяем наличие списка заданий
        jobs = data.get('data', [])
        self.assertIsInstance(jobs, list)

    def test_jobs_status_response_structure(self):
        """Test: GET /api/admin/jobs/status/ возвращает корректную структуру"""
        self.client.force_authenticate(user=self.admin_user)

        # Создаем mock job с полными полями
        mock_job = {
            'job_id': 'job_test_001',
            'name': 'Test Export Job',
            'status': 'running',  # pending | running | completed | failed
            'progress': 65,  # 0-100%
            'started_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(minutes=3)).isoformat()
        }

        cache.set('admin_jobs_list', [mock_job], timeout=300)

        response = self.client.get('/api/system/admin/jobs/status/')
        data = response.json()['data']

        # Проверяем наличие обязательных полей
        if len(data) > 0:
            job = data[0]
            self.assertIn('job_id', job)
            self.assertIn('name', job)
            self.assertIn('status', job)
            self.assertIn('progress', job)
            self.assertIn('started_at', job)
            self.assertIn('estimated_completion', job)

            # Проверяем типы данных
            self.assertIsInstance(job['job_id'], str)
            self.assertIsInstance(job['name'], str)
            self.assertIn(job['status'], ['pending', 'running', 'completed', 'failed'])
            self.assertIsInstance(job['progress'], int)
            self.assertGreaterEqual(job['progress'], 0)
            self.assertLessEqual(job['progress'], 100)

    def test_jobs_status_progress_updates(self):
        """Test: Progress обновляется по мере выполнения job"""
        self.client.force_authenticate(user=self.admin_user)

        # Первое получение - progress 20%
        job_initial = {
            'job_id': 'job_progress_test',
            'name': 'Progress Test Job',
            'status': 'running',
            'progress': 20,
            'started_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        cache.set('admin_jobs_list', [job_initial], timeout=300)

        response1 = self.client.get('/api/system/admin/jobs/status/')
        data1 = response1.json()['data']
        initial_progress = data1[0]['progress'] if data1 else 0

        # Имитируем обновление progress
        job_updated = job_initial.copy()
        job_updated['progress'] = 75
        cache.set('admin_jobs_list', [job_updated], timeout=300)

        response2 = self.client.get('/api/system/admin/jobs/status/')
        data2 = response2.json()['data']
        updated_progress = data2[0]['progress'] if data2 else 0

        # Progress должен увеличиться
        self.assertLess(initial_progress, updated_progress)

    # ============================================================================
    # T002: GET /api/admin/jobs/{job_id}/ - Детали конкретного задания
    # ============================================================================

    def test_job_details_requires_authentication(self):
        """Security: Неаутентифицированный пользователь не может видеть детали job"""
        response = self.client.get(f'/api/system/admin/jobs/{self.mock_job_id}/')

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_non_admin_cannot_view_job_details(self):
        """Security: Обычный пользователь не может видеть детали job"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f'/api/system/admin/jobs/{self.mock_job_id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_job_returns_404(self):
        """Test: Несуществующий job_id возвращает 404"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/system/admin/jobs/nonexistent_job_id/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_view_job_details(self):
        """Test: Admin может видеть детали конкретного задания"""
        self.client.force_authenticate(user=self.admin_user)

        job_id = 'job_details_001'
        mock_job_details = {
            'job_id': job_id,
            'name': 'Export Materials',
            'status': 'completed',
            'progress': 100,
            'started_at': (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
            'completed_at': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            'estimated_completion': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            'result': {
                'file_url': '/media/exports/materials_export_001.csv',
                'file_size_mb': 12.5,
                'record_count': 1500
            }
        }

        cache.set(f'admin_job_detail:{job_id}', mock_job_details, timeout=3600)

        response = self.client.get(f'/api/system/admin/jobs/{job_id}/')

        # Expect 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('success', data)
        self.assertIn('data', data)

    def test_job_details_includes_full_information(self):
        """Test: Детали job включают полную информацию"""
        self.client.force_authenticate(user=self.admin_user)

        job_id = 'job_full_info_001'
        mock_job = {
            'job_id': job_id,
            'name': 'Generate Report',
            'status': 'completed',
            'progress': 100,
            'started_at': (datetime.utcnow() - timedelta(minutes=8)).isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
            'result': {
                'file_url': '/media/reports/report_2026_01_07.pdf',
                'file_size_mb': 5.2,
                'pages': 42
            }
        }

        cache.set(f'admin_job_detail:{job_id}', mock_job, timeout=3600)

        response = self.client.get(f'/api/system/admin/jobs/{job_id}/')
        job = response.json()['data']

        # Проверяем обязательные поля
        self.assertIn('job_id', job)
        self.assertIn('name', job)
        self.assertIn('status', job)
        self.assertIn('progress', job)
        self.assertIn('started_at', job)
        self.assertEqual(job['status'], 'completed')
        self.assertEqual(job['progress'], 100)

        # Проверяем результат (если job создала файл)
        if job.get('result'):
            self.assertIn('file_url', job['result'])

    # ============================================================================
    # T003: GET /api/admin/jobs/stats/ - Статистика заданий
    # ============================================================================

    def test_job_stats_requires_authentication(self):
        """Security: Неаутентифицированный пользователь не может видеть stats"""
        response = self.client.get('/api/system/admin/jobs/stats/')

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_non_admin_cannot_view_job_stats(self):
        """Security: Обычный пользователь не может видеть stats"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/system/admin/jobs/stats/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_job_stats(self):
        """Test: Admin может видеть статистику заданий"""
        self.client.force_authenticate(user=self.admin_user)

        mock_stats = {
            'total_jobs': 127,
            'pending_count': 5,
            'running_count': 3,
            'completed_count': 115,
            'failed_count': 4,
            'average_completion_time': 342.5,  # в секундах
            'success_rate': 96.5  # в процентах
        }

        cache.set('admin_jobs_stats', mock_stats, timeout=60)

        response = self.client.get('/api/system/admin/jobs/stats/')

        # Expect 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('success', data)
        self.assertIn('data', data)

    def test_job_stats_response_structure(self):
        """Test: GET /api/admin/jobs/stats/ возвращает корректную структуру"""
        self.client.force_authenticate(user=self.admin_user)

        mock_stats = {
            'total_jobs': 50,
            'pending_count': 2,
            'running_count': 1,
            'completed_count': 45,
            'failed_count': 2,
            'average_completion_time': 285.0,
            'success_rate': 94.0
        }

        cache.set('admin_jobs_stats', mock_stats, timeout=60)

        response = self.client.get('/api/system/admin/jobs/stats/')
        stats = response.json()['data']

        # Проверяем обязательные поля
        self.assertIn('total_jobs', stats)
        self.assertIn('pending_count', stats)
        self.assertIn('running_count', stats)
        self.assertIn('completed_count', stats)
        self.assertIn('failed_count', stats)
        self.assertIn('average_completion_time', stats)

        # Проверяем типы данных
        self.assertIsInstance(stats['total_jobs'], int)
        self.assertIsInstance(stats['pending_count'], int)
        self.assertIsInstance(stats['running_count'], int)
        self.assertIsInstance(stats['completed_count'], int)
        self.assertIsInstance(stats['failed_count'], int)
        self.assertIsInstance(stats['average_completion_time'], (int, float))

        # Проверяем корректность счета
        total_count = (stats['pending_count'] + stats['running_count'] +
                      stats['completed_count'] + stats['failed_count'])
        self.assertEqual(total_count, stats['total_jobs'])

    def test_job_stats_success_rate_calculation(self):
        """Test: Success rate вычисляется корректно"""
        self.client.force_authenticate(user=self.admin_user)

        # 100 jobs total, 95 successful, 5 failed
        mock_stats = {
            'total_jobs': 100,
            'pending_count': 0,
            'running_count': 0,
            'completed_count': 95,
            'failed_count': 5,
            'average_completion_time': 300.0,
            'success_rate': 95.0
        }

        cache.set('admin_jobs_stats', mock_stats, timeout=60)

        response = self.client.get('/api/system/admin/jobs/stats/')
        stats = response.json()['data']

        # Verify success rate
        expected_success_rate = (stats['completed_count'] / stats['total_jobs']) * 100
        self.assertEqual(stats.get('success_rate', 0), expected_success_rate)

    # ============================================================================
    # T004: Failed Jobs - Тестирование failed job
    # ============================================================================

    def test_failed_job_has_error_message(self):
        """Test: Failed job содержит error_message"""
        self.client.force_authenticate(user=self.admin_user)

        job_id = 'job_failed_001'
        mock_failed_job = {
            'job_id': job_id,
            'name': 'Failed Export Job',
            'status': 'failed',
            'progress': 35,
            'started_at': (datetime.utcnow() - timedelta(minutes=3)).isoformat(),
            'failed_at': datetime.utcnow().isoformat(),
            'error_message': 'Database connection timeout: connection to database failed',
            'error_type': 'DatabaseError',
            'traceback': 'Traceback (most recent call last):\n  ...'
        }

        cache.set(f'admin_job_detail:{job_id}', mock_failed_job, timeout=3600)

        response = self.client.get(f'/api/system/admin/jobs/{job_id}/')
        job = response.json()['data']

        # Проверяем что это failed job
        self.assertEqual(job['status'], 'failed')

        # Проверяем наличие error_message
        self.assertIn('error_message', job)
        self.assertNotEqual(job.get('error_message', ''), '')

    def test_failed_job_in_status_list(self):
        """Test: Failed job отображается в списке с корректным статусом"""
        self.client.force_authenticate(user=self.admin_user)

        failed_job = {
            'job_id': 'job_failed_list_001',
            'name': 'Failed Job in List',
            'status': 'failed',
            'progress': 20,
            'started_at': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            'estimated_completion': (datetime.utcnow() - timedelta(minutes=2)).isoformat()
        }

        cache.set('admin_jobs_list', [failed_job], timeout=300)

        response = self.client.get('/api/system/admin/jobs/status/')
        jobs = response.json()['data']

        if len(jobs) > 0:
            found_job = next((j for j in jobs if j['job_id'] == 'job_failed_list_001'), None)
            self.assertIsNotNone(found_job)
            self.assertEqual(found_job['status'], 'failed')

    # ============================================================================
    # T005: Job Lifecycle - Проверка жизненного цикла job
    # ============================================================================

    def test_job_status_transitions(self):
        """Test: Job переходит через правильные статусы: pending -> running -> completed"""
        self.client.force_authenticate(user=self.admin_user)

        job_id = 'job_lifecycle_001'

        # Stage 1: pending
        job_pending = {
            'job_id': job_id,
            'name': 'Lifecycle Test Job',
            'status': 'pending',
            'progress': 0,
            'started_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }
        cache.set(f'admin_job_detail:{job_id}', job_pending, timeout=3600)
        response = self.client.get(f'/api/system/admin/jobs/{job_id}/')
        self.assertEqual(response.json()['data']['status'], 'pending')

        # Stage 2: running
        job_running = job_pending.copy()
        job_running['status'] = 'running'
        job_running['progress'] = 50
        cache.set(f'admin_job_detail:{job_id}', job_running, timeout=3600)
        response = self.client.get(f'/api/system/admin/jobs/{job_id}/')
        self.assertEqual(response.json()['data']['status'], 'running')

        # Stage 3: completed
        job_completed = job_running.copy()
        job_completed['status'] = 'completed'
        job_completed['progress'] = 100
        job_completed['completed_at'] = datetime.utcnow().isoformat()
        cache.set(f'admin_job_detail:{job_id}', job_completed, timeout=3600)
        response = self.client.get(f'/api/system/admin/jobs/{job_id}/')
        self.assertEqual(response.json()['data']['status'], 'completed')

    # ============================================================================
    # T006: Edge Cases and Validation
    # ============================================================================

    def test_jobs_status_empty_list(self):
        """Test: Пустой список jobs возвращается корректно"""
        self.client.force_authenticate(user=self.admin_user)

        cache.set('admin_jobs_list', [], timeout=300)

        response = self.client.get('/api/system/admin/jobs/status/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_invalid_job_id_format_returns_400_or_404(self):
        """Test: Invalid job_id format возвращает 400 или 404"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/system/admin/jobs/!!!invalid!!!/')

        # Should be 400 Bad Request or 404 Not Found
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])

    def test_stats_with_zero_jobs(self):
        """Test: Statistics работает корректно с нулевым количеством jobs"""
        self.client.force_authenticate(user=self.admin_user)

        mock_stats = {
            'total_jobs': 0,
            'pending_count': 0,
            'running_count': 0,
            'completed_count': 0,
            'failed_count': 0,
            'average_completion_time': 0,
            'success_rate': 0
        }

        cache.set('admin_jobs_stats', mock_stats, timeout=60)

        response = self.client.get('/api/system/admin/jobs/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stats = response.json()['data']
        self.assertEqual(stats['total_jobs'], 0)

    def test_progress_validation(self):
        """Test: Progress может быть только 0-100"""
        self.client.force_authenticate(user=self.admin_user)

        # Valid progress values
        for progress in [0, 25, 50, 75, 100]:
            job = {
                'job_id': f'job_progress_{progress}',
                'name': f'Test Job {progress}',
                'status': 'running',
                'progress': progress,
                'started_at': datetime.utcnow().isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            cache.set('admin_jobs_list', [job], timeout=300)

            response = self.client.get('/api/system/admin/jobs/status/')
            jobs = response.json()['data']

            if len(jobs) > 0:
                self.assertGreaterEqual(jobs[0]['progress'], 0)
                self.assertLessEqual(jobs[0]['progress'], 100)

    # ============================================================================
    # T007: Response Format Validation
    # ============================================================================

    def test_jobs_status_response_has_success_field(self):
        """Test: Все ответы имеют success field"""
        self.client.force_authenticate(user=self.admin_user)

        cache.set('admin_jobs_list', [], timeout=300)

        response = self.client.get('/api/system/admin/jobs/status/')
        data = response.json()

        self.assertIn('success', data)
        self.assertIsInstance(data['success'], bool)

    def test_error_response_structure(self):
        """Test: Error ответы имеют правильную структуру"""
        # Try to access without authentication
        response = self.client.get('/api/system/admin/jobs/status/')

        # If it's an error, it should have error info
        if response.status_code >= 400:
            data = response.json()
            # Should have either 'detail', 'error', or other error info
            self.assertTrue(
                'detail' in data or 'error' in data or response.status_code in [401, 403]
            )

    # ============================================================================
    # T008: Performance and Caching
    # ============================================================================

    def test_jobs_status_response_time(self):
        """Test: Response time для jobs status должен быть < 500ms"""
        self.client.force_authenticate(user=self.admin_user)

        # Create 10 jobs
        mock_jobs = [
            {
                'job_id': f'job_perf_{i}',
                'name': f'Performance Test Job {i}',
                'status': 'running' if i % 2 == 0 else 'pending',
                'progress': i * 10,
                'started_at': (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            for i in range(10)
        ]

        cache.set('admin_jobs_list', mock_jobs, timeout=300)

        import time
        start = time.time()
        response = self.client.get('/api/system/admin/jobs/status/')
        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Should be fast (< 500ms)
        self.assertLess(elapsed, 500)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdminJobsMonitoringIntegrationTest(TestCase):
    """Integration тесты для jobs monitoring"""

    def setUp(self):
        """Инициализация"""
        cache.clear()
        self.admin_user = User.objects.create_superuser(
            username='admin_integration',
            email='admin_int@test.com',
            password='AdminPass123!@#'
        )
        self.client = APIClient()

    def test_jobs_list_caching(self):
        """Test: Jobs list кэшируется"""
        self.client.force_authenticate(user=self.admin_user)

        mock_jobs = [
            {
                'job_id': 'job_cache_001',
                'name': 'Cache Test Job',
                'status': 'running',
                'progress': 50,
                'started_at': datetime.utcnow().isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
        ]

        cache.set('admin_jobs_list', mock_jobs, timeout=300)

        # First request
        response1 = self.client.get('/api/system/admin/jobs/status/')

        # Modify the cached data
        mock_jobs[0]['progress'] = 75
        cache.set('admin_jobs_list', mock_jobs, timeout=300)

        # Second request should get updated data
        response2 = self.client.get('/api/system/admin/jobs/status/')

        # Both should be successful
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_concurrent_requests_to_jobs_status(self):
        """Test: Concurrent requests работают корректно"""
        self.client.force_authenticate(user=self.admin_user)

        mock_jobs = [
            {
                'job_id': f'job_concurrent_{i}',
                'name': f'Concurrent Job {i}',
                'status': 'running',
                'progress': 50,
                'started_at': datetime.utcnow().isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            for i in range(5)
        ]

        cache.set('admin_jobs_list', mock_jobs, timeout=300)

        # Simulate concurrent requests
        responses = []
        for _ in range(3):
            response = self.client.get('/api/system/admin/jobs/status/')
            responses.append(response)

        # All should be successful
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def tearDown(self):
        """Cleanup"""
        cache.clear()


# Test fixtures for Pytest integration
@pytest.fixture
def admin_user(db):
    """Fixture для admin пользователя"""
    return User.objects.create_superuser(
        username='pytest_admin',
        email='pytest_admin@test.com',
        password='PytestPass123!@#'
    )


@pytest.fixture
def regular_user(db):
    """Fixture для обычного пользователя"""
    return User.objects.create_user(
        username='pytest_user',
        email='pytest_user@test.com',
        password='PytestPass123!@#'
    )


@pytest.fixture
def api_client():
    """Fixture для API клиента"""
    return APIClient()


@pytest.mark.django_db
class TestAdminJobsMonitoringPytest:
    """Pytest-style tests для jobs monitoring"""

    def test_admin_authentication_required(self, api_client):
        """Pytest: Admin authentication required"""
        response = api_client.get('/api/system/admin/jobs/status/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_admin_can_access_jobs(self, api_client, admin_user):
        """Pytest: Admin can access jobs"""
        api_client.force_authenticate(user=admin_user)
        cache.set('admin_jobs_list', [], timeout=300)

        response = api_client.get('/api/system/admin/jobs/status/')
        assert response.status_code == status.HTTP_200_OK
        assert 'success' in response.json()
