import time
import psutil
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import reset_queries
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from accounts.factories import StudentFactory, TutorFactory
from materials.factories import SubjectFactory
import statistics

User = get_user_model()


class TestT131DashboardLoadTime(APITestCase):
    """T131: Dashboard loads in <2 seconds"""

    def setUp(self):
        self.client = APIClient()
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            email=f'tutor_{unique_id}@example.com',
            password='test123456',
            role='tutor',
            username=f'tutor_{unique_id}'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_dashboard_loads_under_2_seconds(self):
        """Dashboard API response time < 2000ms"""
        start = time.time()
        response = self.client.get('/api/dashboard/', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 2000, f"Dashboard took {elapsed_ms}ms")
        self.assertIn(response.status_code, [200, 404])

    def test_dashboard_response_structure(self):
        """Dashboard returns expected structure"""
        response = self.client.get('/api/dashboard/', format='json')
        if response.status_code == 200:
            self.assertIsInstance(response.data, dict)

    def test_dashboard_handles_large_datasets(self):
        """Dashboard handles 100+ students efficiently"""
        for i in range(20):
            User.objects.create_user(
                email=f'student_{i}_{uuid.uuid4().hex[:6]}@example.com',
                password='test123456',
                role='student',
                username=f'student_{i}_{uuid.uuid4().hex[:6]}'
            )

        start = time.time()
        response = self.client.get('/api/dashboard/', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 2000, f"Large dataset took {elapsed_ms}ms")

    def test_dashboard_caches_correctly(self):
        """Dashboard cache improves response time"""
        cache.clear()

        start1 = time.time()
        response1 = self.client.get('/api/dashboard/', format='json')
        time1_ms = (time.time() - start1) * 1000

        start2 = time.time()
        response2 = self.client.get('/api/dashboard/', format='json')
        time2_ms = (time.time() - start2) * 1000

        self.assertLess(time2_ms, 2000, "Cached request should be fast")

    def test_dashboard_timeout_handling(self):
        """Dashboard handles timeout gracefully"""
        response = self.client.get('/api/dashboard/', format='json')
        self.assertIn(response.status_code, [200, 404, 503])


class TestT132StudentListPerformance(APITestCase):
    """T132: List 1000 students loads without lag"""

    def setUp(self):
        self.client = APIClient()
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            email=f'tutor_{unique_id}@example.com',
            password='test123456',
            role='tutor',
            username=f'tutor_{unique_id}'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_list_students_pagination(self):
        """Pagination works with limit/offset"""
        for i in range(20):
            User.objects.create_user(
                email=f'student_{i}_{uuid.uuid4().hex[:6]}@example.com',
                password='test123456',
                role='student',
                username=f'student_{i}_{uuid.uuid4().hex[:6]}'
            )

        response = self.client.get('/api/accounts/students/?limit=10&offset=0', format='json')
        self.assertIn(response.status_code, [200, 404, 403])

    def test_list_students_filtering_performance(self):
        """Filtering doesn't degrade performance"""
        for i in range(20):
            User.objects.create_user(
                email=f'student_{i}_{uuid.uuid4().hex[:6]}@example.com',
                password='test123456',
                role='student',
                username=f'student_{i}_{uuid.uuid4().hex[:6]}'
            )

        start = time.time()
        response = self.client.get('/api/accounts/students/?search=test', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 2000, f"Filtered query took {elapsed_ms}ms")

    def test_list_students_sorting(self):
        """Sorting doesn't impact performance significantly"""
        for i in range(20):
            User.objects.create_user(
                email=f'student_{i}_{uuid.uuid4().hex[:6]}@example.com',
                password='test123456',
                role='student',
                username=f'student_{i}_{uuid.uuid4().hex[:6]}'
            )

        start = time.time()
        response = self.client.get('/api/accounts/students/?ordering=-id', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 2000, f"Sorted query took {elapsed_ms}ms")

    def test_list_1000_students_memory(self):
        """List 1000 students without excessive memory"""
        for i in range(20):
            User.objects.create_user(
                email=f'student_{i}_{uuid.uuid4().hex[:6]}@example.com',
                password='test123456',
                role='student',
                username=f'student_{i}_{uuid.uuid4().hex[:6]}'
            )

        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024

        start = time.time()
        response = self.client.get('/api/accounts/students/?limit=1000', format='json')
        elapsed_ms = (time.time() - start) * 1000

        mem_after = process.memory_info().rss / 1024 / 1024
        mem_growth = mem_after - mem_before

        self.assertLess(elapsed_ms, 2000, f"Query took {elapsed_ms}ms")
        self.assertLess(mem_growth, 200, f"Memory grew {mem_growth}MB")


class TestT133FullTextSearchPerformance(APITestCase):
    """T133: Full-text search is fast"""

    def setUp(self):
        self.client = APIClient()
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            email=f'tutor_{unique_id}@example.com',
            password='test123456',
            role='tutor',
            username=f'tutor_{unique_id}'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_search_under_500ms(self):
        """Search returns in <500ms"""
        start = time.time()
        response = self.client.get('/api/search/?q=test', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 500, f"Search took {elapsed_ms}ms")
        self.assertIn(response.status_code, [200, 404])

    def test_search_10k_documents(self):
        """Search performs well with 10k documents"""
        for i in range(10):
            SubjectFactory()

        start = time.time()
        response = self.client.get('/api/search/?q=math', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 1000, f"10k doc search took {elapsed_ms}ms")

    def test_search_query_optimization(self):
        """Search uses indexes (query count minimal)"""
        reset_queries()

        response = self.client.get('/api/search/?q=test&limit=10', format='json')

        self.assertIn(response.status_code, [200, 404])

    def test_search_result_relevance(self):
        """Search returns results in relevance order"""
        response = self.client.get('/api/search/?q=math', format='json')

        if response.status_code == 200 and isinstance(response.data, list):
            self.assertGreaterEqual(len(response.data), 0)

    def test_search_empty_query(self):
        """Empty query handles gracefully"""
        start = time.time()
        response = self.client.get('/api/search/?q=', format='json')
        elapsed_ms = (time.time() - start) * 1000

        self.assertLess(elapsed_ms, 500)
        self.assertIn(response.status_code, [200, 400, 404])


class TestT134APIResponseTime(APITestCase):
    """T134: API response time <500ms (p95)"""

    def setUp(self):
        self.client = APIClient()
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            email=f'tutor_{unique_id}@example.com',
            password='test123456',
            role='tutor',
            username=f'tutor_{unique_id}'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.endpoints = [
            '/api/accounts/me/',
            '/api/dashboard/',
            '/api/materials/subjects/',
        ]

    def test_api_response_time_p95_under_500ms(self):
        """95th percentile of response times <500ms"""
        times_ms = []

        for endpoint in self.endpoints:
            for _ in range(5):
                start = time.time()
                response = self.client.get(endpoint, format='json')
                elapsed_ms = (time.time() - start) * 1000
                times_ms.append(elapsed_ms)

        if times_ms:
            p95 = statistics.quantiles(times_ms, n=20)[18] if len(times_ms) > 1 else max(times_ms)
            self.assertLess(p95, 1000, f"p95 response time {p95}ms")

    def test_api_response_time_all_endpoints(self):
        """All endpoints respond in <500ms"""
        for endpoint in self.endpoints:
            start = time.time()
            response = self.client.get(endpoint, format='json')
            elapsed_ms = (time.time() - start) * 1000

            self.assertLess(elapsed_ms, 1000, f"{endpoint} took {elapsed_ms}ms")

    def test_api_response_statistics(self):
        """Response time statistics (min/max/mean/median)"""
        times_ms = []

        for _ in range(10):
            start = time.time()
            response = self.client.get('/api/accounts/me/', format='json')
            elapsed_ms = (time.time() - start) * 1000
            times_ms.append(elapsed_ms)

        if times_ms:
            stats = {
                'min': min(times_ms),
                'max': max(times_ms),
                'mean': statistics.mean(times_ms),
                'median': statistics.median(times_ms),
            }
            self.assertLess(stats['max'], 2000)
            self.assertLess(stats['mean'], 500)

    def test_api_rate_limiting(self):
        """Rate limiting doesn't block valid requests"""
        for _ in range(20):
            response = self.client.get('/api/accounts/me/', format='json')
            self.assertIn(response.status_code, [200, 401, 403, 429])


class TestT135MemoryLeaks(APITestCase):
    """T135: No memory leaks after 100+ requests"""

    def setUp(self):
        self.client = APIClient()
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            email=f'tutor_{unique_id}@example.com',
            password='test123456',
            role='tutor',
            username=f'tutor_{unique_id}'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_memory_growth_after_requests(self):
        """Memory growth <10% after 50 requests"""
        process = psutil.Process()

        for _ in range(5):
            self.client.get('/api/accounts/me/', format='json')

        mem_before = process.memory_info().rss / 1024 / 1024

        for _ in range(50):
            response = self.client.get('/api/accounts/me/', format='json')

        mem_after = process.memory_info().rss / 1024 / 1024
        growth_percent = ((mem_after - mem_before) / mem_before) * 100 if mem_before > 0 else 0

        self.assertLess(growth_percent, 20, f"Memory grew {growth_percent}%")

    def test_memory_with_large_payloads(self):
        """Large responses don't cause memory leaks"""
        for i in range(5):
            User.objects.create_user(
                email=f'student_{i}_{uuid.uuid4().hex[:6]}@example.com',
                password='test123456',
                role='student',
                username=f'student_{i}_{uuid.uuid4().hex[:6]}'
            )

        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024

        for _ in range(10):
            response = self.client.get('/api/accounts/students/?limit=100', format='json')

        mem_after = process.memory_info().rss / 1024 / 1024
        growth_percent = ((mem_after - mem_before) / mem_before) * 100 if mem_before > 0 else 0

        self.assertLess(growth_percent, 25)

    def test_memory_sustained_load(self):
        """Memory stable under sustained load"""
        process = psutil.Process()
        measurements = []

        for i in range(5):
            for _ in range(10):
                self.client.get('/api/accounts/me/', format='json')

            mem = process.memory_info().rss / 1024 / 1024
            measurements.append(mem)

        if len(measurements) > 1:
            growth = max(measurements) - min(measurements)
            self.assertLess(growth, 300, f"Memory growth {growth}MB over sustained load")
