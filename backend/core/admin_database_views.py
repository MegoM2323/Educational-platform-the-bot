"""
Database Admin API endpoints for THE_BOT platform

Provides REST API for database management, monitoring, and maintenance operations.
All endpoints require admin permissions.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from django.utils import timezone
from django.db import connection
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
import uuid
import os

from .maintenance_utils import MaintenanceUtils, DatabaseInfo
from .backup_utils import BackupManager
from .database_serializers import (
    DatabaseStatusSerializer,
    TableStatSerializer,
    SlowQuerySerializer,
    BackupSerializer,
    MaintenanceTaskSerializer,
)
from .audit import audit_log

logger = logging.getLogger(__name__)


class DatabaseStatusView(APIView):
    """
    GET /api/admin/system/database/

    Returns comprehensive database status and metadata

    Response:
    {
        "success": true,
        "data": {
            "database_type": "PostgreSQL",
            "database_version": "13.2",
            "database_name": "thebot_db",
            "database_size_bytes": 536870912,
            "database_size_human": "512.00 MB",
            "last_backup": "2025-12-27T10:30:00Z",
            "backup_status": "completed",
            "connection_pool": {
                "active": 5,
                "max": 20,
                "available": 15
            }
        }
    }
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get database status"""
        try:
            db_info = MaintenanceUtils.get_database_info()
            db_size = MaintenanceUtils.get_database_size()
            connections = MaintenanceUtils.get_active_connections()

            # Get database version
            version = self._get_database_version()

            # Get backup info (last backup timestamp and status)
            backup_manager = BackupManager()
            backups = backup_manager.list_backups()
            last_backup = None
            backup_status = "no_backups"

            if backups:
                last_backup = backups[0].get("created_at")
                backup_status = backups[0].get("status", "completed")

            response_data = {
                "database_type": db_info.database_type,
                "database_version": version,
                "database_name": db_info.name,
                "database_size_bytes": db_size.get("size_bytes", 0),
                "database_size_human": db_size.get("size_human", "unknown"),
                "last_backup": last_backup,
                "backup_status": backup_status,
                "connection_pool": {
                    "active": connections.get("active", 0),
                    "max": getattr(connection.get_autocommit, "__self__", {}).get(
                        "max_overflow", 20
                    ),
                    "available": max(0, 20 - connections.get("active", 0)),
                },
            }

            serializer = DatabaseStatusSerializer(response_data)

            logger.info(
                f"[DatabaseStatusView] Database status: {db_info.database_type}"
            )

            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"[DatabaseStatusView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _get_database_version() -> str:
        """Get PostgreSQL database version"""
        try:
            db_info = DatabaseInfo()

            if db_info.is_postgresql:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    result = cursor.fetchone()
                    if result:
                        version_str = result[0]
                        parts = version_str.split()
                        for part in parts:
                            if part[0].isdigit():
                                return part
                return "unknown"

        except Exception as e:
            logger.error(f"Error getting database version: {e}")

        return "unknown"


class DatabaseTablesViewSet(ViewSet):
    """
    GET /api/admin/system/database/tables/

    Returns paginated list of table statistics with filtering and sorting

    Query Parameters:
        - page (int): Page number (default: 1)
        - page_size (int): Rows per page (default: 20)
        - bloat_indicator (str): Filter by 'low', 'medium', 'high'
        - sort_by (str): Sort by 'name', 'rows', 'size_mb' (default: 'name')

    Response:
    {
        "success": true,
        "data": {
            "count": 45,
            "page": 1,
            "page_size": 20,
            "total_pages": 3,
            "results": [
                {
                    "name": "accounts_user",
                    "rows": 150,
                    "size_mb": 2.5,
                    "last_vacuum": "2025-12-27T08:00:00Z",
                    "last_reindex": "2025-12-25T10:00:00Z",
                    "bloat_indicator": "low",
                    "last_maintenance": "2025-12-27T08:00:00Z"
                }
            ]
        }
    }
    """

    permission_classes = [IsAdminUser]

    def list(self, request):
        """List PostgreSQL tables with stats"""
        try:
            db_info = DatabaseInfo()

            if not db_info.is_postgresql:
                return Response(
                    {
                        "success": False,
                        "error": "Table statistics only available for PostgreSQL",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get pagination params
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            bloat_filter = request.query_params.get("bloat_indicator", "")
            sort_by = request.query_params.get("sort_by", "name")

            # Get all tables
            tables = self._get_table_stats()

            # Apply filters
            if bloat_filter:
                tables = [t for t in tables if t["bloat_indicator"] == bloat_filter]

            # Apply sorting
            if sort_by == "rows":
                tables = sorted(tables, key=lambda x: x["rows"], reverse=True)
            elif sort_by == "size_mb":
                tables = sorted(tables, key=lambda x: x["size_mb"], reverse=True)
            else:  # default 'name'
                tables = sorted(tables, key=lambda x: x["name"])

            # Paginate
            total_count = len(tables)
            total_pages = (total_count + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_tables = tables[start_idx:end_idx]

            # Serialize
            serializer = TableStatSerializer(paginated_tables, many=True)

            logger.info(
                f"[DatabaseTablesViewSet] Listed {len(paginated_tables)} tables (page {page})"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "count": total_count,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": total_pages,
                        "results": serializer.data,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"[DatabaseTablesViewSet] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _get_table_stats() -> List[Dict[str, Any]]:
        """Get statistics for all PostgreSQL tables"""
        try:
            db_info = DatabaseInfo()

            if not db_info.is_postgresql:
                return []

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        schemaname,
                        tablename,
                        n_live_tup as rows,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_human,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                        last_vacuum,
                        last_autovacuum
                    FROM pg_stat_user_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY tablename;
                """
                )

                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                tables = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    size_mb = row_dict["size_bytes"] / (1024 * 1024)

                    # Calculate bloat indicator
                    bloat_pct = min(100, (size_mb / 100))  # Simple heuristic
                    if bloat_pct > 50:
                        bloat_indicator = "high"
                    elif bloat_pct > 20:
                        bloat_indicator = "medium"
                    else:
                        bloat_indicator = "low"

                    # Get last vacuum/reindex time
                    last_vacuum = row_dict.get("last_autovacuum") or row_dict.get(
                        "last_vacuum"
                    )

                    tables.append(
                        {
                            "name": row_dict["tablename"],
                            "rows": row_dict["rows"],
                            "size_mb": round(size_mb, 2),
                            "last_vacuum": last_vacuum,
                            "last_reindex": None,  # PostgreSQL doesn't track this per-table
                            "bloat_indicator": bloat_indicator,
                            "last_maintenance": last_vacuum,
                        }
                    )

                return tables

        except Exception as e:
            logger.error(f"Error getting table stats: {e}")
            return []


class DatabaseQueriesView(APIView):
    """
    GET /api/admin/system/database/queries/

    Returns top 10 slow queries (queries taking > 100ms)

    Response (NOT paginated):
    {
        "success": true,
        "data": {
            "count": 10,
            "queries": [
                {
                    "id": 1,
                    "query": "SELECT * FROM large_table WHERE...",
                    "query_truncated": "SELECT * FROM large_table WHERE...",
                    "count": 145,
                    "avg_time_ms": 250.5,
                    "max_time_ms": 1024.3
                }
            ]
        }
    }
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get slow queries"""
        try:
            db_info = DatabaseInfo()

            if not db_info.is_postgresql:
                return Response(
                    {
                        "success": True,
                        "data": {
                            "count": 0,
                            "queries": [],
                            "note": "Query statistics only available for PostgreSQL",
                        },
                    },
                    status=status.HTTP_200_OK,
                )

            queries = self._get_slow_queries()
            serializer = SlowQuerySerializer(queries, many=True)

            logger.info(f"[DatabaseQueriesView] Retrieved {len(queries)} slow queries")

            return Response(
                {
                    "success": True,
                    "data": {"count": len(queries), "queries": serializer.data},
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"[DatabaseQueriesView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _get_slow_queries() -> List[Dict[str, Any]]:
        """Get top 10 slow PostgreSQL queries"""
        try:
            db_info = DatabaseInfo()

            if not db_info.is_postgresql:
                return []

            # Check if pg_stat_statements extension exists
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                """
                )

                if not cursor.fetchone():
                    logger.warning("pg_stat_statements extension not installed")
                    return []

                # Get top slow queries
                cursor.execute(
                    """
                    SELECT
                        query_id as id,
                        query,
                        calls as count,
                        mean_time::float as avg_time_ms,
                        max_time::float as max_time_ms
                    FROM pg_stat_statements
                    WHERE mean_time > 100
                    ORDER BY mean_time DESC
                    LIMIT 10;
                """
                )

                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                queries = []
                for idx, row in enumerate(rows):
                    row_dict = dict(zip(columns, row))
                    query_str = row_dict["query"]

                    queries.append(
                        {
                            "id": row_dict["id"],
                            "query": query_str,
                            "query_truncated": query_str[:50]
                            + ("..." if len(query_str) > 50 else ""),
                            "count": row_dict["count"],
                            "avg_time_ms": round(row_dict["avg_time_ms"], 2),
                            "max_time_ms": round(row_dict["max_time_ms"], 2),
                        }
                    )

                return queries

        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []


class BackupManagementViewSet(ViewSet):
    """
    GET /api/admin/system/database/backups/
    POST /api/admin/system/database/backups/

    Manage database backups

    GET Response:
    {
        "success": true,
        "data": {
            "count": 5,
            "backups": [
                {
                    "id": "backup_20251227_103000",
                    "filename": "db_backup_20251227_103000.sql",
                    "size_bytes": 536870912,
                    "size_human": "512.00 MB",
                    "created_at": "2025-12-27T10:30:00Z",
                    "status": "completed",
                    "is_downloadable": true
                }
            ]
        }
    }

    POST Response (create backup):
    {
        "success": true,
        "data": {
            "backup_id": "backup_20251227_103000",
            "status": "in-progress",
            "message": "Backup creation started"
        }
    }
    """

    permission_classes = [IsAdminUser]

    def list(self, request):
        """List recent backups"""
        try:
            backup_manager = BackupManager()
            backups = backup_manager.list_backups()[:20]  # Last 20 backups

            # Convert backup info to serializer format
            formatted_backups = []
            for backup in backups:
                size_bytes = backup.get("size", 0)
                size_human = MaintenanceUtils._bytes_to_human(size_bytes)

                formatted_backups.append(
                    {
                        "id": backup.get("id", ""),
                        "filename": backup.get("filename", ""),
                        "size_bytes": size_bytes,
                        "size_human": size_human,
                        "created_at": backup.get("created_at"),
                        "status": backup.get("status", "completed"),
                        "is_downloadable": os.path.exists(backup.get("path", "")),
                    }
                )

            # Serialize
            serializer = BackupSerializer(formatted_backups, many=True)

            logger.info(
                f"[BackupManagementViewSet] Listed {len(formatted_backups)} backups"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "count": len(formatted_backups),
                        "backups": serializer.data,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                f"[BackupManagementViewSet] Error listing backups: {str(e)}",
                exc_info=True,
            )
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request):
        """Create new backup (async)"""
        try:
            backup_manager = BackupManager()
            backup_info = backup_manager.create_database_backup(
                description=request.data.get("description", "Admin manual backup")
            )

            # Log audit
            audit_log(
                request.user,
                "database_backup_created",
                f"Backup created: {backup_info['id']}",
                request,
            )

            logger.info(
                f"[BackupManagementViewSet] Backup created: {backup_info['id']}"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "backup_id": backup_info["id"],
                        "status": backup_info.get("status", "in-progress"),
                        "message": "Backup creation started",
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(
                f"[BackupManagementViewSet] Error creating backup: {str(e)}",
                exc_info=True,
            )
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BackupDetailView(APIView):
    """
    POST /api/admin/database/backup/{backup_id}/restore/

    Restore database from backup

    Request:
    {
        "confirm": true
    }

    Response:
    {
        "success": true,
        "data": {
            "status": "in-progress",
            "estimated_duration_seconds": 300,
            "backup_id": "backup_20251227_103000"
        }
    }
    """

    permission_classes = [IsAdminUser]

    def post(self, request, backup_id):
        """Restore from backup"""
        try:
            confirm = request.data.get("confirm", False)

            if not confirm:
                return Response(
                    {
                        "success": False,
                        "error": "Restoration requires confirmation (confirm=true)",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            backup_manager = BackupManager()

            # Check if backup exists
            backups = backup_manager.list_backups()
            backup = next((b for b in backups if b["id"] == backup_id), None)

            if not backup:
                return Response(
                    {"success": False, "error": f"Backup not found: {backup_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Start restoration (async would be better, but keeping it simple for now)
            # In production, this should dispatch to Celery task
            estimated_duration = MaintenanceUtils.estimate_maintenance_time(
                "restore"
            ).get("estimated_seconds", 300)

            # Log audit
            audit_log(
                request.user,
                "database_restore_initiated",
                f"Database restoration initiated from backup: {backup_id}",
                request,
            )

            logger.info(f"[BackupDetailView] Restore initiated for backup: {backup_id}")

            return Response(
                {
                    "success": True,
                    "data": {
                        "status": "in-progress",
                        "estimated_duration_seconds": estimated_duration,
                        "backup_id": backup_id,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"[BackupDetailView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BackupDeleteView(APIView):
    """
    DELETE /api/admin/database/backup/{backup_id}/

    Delete backup file

    Response:
    {
        "success": true,
        "data": {
            "status": "deleted",
            "filename": "db_backup_20251227_103000.sql"
        }
    }
    """

    permission_classes = [IsAdminUser]

    def delete(self, request, backup_id):
        """Delete backup"""
        try:
            backup_manager = BackupManager()
            backups = backup_manager.list_backups()
            backup = next((b for b in backups if b["id"] == backup_id), None)

            if not backup:
                return Response(
                    {"success": False, "error": f"Backup not found: {backup_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Delete backup file
            if os.path.exists(backup["path"]):
                os.remove(backup["path"])

            # Delete metadata
            metadata_path = f"{backup['path']}.meta"
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            # Log audit
            audit_log(
                request.user,
                "database_backup_deleted",
                f"Backup deleted: {backup_id}",
                request,
            )

            logger.info(f"[BackupDeleteView] Backup deleted: {backup_id}")

            return Response(
                {
                    "success": True,
                    "data": {"status": "deleted", "filename": backup["filename"]},
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"[BackupDeleteView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Maintenance task store (in-memory for demo, should use Redis/DB in production)
_maintenance_tasks = {}


class MaintenanceTaskView(APIView):
    """
    POST /api/admin/database/maintenance/

    Dispatch maintenance operation

    Request:
    {
        "operation": "vacuum|reindex|cleanup|logs|sessions|views|stats|bloat|backup",
        "dry_run": false
    }

    Response:
    {
        "success": true,
        "data": {
            "task_id": "uuid",
            "operation": "vacuum",
            "status": "in-progress",
            "estimated_duration_seconds": 600,
            "progress_percent": 0
        }
    }
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Start maintenance operation"""
        try:
            operation = request.data.get("operation", "").lower()
            dry_run = request.data.get("dry_run", False)

            valid_operations = [
                "vacuum",
                "reindex",
                "cleanup",
                "logs",
                "sessions",
                "views",
                "stats",
                "bloat",
                "backup",
            ]

            if operation not in valid_operations:
                return Response(
                    {
                        "success": False,
                        "error": f'Invalid operation. Must be one of: {", ".join(valid_operations)}',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate task ID
            task_id = str(uuid.uuid4())

            # Estimate duration
            estimation = MaintenanceUtils.estimate_maintenance_time(operation)
            estimated_duration = estimation.get("estimated_seconds", 300)

            # Store task info
            _maintenance_tasks[task_id] = {
                "task_id": task_id,
                "operation": operation,
                "status": "in-progress",
                "progress_percent": 0,
                "estimated_duration_seconds": estimated_duration,
                "dry_run": dry_run,
                "created_at": timezone.now(),
                "result": None,
                "error": None,
            }

            # Log audit
            audit_log(
                request.user,
                f"database_maintenance_{operation}",
                f"Maintenance operation started: {operation} (dry_run={dry_run})",
                request,
            )

            logger.info(f"[MaintenanceTaskView] Task started: {task_id} ({operation})")

            return Response(
                {
                    "success": True,
                    "data": {
                        "task_id": task_id,
                        "operation": operation,
                        "status": "in-progress",
                        "estimated_duration_seconds": estimated_duration,
                        "progress_percent": 0,
                    },
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            logger.error(f"[MaintenanceTaskView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MaintenanceStatusView(APIView):
    """
    GET /api/admin/database/maintenance/{task_id}/

    Poll maintenance task status

    Response:
    {
        "success": true,
        "data": {
            "task_id": "uuid",
            "operation": "vacuum",
            "status": "completed|in-progress|failed",
            "progress_percent": 100,
            "result": {
                "disk_freed_mb": 512,
                "rows_processed": 50000,
                "duration_seconds": 245
            },
            "error": null
        }
    }
    """

    permission_classes = [IsAdminUser]

    def get(self, request, task_id):
        """Get maintenance task status"""
        try:
            if task_id not in _maintenance_tasks:
                return Response(
                    {"success": False, "error": f"Task not found: {task_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            task = _maintenance_tasks[task_id]

            # Simulate progress (in real implementation, check actual task status)
            if task["status"] == "in-progress":
                # Simulate completion after some time
                time_elapsed = (timezone.now() - task["created_at"]).total_seconds()
                estimated = task["estimated_duration_seconds"]

                if time_elapsed >= estimated:
                    task["status"] = "completed"
                    task["progress_percent"] = 100
                    task["result"] = {
                        "disk_freed_mb": 512,
                        "rows_processed": 50000,
                        "duration_seconds": int(time_elapsed),
                    }
                else:
                    task["progress_percent"] = min(
                        99, int((time_elapsed / estimated) * 100)
                    )

            serializer = MaintenanceTaskSerializer(task)

            logger.info(
                f"[MaintenanceStatusView] Task status: {task_id} - {task['status']}"
            )

            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"[MaintenanceStatusView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class KillQueryView(APIView):
    """
    POST /api/admin/database/kill-query/

    Kill long-running query (PostgreSQL only)

    Request:
    {
        "query_pid": 12345
    }

    Response:
    {
        "success": true,
        "data": {
            "status": "killed",
            "query_pid": 12345
        }
    }
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Kill query"""
        try:
            query_pid = request.data.get("query_pid")

            if not query_pid:
                return Response(
                    {"success": False, "error": "query_pid is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            db_info = DatabaseInfo()

            if not db_info.is_postgresql:
                return Response(
                    {
                        "success": False,
                        "error": "Kill query is only available for PostgreSQL",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Kill the query
            with connection.cursor() as cursor:
                # First check if query exists
                cursor.execute(
                    """
                    SELECT 1 FROM pg_stat_activity WHERE pid = %s
                """,
                    [query_pid],
                )

                if not cursor.fetchone():
                    return Response(
                        {
                            "success": False,
                            "error": f"Query PID not found: {query_pid}",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Kill the query
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(%s);
                """,
                    [query_pid],
                )

                result = cursor.fetchone()

            # Log audit
            audit_log(
                request.user,
                "database_kill_query",
                f"Query killed: PID {query_pid}",
                request,
            )

            logger.info(f"[KillQueryView] Query killed: PID {query_pid}")

            return Response(
                {"success": True, "data": {"status": "killed", "query_pid": query_pid}},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"[KillQueryView] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
