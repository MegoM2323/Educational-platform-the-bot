"""
Report Data Aggregation Service

Comprehensive data aggregation service for computing report statistics including:
- Student progress metrics
- Assignment statistics (completion rates, average scores, score distributions)
- Learning metrics (engagement, performance trends)
- Time-based aggregations (daily, weekly, monthly)
- Subject-based performance analysis

Features:
- Django aggregation functions for efficient database queries
- Statistical calculations (mean, median, standard deviation, percentiles)
- Time-based grouping and trend analysis
- Flexible filtering (student, teacher, subject, date range, status)
- Performance optimization with select_related/prefetch_related
- Caching of aggregated results (1 hour TTL)
- Safe handling of null/missing data

Usage:
    from reports.aggregation import ReportDataAggregationService

    aggregator = ReportDataAggregationService()

    # Get student progress metrics
    progress = aggregator.get_student_progress_metrics(
        student_id=123,
        date_from='2025-01-01',
        date_to='2025-12-31'
    )

    # Get assignment statistics
    stats = aggregator.get_assignment_statistics(
        teacher_id=456,
        date_from='2025-01-01'
    )

    # Get weekly aggregation
    weekly = aggregator.aggregate_weekly(
        teacher_id=456,
        include_metrics=['completion_rate', 'average_score']
    )
"""

import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from statistics import mean, median, stdev

from django.db.models import (
    Avg, Count, Max, Min, Sum, Q, F, Value, Case, When,
    IntegerField, DecimalField, CharField, Subquery, OuterRef
)
from django.db.models.functions import (
    TruncDate, TruncWeek, TruncMonth, Coalesce, ExtractDay
)
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ReportDataAggregationService:
    """
    Service for aggregating data across reports and generating statistics.

    Provides methods for:
    - Student progress aggregation
    - Assignment statistics
    - Learning metrics and engagement
    - Time-based aggregation (daily, weekly, monthly)
    - Filtering by student, teacher, subject, date range
    """

    # Cache TTL: 1 hour
    CACHE_TTL = 3600

    def __init__(self):
        """Initialize aggregation service."""
        self.logger = logging.getLogger(__name__)

    def _get_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from params.

        Args:
            prefix: Cache key prefix (e.g., 'student_progress')
            params: Parameters dictionary

        Returns:
            Cache key string
        """
        import hashlib
        params_str = str(sorted(params.items()))
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"reports_agg_{prefix}_{params_hash}"

    def _use_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available.

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None
        """
        try:
            result = cache.get(cache_key)
            if result is not None:
                self.logger.debug(f"Cache hit: {cache_key}")
                return result
        except Exception as e:
            self.logger.warning(f"Cache read error: {e}")

        return None

    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store result in cache.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        try:
            cache.set(cache_key, data, self.CACHE_TTL)
        except Exception as e:
            self.logger.warning(f"Cache write error: {e}")

    # ========================================================================
    # STUDENT PROGRESS METRICS
    # ========================================================================

    def get_student_progress_metrics(
        self,
        student_id: int,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive progress metrics for a student.

        Includes:
        - Overall progress percentage
        - Material completion metrics
        - Assignment submission and score metrics
        - Engagement metrics
        - Performance trends

        Args:
            student_id: Student ID
            date_from: Start date (YYYY-MM-DD), default: 30 days ago
            date_to: End date (YYYY-MM-DD), default: today
            use_cache: Use cached results if available

        Returns:
            {
                'student_id': int,
                'overall_progress': float (0-100),
                'materials': {
                    'total': int,
                    'completed': int,
                    'in_progress': int,
                    'not_started': int,
                    'avg_progress': float
                },
                'assignments': {
                    'total': int,
                    'submitted': int,
                    'graded': int,
                    'pending': int,
                    'avg_score': float,
                    'late_submissions': int
                },
                'engagement': {
                    'total_time_spent_hours': float,
                    'avg_session_duration_minutes': float,
                    'activity_days': int
                },
                'trends': {
                    'previous_period_progress': float,
                    'progress_change': float,
                    'is_improving': bool
                }
            }
        """
        cache_params = {
            'student_id': student_id,
            'date_from': date_from,
            'date_to': date_to
        }
        cache_key = self._get_cache_key('student_progress_metrics', cache_params)

        # Check cache
        if use_cache:
            cached_result = self._use_cache(cache_key)
            if cached_result is not None:
                return cached_result

        # Parse dates
        if date_to is None:
            date_to_obj = timezone.now().date()
        else:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()

        if date_from is None:
            date_from_obj = date_to_obj - timedelta(days=30)
        else:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()

        try:
            # Material progress metrics
            from materials.models import MaterialProgress
            material_metrics = self._aggregate_material_progress(
                student_id, date_from_obj, date_to_obj
            )

            # Assignment metrics
            assignment_metrics = self._aggregate_assignment_metrics(
                student_id=student_id, date_from=date_from_obj, date_to=date_to_obj
            )

            # Engagement metrics
            engagement_metrics = self._aggregate_engagement_metrics(
                student_id, date_from_obj, date_to_obj
            )

            # Calculate overall progress
            overall_progress = self._calculate_overall_progress(
                material_metrics, assignment_metrics
            )

            # Calculate trends
            trends = self._calculate_progress_trends(
                student_id, date_from_obj, date_to_obj
            )

            result = {
                'student_id': student_id,
                'overall_progress': round(overall_progress, 2),
                'materials': material_metrics,
                'assignments': assignment_metrics,
                'engagement': engagement_metrics,
                'trends': trends,
                'date_from': date_from_obj.isoformat(),
                'date_to': date_to_obj.isoformat()
            }

            # Cache result
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            self.logger.error(f"Error aggregating student progress: {e}")
            raise

    def _aggregate_material_progress(
        self,
        student_id: int,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """
        Aggregate material progress data for student.

        Args:
            student_id: Student ID
            date_from: Start date
            date_to: End date

        Returns:
            Material progress metrics dict
        """
        from materials.models import MaterialProgress

        # Get all material progress records
        progress_records = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).values(
            'material_id', 'progress_percentage', 'is_completed'
        )

        if not progress_records:
            return {
                'total': 0,
                'completed': 0,
                'in_progress': 0,
                'not_started': 0,
                'avg_progress': 0.0
            }

        completed = sum(1 for r in progress_records if r['is_completed'])
        in_progress = sum(1 for r in progress_records if r['progress_percentage'] > 0 and not r['is_completed'])
        not_started = sum(1 for r in progress_records if r['progress_percentage'] == 0)

        progress_values = [r['progress_percentage'] for r in progress_records if r['progress_percentage']]
        avg_progress = mean(progress_values) if progress_values else 0.0

        return {
            'total': len(progress_records),
            'completed': completed,
            'in_progress': in_progress,
            'not_started': not_started,
            'avg_progress': round(avg_progress, 2)
        }

    # ========================================================================
    # ASSIGNMENT STATISTICS
    # ========================================================================

    def get_assignment_statistics(
        self,
        teacher_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for assignments.

        Includes:
        - Submission rates and completion rates
        - Score statistics (average, median, min, max, std dev)
        - Score distribution (percentiles)
        - Late submission analysis
        - Time-to-complete analysis

        Args:
            teacher_id: Filter by teacher (optional)
            assignment_id: Filter by specific assignment (optional)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            use_cache: Use cached results

        Returns:
            {
                'total_assignments': int,
                'total_submissions': int,
                'completion_rate': float (0-100),
                'late_submission_rate': float (0-100),
                'score_statistics': {
                    'average': float,
                    'median': float,
                    'min': float,
                    'max': float,
                    'std_dev': float,
                    'percentiles': {'25th': float, '50th': float, '75th': float, '90th': float}
                },
                'score_distribution': {
                    'a': int,  # 90-100
                    'b': int,  # 80-89
                    'c': int,  # 70-79
                    'd': int,  # 60-69
                    'f': int   # <60
                },
                'submission_trends': [...]
            }
        """
        cache_params = {
            'teacher_id': teacher_id,
            'assignment_id': assignment_id,
            'date_from': date_from,
            'date_to': date_to
        }
        cache_key = self._get_cache_key('assignment_statistics', cache_params)

        # Check cache
        if use_cache:
            cached_result = self._use_cache(cache_key)
            if cached_result is not None:
                return cached_result

        try:
            result = self._aggregate_assignment_statistics(
                teacher_id=teacher_id,
                assignment_id=assignment_id,
                date_from=date_from,
                date_to=date_to
            )

            # Cache result
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            self.logger.error(f"Error aggregating assignment statistics: {e}")
            raise

    def _aggregate_assignment_statistics(
        self,
        teacher_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal method to aggregate assignment statistics.

        Args:
            teacher_id: Filter by teacher
            assignment_id: Filter by assignment
            date_from: Start date
            date_to: End date

        Returns:
            Assignment statistics dict
        """
        from assignments.models import AssignmentSubmission, Assignment

        # Build query
        query = AssignmentSubmission.objects.all()

        if teacher_id:
            query = query.filter(assignment__author_id=teacher_id)

        if assignment_id:
            query = query.filter(assignment_id=assignment_id)

        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(submitted_at__date__gte=date_from_obj)

        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(submitted_at__date__lte=date_to_obj)

        # Get submissions
        submissions = query.select_related('assignment').values(
            'id', 'score', 'is_late', 'submitted_at', 'assignment_id'
        )

        if not submissions:
            return {
                'total_assignments': 0,
                'total_submissions': 0,
                'completion_rate': 0.0,
                'late_submission_rate': 0.0,
                'score_statistics': self._empty_score_statistics(),
                'score_distribution': self._empty_score_distribution(),
                'submission_trends': []
            }

        # Calculate statistics
        total_submissions = len(submissions)
        late_submissions = sum(1 for s in submissions if s.get('is_late'))

        scores = [s['score'] for s in submissions if s.get('score') is not None]

        score_stats = self._calculate_score_statistics(scores)
        score_dist = self._calculate_score_distribution(scores)

        # Get unique assignments
        unique_assignments = len(set(s['assignment_id'] for s in submissions))

        # Get all assignments for completion rate
        if teacher_id:
            all_assignments = Assignment.objects.filter(author_id=teacher_id).count()
        elif assignment_id:
            all_assignments = 1
        else:
            all_assignments = unique_assignments

        completion_rate = (unique_assignments / all_assignments * 100) if all_assignments > 0 else 0.0
        late_rate = (late_submissions / total_submissions * 100) if total_submissions > 0 else 0.0

        return {
            'total_assignments': unique_assignments,
            'total_submissions': total_submissions,
            'completion_rate': round(completion_rate, 2),
            'late_submission_rate': round(late_rate, 2),
            'score_statistics': score_stats,
            'score_distribution': score_dist,
            'submission_trends': self._calculate_submission_trends(submissions)
        }

    # ========================================================================
    # LEARNING METRICS
    # ========================================================================

    def get_learning_metrics(
        self,
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get learning metrics including engagement and performance.

        Args:
            student_id: Filter by student
            teacher_id: Filter by teacher
            subject_id: Filter by subject
            date_from: Start date
            date_to: End date
            use_cache: Use cache

        Returns:
            {
                'engagement_score': float (0-100),
                'performance_score': float (0-100),
                'activity_level': str (low/medium/high),
                'time_spent_hours': float,
                'participation_rate': float (0-100),
                'consistency_score': float (0-100),
                'improvement_trend': str (improving/stable/declining)
            }
        """
        cache_params = {
            'student_id': student_id,
            'teacher_id': teacher_id,
            'subject_id': subject_id,
            'date_from': date_from,
            'date_to': date_to
        }
        cache_key = self._get_cache_key('learning_metrics', cache_params)

        if use_cache:
            cached_result = self._use_cache(cache_key)
            if cached_result is not None:
                return cached_result

        try:
            result = self._calculate_learning_metrics(
                student_id=student_id,
                teacher_id=teacher_id,
                subject_id=subject_id,
                date_from=date_from,
                date_to=date_to
            )

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            self.logger.error(f"Error calculating learning metrics: {e}")
            raise

    def _calculate_learning_metrics(
        self,
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate learning metrics from available data."""
        from materials.models import MaterialProgress
        from assignments.models import AssignmentSubmission

        # Parse dates
        if date_to is None:
            date_to_obj = timezone.now().date()
        else:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()

        if date_from is None:
            date_from_obj = date_to_obj - timedelta(days=30)
        else:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()

        # Calculate engagement
        engagement_score = self._calculate_engagement_score(
            student_id=student_id,
            date_from=date_from_obj,
            date_to=date_to_obj
        )

        # Calculate performance
        performance_score = self._calculate_performance_score(
            student_id=student_id,
            teacher_id=teacher_id,
            date_from=date_from_obj,
            date_to=date_to_obj
        )

        # Determine activity level
        activity_level = 'high' if engagement_score >= 75 else ('medium' if engagement_score >= 50 else 'low')

        # Calculate time spent
        time_spent = self._calculate_time_spent(
            student_id=student_id,
            date_from=date_from_obj,
            date_to=date_to_obj
        )

        # Calculate participation rate
        participation_rate = self._calculate_participation_rate(
            student_id=student_id,
            date_from=date_from_obj,
            date_to=date_to_obj
        )

        # Calculate consistency
        consistency_score = self._calculate_consistency_score(
            student_id=student_id,
            date_from=date_from_obj,
            date_to=date_to_obj
        )

        # Calculate improvement trend
        improvement_trend = self._calculate_improvement_trend(
            student_id=student_id,
            date_from=date_from_obj,
            date_to=date_to_obj
        )

        return {
            'engagement_score': round(engagement_score, 2),
            'performance_score': round(performance_score, 2),
            'activity_level': activity_level,
            'time_spent_hours': round(time_spent, 2),
            'participation_rate': round(participation_rate, 2),
            'consistency_score': round(consistency_score, 2),
            'improvement_trend': improvement_trend
        }

    # ========================================================================
    # TIME-BASED AGGREGATION
    # ========================================================================

    def aggregate_daily(
        self,
        teacher_id: Optional[int] = None,
        student_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate data by day.

        Args:
            teacher_id: Filter by teacher
            student_id: Filter by student
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            include_metrics: List of metrics to include (default: all)

        Returns:
            {
                'period': 'daily',
                'aggregations': [
                    {
                        'date': YYYY-MM-DD,
                        'submissions': int,
                        'avg_score': float,
                        'completion_rate': float,
                        ...
                    },
                    ...
                ]
            }
        """
        if include_metrics is None:
            include_metrics = ['submissions', 'avg_score', 'completion_rate']

        return self._aggregate_by_period(
            period='day',
            teacher_id=teacher_id,
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            include_metrics=include_metrics
        )

    def aggregate_weekly(
        self,
        teacher_id: Optional[int] = None,
        student_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate data by week.

        Args:
            teacher_id: Filter by teacher
            student_id: Filter by student
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            include_metrics: List of metrics to include

        Returns:
            Aggregated weekly data
        """
        if include_metrics is None:
            include_metrics = ['submissions', 'avg_score', 'completion_rate', 'engagement']

        return self._aggregate_by_period(
            period='week',
            teacher_id=teacher_id,
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            include_metrics=include_metrics
        )

    def aggregate_monthly(
        self,
        teacher_id: Optional[int] = None,
        student_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate data by month.

        Args:
            teacher_id: Filter by teacher
            student_id: Filter by student
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            include_metrics: List of metrics to include

        Returns:
            Aggregated monthly data
        """
        if include_metrics is None:
            include_metrics = ['submissions', 'avg_score', 'completion_rate', 'engagement']

        return self._aggregate_by_period(
            period='month',
            teacher_id=teacher_id,
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            include_metrics=include_metrics
        )

    def _aggregate_by_period(
        self,
        period: str,
        teacher_id: Optional[int] = None,
        student_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Internal method for time-based aggregation.

        Args:
            period: 'day', 'week', or 'month'
            teacher_id: Filter by teacher
            student_id: Filter by student
            date_from: Start date
            date_to: End date
            include_metrics: Metrics to include

        Returns:
            Aggregated data by period
        """
        from assignments.models import AssignmentSubmission
        from materials.models import MaterialProgress

        # Parse dates
        if date_to is None:
            date_to_obj = timezone.now().date()
        else:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()

        if date_from is None:
            date_from_obj = date_to_obj - timedelta(days=90)
        else:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()

        # Map period to Django ORM function
        period_map = {
            'day': TruncDate,
            'week': TruncWeek,
            'month': TruncMonth
        }

        period_func = period_map.get(period, TruncDate)

        # Query submissions by period
        submissions = AssignmentSubmission.objects.filter(
            submitted_at__date__gte=date_from_obj,
            submitted_at__date__lte=date_to_obj
        ).annotate(
            period=period_func('submitted_at')
        ).values('period').annotate(
            submission_count=Count('id'),
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score')
        ).order_by('period')

        if teacher_id:
            submissions = submissions.filter(assignment__author_id=teacher_id)

        if student_id:
            submissions = submissions.filter(student_id=student_id)

        # Format results
        aggregations = []
        for record in submissions:
            agg_record = {
                'period_start': record['period'].isoformat() if hasattr(record['period'], 'isoformat') else str(record['period'])
            }

            if 'submissions' in (include_metrics or []):
                agg_record['submissions'] = record['submission_count']
            if 'avg_score' in (include_metrics or []):
                agg_record['avg_score'] = round(float(record['avg_score'])) if record['avg_score'] else None
            if 'completion_rate' in (include_metrics or []):
                agg_record['completion_rate'] = 100.0  # Simplified

            aggregations.append(agg_record)

        return {
            'period': period,
            'date_from': date_from_obj.isoformat(),
            'date_to': date_to_obj.isoformat(),
            'aggregations': aggregations
        }

    # ========================================================================
    # SUBJECT-BASED AGGREGATION
    # ========================================================================

    def aggregate_by_subject(
        self,
        teacher_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate performance metrics grouped by subject.

        Args:
            teacher_id: Filter by teacher
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            {
                'subjects': [
                    {
                        'subject_id': int,
                        'subject_name': str,
                        'avg_score': float,
                        'completion_rate': float,
                        'student_count': int,
                        'submission_count': int
                    },
                    ...
                ]
            }
        """
        from assignments.models import AssignmentSubmission, Assignment
        from materials.models import Subject

        query = AssignmentSubmission.objects.select_related(
            'assignment__author'
        ).values(
            'assignment__author_id'
        ).annotate(
            avg_score=Avg('score'),
            submission_count=Count('id'),
            student_count=Count('student_id', distinct=True)
        )

        if teacher_id:
            query = query.filter(assignment__author_id=teacher_id)

        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(submitted_at__date__gte=date_from_obj)

        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(submitted_at__date__lte=date_to_obj)

        authors = []
        for record in query:
            if record['assignment__author_id']:
                authors.append({
                    'author_id': record['assignment__author_id'],
                    'avg_score': round(float(record['avg_score'])) if record['avg_score'] else 0.0,
                    'student_count': record['student_count'],
                    'submission_count': record['submission_count']
                })

        return {
            'authors': authors,
            'total_authors': len(authors)
        }

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _aggregate_assignment_metrics(
        self,
        student_id: int,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """
        Aggregate assignment metrics for a student.

        Args:
            student_id: Student ID
            date_from: Start date
            date_to: End date

        Returns:
            Assignment metrics dict
        """
        from assignments.models import AssignmentSubmission

        submissions = AssignmentSubmission.objects.filter(
            student_id=student_id,
            submitted_at__date__gte=date_from,
            submitted_at__date__lte=date_to
        ).values('score', 'is_late', 'status')

        if not submissions:
            return {
                'total': 0,
                'submitted': 0,
                'graded': 0,
                'pending': 0,
                'avg_score': 0.0,
                'late_submissions': 0
            }

        submitted = len(submissions)
        graded = sum(1 for s in submissions if s.get('status') == 'graded')
        pending = sum(1 for s in submissions if s.get('status') in ('submitted', 'in_review'))
        late = sum(1 for s in submissions if s.get('is_late'))

        scores = [s['score'] for s in submissions if s.get('score') is not None]
        avg_score = mean(scores) if scores else 0.0

        return {
            'total': submitted,
            'submitted': submitted,
            'graded': graded,
            'pending': pending,
            'avg_score': round(avg_score, 2),
            'late_submissions': late
        }

    def _aggregate_engagement_metrics(
        self,
        student_id: int,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """
        Aggregate engagement metrics for a student.

        Args:
            student_id: Student ID
            date_from: Start date
            date_to: End date

        Returns:
            Engagement metrics dict
        """
        from materials.models import MaterialProgress
        from assignments.models import AssignmentSubmission

        # Get total time spent from material progress
        material_progress = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).aggregate(
            total_time=Sum('time_spent')
        )

        total_time_minutes = material_progress.get('total_time') or 0
        total_time_hours = total_time_minutes / 60 if total_time_minutes else 0

        # Get activity days
        activity_days = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).values(
            'last_accessed__date'
        ).distinct().count()

        # Calculate avg session duration
        days_in_period = (date_to - date_from).days + 1
        avg_session = (total_time_minutes / activity_days) if activity_days > 0 else 0

        return {
            'total_time_spent_hours': round(total_time_hours, 2),
            'avg_session_duration_minutes': round(avg_session, 2),
            'activity_days': activity_days
        }

    def _calculate_overall_progress(
        self,
        material_metrics: Dict[str, Any],
        assignment_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall progress from material and assignment metrics."""
        if material_metrics['total'] == 0 and assignment_metrics['total'] == 0:
            return 0.0

        material_progress = (material_metrics['avg_progress'] * material_metrics['total']) if material_metrics['total'] > 0 else 0
        assignment_progress = (assignment_metrics['avg_score'] / 100 * 100 * assignment_metrics['total']) if assignment_metrics['total'] > 0 else 0

        total_items = material_metrics['total'] + assignment_metrics['total']

        if total_items == 0:
            return 0.0

        return (material_progress + assignment_progress) / total_items

    def _calculate_progress_trends(
        self,
        student_id: int,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """Calculate progress trends."""
        # Get previous period
        period_length = (date_to - date_from).days
        prev_date_to = date_from - timedelta(days=1)
        prev_date_from = prev_date_to - timedelta(days=period_length)

        # Get metrics for both periods
        current_progress = self._calculate_overall_progress(
            self._aggregate_material_progress(student_id, date_from, date_to),
            self._aggregate_assignment_metrics(student_id, date_from, date_to)
        )

        prev_progress = self._calculate_overall_progress(
            self._aggregate_material_progress(student_id, prev_date_from, prev_date_to),
            self._aggregate_assignment_metrics(student_id, prev_date_from, prev_date_to)
        )

        change = current_progress - prev_progress

        return {
            'previous_period_progress': round(prev_progress, 2),
            'progress_change': round(change, 2),
            'is_improving': change > 0
        }

    def _calculate_score_statistics(self, scores: List[float]) -> Dict[str, Any]:
        """Calculate score statistics."""
        if not scores:
            return self._empty_score_statistics()

        sorted_scores = sorted(scores)

        try:
            std_dev = stdev(scores) if len(scores) > 1 else 0.0
        except:
            std_dev = 0.0

        percentiles = {
            '25th': self._percentile(sorted_scores, 25),
            '50th': self._percentile(sorted_scores, 50),
            '75th': self._percentile(sorted_scores, 75),
            '90th': self._percentile(sorted_scores, 90)
        }

        return {
            'average': round(mean(scores), 2),
            'median': round(median(scores), 2),
            'min': round(min(scores), 2),
            'max': round(max(scores), 2),
            'std_dev': round(std_dev, 2),
            'percentiles': {k: round(v, 2) for k, v in percentiles.items()}
        }

    def _empty_score_statistics(self) -> Dict[str, Any]:
        """Return empty score statistics."""
        return {
            'average': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'std_dev': 0.0,
            'percentiles': {'25th': 0.0, '50th': 0.0, '75th': 0.0, '90th': 0.0}
        }

    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate score distribution (letter grades)."""
        if not scores:
            return self._empty_score_distribution()

        a = sum(1 for s in scores if s >= 90)
        b = sum(1 for s in scores if 80 <= s < 90)
        c = sum(1 for s in scores if 70 <= s < 80)
        d = sum(1 for s in scores if 60 <= s < 70)
        f = sum(1 for s in scores if s < 60)

        return {'a': a, 'b': b, 'c': c, 'd': d, 'f': f}

    def _empty_score_distribution(self) -> Dict[str, int]:
        """Return empty score distribution."""
        return {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'f': 0}

    def _calculate_submission_trends(self, submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate submission trends over time."""
        from collections import defaultdict

        trends_by_date = defaultdict(lambda: {'count': 0, 'avg_score': 0, 'scores': []})

        for submission in submissions:
            date = submission['submitted_at'].date() if submission.get('submitted_at') else timezone.now().date()
            trends_by_date[date]['count'] += 1
            if submission.get('score'):
                trends_by_date[date]['scores'].append(submission['score'])

        trends = []
        for date in sorted(trends_by_date.keys()):
            data = trends_by_date[date]
            avg_score = mean(data['scores']) if data['scores'] else 0.0

            trends.append({
                'date': date.isoformat(),
                'submission_count': data['count'],
                'avg_score': round(avg_score, 2)
            })

        return trends

    def _percentile(self, sorted_list: List[float], percentile: float) -> float:
        """Calculate percentile from sorted list."""
        if not sorted_list:
            return 0.0

        index = (percentile / 100) * len(sorted_list)

        if index == int(index):
            return sorted_list[int(index) - 1]
        else:
            lower = sorted_list[int(index) - 1]
            upper = sorted_list[int(index)]
            return lower + (upper - lower) * (index - int(index))

    def _calculate_engagement_score(self, student_id: Optional[int], date_from: date, date_to: date) -> float:
        """Calculate engagement score (0-100)."""
        from materials.models import MaterialProgress
        from assignments.models import AssignmentSubmission

        # Count activities
        material_updates = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).count()

        submissions = AssignmentSubmission.objects.filter(
            student_id=student_id,
            submitted_at__date__gte=date_from,
            submitted_at__date__lte=date_to
        ).count()

        total_activities = material_updates + submissions
        period_days = (date_to - date_from).days + 1

        # Activity frequency: aim for 1+ activity per day
        engagement = min((total_activities / period_days) * 20, 100)

        return engagement

    def _calculate_performance_score(
        self,
        student_id: Optional[int],
        teacher_id: Optional[int],
        date_from: date,
        date_to: date
    ) -> float:
        """Calculate performance score based on scores (0-100)."""
        from assignments.models import AssignmentSubmission

        submissions = AssignmentSubmission.objects.filter(
            student_id=student_id,
            submitted_at__date__gte=date_from,
            submitted_at__date__lte=date_to
        )

        if teacher_id:
            submissions = submissions.filter(assignment__author_id=teacher_id)

        scores = list(submissions.values_list('score', flat=True).filter(score__isnull=False))

        if not scores:
            return 0.0

        return mean(scores)

    def _calculate_time_spent(self, student_id: Optional[int], date_from: date, date_to: date) -> float:
        """Calculate time spent in hours."""
        from materials.models import MaterialProgress

        result = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).aggregate(
            total=Sum('time_spent')
        )

        minutes = result['total'] or 0
        return minutes / 60

    def _calculate_participation_rate(self, student_id: Optional[int], date_from: date, date_to: date) -> float:
        """Calculate participation rate (0-100)."""
        from materials.models import MaterialProgress

        # Get activity days vs period days
        activity_days = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).values(
            'last_accessed__date'
        ).distinct().count()

        period_days = (date_to - date_from).days + 1

        return (activity_days / period_days * 100) if period_days > 0 else 0.0

    def _calculate_consistency_score(self, student_id: Optional[int], date_from: date, date_to: date) -> float:
        """Calculate consistency score (0-100)."""
        from materials.models import MaterialProgress

        # Check if student has regular activity
        daily_activities = MaterialProgress.objects.filter(
            student_id=student_id,
            last_accessed__date__gte=date_from,
            last_accessed__date__lte=date_to
        ).values(
            'last_accessed__date'
        ).annotate(
            count=Count('id')
        )

        if not daily_activities:
            return 0.0

        activity_counts = [d['count'] for d in daily_activities]

        # Consistency = low variance in activity counts
        if len(activity_counts) <= 1:
            return 50.0

        avg_count = mean(activity_counts)
        variance = sum((x - avg_count) ** 2 for x in activity_counts) / len(activity_counts)

        # Convert variance to 0-100 score (lower variance = higher consistency)
        consistency = max(0, 100 - (variance * 5))

        return consistency

    def _calculate_improvement_trend(self, student_id: Optional[int], date_from: date, date_to: date) -> str:
        """Determine improvement trend (improving/stable/declining)."""
        from assignments.models import AssignmentSubmission

        period_length = (date_to - date_from).days
        mid_date = date_from + timedelta(days=period_length // 2)

        # First half scores
        first_half = AssignmentSubmission.objects.filter(
            student_id=student_id,
            submitted_at__date__gte=date_from,
            submitted_at__date__lt=mid_date
        ).aggregate(
            avg=Avg('score')
        )['avg']

        # Second half scores
        second_half = AssignmentSubmission.objects.filter(
            student_id=student_id,
            submitted_at__date__gte=mid_date,
            submitted_at__date__lte=date_to
        ).aggregate(
            avg=Avg('score')
        )['avg']

        if first_half is None or second_half is None:
            return 'stable'

        if second_half > first_half * 1.05:
            return 'improving'
        elif second_half < first_half * 0.95:
            return 'declining'
        else:
            return 'stable'
