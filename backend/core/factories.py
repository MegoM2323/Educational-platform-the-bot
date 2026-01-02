import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from .models import FailedTask, TaskExecutionLog, AuditLog, Configuration
from accounts.factories import UserFactory


class FailedTaskFactory(DjangoModelFactory):
    class Meta:
        model = FailedTask

    task_id = factory.Sequence(lambda n: f"task_{n}")
    task_name = "test_task"
    status = FailedTask.Status.FAILED
    error_message = "Test error occurred"
    error_type = "TimeoutError"
    traceback = "Traceback: ..."
    retry_count = 0
    is_transient = False
    metadata = {}


class TaskExecutionLogFactory(DjangoModelFactory):
    class Meta:
        model = TaskExecutionLog

    task_id = factory.Sequence(lambda n: f"task_{n}")
    task_name = "test_task"
    status = TaskExecutionLog.Status.SUCCESS
    started_at = timezone.now()
    completed_at = timezone.now()
    duration_seconds = 1.5
    retry_count = 0
    result = {}
    error_message = ""


class AuditLogFactory(DjangoModelFactory):
    class Meta:
        model = AuditLog

    user = factory.SubFactory(UserFactory)
    action = AuditLog.Action.LOGIN
    target_type = "user"
    target_id = 1
    ip_address = "192.168.1.1"
    user_agent = "Mozilla/5.0"
    metadata = {}


class ConfigurationFactory(DjangoModelFactory):
    class Meta:
        model = Configuration

    key = factory.Sequence(lambda n: f"config.key_{n}")
    value = "test_value"
    value_type = Configuration.ConfigType.STRING
    description = "Test configuration"
    group = "test"
    updated_by = factory.SubFactory(UserFactory)
