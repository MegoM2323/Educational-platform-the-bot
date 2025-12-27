"""
Management command for cache warming.

This command pre-populates caches with popular endpoints to optimize
application startup and deployment processes. It warms:
- Popular materials
- Subject lists
- Dashboard data for active users
- Analytics and reports data
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache, caches
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    """Manage cache warming for popular endpoints."""

    help = 'Warm caches with popular endpoint data to optimize startup'

    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full cache warming (all endpoints)',
        )
        parser.add_argument(
            '--endpoints',
            nargs='+',
            help='Specific endpoints to warm (materials, subjects, dashboards, reports)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print detailed warming information',
        )

    def handle(self, *args, **options):
        """Execute cache warming."""
        verbose = options.get('verbose', False)
        full = options.get('full', False)
        endpoints = options.get('endpoints', [])

        self.stdout.write(self.style.SUCCESS('\n=== Cache Warming Started ===\n'))

        try:
            # Determine which endpoints to warm
            if full:
                endpoints = [
                    'materials',
                    'subjects',
                    'dashboards',
                    'reports',
                ]
            elif not endpoints:
                # Default: warm popular endpoints
                endpoints = [
                    'materials',
                    'subjects',
                ]

            stats = {
                'materials': 0,
                'subjects': 0,
                'dashboards': 0,
                'reports': 0,
            }

            # Warm each endpoint type
            for endpoint in endpoints:
                if endpoint == 'materials':
                    stats['materials'] = self._warm_materials(verbose)
                elif endpoint == 'subjects':
                    stats['subjects'] = self._warm_subjects(verbose)
                elif endpoint == 'dashboards':
                    stats['dashboards'] = self._warm_dashboards(verbose)
                elif endpoint == 'reports':
                    stats['reports'] = self._warm_reports(verbose)

            # Display summary
            self._print_summary(stats)

            self.stdout.write(self.style.SUCCESS('\n=== Cache Warming Completed ===\n'))

        except Exception as e:
            logger.exception(f'Cache warming failed: {e}')
            raise CommandError(f'Cache warming failed: {e}')

    def _warm_materials(self, verbose: bool) -> int:
        """Warm materials cache."""
        self.stdout.write('\n[1/4] Warming materials cache...')

        from materials.models import Material
        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS

        count = 0
        try:
            # Warm popular materials (top 20 by views or recent)
            materials = Material.objects.filter(
                status='published'
            ).prefetch_related(
                'assigned_to',
                'progress'
            ).select_related(
                'author',
                'subject'
            ).order_by('-updated_at')[:20]

            for material in materials:
                # Create cache key for material detail
                cache_key = CacheKeyBuilder.make_key(
                    'material_detail',
                    material.id
                )

                # Serialize material data
                from materials.serializers import MaterialDetailSerializer
                serializer = MaterialDetailSerializer(material)
                cache.set(
                    cache_key,
                    serializer.data,
                    CACHE_TIMEOUTS.get('material_detail', 3600)
                )

                count += 1
                if verbose:
                    self.stdout.write(
                        f'  - Warmed: {material.title}'
                    )

            # Warm materials list cache
            materials_list = Material.objects.filter(
                status='published'
            ).values('id', 'title', 'subject', 'type').order_by('-updated_at')[:50]

            cache_key = CacheKeyBuilder.make_key('materials', 'list')
            cache.set(
                cache_key,
                list(materials_list),
                CACHE_TIMEOUTS.get('materials_list', 1800)
            )

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Warmed {count} materials')
            )
            return count

        except Exception as e:
            logger.warning(f'Error warming materials: {e}')
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Error warming materials: {e}')
            )
            return count

    def _warm_subjects(self, verbose: bool) -> int:
        """Warm subjects cache."""
        self.stdout.write('\n[2/4] Warming subjects cache...')

        from materials.models import Subject
        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS

        count = 0
        try:
            # Warm all subjects
            subjects = Subject.objects.prefetch_related(
                'subject_teachers'
            ).order_by('name')

            for subject in subjects:
                # Create cache key for subject detail
                cache_key = CacheKeyBuilder.make_key(
                    'subject_detail',
                    subject.id
                )

                # Serialize subject data
                from materials.serializers import SubjectSerializer
                serializer = SubjectSerializer(subject)
                cache.set(
                    cache_key,
                    serializer.data,
                    CACHE_TIMEOUTS.get('long', 3600)
                )

                count += 1
                if verbose:
                    self.stdout.write(
                        f'  - Warmed: {subject.name}'
                    )

            # Warm subjects list cache
            subjects_list = Subject.objects.values('id', 'name', 'description').order_by('name')

            cache_key = CacheKeyBuilder.make_key('subjects', 'list')
            cache.set(
                cache_key,
                list(subjects_list),
                CACHE_TIMEOUTS.get('long', 3600)
            )

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Warmed {count} subjects')
            )
            return count

        except Exception as e:
            logger.warning(f'Error warming subjects: {e}')
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Error warming subjects: {e}')
            )
            return count

    def _warm_dashboards(self, verbose: bool) -> int:
        """Warm dashboard cache for active users."""
        self.stdout.write('\n[3/4] Warming dashboard cache...')

        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS
        from accounts.models import StudentProfile, TeacherProfile

        count = 0
        try:
            # Warm dashboards for active students (last 7 days)
            cutoff_date = timezone.now() - timezone.timedelta(days=7)
            active_students = StudentProfile.objects.filter(
                user__last_login__gte=cutoff_date
            ).select_related('user').order_by('-user__last_login')[:50]

            for student_profile in active_students:
                cache_key = CacheKeyBuilder.user_key(
                    'dashboard',
                    student_profile.user.id
                )

                # Create minimal dashboard data
                dashboard_data = {
                    'user_id': student_profile.user.id,
                    'role': 'student',
                    'cached_at': timezone.now().isoformat(),
                }

                cache.set(
                    cache_key,
                    dashboard_data,
                    CACHE_TIMEOUTS.get('dashboard', 300)
                )

                count += 1
                if verbose:
                    self.stdout.write(
                        f'  - Warmed student: {student_profile.user.email}'
                    )

            # Warm dashboards for active teachers
            active_teachers = TeacherProfile.objects.filter(
                user__last_login__gte=cutoff_date
            ).select_related('user').order_by('-user__last_login')[:30]

            for teacher_profile in active_teachers:
                cache_key = CacheKeyBuilder.user_key(
                    'dashboard',
                    teacher_profile.user.id
                )

                dashboard_data = {
                    'user_id': teacher_profile.user.id,
                    'role': 'teacher',
                    'cached_at': timezone.now().isoformat(),
                }

                cache.set(
                    cache_key,
                    dashboard_data,
                    CACHE_TIMEOUTS.get('dashboard', 300)
                )

                count += 1
                if verbose:
                    self.stdout.write(
                        f'  - Warmed teacher: {teacher_profile.user.email}'
                    )

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Warmed {count} dashboard caches')
            )
            return count

        except Exception as e:
            logger.warning(f'Error warming dashboards: {e}')
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Error warming dashboards: {e}')
            )
            return count

    def _warm_reports(self, verbose: bool) -> int:
        """Warm reports and analytics cache."""
        self.stdout.write('\n[4/4] Warming reports cache...')

        from config.cache import CacheKeyBuilder, CACHE_TIMEOUTS

        count = 0
        try:
            # Warm system-wide analytics cache
            analytics_cache_key = CacheKeyBuilder.make_key('analytics', 'system_overview')

            analytics_data = {
                'total_users': 0,
                'active_users': 0,
                'total_materials': 0,
                'avg_progress': 0.0,
                'cached_at': timezone.now().isoformat(),
            }

            cache.set(
                analytics_cache_key,
                analytics_data,
                CACHE_TIMEOUTS.get('analytics', 1800)
            )

            count += 1
            if verbose:
                self.stdout.write('  - Warmed: System analytics overview')

            # Warm recent reports cache
            reports_cache_key = CacheKeyBuilder.make_key('reports', 'recent')

            reports_data = {
                'recent_reports': [],
                'cached_at': timezone.now().isoformat(),
            }

            cache.set(
                reports_cache_key,
                reports_data,
                CACHE_TIMEOUTS.get('analytics', 1800)
            )

            count += 1
            if verbose:
                self.stdout.write('  - Warmed: Recent reports list')

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Warmed {count} analytics caches')
            )
            return count

        except Exception as e:
            logger.warning(f'Error warming reports: {e}')
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Error warming reports: {e}')
            )
            return count

    def _print_summary(self, stats: dict):
        """Print warming summary."""
        self.stdout.write('\n=== Summary ===\n')

        total = sum(stats.values())
        self.stdout.write(f'Materials:   {stats["materials"]:>3} items')
        self.stdout.write(f'Subjects:    {stats["subjects"]:>3} items')
        self.stdout.write(f'Dashboards:  {stats["dashboards"]:>3} items')
        self.stdout.write(f'Reports:     {stats["reports"]:>3} items')
        self.stdout.write('-' * 30)
        self.stdout.write(f'Total:       {total:>3} cached items')
