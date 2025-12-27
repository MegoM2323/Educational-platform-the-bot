"""
Serializers для Database Admin API endpoints
"""
from rest_framework import serializers


class DatabaseStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса базы данных"""
    database_type = serializers.CharField()
    database_version = serializers.CharField()
    database_name = serializers.CharField()
    database_size_bytes = serializers.IntegerField()
    database_size_human = serializers.CharField()
    last_backup = serializers.DateTimeField(allow_null=True)
    backup_status = serializers.CharField()
    connection_pool = serializers.DictField()


class TableStatSerializer(serializers.Serializer):
    """Сериализатор для статистики таблицы"""
    name = serializers.CharField()
    rows = serializers.IntegerField()
    size_mb = serializers.FloatField()
    last_vacuum = serializers.DateTimeField(allow_null=True)
    last_reindex = serializers.DateTimeField(allow_null=True)
    bloat_indicator = serializers.CharField()  # 'low', 'medium', 'high'
    last_maintenance = serializers.DateTimeField(allow_null=True)


class SlowQuerySerializer(serializers.Serializer):
    """Сериализатор для медленного запроса"""
    id = serializers.IntegerField()
    query = serializers.CharField()
    query_truncated = serializers.CharField()
    count = serializers.IntegerField()
    avg_time_ms = serializers.FloatField()
    max_time_ms = serializers.FloatField()


class BackupSerializer(serializers.Serializer):
    """Сериализатор для резервной копии"""
    id = serializers.CharField()
    filename = serializers.CharField()
    size_bytes = serializers.IntegerField()
    size_human = serializers.CharField()
    created_at = serializers.DateTimeField()
    status = serializers.CharField()  # 'pending', 'in-progress', 'completed', 'failed'
    is_downloadable = serializers.BooleanField()


class MaintenanceTaskSerializer(serializers.Serializer):
    """Сериализатор для задачи обслуживания"""
    task_id = serializers.CharField()
    operation = serializers.CharField()
    status = serializers.CharField()  # 'in-progress', 'completed', 'failed'
    progress_percent = serializers.IntegerField()
    estimated_duration_seconds = serializers.IntegerField(allow_null=True)
    result = serializers.DictField(allow_null=True)
    error = serializers.CharField(allow_null=True)
