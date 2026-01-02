"""
Модели для системы мониторинга и управления задачами
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model


class FailedTask(models.Model):
    """
    Dead Letter Queue для неудачных Celery задач

    Хранит информацию о задачах, которые не удалось выполнить
    после всех попыток retry для последующего анализа и ручной обработки
    """

    class Status(models.TextChoices):
        FAILED = "failed", "Failed"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    # Основная информация о задаче
    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.FAILED, db_index=True
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
        db_table = "core_failed_task"
        ordering = ["-failed_at"]
        indexes = [
            models.Index(fields=["task_name", "status"]),
            models.Index(fields=["failed_at", "status"]),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.task_id}) - {self.status}"

    def mark_investigating(self, notes=""):
        """Помечает задачу как исследуемую"""
        self.status = self.Status.INVESTIGATING
        self.investigated_at = timezone.now()
        if notes:
            self.investigation_notes = notes
        self.save(update_fields=["status", "investigated_at", "investigation_notes"])

    def mark_resolved(self, notes=""):
        """Помечает задачу как решенную"""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=["status", "resolved_at", "resolution_notes"])

    def mark_ignored(self, notes=""):
        """Помечает задачу как игнорируемую (не требует действий)"""
        self.status = self.Status.IGNORED
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=["status", "resolution_notes"])


class TaskExecutionLog(models.Model):
    """
    Лог выполнения периодических задач для мониторинга

    Отслеживает каждый запуск задачи: время, длительность, результат
    """

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"

    task_id = models.CharField(max_length=255, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True
    )

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    retry_count = models.IntegerField(default=0)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "core_task_execution_log"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["task_name", "status", "started_at"]),
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

        self.save(
            update_fields=[
                "completed_at",
                "duration_seconds",
                "status",
                "error_message",
                "result",
            ]
        )


class AuditLog(models.Model):
    """
    Centralized audit log for user activities.

    Tracks all user actions including logins, API calls, material views,
    assignment submissions, and data modifications. Provides compliance
    and security audit trail.
    """

    class Action(models.TextChoices):
        """Common audit action types"""

        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        VIEW_MATERIAL = "view_material", "View Material"
        DOWNLOAD_MATERIAL = "download_material", "Download Material"
        SUBMIT_ASSIGNMENT = "submit_assignment", "Submit Assignment"
        VIEW_ASSIGNMENT = "view_assignment", "View Assignment"
        CREATE_MATERIAL = "create_material", "Create Material"
        EDIT_MATERIAL = "edit_material", "Edit Material"
        DELETE_MATERIAL = "delete_material", "Delete Material"
        GRADE_ASSIGNMENT = "grade_assignment", "Grade Assignment"
        CREATE_CHAT = "create_chat", "Create Chat"
        SEND_MESSAGE = "send_message", "Send Message"
        VIEW_CHAT = "view_chat", "View Chat"
        DELETE_MESSAGE = "delete_message", "Delete Message"
        CREATE_INVOICE = "create_invoice", "Create Invoice"
        PROCESS_PAYMENT = "process_payment", "Process Payment"
        VIEW_REPORT = "view_report", "View Report"
        EXPORT_REPORT = "export_report", "Export Report"
        CREATE_KNOWLEDGE_GRAPH = "create_knowledge_graph", "Create Knowledge Graph"
        UPDATE_KNOWLEDGE_GRAPH = "update_knowledge_graph", "Update Knowledge Graph"
        USER_UPDATE = "user_update", "User Update"
        ROLE_CHANGE = "role_change", "Role Change"
        PASSWORD_CHANGE = "password_change", "Password Change"
        PERMISSION_CHANGE = "permission_change", "Permission Change"
        API_CALL = "api_call", "API Call"
        ADMIN_ACTION = "admin_action", "Admin Action"
        ADMIN_CREATE = "admin_create", "Admin Create"
        ADMIN_UPDATE = "admin_update", "Admin Update"
        ADMIN_DELETE = "admin_delete", "Admin Delete"
        ADMIN_RESET_PASSWORD = "admin_reset_password", "Admin Reset Password"
        DATA_EXPORT = "data_export", "Data Export"
        DATA_IMPORT = "data_import", "Data Import"
        ERROR = "error", "Error"

    # User performing the action
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
        verbose_name="User",
    )

    # Action details
    action = models.CharField(
        max_length=50, choices=Action.choices, db_index=True, verbose_name="Action"
    )

    # Target object information
    target_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Target Type",
        help_text="Type of object affected (material, assignment, user, etc.)",
    )

    target_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Target ID",
        help_text="ID of the object affected",
    )

    # Request metadata
    ip_address = models.GenericIPAddressField(
        verbose_name="IP Address", help_text="Client IP address"
    )

    user_agent = models.CharField(
        max_length=500,
        verbose_name="User-Agent",
        help_text="Browser/client user-agent string",
    )

    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text="Additional context in JSON format",
    )

    # Timestamp
    timestamp = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Timestamp"
    )

    class Meta:
        db_table = "core_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
            models.Index(fields=["target_type", "target_id"]),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"

    @property
    def target_description(self) -> str:
        """Human-readable description of the target"""
        if self.target_type and self.target_id:
            return f"{self.target_type}:{self.target_id}"
        return "-"


class Configuration(models.Model):
    """
    Dynamic system configuration management.

    Stores system-wide settings that can be modified at runtime without
    restarting the application. Supports feature flags, rate limits, email
    settings, payment settings, and UI customization.

    Each configuration key is unique and stores a JSON value with type
    validation. Changes are tracked in the audit log.
    """

    class ConfigType(models.TextChoices):
        STRING = "string", "String"
        INTEGER = "integer", "Integer"
        BOOLEAN = "boolean", "Boolean"
        LIST = "list", "List"
        JSON = "json", "JSON"

    # Configuration key (e.g., 'feature_flags.assignments_enabled')
    key = models.CharField(
        max_length=255, unique=True, db_index=True, verbose_name="Configuration Key"
    )

    # Configuration value stored as JSON
    value = models.JSONField(default=None, null=True, blank=True, verbose_name="Value")

    # Data type of the value
    value_type = models.CharField(
        max_length=20,
        choices=ConfigType.choices,
        default=ConfigType.STRING,
        verbose_name="Value Type",
    )

    # Human-readable description
    description = models.TextField(
        blank=True, verbose_name="Description", help_text="What this configuration does"
    )

    # Configuration group (e.g., 'feature_flags', 'rate_limit')
    group = models.CharField(
        max_length=100, blank=True, db_index=True, verbose_name="Configuration Group"
    )

    # User who last updated this configuration
    updated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="config_changes",
        verbose_name="Updated By",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "core_configuration"
        ordering = ["group", "key"]
        indexes = [
            models.Index(fields=["group", "key"]),
            models.Index(fields=["updated_at"]),
        ]
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"

    def __str__(self):
        return f"{self.key}: {self.value}"

    def save(self, *args, **kwargs):
        """Validate value type before saving."""
        self._validate_value()
        super().save(*args, **kwargs)

    def _validate_value(self):
        """Validate that the value matches the declared type."""
        if self.value is None:
            return

        if self.value_type == self.ConfigType.STRING and not isinstance(
            self.value, str
        ):
            raise ValueError(f"Value must be a string, got {type(self.value).__name__}")
        elif self.value_type == self.ConfigType.INTEGER and not isinstance(
            self.value, int
        ):
            raise ValueError(
                f"Value must be an integer, got {type(self.value).__name__}"
            )
        elif self.value_type == self.ConfigType.BOOLEAN and not isinstance(
            self.value, bool
        ):
            raise ValueError(
                f"Value must be a boolean, got {type(self.value).__name__}"
            )
        elif self.value_type == self.ConfigType.LIST and not isinstance(
            self.value, list
        ):
            raise ValueError(f"Value must be a list, got {type(self.value).__name__}")
        # JSON type accepts any JSON-serializable value
