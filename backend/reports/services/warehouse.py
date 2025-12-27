"""
Data Warehouse Service for Large-Scale Analytics.

Features:
- Materialized views for common aggregations
- Optimized raw SQL queries with pagination
- Read replica routing (if available)
- Query result caching (1 hour)
- Query timeout handling (30 seconds)
- Execution time logging and monitoring

Usage:
    from reports.services.warehouse import DataWarehouseService

    # Get student progress
    warehouse = DataWarehouseService()
    progress = warehouse.get_student_progress_over_time(
        student_id=123,
        granularity='week',
        days_back=30
    )
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db import connection, connections
from django.db.utils import DatabaseError, OperationalError
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class DataWarehouseService:
    """
    Service for executing large-scale analytics queries against data warehouse.

    Provides:
    - Query execution with timeout handling
    - Result caching (1 hour TTL)
    - Read replica routing
    - Query performance monitoring
    - Pagination support
    """

    # Query timeout (30 seconds)
    QUERY_TIMEOUT = 30

    # Result cache TTL (1 hour)
    CACHE_TTL = 3600

    # Max result set size (10,000 rows)
    MAX_RESULT_SIZE = 10000

    # Default pagination
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 10000

    def __init__(self, use_replica: bool = True):
        """
        Initialize warehouse service.

        Args:
            use_replica: Use read replica if available (default: True)
        """
        self.use_replica = use_replica
        self._replica_available = self._check_replica_availability()
        self.db_alias = self._get_db_alias()

    def _check_replica_availability(self) -> bool:
        """Check if read replica is configured and available."""
        if not self.use_replica:
            return False

        replica_alias = getattr(settings, 'REPORTING_DB_REPLICA', None)
        if not replica_alias or replica_alias not in connections.databases:
            return False

        try:
            with connections[replica_alias].cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except (DatabaseError, OperationalError):
            logger.warning(
                "Reporting database replica unavailable, falling back to primary"
            )
            return False

    def _get_db_alias(self) -> str:
        """Get database alias (replica or primary)."""
        if self._replica_available:
            replica_alias = getattr(settings, 'REPORTING_DB_REPLICA', None)
            if replica_alias:
                return replica_alias
        return 'default'

    def _get_cache_key(self, query_name: str, params: Tuple) -> str:
        """Generate cache key for query results."""
        # Create hash of query parameters
        import hashlib
        params_str = str(params)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"warehouse_{query_name}_{params_hash}"

    def _execute_query(
        self,
        sql: str,
        params: Tuple = (),
        timeout: Optional[int] = None,
        use_cache: bool = True,
        cache_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query with timeout, caching, and error handling.

        Args:
            sql: SQL query string
            params: Query parameters (tuple)
            timeout: Query timeout in seconds (default: 30)
            use_cache: Cache results (default: True)
            cache_key: Custom cache key

        Returns:
            List of result dictionaries

        Raises:
            DatabaseError: On query execution error
            TimeoutError: If query exceeds timeout
        """
        timeout = timeout or self.QUERY_TIMEOUT

        # Check cache
        if use_cache and cache_key:
            cached_results = cache.get(cache_key)
            if cached_results is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_results

        start_time = time.time()
        results = []

        try:
            # Get connection (replica or primary)
            db_connection = connections[self.db_alias]

            # Execute query with timeout
            with db_connection.cursor() as cursor:
                # Set statement timeout (PostgreSQL)
                if 'postgresql' in db_connection.settings_dict.get('ENGINE', ''):
                    cursor.execute(f"SET statement_timeout = {timeout * 1000};")

                # Execute main query
                cursor.execute(sql, params)

                # Fetch results
                columns = [col[0] for col in cursor.description or []]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

        except DatabaseError as e:
            # Handle query-specific errors
            if 'statement timeout' in str(e).lower():
                logger.error(f"Query timeout ({timeout}s): {sql[:100]}...")
                raise TimeoutError(f"Query exceeded {timeout}s timeout")

            logger.error(f"Database error executing query: {e}")
            raise

        except OperationalError as e:
            # Handle connection errors
            logger.error(f"Connection error: {e}")
            raise

        finally:
            # Log execution time
            execution_time = time.time() - start_time
            if execution_time > 1.0:
                logger.warning(
                    f"Slow query ({execution_time:.2f}s): {sql[:100]}..."
                )

        # Cache results
        if use_cache and cache_key and results:
            cache.set(cache_key, results, self.CACHE_TTL)
            logger.debug(f"Cached results for {cache_key} ({len(results)} rows)")

        # Warn if result set too large
        if len(results) >= self.MAX_RESULT_SIZE:
            logger.warning(
                f"Large result set ({len(results)} rows), consider pagination"
            )

        return results

    # ========================================================================
    # STUDENT ANALYTICS QUERIES
    # ========================================================================

    def get_student_progress_over_time(
        self,
        student_id: int,
        granularity: str = 'week',
        days_back: int = 30,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get student progress over time periods.

        Args:
            student_id: Student ID
            granularity: 'day', 'week', or 'month'
            days_back: Look back this many days
            limit: Maximum results (max 10,000)
            offset: Result offset for pagination

        Returns:
            {
                'periods': [...],
                'total_count': int,
                'limit': int,
                'offset': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import STUDENT_PROGRESS_OVER_TIME

        limit = min(limit, self.MAX_LIMIT)
        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()

        sql = STUDENT_PROGRESS_OVER_TIME.format(granularity=granularity)
        params = (student_id, start_date, end_date, limit, offset)

        cache_key = self._get_cache_key('student_progress', params)

        start_time = time.time()
        results = self._execute_query(sql, params, use_cache=True, cache_key=cache_key)
        execution_time = (time.time() - start_time) * 1000

        return {
            'student_id': student_id,
            'periods': results,
            'total_count': len(results),
            'limit': limit,
            'offset': offset,
            'granularity': granularity,
            'execution_time_ms': round(execution_time, 2)
        }

    def get_subject_performance_comparison(
        self,
        student_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Compare student performance across subjects.

        Args:
            student_id: Student ID
            limit: Maximum results
            offset: Result offset

        Returns:
            {
                'subjects': [...],
                'total_count': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import SUBJECT_PERFORMANCE_COMPARISON

        limit = min(limit, self.MAX_LIMIT)
        params = (student_id, limit, offset)

        cache_key = self._get_cache_key('subject_performance', params)

        start_time = time.time()
        results = self._execute_query(
            SUBJECT_PERFORMANCE_COMPARISON, params,
            use_cache=True, cache_key=cache_key
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            'student_id': student_id,
            'subjects': results,
            'total_count': len(results),
            'execution_time_ms': round(execution_time, 2)
        }

    def get_student_engagement_metrics(
        self,
        days_back: int = 30,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get engagement metrics for all students.

        Args:
            days_back: Look back this many days
            limit: Maximum results
            offset: Result offset

        Returns:
            {
                'students': [...],
                'total_count': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import STUDENT_ENGAGEMENT_METRICS

        limit = min(limit, self.MAX_LIMIT)
        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()
        days_in_period = days_back

        sql = STUDENT_ENGAGEMENT_METRICS.format(days_in_period=days_in_period)
        params = (start_date, end_date, limit, offset)

        cache_key = self._get_cache_key('student_engagement', params)

        start_time = time.time()
        results = self._execute_query(sql, params, use_cache=True, cache_key=cache_key)
        execution_time = (time.time() - start_time) * 1000

        return {
            'students': results,
            'total_count': len(results),
            'days_back': days_back,
            'execution_time_ms': round(execution_time, 2)
        }

    # ========================================================================
    # TEACHER ANALYTICS QUERIES
    # ========================================================================

    def get_teacher_workload_analysis(
        self,
        teacher_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze teacher review/grading workload.

        Args:
            teacher_id: Teacher ID
            days_back: Look back this many days

        Returns:
            {
                'teacher_id': int,
                'total_assignments': int,
                'pending_reviews': int,
                'avg_grade_time_hours': float,
                'overdue_percentage': float,
                ...
            }
        """
        from reports.queries.analytics import TEACHER_WORKLOAD_ANALYSIS

        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()
        params = (teacher_id, start_date, end_date)

        cache_key = self._get_cache_key('teacher_workload', params)

        start_time = time.time()
        results = self._execute_query(
            TEACHER_WORKLOAD_ANALYSIS, params,
            use_cache=True, cache_key=cache_key
        )
        execution_time = (time.time() - start_time) * 1000

        if results:
            result = results[0]
            result['execution_time_ms'] = round(execution_time, 2)
            return result

        return {
            'teacher_id': teacher_id,
            'error': 'No data found',
            'execution_time_ms': round(execution_time, 2)
        }

    # ========================================================================
    # SUBJECT ANALYTICS QUERIES
    # ========================================================================

    def get_top_performers(
        self,
        min_submissions: int = 3,
        days_back: int = 90,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get top performers by subject.

        Args:
            min_submissions: Minimum submissions to include
            days_back: Look back this many days
            limit: Maximum results per subject
            offset: Result offset

        Returns:
            {
                'performers': [...],
                'total_count': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import TOP_PERFORMERS

        limit = min(limit, self.MAX_LIMIT)
        start_date = datetime.now() - timedelta(days=days_back)
        params = (start_date, min_submissions, limit, offset)

        cache_key = self._get_cache_key('top_performers', params)

        start_time = time.time()
        results = self._execute_query(
            TOP_PERFORMERS, params,
            use_cache=True, cache_key=cache_key
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            'performers': results,
            'total_count': len(results),
            'execution_time_ms': round(execution_time, 2)
        }

    def get_bottom_performers(
        self,
        min_submissions: int = 3,
        days_back: int = 90,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get bottom performers by subject (need help).

        Args:
            min_submissions: Minimum submissions to include
            days_back: Look back this many days
            limit: Maximum results per subject
            offset: Result offset

        Returns:
            {
                'performers': [...],
                'total_count': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import BOTTOM_PERFORMERS

        limit = min(limit, self.MAX_LIMIT)
        start_date = datetime.now() - timedelta(days=days_back)
        params = (start_date, min_submissions, limit, offset)

        cache_key = self._get_cache_key('bottom_performers', params)

        start_time = time.time()
        results = self._execute_query(
            BOTTOM_PERFORMERS, params,
            use_cache=True, cache_key=cache_key
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            'performers': results,
            'total_count': len(results),
            'execution_time_ms': round(execution_time, 2)
        }

    # ========================================================================
    # ATTENDANCE & CORRELATION QUERIES
    # ========================================================================

    def get_attendance_vs_grades_correlation(
        self,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Analyze correlation between attendance and grades.

        Args:
            days_back: Look back this many days

        Returns:
            {
                'correlations': [...],
                'total_count': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import ATTENDANCE_VS_GRADES_CORRELATION

        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()
        params = (start_date, end_date, start_date, end_date)

        cache_key = self._get_cache_key('attendance_grades', params)

        start_time = time.time()
        results = self._execute_query(
            ATTENDANCE_VS_GRADES_CORRELATION, params,
            use_cache=True, cache_key=cache_key
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            'correlations': results,
            'total_count': len(results),
            'execution_time_ms': round(execution_time, 2)
        }

    # ========================================================================
    # CLASS ANALYTICS QUERIES
    # ========================================================================

    def get_class_performance_trends(
        self,
        granularity: str = 'week',
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Get class-level performance trends over time.

        Args:
            granularity: 'day', 'week', or 'month'
            days_back: Look back this many days

        Returns:
            {
                'trends': [...],
                'total_count': int,
                'execution_time_ms': float
            }
        """
        from reports.queries.analytics import CLASS_PERFORMANCE_TRENDS

        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()

        sql = CLASS_PERFORMANCE_TRENDS.format(granularity=granularity)
        params = (start_date, end_date)

        cache_key = self._get_cache_key('class_trends', (granularity, days_back))

        start_time = time.time()
        results = self._execute_query(sql, params, use_cache=True, cache_key=cache_key)
        execution_time = (time.time() - start_time) * 1000

        return {
            'trends': results,
            'total_count': len(results),
            'granularity': granularity,
            'days_back': days_back,
            'execution_time_ms': round(execution_time, 2)
        }

    # ========================================================================
    # CACHE MANAGEMENT
        # ========================================================================

    def invalidate_cache(self, prefix: Optional[str] = None) -> int:
        """
        Invalidate cached query results.

        Args:
            prefix: Cache key prefix (e.g., 'warehouse_student').
                   If None, clears all warehouse cache.

        Returns:
            Number of keys deleted
        """
        if not prefix:
            prefix = 'warehouse_'

        # Note: Depending on cache backend, this might not work for all backends
        # For Redis, we can use pattern matching
        try:
            if hasattr(cache, 'delete_pattern'):
                return cache.delete_pattern(f"{prefix}*")
        except (AttributeError, NotImplementedError):
            logger.warning(f"Cache backend does not support pattern deletion")

        return 0

    def warm_cache(self, query_type: str = 'all') -> int:
        """
        Pre-populate cache with common queries.

        Used before admin dashboard view to reduce initial load times.

        Args:
            query_type: 'all', 'engagement', 'performance', 'workload'

        Returns:
            Number of queries executed
        """
        queries_executed = 0

        try:
            if query_type in ('all', 'engagement'):
                # Warm student engagement cache
                self.get_student_engagement_metrics(limit=50)
                queries_executed += 1

            if query_type in ('all', 'performance'):
                # Warm top/bottom performers cache
                self.get_top_performers(limit=20)
                self.get_bottom_performers(limit=20)
                queries_executed += 2

            logger.info(f"Warmed {queries_executed} cache entries")

        except Exception as e:
            logger.error(f"Error warming cache: {e}")

        return queries_executed
