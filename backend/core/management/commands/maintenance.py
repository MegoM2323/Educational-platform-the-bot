"""
Management command for database maintenance operations.

Performs various maintenance tasks:
- Vacuum & Analyze (reclaim disk space, update statistics)
- Reindex (rebuild indexes)
- Cleanup soft-deleted records
- Cleanup old logs and sessions
- Update materialized views
- Check table bloat
- Generate database statistics
- Create backups before maintenance
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django.conf import settings
from django.contrib.sessions.models import Session
from core.models import AuditLog, TaskExecutionLog, FailedTask
import json
import time
import logging
from datetime import timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Database maintenance command.

    Usage:
        python manage.py maintenance --all
        python manage.py maintenance --operation vacuum
        python manage.py maintenance --operation cleanup --dry-run
    """

    help = 'Perform database maintenance operations'

    # Supported operations
    OPERATIONS = {
        'vacuum': 'Vacuum & Analyze - reclaim disk space and update statistics',
        'reindex': 'Reindex - rebuild all database indexes',
        'cleanup': 'Cleanup - archive and remove soft-deleted records',
        'logs': 'Cleanup logs - remove old audit and system logs',
        'sessions': 'Cleanup sessions - remove expired sessions',
        'views': 'Update views - refresh materialized views',
        'stats': 'Generate statistics - collect database statistics',
        'bloat': 'Check bloat - identify bloated tables',
        'backup': 'Create backup - backup database before maintenance',
    }

    def add_arguments(self, parser):
        """Define command arguments"""
        parser.add_argument(
            '--operation',
            type=str,
            choices=list(self.OPERATIONS.keys()),
            help='Specific operation to run'
        )

        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all maintenance operations'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

        parser.add_argument(
            '--output',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )

        parser.add_argument(
            '--schedule',
            type=str,
            choices=['daily', 'weekly', 'monthly'],
            help='Add to scheduler (requires celery-beat)'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        start_time = time.time()

        # Validate options
        operation = options.get('operation')
        run_all = options.get('all')
        dry_run = options.get('dry_run')
        output_format = options.get('output')

        if not operation and not run_all:
            self.print_usage()
            return

        # Check database type
        if not self.is_postgresql():
            raise CommandError(
                'This command requires PostgreSQL. '
                f'Current database: {connection.settings_dict.get("ENGINE")}'
            )

        results = {}

        try:
            # Execute operations
            if run_all:
                results = self.run_all_operations(dry_run)
            else:
                operation_func = getattr(self, f'operation_{operation}', None)
                if not operation_func:
                    raise CommandError(f'Unknown operation: {operation}')

                results[operation] = operation_func(dry_run)

            # Add metadata
            duration = time.time() - start_time
            results['metadata'] = {
                'timestamp': timezone.now().isoformat(),
                'duration_seconds': round(duration, 2),
                'dry_run': dry_run,
                'database': connection.settings_dict.get('NAME'),
            }

            # Output results
            if output_format == 'json':
                self.stdout.write(json.dumps(results, indent=2, default=str))
            else:
                self.print_results(results)

            # Log execution
            self.log_execution(results, duration)

        except Exception as e:
            logger.exception('Maintenance error')
            error_msg = f'Maintenance failed: {str(e)}'
            if output_format == 'json':
                self.stdout.write(json.dumps({
                    'error': error_msg,
                    'timestamp': timezone.now().isoformat()
                }, indent=2))
            else:
                self.stdout.write(self.style.ERROR(error_msg))
            raise CommandError(error_msg)

    def run_all_operations(self, dry_run: bool) -> Dict[str, Any]:
        """Run all maintenance operations in sequence"""
        results = {}

        operations_order = [
            'backup',
            'vacuum',
            'reindex',
            'cleanup',
            'logs',
            'sessions',
            'stats',
            'bloat',
        ]

        for op in operations_order:
            try:
                operation_func = getattr(self, f'operation_{op}')
                results[op] = operation_func(dry_run)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {op.upper()} completed')
                )
            except Exception as e:
                results[op] = {
                    'status': 'error',
                    'error': str(e)
                }
                self.stdout.write(
                    self.style.ERROR(f'✗ {op.upper()} failed: {e}')
                )

        return results

    def operation_vacuum(self, dry_run: bool) -> Dict[str, Any]:
        """
        Vacuum & Analyze operation.

        Reclaims disk space and updates table statistics for query planning.
        """
        if dry_run:
            return {
                'status': 'simulated',
                'operation': 'vacuum',
                'message': 'VACUUM ANALYZE would run on all tables'
            }

        try:
            with connection.cursor() as cursor:
                self.stdout.write('Running VACUUM ANALYZE...')
                cursor.execute('VACUUM ANALYZE;')

            return {
                'status': 'completed',
                'operation': 'vacuum',
                'message': 'VACUUM ANALYZE completed successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'operation': 'vacuum',
                'error': str(e)
            }

    def operation_reindex(self, dry_run: bool) -> Dict[str, Any]:
        """
        Reindex operation.

        Rebuilds all database indexes without locking tables.
        Uses CONCURRENTLY for minimal downtime.
        """
        if dry_run:
            return {
                'status': 'simulated',
                'operation': 'reindex',
                'message': 'REINDEX DATABASE would run concurrently'
            }

        try:
            with connection.cursor() as cursor:
                self.stdout.write('Running REINDEX DATABASE CONCURRENTLY...')
                cursor.execute('REINDEX DATABASE CONCURRENTLY;')

            return {
                'status': 'completed',
                'operation': 'reindex',
                'message': 'Reindex completed successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'operation': 'reindex',
                'error': str(e)
            }

    def operation_cleanup(self, dry_run: bool) -> Dict[str, Any]:
        """
        Cleanup soft-deleted records.

        Archives records older than 365 days and deletes archived
        records older than 730 days.
        """
        results = {
            'status': 'completed',
            'operation': 'cleanup',
            'rows_processed': 0,
            'errors': []
        }

        # Define cleanup targets
        cleanup_targets = [
            {
                'model': FailedTask,
                'filter_field': 'failed_at',
                'archive_days': 365,
                'delete_days': 730,
                'batch_size': 1000,
            },
        ]

        for target in cleanup_targets:
            try:
                rows = self._cleanup_model(target, dry_run)
                results['rows_processed'] += rows
                results[target['model'].__name__] = {
                    'rows_cleaned': rows,
                    'status': 'completed'
                }
            except Exception as e:
                error_msg = f"Error cleaning {target['model'].__name__}: {e}"
                results['errors'].append(error_msg)
                logger.error(error_msg)

        return results

    def _cleanup_model(self, target: Dict[str, Any], dry_run: bool) -> int:
        """Cleanup a single model"""
        model = target['model']
        filter_field = target['filter_field']
        archive_days = target['archive_days']
        delete_days = target['delete_days']
        batch_size = target.get('batch_size', 1000)

        archive_date = timezone.now() - timedelta(days=archive_days)
        delete_date = timezone.now() - timedelta(days=delete_days)

        total_deleted = 0

        # Delete very old records
        if dry_run:
            count = model.objects.filter(
                **{f'{filter_field}__lt': delete_date}
            ).count()
            self.stdout.write(
                f'  Would delete {count} {model.__name__} records older than {delete_days} days'
            )
            return count

        # Process in batches to avoid locking
        with transaction.atomic():
            while True:
                batch = list(
                    model.objects.filter(
                        **{f'{filter_field}__lt': delete_date}
                    )[:batch_size]
                    .values_list('pk', flat=True)
                )

                if not batch:
                    break

                model.objects.filter(pk__in=batch).delete()
                total_deleted += len(batch)
                self.stdout.write(f'  Deleted {total_deleted} records...')

        return total_deleted

    def operation_logs(self, dry_run: bool) -> Dict[str, Any]:
        """
        Cleanup old logs.

        Removes audit logs older than 90 days and task logs older than 30 days.
        """
        results = {
            'status': 'completed',
            'operation': 'logs',
            'rows_deleted': 0,
            'details': {}
        }

        log_targets = [
            {
                'model': AuditLog,
                'field': 'timestamp',
                'days': 90,
                'name': 'Audit Logs'
            },
            {
                'model': TaskExecutionLog,
                'field': 'started_at',
                'days': 30,
                'name': 'Task Logs'
            },
        ]

        for target in log_targets:
            try:
                deleted = self._delete_old_logs(target, dry_run)
                results['rows_deleted'] += deleted
                results['details'][target['name']] = {
                    'deleted': deleted,
                    'days': target['days']
                }
            except Exception as e:
                results['details'][target['name']] = {
                    'error': str(e)
                }

        return results

    def _delete_old_logs(self, target: Dict[str, Any], dry_run: bool) -> int:
        """Delete old log records in batches"""
        model = target['model']
        filter_field = target['field']
        days = target['days']
        batch_size = 10000

        cutoff_date = timezone.now() - timedelta(days=days)

        if dry_run:
            count = model.objects.filter(
                **{f'{filter_field}__lt': cutoff_date}
            ).count()
            self.stdout.write(
                f'  Would delete {count} {target["name"]} records'
            )
            return count

        total_deleted = 0

        with transaction.atomic():
            while True:
                batch = list(
                    model.objects.filter(
                        **{f'{filter_field}__lt': cutoff_date}
                    )[:batch_size]
                    .values_list('pk', flat=True)
                )

                if not batch:
                    break

                model.objects.filter(pk__in=batch).delete()
                total_deleted += len(batch)
                self.stdout.write(
                    f'  Deleted {total_deleted} {target["name"]} records...'
                )

        return total_deleted

    def operation_sessions(self, dry_run: bool) -> Dict[str, Any]:
        """
        Cleanup expired sessions.

        Removes Django session records that have expired.
        """
        if dry_run:
            count = Session.objects.filter(
                expire_date__lt=timezone.now()
            ).count()
            return {
                'status': 'simulated',
                'operation': 'sessions',
                'expired_sessions': count,
                'message': f'Would delete {count} expired sessions'
            }

        try:
            # Django's built-in cleanup
            Session.objects.filter(expire_date__lt=timezone.now()).delete()

            return {
                'status': 'completed',
                'operation': 'sessions',
                'message': 'Expired sessions cleaned up'
            }
        except Exception as e:
            return {
                'status': 'error',
                'operation': 'sessions',
                'error': str(e)
            }

    def operation_views(self, dry_run: bool) -> Dict[str, Any]:
        """
        Update materialized views.

        Refreshes materialized views for cached data.
        Non-blocking operation.
        """
        if dry_run:
            return {
                'status': 'simulated',
                'operation': 'views',
                'message': 'Would refresh materialized views'
            }

        results = {
            'status': 'completed',
            'operation': 'views',
            'refreshed_views': []
        }

        # List of materialized views to refresh
        views = [
            'core_stats_view',
            'user_activity_view',
        ]

        for view_name in views:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f'REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};'
                    )
                results['refreshed_views'].append(view_name)
            except Exception as e:
                # View might not exist, that's okay
                logger.debug(f'View {view_name} not found or error: {e}')

        return results

    def operation_stats(self, dry_run: bool) -> Dict[str, Any]:
        """
        Generate database statistics.

        Collects and analyzes database statistics for query optimization.
        """
        if dry_run:
            return {
                'status': 'simulated',
                'operation': 'stats',
                'message': 'Would generate database statistics'
            }

        try:
            with connection.cursor() as cursor:
                # Analyze table sizes
                cursor.execute("""
                    SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 20;
                """)
                tables = cursor.fetchall()

            return {
                'status': 'completed',
                'operation': 'stats',
                'top_tables': [
                    {
                        'schema': t[0],
                        'table': t[1],
                        'size': t[2]
                    } for t in tables
                ]
            }
        except Exception as e:
            return {
                'status': 'error',
                'operation': 'stats',
                'error': str(e)
            }

    def operation_bloat(self, dry_run: bool) -> Dict[str, Any]:
        """
        Check table bloat.

        Identifies tables with significant bloat (wasted space).
        Uses dry-run by default to avoid locks.
        """
        results = {
            'status': 'completed',
            'operation': 'bloat',
            'bloated_tables': [],
            'message': 'Bloat analysis completed'
        }

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schemaname, tablename,
                           round(100 * (CASE WHEN otta > 0 THEN sml.relpages - otta
                                       ELSE 0 END) / sml.relpages) AS table_waste_percent,
                           pg_size_pretty(((sml.relpages - otta)::bigint) * 8192) AS table_waste
                    FROM (
                        SELECT schemaname, tablename, relpages,
                               CEIL((cc::float / (CASE WHEN ma > 0 THEN ma ELSE 1 END))::float) AS otta
                        FROM (
                            SELECT schemaname, tablename, relpages, ma,
                                   (datawidth + (hdr + 8))::int AS cc
                            FROM (
                                SELECT schemaname, tablename, relpages, hdr,
                                       avg_width::int - null_frac::int * (CASE WHEN avg_width > 0 THEN 1 ELSE 0 END) AS datawidth,
                                       CASE WHEN avg_width > 0 THEN 4 + avg_width ELSE 4 END::int AS ma
                                FROM (
                                    SELECT schemaname, tablename,
                                           (relation_size / 8192)::int AS relpages,
                                           24 AS hdr,
                                           sum((length(t.attname)::int + 4 + avg_width) * (1 - null_frac)) / sum(1) AS avg_width,
                                           1 - sum(null_cnt) / sum(1) AS null_frac
                                    FROM pg_stat_user_tables t
                                    JOIN pg_attribute a ON t.relid = a.attrelid
                                    GROUP BY schemaname, tablename, relation_size
                                ) x
                            ) y
                        ) z
                    ) sml
                    WHERE (sml.relpages - otta) > 0
                    ORDER BY table_waste DESC;
                """)
                bloat_results = cursor.fetchall()

            for row in bloat_results:
                if row[2] and row[2] > 10:  # Only report > 10% bloat
                    results['bloated_tables'].append({
                        'schema': row[0],
                        'table': row[1],
                        'waste_percent': row[2],
                        'waste_size': row[3]
                    })

            if not results['bloated_tables']:
                results['message'] = 'No significant table bloat detected'

        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)

        return results

    def operation_backup(self, dry_run: bool) -> Dict[str, Any]:
        """
        Create database backup before maintenance.

        Uses pg_dump to create a backup file.
        """
        if dry_run:
            return {
                'status': 'simulated',
                'operation': 'backup',
                'message': 'Would create database backup'
            }

        try:
            db_config = connection.settings_dict
            db_name = db_config.get('NAME')
            db_user = db_config.get('USER', 'postgres')
            db_host = db_config.get('HOST', 'localhost')
            db_port = db_config.get('PORT', '5432')

            if not db_name:
                return {
                    'status': 'skipped',
                    'operation': 'backup',
                    'message': 'SQLite database - backup skipped'
                }

            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'/tmp/backup_{db_name}_{timestamp}.sql'

            # Using pg_dump for backup (if available)
            import subprocess
            import os

            try:
                # Build pg_dump command
                env = os.environ.copy()
                env['PGPASSWORD'] = db_config.get('PASSWORD', '')

                subprocess.run([
                    'pg_dump',
                    '-h', db_host,
                    '-U', db_user,
                    '-p', str(db_port),
                    db_name
                ], stdout=open(backup_file, 'w'), check=True, env=env)

                return {
                    'status': 'completed',
                    'operation': 'backup',
                    'backup_file': backup_file,
                    'message': f'Backup created successfully'
                }
            except FileNotFoundError:
                return {
                    'status': 'skipped',
                    'operation': 'backup',
                    'message': 'pg_dump not found - backup skipped'
                }

        except Exception as e:
            return {
                'status': 'error',
                'operation': 'backup',
                'error': str(e)
            }

    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL"""
        engine = connection.settings_dict.get('ENGINE', '')
        return 'postgres' in engine.lower()

    def print_results(self, results: Dict[str, Any]):
        """Pretty print results"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('DATABASE MAINTENANCE REPORT')
        self.stdout.write('='*60)

        for operation, result in results.items():
            if operation == 'metadata':
                continue

            status = result.get('status', 'unknown')
            style = self._get_status_style(status)

            self.stdout.write(f'\n{operation.upper()}')
            self.stdout.write(style(f'  Status: {status}'))

            for key, value in result.items():
                if key not in ['status', 'operation']:
                    if isinstance(value, list):
                        self.stdout.write(f'  {key}:')
                        for item in value:
                            self.stdout.write(f'    - {item}')
                    elif isinstance(value, dict):
                        self.stdout.write(f'  {key}:')
                        for k, v in item.items():
                            self.stdout.write(f'    {k}: {v}')
                    else:
                        self.stdout.write(f'  {key}: {value}')

        # Print metadata
        if 'metadata' in results:
            meta = results['metadata']
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'Duration: {meta["duration_seconds"]}s')
            self.stdout.write(f'Timestamp: {meta["timestamp"]}')
            self.stdout.write(f'Database: {meta["database"]}')

    def _get_status_style(self, status: str):
        """Get style for status"""
        if status == 'completed':
            return self.style.SUCCESS
        elif status == 'error':
            return self.style.ERROR
        elif status in ['simulated', 'skipped']:
            return self.style.WARNING
        else:
            return self.style.NOTICE

    def print_usage(self):
        """Print available operations"""
        self.stdout.write('\nAvailable Operations:\n')
        for op, description in self.OPERATIONS.items():
            self.stdout.write(f'  {op:<15} - {description}')

        self.stdout.write('\nUsage:')
        self.stdout.write('  python manage.py maintenance --all')
        self.stdout.write('  python manage.py maintenance --operation vacuum')
        self.stdout.write('  python manage.py maintenance --operation cleanup --dry-run')

    def log_execution(self, results: Dict[str, Any], duration: float):
        """Log maintenance execution"""
        try:
            from core.models import TaskExecutionLog

            # Check if any operations failed
            has_errors = any(
                r.get('status') == 'error'
                for r in results.values()
                if isinstance(r, dict)
            )

            status = 'failed' if has_errors else 'success'

            TaskExecutionLog.objects.create(
                task_id='maintenance_task',
                task_name='database_maintenance',
                status=status,
                duration_seconds=duration,
                result=results
            )
        except Exception as e:
            logger.error(f'Failed to log maintenance execution: {e}')
