"""
Report Query Optimization Module

Provides tools for optimizing database queries in report generation:
- N+1 query detection and prevention
- Query monitoring and logging
- Composite index strategies
- Performance benchmarking
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Dict, List

from django.db import connection, reset_queries
from django.db.models import QuerySet, Prefetch, Q, F, Count, Avg, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class QueryMonitor:
    """
    Monitor and log database query performance.
    Tracks query count, execution time, and slow query detection.
    """

    SLOW_QUERY_THRESHOLD = 1.0  # seconds

    def __init__(self, operation_name: str = "Operation"):
        """
        Initialize query monitor.

        Args:
            operation_name: Name of the operation being monitored
        """
        self.operation_name = operation_name
        self.start_queries = 0
        self.start_time = 0
        self.queries = []

    def __enter__(self):
        """Context manager entry."""
        reset_queries()
        self.start_queries = len(connection.queries)
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit. Log results."""
        execution_time = time.time() - self.start_time
        total_queries = len(connection.queries) - self.start_queries
        self.queries = connection.queries[self.start_queries:]

        # Log query statistics
        log_data = {
            "operation": self.operation_name,
            "total_queries": total_queries,
            "execution_time_ms": round(execution_time * 1000, 2),
            "slow_queries": self._count_slow_queries(),
        }

        logger.info(f"Query Monitor: {log_data}")

        # Log slow queries
        if execution_time > self.SLOW_QUERY_THRESHOLD:
            logger.warning(
                f"Slow query detected in {self.operation_name}: "
                f"{execution_time:.3f}s ({total_queries} queries)"
            )
            self._log_slow_queries()

    def _count_slow_queries(self) -> int:
        """Count queries slower than threshold."""
        count = 0
        for query in self.queries:
            if float(query.get("time", 0)) > 0.1:  # 100ms threshold
                count += 1
        return count

    def _log_slow_queries(self):
        """Log individual slow queries."""
        for query in self.queries:
            if float(query.get("time", 0)) > 0.1:
                logger.warning(f"  Slow Query ({query['time']}s): {query['sql'][:100]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        return {
            "total_queries": len(self.queries),
            "slow_queries": self._count_slow_queries(),
            "queries": [
                {
                    "sql": q["sql"][:200],
                    "time": float(q.get("time", 0)),
                }
                for q in self.queries
            ],
        }


def monitor_queries(operation_name: str = "Database Operation") -> Callable:
    """
    Decorator to monitor database queries in a function.

    Args:
        operation_name: Name of the operation being monitored

    Returns:
        Decorated function that monitors queries
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with QueryMonitor(operation_name or func.__name__) as monitor:
                result = func(*args, **kwargs)
            # Attach stats to result if possible
            if hasattr(result, "_query_stats"):
                result._query_stats = monitor.get_stats()
            return result

        return wrapper

    return decorator


class ReportQueryOptimizer:
    """
    Optimize common report queries using select_related/prefetch_related.
    """

    @staticmethod
    def optimize_student_report_queryset(queryset: QuerySet) -> QuerySet:
        """
        Optimize StudentReport queryset with related data.

        Prevents N+1 queries when accessing:
        - teacher, student, parent, tutor (ForeignKeys)
        - related submissions and grades
        """
        return (
            queryset
            .select_related(
                "teacher",
                "student",
                "parent",
                "tutor",
            )
            .prefetch_related(
                "student__student_profile__tutor",
            )
            .annotate(
                subject_count=Count("student__student_reports", distinct=True),
            )
        )

    @staticmethod
    def optimize_tutor_report_queryset(queryset: QuerySet) -> QuerySet:
        """
        Optimize TutorWeeklyReport queryset with related data.

        Prevents N+1 queries when accessing:
        - tutor, student, parent (ForeignKeys)
        - student profile and relationships
        """
        return (
            queryset
            .select_related(
                "tutor",
                "student",
                "parent",
            )
            .prefetch_related(
                "student__student_profile",
                "student__student_profile__parent",
            )
        )

    @staticmethod
    def optimize_teacher_report_queryset(queryset: QuerySet) -> QuerySet:
        """
        Optimize TeacherWeeklyReport queryset with related data.

        Prevents N+1 queries when accessing:
        - teacher, student, tutor, subject (ForeignKeys)
        - student profile and relationships
        """
        return (
            queryset
            .select_related(
                "teacher",
                "student",
                "tutor",
                "subject",
            )
            .prefetch_related(
                "student__student_profile",
                "student__student_profile__tutor",
            )
        )

    @staticmethod
    def optimize_report_queryset(queryset: QuerySet) -> QuerySet:
        """
        Optimize Report queryset with related data and annotations.

        Prevents N+1 queries when accessing:
        - author, target_students, target_parents (ForeignKeys and M2M)
        - recipient counts
        """
        return (
            queryset
            .select_related("author")
            .prefetch_related(
                "target_students",
                "target_parents",
                Prefetch(
                    "recipients",
                    queryset=connection.queries,  # Placeholder for performance
                ),
            )
            .annotate(
                target_students_count=Count("target_students", distinct=True),
                target_parents_count=Count("target_parents", distinct=True),
                recipients_count=Count("recipients", distinct=True),
            )
        )

    @staticmethod
    def optimize_analytics_queryset(
        queryset: QuerySet, student_id: int = None
    ) -> QuerySet:
        """
        Optimize AnalyticsData queryset for student progress reporting.

        Args:
            queryset: Base AnalyticsData queryset
            student_id: Optional filter for specific student

        Returns:
            Optimized queryset with annotations
        """
        qs = queryset.select_related("student")

        if student_id:
            qs = qs.filter(student_id=student_id)

        return qs.annotate(
            avg_value=Avg("value"),
            max_value=Avg("value"),
            min_value=Avg("value"),
        ).order_by("-date")

    @staticmethod
    def get_student_progress_summary(
        student_id: int, period_start=None, period_end=None
    ) -> Dict[str, Any]:
        """
        Get student progress summary with optimized queries.

        Args:
            student_id: Student user ID
            period_start: Optional start date for period
            period_end: Optional end date for period

        Returns:
            Dictionary with progress metrics
        """
        from .models import AnalyticsData

        with QueryMonitor(f"Student Progress Summary (student_id={student_id})"):
            # Single query with aggregation
            queryset = AnalyticsData.objects.filter(student_id=student_id)

            if period_start:
                queryset = queryset.filter(date__gte=period_start)
            if period_end:
                queryset = queryset.filter(date__lte=period_end)

            stats = queryset.values("metric_type").annotate(
                avg_value=Avg("value"),
                max_value=Avg("value"),
                latest_value=Coalesce(
                    Avg("value"), 0.0, output_field=DecimalField()
                ),
                count=Count("id"),
            )

            return {
                "student_id": student_id,
                "period_start": period_start,
                "period_end": period_end,
                "metrics": list(stats),
            }

    @staticmethod
    def get_class_performance_summary(
        teacher_id: int, period_start=None, period_end=None
    ) -> Dict[str, Any]:
        """
        Get class performance summary with optimized queries.

        Args:
            teacher_id: Teacher user ID
            period_start: Optional start date for period
            period_end: Optional end date for period

        Returns:
            Dictionary with class metrics
        """
        from .models import StudentReport

        with QueryMonitor(f"Class Performance Summary (teacher_id={teacher_id})"):
            # Single query with annotations
            queryset = StudentReport.objects.filter(teacher_id=teacher_id)

            if period_start:
                queryset = queryset.filter(period_start__gte=period_start)
            if period_end:
                queryset = queryset.filter(period_end__lte=period_end)

            stats = queryset.aggregate(
                student_count=Count("student", distinct=True),
                avg_progress=Avg("progress_percentage"),
                avg_attendance=Avg("attendance_percentage"),
                avg_behavior=Avg("behavior_rating"),
                total_reports=Count("id"),
            )

            return {
                "teacher_id": teacher_id,
                "period_start": period_start,
                "period_end": period_end,
                "metrics": stats,
            }


class QueryCacheManager:
    """
    Cache report queries with automatic invalidation.
    """

    CACHE_PREFIX = "report_query:"
    DEFAULT_TTL = 300  # 5 minutes

    @classmethod
    def get_cache_key(cls, query_name: str, *args, **kwargs) -> str:
        """Generate cache key from query name and arguments."""
        import hashlib

        key_data = f"{query_name}:{str(args)}:{str(kwargs)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{cls.CACHE_PREFIX}{key_hash}"

    @classmethod
    def get_or_set(
        cls, query_name: str, query_func: Callable, ttl: int = DEFAULT_TTL, *args,
        **kwargs
    ) -> Any:
        """
        Get cached query result or execute and cache.

        Args:
            query_name: Name of the query (for cache key)
            query_func: Callable that returns query result
            ttl: Cache time-to-live in seconds
            *args, **kwargs: Arguments to pass to query_func

        Returns:
            Query result (cached or fresh)
        """
        cache_key = cls.get_cache_key(query_name, *args, **kwargs)

        # Try to get from cache
        result = cache.get(cache_key)
        if result is not None:
            logger.debug(f"Cache hit: {query_name}")
            return result

        # Execute query
        logger.debug(f"Cache miss: {query_name}")
        result = query_func(*args, **kwargs)

        # Cache result
        cache.set(cache_key, result, ttl)
        return result

    @classmethod
    def invalidate(cls, query_name: str, *args, **kwargs):
        """Invalidate cached query result."""
        cache_key = cls.get_cache_key(query_name, *args, **kwargs)
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated: {query_name}")

    @classmethod
    def invalidate_pattern(cls, pattern: str):
        """Invalidate all cache entries matching pattern."""
        import redis

        try:
            r = cache._cache
            if isinstance(r, redis.Redis):
                keys = r.keys(f"{cls.CACHE_PREFIX}{pattern}*")
                for key in keys:
                    r.delete(key)
                logger.debug(f"Invalidated cache pattern: {pattern}")
        except (AttributeError, ImportError):
            logger.warning("Redis not available for pattern invalidation")

    @classmethod
    def clear_all(cls):
        """Clear all report query cache."""
        import redis

        try:
            r = cache._cache
            if isinstance(r, redis.Redis):
                keys = r.keys(f"{cls.CACHE_PREFIX}*")
                for key in keys:
                    r.delete(key)
                logger.debug("Cleared all report query cache")
        except (AttributeError, ImportError):
            logger.warning("Redis not available for cache clearing")


def cached_report_query(
    query_name: str = None, ttl: int = QueryCacheManager.DEFAULT_TTL
) -> Callable:
    """
    Decorator to cache report queries.

    Args:
        query_name: Name for cache key (defaults to function name)
        ttl: Cache time-to-live in seconds

    Returns:
        Decorated function with caching
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = query_name or func.__name__
            return QueryCacheManager.get_or_set(
                name, func, ttl, *args, **kwargs
            )

        return wrapper

    return decorator
