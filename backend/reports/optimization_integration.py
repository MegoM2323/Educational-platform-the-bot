"""
Integration module for applying query optimizations to report views.

This module provides helper functions and mixins to apply the query
optimization strategies to Django REST framework viewsets.
"""

from functools import wraps
from typing import Callable, Any

from django.db.models import QuerySet

from .query_optimization import (
    ReportQueryOptimizer, QueryMonitor, monitor_queries, QueryCacheManager
)


class OptimizedQuerysetMixin:
    """
    Mixin for ViewSets to automatically optimize querysets.

    Usage in ViewSet:
        class ReportViewSet(OptimizedQuerysetMixin, viewsets.ModelViewSet):
            # Your existing code
            pass
    """

    def get_queryset(self) -> QuerySet:
        """
        Get base queryset and apply optimizations.

        Subclasses should implement _get_base_queryset() instead.
        """
        if not hasattr(self, '_get_base_queryset'):
            raise NotImplementedError(
                f"{self.__class__.__name__} must implement _get_base_queryset()"
            )

        queryset = self._get_base_queryset()
        return self._optimize_queryset(queryset)

    def _optimize_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Apply model-specific optimizations to queryset.

        Override in subclass for custom optimization.
        """
        model = queryset.model
        model_name = model.__name__

        # Auto-detect optimization based on model
        if model_name == 'StudentReport':
            return ReportQueryOptimizer.optimize_student_report_queryset(queryset)
        elif model_name == 'TutorWeeklyReport':
            return ReportQueryOptimizer.optimize_tutor_report_queryset(queryset)
        elif model_name == 'TeacherWeeklyReport':
            return ReportQueryOptimizer.optimize_teacher_report_queryset(queryset)
        elif model_name == 'Report':
            return ReportQueryOptimizer.optimize_report_queryset(queryset)

        return queryset


def optimize_list_action(func: Callable) -> Callable:
    """
    Decorator to optimize list view actions.

    Usage:
        @optimize_list_action
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
    """

    @wraps(func)
    def wrapper(self, request, *args, **kwargs) -> Any:
        with QueryMonitor(f"{self.__class__.__name__}.{func.__name__}"):
            return func(self, request, *args, **kwargs)

    return wrapper


def optimize_retrieve_action(func: Callable) -> Callable:
    """
    Decorator to optimize retrieve view actions.

    Usage:
        @optimize_retrieve_action
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)
    """

    @wraps(func)
    def wrapper(self, request, *args, **kwargs) -> Any:
        with QueryMonitor(f"{self.__class__.__name__}.{func.__name__}"):
            return func(self, request, *args, **kwargs)

    return wrapper


def cache_report_list(ttl: int = 300) -> Callable:
    """
    Decorator to cache report list results.

    Args:
        ttl: Cache time-to-live in seconds (default: 5 minutes)

    Usage:
        @cache_report_list(ttl=600)
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs) -> Any:
            # Generate cache key from request
            cache_key = f"{self.__class__.__name__}:list:{request.user.id}"

            # Try to get from cache
            result = QueryCacheManager.get_or_set(
                cache_key,
                lambda: func(self, request, *args, **kwargs),
                ttl,
            )

            return result

        return wrapper

    return decorator


class ReportViewSetOptimizationHelper:
    """
    Helper class with methods to apply optimizations to report viewsets.

    Usage:
        class StudentReportViewSet(viewsets.ModelViewSet):
            def get_queryset(self):
                qs = StudentReport.objects.all()
                return ReportViewSetOptimizationHelper.optimize_student_report(qs)
    """

    @staticmethod
    def optimize_student_report(queryset: QuerySet) -> QuerySet:
        """Optimize StudentReport queryset."""
        return ReportQueryOptimizer.optimize_student_report_queryset(queryset)

    @staticmethod
    def optimize_tutor_report(queryset: QuerySet) -> QuerySet:
        """Optimize TutorWeeklyReport queryset."""
        return ReportQueryOptimizer.optimize_tutor_report_queryset(queryset)

    @staticmethod
    def optimize_teacher_report(queryset: QuerySet) -> QuerySet:
        """Optimize TeacherWeeklyReport queryset."""
        return ReportQueryOptimizer.optimize_teacher_report_queryset(queryset)

    @staticmethod
    def optimize_report(queryset: QuerySet) -> QuerySet:
        """Optimize Report queryset."""
        return ReportQueryOptimizer.optimize_report_queryset(queryset)

    @staticmethod
    def monitor_action(action_name: str) -> Callable:
        """
        Get a monitor context manager for an action.

        Usage:
            with ReportViewSetOptimizationHelper.monitor_action('list'):
                # Code to monitor
                pass
        """
        return QueryMonitor(action_name)


class CachedReportQueries:
    """
    Cached query helpers for common report operations.
    """

    @staticmethod
    def get_student_progress(student_id: int, use_cache: bool = True):
        """
        Get student progress with optional caching.

        Args:
            student_id: Student user ID
            use_cache: Whether to use caching

        Returns:
            Student progress summary
        """
        if use_cache:
            return QueryCacheManager.get_or_set(
                f"student_progress:{student_id}",
                lambda: ReportQueryOptimizer.get_student_progress_summary(student_id),
                ttl=300,
            )
        else:
            return ReportQueryOptimizer.get_student_progress_summary(student_id)

    @staticmethod
    def get_class_performance(teacher_id: int, use_cache: bool = True):
        """
        Get class performance with optional caching.

        Args:
            teacher_id: Teacher user ID
            use_cache: Whether to use caching

        Returns:
            Class performance summary
        """
        if use_cache:
            return QueryCacheManager.get_or_set(
                f"class_performance:{teacher_id}",
                lambda: ReportQueryOptimizer.get_class_performance_summary(teacher_id),
                ttl=300,
            )
        else:
            return ReportQueryOptimizer.get_class_performance_summary(teacher_id)

    @staticmethod
    def invalidate_student_cache(student_id: int):
        """Invalidate student progress cache."""
        QueryCacheManager.invalidate(f"student_progress:{student_id}")

    @staticmethod
    def invalidate_teacher_cache(teacher_id: int):
        """Invalidate teacher class performance cache."""
        QueryCacheManager.invalidate(f"class_performance:{teacher_id}")
