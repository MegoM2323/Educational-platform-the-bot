"""
Utility functions for database maintenance operations.

Provides helper functions for:
- Detecting database type (PostgreSQL vs SQLite)
- Getting database statistics
- Checking for locks
- Executing maintenance operations safely
- Monitoring bloat and unused space
"""

from django.db import connection
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseInfo:
    """Information about the connected database"""

    def __init__(self):
        """Initialize database info from current connection"""
        self.settings = connection.settings_dict
        self.engine = self.settings.get('ENGINE', '')
        self.name = self.settings.get('NAME', '')
        self.host = self.settings.get('HOST', 'localhost')
        self.port = self.settings.get('PORT', '5432')
        self.user = self.settings.get('USER', 'postgres')

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL"""
        return 'postgres' in self.engine.lower()

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite"""
        return 'sqlite' in self.engine.lower()

    @property
    def database_type(self) -> str:
        """Get database type name"""
        if self.is_postgresql:
            return 'PostgreSQL'
        elif self.is_sqlite:
            return 'SQLite'
        else:
            return 'Unknown'

    def __str__(self) -> str:
        """String representation"""
        return f"{self.database_type} - {self.name}"


class MaintenanceUtils:
    """Utilities for database maintenance operations"""

    @staticmethod
    def get_database_info() -> DatabaseInfo:
        """Get information about connected database"""
        return DatabaseInfo()

    @staticmethod
    def get_database_size() -> Dict[str, Any]:
        """
        Get total database size.

        PostgreSQL: Uses pg_database_size()
        SQLite: Uses file size
        """
        db_info = DatabaseInfo()

        if db_info.is_postgresql:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            pg_database.datname,
                            pg_size_pretty(pg_database_size(pg_database.datname)) AS size,
                            pg_database_size(pg_database.datname) AS bytes
                        FROM pg_database
                        WHERE datname = current_database();
                    """)
                    result = cursor.fetchone()
                    if result:
                        return {
                            'database': result[0],
                            'size_human': result[1],
                            'size_bytes': result[2]
                        }
            except Exception as e:
                logger.error(f"Error getting database size: {e}")

        elif db_info.is_sqlite:
            import os
            try:
                if os.path.exists(db_info.name):
                    size = os.path.getsize(db_info.name)
                    return {
                        'database': db_info.name,
                        'size_bytes': size,
                        'size_human': MaintenanceUtils._bytes_to_human(size)
                    }
            except Exception as e:
                logger.error(f"Error getting SQLite size: {e}")

        return {'error': 'Could not determine database size'}

    @staticmethod
    def get_table_sizes() -> List[Dict[str, Any]]:
        """
        Get sizes of all tables in the database.

        PostgreSQL only.
        """
        db_info = DatabaseInfo()

        if not db_info.is_postgresql:
            return []

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as bytes,
                        (SELECT count(*) FROM information_schema.columns
                         WHERE table_name = tablename AND table_schema = schemaname) as column_count
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting table sizes: {e}")
            return []

    @staticmethod
    def get_index_info() -> List[Dict[str, Any]]:
        """
        Get information about indexes.

        PostgreSQL only.
        """
        db_info = DatabaseInfo()

        if not db_info.is_postgresql:
            return []

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        schemaname,
                        indexname,
                        tablename,
                        pg_size_pretty(pg_relation_size(indexrelid)) as size,
                        pg_relation_size(indexrelid) as bytes,
                        idx_scan as scans
                    FROM pg_indexes
                    JOIN pg_stat_user_indexes
                        ON pg_indexes.indexname = pg_stat_user_indexes.indexrelname
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY pg_relation_size(indexrelid) DESC;
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting index info: {e}")
            return []

    @staticmethod
    def get_unused_indexes() -> List[Dict[str, Any]]:
        """
        Find unused indexes that could be removed.

        PostgreSQL only.
        """
        db_info = DatabaseInfo()

        if not db_info.is_postgresql:
            return []

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        pg_size_pretty(pg_relation_size(indexrelid)) as size,
                        idx_scan as scans
                    FROM pg_stat_user_indexes
                    WHERE idx_scan = 0
                    AND indexrelname NOT LIKE 'pg_toast%'
                    ORDER BY pg_relation_size(indexrelid) DESC;
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error finding unused indexes: {e}")
            return []

    @staticmethod
    def get_active_connections() -> Dict[str, Any]:
        """
        Get information about active database connections.

        PostgreSQL only.
        """
        db_info = DatabaseInfo()

        if not db_info.is_postgresql:
            return {'message': 'PostgreSQL only'}

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        count(*) as total,
                        sum(case when state = 'active' then 1 else 0 end) as active,
                        sum(case when state = 'idle' then 1 else 0 end) as idle
                    FROM pg_stat_activity
                    WHERE datname = current_database();
                """)
                result = cursor.fetchone()
                if result:
                    return {
                        'total': result[0],
                        'active': result[1],
                        'idle': result[2]
                    }
        except Exception as e:
            logger.error(f"Error getting connections: {e}")

        return {}

    @staticmethod
    def get_long_running_queries(minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Get long-running queries that might need attention.

        PostgreSQL only.
        """
        db_info = DatabaseInfo()

        if not db_info.is_postgresql:
            return []

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT
                        pid,
                        usename,
                        application_name,
                        query,
                        now() - query_start as duration,
                        query_start,
                        state
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    AND query_start < now() - interval '{minutes} minutes'
                    ORDER BY query_start;
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting long running queries: {e}")
            return []

    @staticmethod
    def check_for_locks() -> Dict[str, Any]:
        """
        Check if there are any locks that might interfere with maintenance.

        PostgreSQL only.
        """
        db_info = DatabaseInfo()

        if not db_info.is_postgresql:
            return {'message': 'PostgreSQL only'}

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        l.locktype,
                        l.relation,
                        l.mode,
                        l.pid,
                        a.usename,
                        a.query
                    FROM pg_locks l
                    JOIN pg_stat_activity a ON l.pid = a.pid
                    WHERE l.granted = false
                    ORDER BY a.query_start;
                """)
                columns = [col[0] for col in cursor.description]
                locks = [dict(zip(columns, row)) for row in cursor.fetchall()]

                return {
                    'has_locks': len(locks) > 0,
                    'lock_count': len(locks),
                    'locks': locks
                }
        except Exception as e:
            logger.error(f"Error checking locks: {e}")
            return {}

    @staticmethod
    def estimate_maintenance_time(operation: str) -> Dict[str, Any]:
        """
        Estimate how long maintenance operation will take.

        Based on database size and current load.
        """
        db_info = DatabaseInfo()
        db_size = MaintenanceUtils.get_database_size()
        connections = MaintenanceUtils.get_active_connections()

        size_bytes = db_size.get('size_bytes', 0)
        active_connections = connections.get('active', 0)

        # Estimates based on empirical data
        estimates = {
            'vacuum': {
                'base_seconds': 60,
                'per_gb': 300,
                'per_connection': 10
            },
            'reindex': {
                'base_seconds': 30,
                'per_gb': 150,
                'per_connection': 5
            },
            'analyze': {
                'base_seconds': 30,
                'per_gb': 100,
                'per_connection': 2
            }
        }

        if operation not in estimates:
            return {'error': f'Unknown operation: {operation}'}

        est = estimates[operation]
        size_gb = size_bytes / (1024 ** 3)

        estimated_seconds = (
            est['base_seconds'] +
            (est['per_gb'] * size_gb) +
            (est['per_connection'] * active_connections)
        )

        return {
            'operation': operation,
            'estimated_seconds': int(estimated_seconds),
            'database_size_gb': round(size_gb, 2),
            'active_connections': active_connections
        }

    @staticmethod
    def _bytes_to_human(bytes_size: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.2f} PB"

    @staticmethod
    def get_maintenance_report() -> Dict[str, Any]:
        """
        Generate a comprehensive maintenance report.

        Includes database size, table sizes, index information,
        unused indexes, and active connections.
        """
        db_info = DatabaseInfo()

        report = {
            'timestamp': datetime.now().isoformat(),
            'database': str(db_info),
            'database_size': MaintenanceUtils.get_database_size(),
            'active_connections': MaintenanceUtils.get_active_connections(),
            'long_running_queries': MaintenanceUtils.get_long_running_queries(),
            'locks': MaintenanceUtils.check_for_locks(),
        }

        if db_info.is_postgresql:
            report['table_sizes'] = MaintenanceUtils.get_table_sizes()
            report['index_info'] = MaintenanceUtils.get_index_info()
            report['unused_indexes'] = MaintenanceUtils.get_unused_indexes()

        return report
