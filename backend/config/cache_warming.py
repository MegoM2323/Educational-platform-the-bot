"""
Cache warming configuration and utilities.

This module provides:
- Scheduled cache warming tasks via Celery Beat
- Cache warming strategies for different endpoint types
- Cache warming metrics and monitoring
- Automatic cache invalidation on data changes
"""

import logging
from typing import Dict, Any, List, Optional
from django.core.cache import cache, caches
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class CacheWarmingManager:
    """
    Manage cache warming operations.

    Provides utilities for pre-populating caches with frequently accessed data
    to improve performance and reduce load on the database during peak hours.
    """

    def __init__(self):
        """Initialize cache warming manager."""
        self.cache = cache
        self.stats = {
            'items_warmed': 0,
            'bytes_cached': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
        }

    def warm_popular_endpoints(self) -> Dict[str, int]:
        """
        Warm cache for popular endpoints.

        Returns:
            Dictionary with warming statistics per endpoint type
        """
        stats = {}

        try:
            self.stats['start_time'] = timezone.now()

            # Warm each endpoint type
            stats['materials'] = self._warm_materials_endpoint()
            stats['subjects'] = self._warm_subjects_endpoint()
            stats['dashboards'] = self._warm_active_dashboards()
            stats['analytics'] = self._warm_analytics_endpoint()

            self.stats['end_time'] = timezone.now()
            self.stats['items_warmed'] = sum(stats.values())

            logger.info(
                f'Cache warming completed: {self.stats["items_warmed"]} items warmed'
            )

            return stats

        except Exception as e:
            logger.exception(f'Error during cache warming: {e}')
            self.stats['errors'] += 1
            raise

    def _warm_materials_endpoint(self) -> int:
        """Warm materials endpoint cache."""
        from materials.models import Material
        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS
        from materials.serializers import MaterialListSerializer

        count = 0

        try:
            # Get popular materials (recent, published)
            materials = Material.objects.filter(
                status='published'
            ).select_related('author', 'subject').order_by('-updated_at')[:20]

            # Cache each material
            for material in materials:
                cache_key = CacheKeyBuilder.make_key('material', material.id)

                try:
                    # Simple cache with key info
                    material_data = {
                        'id': material.id,
                        'title': material.title,
                        'subject_id': material.subject_id,
                        'type': material.type,
                        'difficulty_level': material.difficulty_level,
                    }

                    self.cache.set(
                        cache_key,
                        material_data,
                        CACHE_TIMEOUTS.get('material_detail', 3600)
                    )

                    count += 1

                except Exception as e:
                    logger.warning(f'Error warming material {material.id}: {e}')
                    self.stats['errors'] += 1

            logger.info(f'Warmed {count} materials')
            return count

        except Exception as e:
            logger.warning(f'Error warming materials endpoint: {e}')
            self.stats['errors'] += 1
            return count

    def _warm_subjects_endpoint(self) -> int:
        """Warm subjects endpoint cache."""
        from materials.models import Subject
        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS

        count = 0

        try:
            # Get all subjects
            subjects = Subject.objects.all().order_by('name')

            for subject in subjects:
                cache_key = CacheKeyBuilder.make_key('subject', subject.id)

                try:
                    subject_data = {
                        'id': subject.id,
                        'name': subject.name,
                        'description': subject.description,
                    }

                    self.cache.set(
                        cache_key,
                        subject_data,
                        CACHE_TIMEOUTS.get('long', 3600)
                    )

                    count += 1

                except Exception as e:
                    logger.warning(f'Error warming subject {subject.id}: {e}')
                    self.stats['errors'] += 1

            logger.info(f'Warmed {count} subjects')
            return count

        except Exception as e:
            logger.warning(f'Error warming subjects endpoint: {e}')
            self.stats['errors'] += 1
            return count

    def _warm_active_dashboards(self) -> int:
        """Warm dashboard cache for active users."""
        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS
        from accounts.models import StudentProfile, TeacherProfile

        count = 0

        try:
            # Warm student dashboards (active in last 7 days)
            cutoff = timezone.now() - timezone.timedelta(days=7)

            try:
                active_students = StudentProfile.objects.filter(
                    user__last_login__gte=cutoff
                ).select_related('user')[:50]

                for student in active_students:
                    cache_key = CacheKeyBuilder.user_key('dashboard', student.user.id)

                    try:
                        dashboard_data = {
                            'user_id': student.user.id,
                            'role': 'student',
                            'warmed_at': timezone.now().isoformat(),
                        }

                        self.cache.set(
                            cache_key,
                            dashboard_data,
                            CACHE_TIMEOUTS.get('dashboard', 300)
                        )

                        count += 1

                    except Exception as e:
                        logger.warning(f'Error warming student dashboard: {e}')
                        self.stats['errors'] += 1

            except Exception as e:
                logger.warning(f'Error getting active students: {e}')

            # Warm teacher dashboards
            try:
                active_teachers = TeacherProfile.objects.filter(
                    user__last_login__gte=cutoff
                ).select_related('user')[:30]

                for teacher in active_teachers:
                    cache_key = CacheKeyBuilder.user_key('dashboard', teacher.user.id)

                    try:
                        dashboard_data = {
                            'user_id': teacher.user.id,
                            'role': 'teacher',
                            'warmed_at': timezone.now().isoformat(),
                        }

                        self.cache.set(
                            cache_key,
                            dashboard_data,
                            CACHE_TIMEOUTS.get('dashboard', 300)
                        )

                        count += 1

                    except Exception as e:
                        logger.warning(f'Error warming teacher dashboard: {e}')
                        self.stats['errors'] += 1

            except Exception as e:
                logger.warning(f'Error getting active teachers: {e}')

            logger.info(f'Warmed {count} dashboards')
            return count

        except Exception as e:
            logger.warning(f'Error warming dashboards: {e}')
            self.stats['errors'] += 1
            return count

    def _warm_analytics_endpoint(self) -> int:
        """Warm analytics and reports cache."""
        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS

        count = 0

        try:
            # Cache analytics overview
            analytics_key = CacheKeyBuilder.make_key('analytics', 'overview')

            analytics_data = {
                'cached_at': timezone.now().isoformat(),
                'cache_version': '1.0',
            }

            self.cache.set(
                analytics_key,
                analytics_data,
                CACHE_TIMEOUTS.get('analytics', 1800)
            )

            count += 1

            logger.info('Warmed analytics cache')
            return count

        except Exception as e:
            logger.warning(f'Error warming analytics: {e}')
            self.stats['errors'] += 1
            return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics."""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        return {
            'items_warmed': self.stats['items_warmed'],
            'bytes_cached': self.stats['bytes_cached'],
            'errors': self.stats['errors'],
            'duration_seconds': duration,
            'timestamp': timezone.now().isoformat(),
        }


# Cache warming strategies for different scenarios
CACHE_WARMING_STRATEGIES = {
    'startup': [
        'materials',
        'subjects',
        'analytics',
    ],
    'full': [
        'materials',
        'subjects',
        'dashboards',
        'analytics',
    ],
    'light': [
        'subjects',
        'analytics',
    ],
}


def should_warm_cache() -> bool:
    """
    Determine if cache warming should be performed.

    Returns:
        True if conditions are favorable for cache warming
    """
    try:
        # Check if Redis is available
        from django.core.cache import cache as default_cache
        default_cache.set('_cache_test', '1', 1)
        default_cache.get('_cache_test')
        return True
    except Exception:
        logger.warning('Cache not available for warming')
        return False


def get_cache_warming_config() -> Dict[str, Any]:
    """Get cache warming configuration."""
    return {
        'enabled': getattr(settings, 'CACHE_WARMING_ENABLED', True),
        'strategy': getattr(settings, 'CACHE_WARMING_STRATEGY', 'startup'),
        'max_items_per_type': getattr(settings, 'CACHE_WARMING_MAX_ITEMS', 100),
        'ttl_multiplier': getattr(settings, 'CACHE_WARMING_TTL_MULTIPLIER', 1.2),
    }
