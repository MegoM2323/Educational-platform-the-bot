"""
Модели для системы мониторинга и управления задачами
"""
from django.db import models
from django.utils import timezone


class FailedTask(models.Model):
    """
    Dead Letter Queue для неудачных Celery задач

    Хранит информацию о задачах, которые не удалось выполнить
    после всех попыток retry для последующего анализа и ручной обработки
    """

    class Status(models.TextChoices):
        FAILED = 'failed', 'Failed'
        INVESTIGATING = 'investigating', 'Investigating'
        RESOLVED = 'resolved', 'Resolved'
        IGNORED = 'ignored', 'Ignored'

    # Основная информация о задаче
    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FAILED,
        db_index=True
    )

    # Детали ошибки
    error_message = models.TextField()
    error_type = models.CharField(max_length=255)
    traceback = models.TextField(blank=True)

    # Метаданные
    retry_count = models.IntegerField(default=0)
    is_transient = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    # Временные метки
    failed_at = models.DateTimeField(default=timezone.now, db_index=True)
    investigated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Комментарии для анализа
    investigation_notes = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'core_failed_task'
        ordering = ['-failed_at']
        indexes = [
            models.Index(fields=['task_name', 'status']),
            models.Index(fields=['failed_at', 'status']),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.task_id}) - {self.status}"

    def mark_investigating(self, notes=''):
        """Помечает задачу как исследуемую"""
        self.status = self.Status.INVESTIGATING
        self.investigated_at = timezone.now()
        if notes:
            self.investigation_notes = notes
        self.save(update_fields=['status', 'investigated_at', 'investigation_notes'])

    def mark_resolved(self, notes=''):
        """Помечает задачу как решенную"""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=['status', 'resolved_at', 'resolution_notes'])

    def mark_ignored(self, notes=''):
        """Помечает задачу как игнорируемую (не требует действий)"""
        self.status = self.Status.IGNORED
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=['status', 'resolution_notes'])


class TaskExecutionLog(models.Model):
    """
    Лог выполнения периодических задач для мониторинга

    Отслеживает каждый запуск задачи: время, длительность, результат
    """

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        RETRYING = 'retrying', 'Retrying'

    task_id = models.CharField(max_length=255, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUCCESS,
        db_index=True
    )

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    retry_count = models.IntegerField(default=0)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'core_task_execution_log'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['task_name', 'status', 'started_at']),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.task_id}) - {self.status} at {self.started_at}"

    def complete(self, result=None, error=None):
        """Завершает запись о выполнении задачи"""
        self.completed_at = timezone.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

        if error:
            self.status = self.Status.FAILED
            self.error_message = str(error)
        else:
            self.status = self.Status.SUCCESS

        if result:
            self.result = result

        self.save(update_fields=[
            'completed_at',
            'duration_seconds',
            'status',
            'error_message',
            'result'
        ])
