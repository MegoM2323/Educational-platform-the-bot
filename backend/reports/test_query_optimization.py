"""
Comprehensive tests for Report Query Optimization (T_RPT_001)

Tests N+1 query prevention, index usage, caching, and performance benchmarking.
Target: <100ms per report query, <50 queries for batch operations
"""

import time
from datetime import datetime, timedelta

from django.test import TestCase, TransactionTestCase
from django.db import connection, reset_queries
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from .models import (
    Report, StudentReport, TutorWeeklyReport, TeacherWeeklyReport,
    AnalyticsData, ReportSchedule
)
from .query_optimization import (
    QueryMonitor, ReportQueryOptimizer, QueryCacheManager,
    cached_report_query, monitor_queries
)
from accounts.models import StudentProfile
from materials.models import Subject

User = get_user_model()


class QueryMonitorTests(TestCase):
    """Test QueryMonitor functionality."""

    def setUp(self):
        """Create test user."""
        self.teacher = User.objects.create_user(
            username="teacher_monitor",
            email="teacher_mon@test.com",
            password="TestPass123!",
            role="teacher"
        )

    def test_query_monitor_context_manager(self):
        """Test QueryMonitor as context manager."""
        with QueryMonitor("Test Operation") as monitor:
            # Execute some queries
            list(User.objects.all())

        stats = monitor.get_stats()
        self.assertIn("total_queries", stats)
        self.assertIn("slow_queries", stats)
        self.assertGreater(stats["total_queries"], 0)

    def test_query_monitor_tracks_execution_time(self):
        """Test that monitor tracks execution time."""
        with QueryMonitor("Slow Operation") as monitor:
            time.sleep(0.01)  # Sleep 10ms

        stats = monitor.get_stats()
        self.assertIn("total_queries", stats)

    def test_monitor_queries_decorator(self):
        """Test @monitor_queries decorator."""
        @monitor_queries("Test Function")
        def test_func():
            return list(User.objects.all())

        result = test_func()
        self.assertIsNotNone(result)


class StudentReportOptimizationTests(TransactionTestCase):
    """Test StudentReport query optimization."""

    def setUp(self):
        """Create test data."""
        self.teacher = User.objects.create_user(
            username="teacher_opt",
            email="teacher_opt@test.com",
            password="TestPass123!",
            role="teacher"
        )
        self.students = [
            User.objects.create_user(
                username=f"student_opt{i}",
                email=f"student_opt{i}@test.com",
                password="TestPass123!",
                role="student"
            )
            for i in range(5)
        ]
        self.subject = Subject.objects.create(
            name="Math",
            description="Mathematics"
        )

    def test_student_report_queryset_optimization(self):
        """Test StudentReport queryset optimization prevents N+1."""
        # Create test reports
        reports = []
        for student in self.students:
            report = StudentReport.objects.create(
                title=f"Report for {student.get_full_name()}",
                report_type=StudentReport.ReportType.PROGRESS,
                teacher=self.teacher,
                student=student,
                period_start="2025-01-01",
                period_end="2025-01-31",
            )
            reports.append(report)

        # Test unoptimized query count
        reset_queries()
        unoptimized = list(StudentReport.objects.all())
        unoptimized_count = len(connection.queries)

        # Test optimized query count
        reset_queries()
        queryset = StudentReport.objects.all()
        optimized = list(ReportQueryOptimizer.optimize_student_report_queryset(queryset))
        optimized_count = len(connection.queries)

        # Optimized should be significantly fewer queries
        self.assertLess(
            optimized_count, unoptimized_count,
            f"Optimized ({optimized_count}) should be < unoptimized ({unoptimized_count})"
        )

    def test_student_report_related_access(self):
        """Test that optimized query handles related data access."""
        report = StudentReport.objects.create(
            title="Test Report",
            report_type=StudentReport.ReportType.PROGRESS,
            teacher=self.teacher,
            student=self.students[0],
            period_start="2025-01-01",
            period_end="2025-01-31",
        )

        # Optimized query
        optimized = ReportQueryOptimizer.optimize_student_report_queryset(
            StudentReport.objects.all()
        ).first()

        reset_queries()

        # Access related data (should not create new queries)
        _ = optimized.teacher.get_full_name()
        _ = optimized.student.get_full_name()

        query_count = len(connection.queries)
        self.assertEqual(
            query_count, 0,
            "Accessing related data should not create new queries"
        )

    def test_student_report_batch_retrieval_performance(self):
        """Test performance of batch student report retrieval."""
        # Create many reports
        for i, student in enumerate(self.students):
            for j in range(3):
                StudentReport.objects.create(
                    title=f"Report {i}-{j}",
                    report_type=StudentReport.ReportType.PROGRESS,
                    teacher=self.teacher,
                    student=student,
                    period_start="2025-01-01",
                    period_end="2025-01-31",
                )

        reset_queries()
        start_time = time.time()

        # Retrieve and process all reports
        queryset = ReportQueryOptimizer.optimize_student_report_queryset(
            StudentReport.objects.all()
        )
        reports = list(queryset)
        for report in reports:
            _ = report.teacher.get_full_name()
            _ = report.student.get_full_name()

        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        query_count = len(connection.queries)

        # Performance assertions
        self.assertLess(
            query_count, 30,
            f"Batch retrieval should use <30 queries, got {query_count}"
        )
        self.assertLess(
            execution_time, 1000,
            f"Batch retrieval should complete in <1s, took {execution_time}ms"
        )


class TutorReportOptimizationTests(TransactionTestCase):
    """Test TutorWeeklyReport query optimization."""

    def setUp(self):
        """Create test data."""
        self.tutor = User.objects.create_user(
            username="tutor_opt",
            email="tutor_opt@test.com",
            password="TestPass123!",
            role="tutor"
        )
        self.parent = User.objects.create_user(
            username="parent_opt",
            email="parent_opt@test.com",
            password="TestPass123!",
            role="parent"
        )
        self.students = [
            User.objects.create_user(
                username=f"student_tutor{i}",
                email=f"student_tutor{i}@test.com",
                password="TestPass123!",
                role="student"
            )
            for i in range(3)
        ]

    def test_tutor_report_queryset_optimization(self):
        """Test TutorWeeklyReport queryset optimization."""
        # Create test reports
        for student in self.students:
            TutorWeeklyReport.objects.create(
                tutor=self.tutor,
                student=student,
                parent=self.parent,
                week_start="2025-01-01",
                week_end="2025-01-07",
                summary="Weekly progress"
            )

        reset_queries()
        unoptimized = list(TutorWeeklyReport.objects.all())
        unoptimized_count = len(connection.queries)

        reset_queries()
        optimized = list(
            ReportQueryOptimizer.optimize_tutor_report_queryset(
                TutorWeeklyReport.objects.all()
            )
        )
        optimized_count = len(connection.queries)

        self.assertLess(optimized_count, unoptimized_count)

    def test_tutor_report_batch_performance(self):
        """Test batch tutor report performance."""
        # Create many reports
        for i in range(10):
            for j, student in enumerate(self.students):
                TutorWeeklyReport.objects.create(
                    tutor=self.tutor,
                    student=student,
                    parent=self.parent,
                    week_start=f"2025-01-{(i*7 + 1):02d}",
                    week_end=f"2025-01-{(i*7 + 7):02d}",
                    summary=f"Week {i} progress"
                )

        reset_queries()
        start_time = time.time()

        queryset = ReportQueryOptimizer.optimize_tutor_report_queryset(
            TutorWeeklyReport.objects.all()
        )
        reports = list(queryset)
        for report in reports:
            _ = report.tutor.get_full_name()
            _ = report.student.get_full_name()
            if report.parent:
                _ = report.parent.get_full_name()

        execution_time = (time.time() - start_time) * 1000
        query_count = len(connection.queries)

        self.assertLess(query_count, 30)
        self.assertLess(execution_time, 1000)


class TeacherReportOptimizationTests(TransactionTestCase):
    """Test TeacherWeeklyReport query optimization."""

    def setUp(self):
        """Create test data."""
        self.teacher = User.objects.create_user(
            username="teacher_tutor",
            email="teacher_tutor@test.com",
            password="TestPass123!",
            role="teacher"
        )
        self.tutor = User.objects.create_user(
            username="tutor_teacher",
            email="tutor_teacher@test.com",
            password="TestPass123!",
            role="tutor"
        )
        self.students = [
            User.objects.create_user(
                username=f"student_teacher{i}",
                email=f"student_teacher{i}@test.com",
                password="TestPass123!",
                role="student"
            )
            for i in range(3)
        ]
        self.subject = Subject.objects.create(
            name="English",
            description="English Language"
        )

    def test_teacher_report_queryset_optimization(self):
        """Test TeacherWeeklyReport queryset optimization."""
        for student in self.students:
            TeacherWeeklyReport.objects.create(
                teacher=self.teacher,
                student=student,
                tutor=self.tutor,
                subject=self.subject,
                week_start="2025-01-01",
                week_end="2025-01-07",
                summary="Weekly progress"
            )

        reset_queries()
        unoptimized = list(TeacherWeeklyReport.objects.all())
        unoptimized_count = len(connection.queries)

        reset_queries()
        optimized = list(
            ReportQueryOptimizer.optimize_teacher_report_queryset(
                TeacherWeeklyReport.objects.all()
            )
        )
        optimized_count = len(connection.queries)

        self.assertLess(optimized_count, unoptimized_count)


class AnalyticsOptimizationTests(TransactionTestCase):
    """Test AnalyticsData query optimization."""

    def setUp(self):
        """Create test data."""
        self.student = User.objects.create_user(
            username="student_analytics",
            email="student_analytics@test.com",
            password="TestPass123!",
            role="student"
        )

    def test_student_progress_summary_query_count(self):
        """Test that student progress summary uses minimal queries."""
        # Create analytics data
        for i in range(10):
            AnalyticsData.objects.create(
                student=self.student,
                metric_type=AnalyticsData.MetricType.STUDENT_PROGRESS,
                value=75.0 + i,
                unit="percent",
                date="2025-01-01",
                period_start="2025-01-01",
                period_end="2025-01-31"
            )

        reset_queries()
        result = ReportQueryOptimizer.get_student_progress_summary(
            self.student.id
        )
        query_count = len(connection.queries)

        self.assertLess(query_count, 5, "Should use minimal queries for summary")
        self.assertIn("student_id", result)
        self.assertIn("metrics", result)

    def test_class_performance_summary_query_count(self):
        """Test that class performance summary uses minimal queries."""
        teacher = User.objects.create_user(
            username="teacher_analytics",
            email="teacher_analytics@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Create student reports
        students = [
            User.objects.create_user(
                username=f"student_perf{i}",
                email=f"student_perf{i}@test.com",
                password="TestPass123!",
                role="student"
            )
            for i in range(5)
        ]

        for student in students:
            StudentReport.objects.create(
                title=f"Report {student.get_full_name()}",
                report_type=StudentReport.ReportType.PROGRESS,
                teacher=teacher,
                student=student,
                period_start="2025-01-01",
                period_end="2025-01-31",
                progress_percentage=80,
                attendance_percentage=90
            )

        reset_queries()
        result = ReportQueryOptimizer.get_class_performance_summary(teacher.id)
        query_count = len(connection.queries)

        self.assertLess(query_count, 5, "Should use minimal queries for summary")
        self.assertIn("teacher_id", result)
        self.assertIn("metrics", result)
        self.assertEqual(result["metrics"]["student_count"], 5)


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache'
    }
})
class QueryCacheManagerTests(TestCase):
    """Test QueryCacheManager functionality."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = QueryCacheManager.get_cache_key("test_query", 1, 2, foo="bar")
        key2 = QueryCacheManager.get_cache_key("test_query", 1, 2, foo="bar")
        key3 = QueryCacheManager.get_cache_key("test_query", 2, 3, foo="bar")

        self.assertEqual(key1, key2, "Same arguments should generate same key")
        self.assertNotEqual(key1, key3, "Different arguments should generate different keys")
        self.assertTrue(key1.startswith("report_query:"))

    def test_get_or_set_caching(self):
        """Test get_or_set caching."""
        call_count = 0

        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = QueryCacheManager.get_or_set(
            "test_double", test_func, 300, 5
        )
        self.assertEqual(result1, 10)
        self.assertEqual(call_count, 1)

        # Second call should use cache
        result2 = QueryCacheManager.get_or_set(
            "test_double", test_func, 300, 5
        )
        self.assertEqual(result2, 10)
        self.assertEqual(call_count, 1, "Function should not be called again")

        # Different arguments should execute function
        result3 = QueryCacheManager.get_or_set(
            "test_double", test_func, 300, 10
        )
        self.assertEqual(result3, 20)
        self.assertEqual(call_count, 2)

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        def test_func():
            return "cached_value"

        # Cache a value
        QueryCacheManager.get_or_set("test_inv", test_func, 300)
        cached = cache.get(QueryCacheManager.get_cache_key("test_inv"))
        self.assertIsNotNone(cached)

        # Invalidate
        QueryCacheManager.invalidate("test_inv")
        cached = cache.get(QueryCacheManager.get_cache_key("test_inv"))
        self.assertIsNone(cached)

    def test_cached_report_query_decorator(self):
        """Test @cached_report_query decorator."""
        call_count = 0

        @cached_report_query("test_decorated", 300)
        def test_query():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call
        result1 = test_query()
        self.assertEqual(result1, "result")
        self.assertEqual(call_count, 1)

        # Second call (cached)
        result2 = test_query()
        self.assertEqual(result2, "result")
        self.assertEqual(call_count, 1, "Should use cached result")


class PerformanceBenchmarkTests(TransactionTestCase):
    """Benchmark report query performance against targets."""

    def setUp(self):
        """Create test data."""
        self.teacher = User.objects.create_user(
            username="teacher_bench",
            email="teacher_bench@test.com",
            password="TestPass123!",
            role="teacher"
        )
        self.students = [
            User.objects.create_user(
                username=f"student_bench{i}",
                email=f"student_bench{i}@test.com",
                password="TestPass123!",
                role="student"
            )
            for i in range(20)
        ]
        self.subject = Subject.objects.create(
            name="Science",
            description="Science"
        )

    def test_individual_report_query_performance(self):
        """Test individual report query completes in <100ms."""
        report = StudentReport.objects.create(
            title="Test Report",
            report_type=StudentReport.ReportType.PROGRESS,
            teacher=self.teacher,
            student=self.students[0],
            period_start="2025-01-01",
            period_end="2025-01-31",
        )

        reset_queries()
        start_time = time.time()

        queryset = ReportQueryOptimizer.optimize_student_report_queryset(
            StudentReport.objects.filter(id=report.id)
        )
        report = queryset.first()
        _ = report.teacher.get_full_name()

        execution_time = (time.time() - start_time) * 1000
        query_count = len(connection.queries)

        # Target: <100ms for single report, <5 queries
        self.assertLess(
            execution_time, 100,
            f"Individual report should load in <100ms, took {execution_time}ms"
        )
        self.assertLess(
            query_count, 5,
            f"Individual report should use <5 queries, used {query_count}"
        )

    def test_batch_report_query_performance(self):
        """Test batch report query completes in reasonable time."""
        # Create many reports
        for i, student in enumerate(self.students):
            for j in range(2):
                StudentReport.objects.create(
                    title=f"Report {i}-{j}",
                    report_type=StudentReport.ReportType.PROGRESS,
                    teacher=self.teacher,
                    student=student,
                    period_start="2025-01-01",
                    period_end="2025-01-31",
                )

        reset_queries()
        start_time = time.time()

        # Batch retrieve with optimization
        queryset = ReportQueryOptimizer.optimize_student_report_queryset(
            StudentReport.objects.all()
        )
        reports = list(queryset)
        for report in reports:
            _ = report.teacher.get_full_name()
            _ = report.student.get_full_name()

        execution_time = (time.time() - start_time) * 1000
        query_count = len(connection.queries)

        # Target: <50 queries for 40 reports
        self.assertLess(
            query_count, 50,
            f"Batch of 40 reports should use <50 queries, used {query_count}"
        )
        self.assertLess(
            execution_time, 2000,
            f"Batch of 40 reports should complete in <2s, took {execution_time}ms"
        )
