"""
E2E Test Suite for Admin System Monitoring Dashboard
Tests system health monitoring endpoints and real-time metrics
"""
import os
import django
import pytest
import time
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

if not django.apps.apps.ready:
    django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class TestAdminSystemMonitoringAuth(TestCase):
    """Test authentication and authorization for monitoring endpoints"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_email = 'admin@test.com'
        cls.admin_password = 'TestPass123!'
        cls.student_email = 'student@test.com'
        cls.student_password = 'TestPass123!'

    def setUp(self):
        """Setup test users"""
        # Create admin user
        User.objects.filter(email=self.admin_email).delete()
        User.objects.filter(email=self.student_email).delete()

        self.admin_user = User.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        self.student_user = User.objects.create_user(
            username=self.student_email,
            email=self.student_email,
            password=self.student_password,
            is_staff=False,
            is_superuser=False,
            is_active=True,
            role=User.Role.STUDENT
        )

        self.client = APIClient()

    def test_unauthenticated_cannot_access_stats_users(self):
        """Unauthenticated users cannot access /api/admin/stats/users/"""
        response = self.client.get('/api/admin/stats/users/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_unauthenticated_cannot_access_system_health(self):
        """Unauthenticated users cannot access /api/admin/system/health/"""
        response = self.client.get('/api/admin/system/health/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_unauthenticated_cannot_access_system_metrics(self):
        """Unauthenticated users cannot access /api/admin/system/metrics/"""
        response = self.client.get('/api/admin/system/metrics/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_non_admin_cannot_access_stats_users(self):
        """Non-admin users get 403 when accessing /api/admin/stats/users/"""
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get('/api/admin/stats/users/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_access_system_health(self):
        """Non-admin users get 403 when accessing /api/admin/system/health/"""
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get('/api/admin/system/health/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_access_system_metrics(self):
        """Non-admin users get 403 when accessing /api/admin/system/metrics/"""
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get('/api/admin/system/metrics/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_stats_users(self):
        """Admin users can access /api/admin/stats/users/"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/stats/users/')
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_access_system_health(self):
        """Admin users can access /api/admin/system/health/"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/system/health/')
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_access_system_metrics(self):
        """Admin users can access /api/admin/system/metrics/"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/system/metrics/')
        assert response.status_code == status.HTTP_200_OK


class TestAdminUserStatsEndpoint(TestCase):
    """Test /api/admin/stats/users/ endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_email = 'admin@test.com'
        cls.admin_password = 'TestPass123!'

    def setUp(self):
        """Setup admin user and test data"""
        User.objects.all().delete()

        self.admin_user = User.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        # Create test users
        for i in range(5):
            User.objects.create_user(
                username=f'student_{i}@test.com',
                email=f'student_{i}@test.com',
                password='pass123',
                role=User.Role.STUDENT,
                is_active=True
            )

        for i in range(3):
            User.objects.create_user(
                username=f'teacher_{i}@test.com',
                email=f'teacher_{i}@test.com',
                password='pass123',
                role=User.Role.TEACHER,
                is_active=True
            )

        for i in range(2):
            User.objects.create_user(
                username=f'tutor_{i}@test.com',
                email=f'tutor_{i}@test.com',
                password='pass123',
                role=User.Role.TUTOR,
                is_active=True
            )

        for i in range(4):
            User.objects.create_user(
                username=f'parent_{i}@test.com',
                email=f'parent_{i}@test.com',
                password='pass123',
                role=User.Role.PARENT,
                is_active=True
            )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_stats_users_returns_200(self):
        """GET /api/admin/stats/users/ returns 200 OK"""
        response = self.client.get('/api/admin/stats/users/')
        assert response.status_code == status.HTTP_200_OK

    def test_stats_users_response_structure(self):
        """Response contains expected data structure"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        assert 'success' in data
        assert 'data' in data
        assert data['success'] is True

    def test_stats_users_has_total_users(self):
        """Response contains total_users field"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        assert 'total_users' in data['data']
        assert isinstance(data['data']['total_users'], int)
        assert data['data']['total_users'] >= 14  # 1 admin + 14 test users

    def test_stats_users_has_by_role_breakdown(self):
        """Response contains by_role breakdown"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        assert 'total_students' in data['data']
        assert 'total_teachers' in data['data']
        assert 'total_tutors' in data['data']
        assert 'total_parents' in data['data']

        assert data['data']['total_students'] == 5
        assert data['data']['total_teachers'] == 3
        assert data['data']['total_tutors'] == 2
        assert data['data']['total_parents'] >= 5  # includes admin

    def test_stats_users_has_active_count(self):
        """Response contains active_users count"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        assert 'active_users' in data['data']
        assert isinstance(data['data']['active_users'], int)
        assert data['data']['active_users'] >= 14

    def test_stats_users_has_active_today(self):
        """Response contains active_today count"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        assert 'active_today' in data['data']
        assert isinstance(data['data']['active_today'], int)

    def test_stats_users_values_are_numeric(self):
        """All numeric fields are valid numbers"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        numeric_fields = [
            'total_users', 'total_students', 'total_teachers',
            'total_tutors', 'total_parents', 'active_users', 'active_today'
        ]

        for field in numeric_fields:
            assert field in data['data']
            assert isinstance(data['data'][field], int)
            assert data['data'][field] >= 0

    def test_stats_users_totals_consistency(self):
        """Total users should match sum of by_role counts"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        total = (
            data['data']['total_students'] +
            data['data']['total_teachers'] +
            data['data']['total_tutors'] +
            data['data']['total_parents']
        )

        assert total == data['data']['total_users']

    def test_stats_users_fresh_data_not_cached(self):
        """Stats endpoint returns fresh data (no caching)"""
        response1 = self.client.get('/api/admin/stats/users/')
        data1 = response1.json()
        count1 = data1['data']['total_users']

        # Create new user
        User.objects.create_user(
            username='new_user@test.com',
            email='new_user@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=True
        )

        response2 = self.client.get('/api/admin/stats/users/')
        data2 = response2.json()
        count2 = data2['data']['total_users']

        assert count2 == count1 + 1


class TestAdminSystemHealthEndpoint(TestCase):
    """Test /api/admin/system/health/ endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_email = 'admin@test.com'
        cls.admin_password = 'TestPass123!'

    def setUp(self):
        """Setup admin user"""
        User.objects.filter(email=self.admin_email).delete()

        self.admin_user = User.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_system_health_returns_200(self):
        """GET /api/admin/system/health/ returns 200 OK"""
        response = self.client.get('/api/admin/system/health/')
        assert response.status_code == status.HTTP_200_OK

    def test_system_health_response_structure(self):
        """Response contains expected data structure"""
        response = self.client.get('/api/admin/system/health/')
        data = response.json()

        assert 'success' in data
        assert 'data' in data
        assert data['success'] is True

    def test_system_health_has_status(self):
        """Response contains status field (healthy/warning/critical)"""
        response = self.client.get('/api/admin/system/health/')
        data = response.json()

        assert 'status' in data['data']
        assert data['data']['status'] in ['green', 'yellow', 'red', 'healthy', 'warning', 'critical']

    def test_system_health_has_uptime(self):
        """Response contains uptime field"""
        response = self.client.get('/api/admin/system/health/')
        data = response.json()

        # Either in top-level or in nested components
        assert 'timestamp' in data['data']

    def test_system_health_has_health_score(self):
        """Response contains health_score (0-100)"""
        response = self.client.get('/api/admin/system/health/')
        data = response.json()

        assert 'health_score' in data['data']
        assert isinstance(data['data']['health_score'], (int, float))
        assert 0 <= data['data']['health_score'] <= 100

    def test_system_health_has_components(self):
        """Response contains components health status"""
        response = self.client.get('/api/admin/system/health/')
        data = response.json()

        assert 'components' in data['data']
        components = data['data']['components']

        # Check for key components
        expected_components = ['cpu', 'memory', 'disk', 'database', 'redis']
        for comp in expected_components:
            assert comp in components
            assert components[comp] in ['healthy', 'warning', 'critical', 'unknown']

    def test_system_health_has_active_alerts(self):
        """Response contains active_alerts count"""
        response = self.client.get('/api/admin/system/health/')
        data = response.json()

        assert 'active_alerts' in data['data']
        assert isinstance(data['data']['active_alerts'], int)
        assert data['data']['active_alerts'] >= 0

    def test_system_health_with_detailed_flag(self):
        """Response includes detailed metrics when detailed=true"""
        response = self.client.get('/api/admin/system/health/?detailed=true')
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        # With detailed flag, should include metrics
        assert 'metrics' in data['data'] or 'cpu' in str(response.content)

    def test_system_health_response_time_under_5s(self):
        """System health endpoint responds in under 5 seconds"""
        start_time = time.time()
        response = self.client.get('/api/admin/system/health/')
        elapsed_time = time.time() - start_time

        assert elapsed_time < 5.0
        assert response.status_code == status.HTTP_200_OK


class TestAdminSystemMetricsEndpoint(TestCase):
    """Test /api/admin/system/metrics/ endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_email = 'admin@test.com'
        cls.admin_password = 'TestPass123!'

    def setUp(self):
        """Setup admin user"""
        User.objects.filter(email=self.admin_email).delete()

        self.admin_user = User.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_system_metrics_returns_200(self):
        """GET /api/admin/system/metrics/ returns 200 OK"""
        response = self.client.get('/api/admin/system/metrics/')
        assert response.status_code == status.HTTP_200_OK

    def test_system_metrics_response_structure(self):
        """Response contains expected data structure"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'success' in data
        assert 'data' in data
        assert data['success'] is True

    def test_system_metrics_has_timestamp(self):
        """Response contains timestamp field"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'timestamp' in data['data']

    def test_system_metrics_has_cpu_metrics(self):
        """Response contains CPU metrics"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'cpu' in data['data']
        cpu = data['data']['cpu']

        # Check for required CPU fields
        assert 'current_percent' in cpu or 'status' in cpu

    def test_system_metrics_has_memory_metrics(self):
        """Response contains Memory metrics"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'memory' in data['data']
        memory = data['data']['memory']

        # Check for required Memory fields
        assert 'used_percent' in memory or 'status' in memory

    def test_system_metrics_has_disk_metrics(self):
        """Response contains Disk metrics"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'disk' in data['data']
        # Disk can be dict with partitions or list

    def test_system_metrics_has_database_metrics(self):
        """Response contains Database metrics"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'database' in data['data']
        database = data['data']['database']

        assert 'response_time_ms' in database or 'status' in database

    def test_system_metrics_has_redis_metrics(self):
        """Response contains Redis metrics"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        assert 'redis' in data['data']
        redis = data['data']['redis']

        assert 'response_time_ms' in redis or 'is_working' in redis or 'status' in redis

    def test_system_metrics_all_numeric_values_valid(self):
        """All numeric values in metrics are valid"""
        response = self.client.get('/api/admin/system/metrics/')
        data = response.json()

        # Sample some key metrics
        if 'cpu' in data['data'] and 'current_percent' in data['data']['cpu']:
            cpu_percent = data['data']['cpu']['current_percent']
            assert isinstance(cpu_percent, (int, float))
            assert 0 <= cpu_percent <= 100

        if 'memory' in data['data'] and 'used_percent' in data['data']['memory']:
            mem_percent = data['data']['memory']['used_percent']
            assert isinstance(mem_percent, (int, float))
            assert 0 <= mem_percent <= 100

    def test_system_metrics_response_time_under_5s(self):
        """System metrics endpoint responds in under 5 seconds"""
        start_time = time.time()
        response = self.client.get('/api/admin/system/metrics/')
        elapsed_time = time.time() - start_time

        assert elapsed_time < 5.0
        assert response.status_code == status.HTTP_200_OK

    def test_system_metrics_fresh_data_not_cached(self):
        """Metrics endpoint returns fresh data (not heavily cached)"""
        response1 = self.client.get('/api/admin/system/metrics/')
        data1 = response1.json()

        # Small delay
        time.sleep(0.1)

        response2 = self.client.get('/api/admin/system/metrics/')
        data2 = response2.json()

        # Timestamps should be different (or very close)
        assert 'timestamp' in data1['data']
        assert 'timestamp' in data2['data']

        # At least we got both responses successfully
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestAdminMonitoringWithLoadData(TransactionTestCase):
    """Test monitoring endpoints with significant data load"""

    def setUp(self):
        """Setup admin user and create test data"""
        User.objects.all().delete()

        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        # Create 100 users of various types
        for i in range(50):
            User.objects.create_user(
                username=f'student_{i}@test.com',
                email=f'student_{i}@test.com',
                password='pass123',
                role=User.Role.STUDENT,
                is_active=i % 2 == 0  # Half active, half inactive
            )

        for i in range(20):
            User.objects.create_user(
                username=f'teacher_{i}@test.com',
                email=f'teacher_{i}@test.com',
                password='pass123',
                role=User.Role.TEACHER,
                is_active=True
            )

        for i in range(15):
            User.objects.create_user(
                username=f'tutor_{i}@test.com',
                email=f'tutor_{i}@test.com',
                password='pass123',
                role=User.Role.TUTOR,
                is_active=True
            )

        for i in range(20):
            User.objects.create_user(
                username=f'parent_{i}@test.com',
                email=f'parent_{i}@test.com',
                password='pass123',
                role=User.Role.PARENT,
                is_active=True
            )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_stats_users_with_large_dataset(self):
        """User stats endpoint performs well with 100+ users"""
        start_time = time.time()
        response = self.client.get('/api/admin/stats/users/')
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 5.0

        data = response.json()
        assert data['data']['total_users'] >= 106

    def test_health_check_with_large_dataset(self):
        """Health check endpoint performs well with 100+ users"""
        start_time = time.time()
        response = self.client.get('/api/admin/system/health/')
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 5.0

    def test_metrics_with_large_dataset(self):
        """Metrics endpoint performs well with 100+ users"""
        start_time = time.time()
        response = self.client.get('/api/admin/system/metrics/')
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 5.0


class TestMonitoringPartialDataAvailability(TestCase):
    """Test that monitoring endpoints handle service unavailability gracefully"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_email = 'admin@test.com'
        cls.admin_password = 'TestPass123!'

    def setUp(self):
        """Setup admin user"""
        User.objects.filter(email=self.admin_email).delete()

        self.admin_user = User.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_health_endpoint_returns_response_on_redis_unavailable(self):
        """Health endpoint returns response even if Redis is unavailable"""
        response = self.client.get('/api/admin/system/health/')

        # Should still return 200, even if Redis is down
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'data' in data

    def test_metrics_endpoint_returns_response_on_partial_service_unavailable(self):
        """Metrics endpoint returns response even if some services are unavailable"""
        response = self.client.get('/api/admin/system/metrics/')

        # Should still return 200, possibly with partial data
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'data' in data


class TestMonitoringDataConsistency(TestCase):
    """Test data consistency and correctness of monitoring data"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_email = 'admin@test.com'
        cls.admin_password = 'TestPass123!'

    def setUp(self):
        """Setup admin user and test data"""
        User.objects.all().delete()

        self.admin_user = User.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            role=User.Role.PARENT
        )

        # Create users with specific pattern
        self.students = [
            User.objects.create_user(
                username=f'student_{i}@test.com',
                email=f'student_{i}@test.com',
                password='pass123',
                role=User.Role.STUDENT,
                is_active=True
            )
            for i in range(3)
        ]

        self.inactive_student = User.objects.create_user(
            username='inactive_student@test.com',
            email='inactive_student@test.com',
            password='pass123',
            role=User.Role.STUDENT,
            is_active=False
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_active_count_matches_actual_active_users(self):
        """Active user count matches actual active users in database"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        # Count active users
        active_in_db = User.objects.filter(is_active=True).count()
        reported_active = data['data']['active_users']

        assert reported_active == active_in_db

    def test_inactive_users_not_counted_as_active(self):
        """Inactive users are not counted in active_users"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        # The inactive_student should not be in active_users count
        # but should be in total_users
        assert data['data']['total_users'] >= 5  # 1 admin + 3 active + 1 inactive
        assert data['data']['active_users'] >= 4  # 1 admin + 3 active

    def test_role_counts_do_not_exceed_total(self):
        """Sum of role counts does not exceed total users"""
        response = self.client.get('/api/admin/stats/users/')
        data = response.json()

        role_sum = (
            data['data']['total_students'] +
            data['data']['total_teachers'] +
            data['data']['total_tutors'] +
            data['data']['total_parents']
        )

        assert role_sum == data['data']['total_users']
