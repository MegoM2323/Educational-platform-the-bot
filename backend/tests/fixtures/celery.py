"""
Celery task test fixtures and utilities
"""
import pytest
from unittest.mock import MagicMock, patch
from celery import Celery
from celery.result import AsyncResult


@pytest.fixture(autouse=True)
def celery_eager_mode(settings):
    """
    Enable Celery eager mode for all tests.
    Tasks will execute synchronously during tests instead of being queued.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def celery_app():
    """Get Celery app instance"""
    from core.celery_config import app
    return app


@pytest.fixture
def mock_celery_task():
    """
    Mock Celery task decorator and execution.
    Usage:
        def test_task(mock_celery_task):
            task = mock_celery_task
            result = task.delay()
            assert result.successful()
    """
    mock_task = MagicMock()
    mock_result = MagicMock(spec=AsyncResult)
    mock_result.id = 'test-task-id-123'
    mock_result.state = 'SUCCESS'
    mock_result.successful.return_value = True
    mock_result.failed.return_value = False
    mock_result.ready.return_value = True
    mock_result.get.return_value = {'status': 'success'}

    mock_task.delay.return_value = mock_result
    mock_task.apply_async.return_value = mock_result

    return mock_task


@pytest.fixture
def mock_celery_chain():
    """Mock Celery chain"""
    with patch('celery.chain') as mock:
        mock_result = MagicMock(spec=AsyncResult)
        mock_result.id = 'test-chain-id-123'
        mock_result.state = 'SUCCESS'
        mock.return_value.apply_async.return_value = mock_result
        yield mock


@pytest.fixture
def mock_celery_group():
    """Mock Celery group"""
    with patch('celery.group') as mock:
        mock_result = MagicMock()
        mock_result.id = 'test-group-id-123'
        mock.return_value.apply_async.return_value = mock_result
        yield mock


@pytest.fixture
def mock_celery_chord():
    """Mock Celery chord"""
    with patch('celery.chord') as mock:
        mock_result = MagicMock(spec=AsyncResult)
        mock_result.id = 'test-chord-id-123'
        mock.return_value.apply_async.return_value = mock_result
        yield mock


@pytest.fixture
def mock_subscription_payment_task():
    """
    Mock process_subscription_payments task.
    This is the recurring task that charges subscriptions.
    """
    with patch('materials.tasks.process_subscription_payments') as mock_task:
        mock_result = MagicMock(spec=AsyncResult)
        mock_result.id = 'test-subscription-payment-task-123'
        mock_result.state = 'SUCCESS'
        mock_result.get.return_value = {
            'processed': 5,
            'succeeded': 4,
            'failed': 1
        }

        mock_task.delay.return_value = mock_result
        mock_task.apply_async.return_value = mock_result

        yield mock_task


@pytest.fixture
def mock_backup_task():
    """Mock daily_backup task"""
    with patch('core.tasks.daily_backup') as mock_task:
        mock_result = MagicMock(spec=AsyncResult)
        mock_result.id = 'test-backup-task-123'
        mock_result.state = 'SUCCESS'
        mock_result.get.return_value = {
            'backup_file': '/backups/2024-01-01.sql',
            'size': 1024000
        }

        mock_task.delay.return_value = mock_result
        yield mock_task


@pytest.fixture
def mock_health_check_task():
    """Mock system_health_check task"""
    with patch('core.tasks.system_health_check') as mock_task:
        mock_result = MagicMock(spec=AsyncResult)
        mock_result.id = 'test-health-check-task-123'
        mock_result.state = 'SUCCESS'
        mock_result.get.return_value = {
            'status': 'healthy',
            'cpu': 25.5,
            'memory': 60.2,
            'disk': 45.0
        }

        mock_task.delay.return_value = mock_result
        yield mock_task


@pytest.fixture
def mock_email_task():
    """Mock send_email task (if exists)"""
    with patch('core.tasks.send_email', create=True) as mock_task:
        mock_result = MagicMock(spec=AsyncResult)
        mock_result.id = 'test-email-task-123'
        mock_result.state = 'SUCCESS'

        mock_task.delay.return_value = mock_result
        yield mock_task


@pytest.fixture
def celery_worker():
    """
    Start a test Celery worker.
    Use this for integration tests that need actual task execution.
    """
    from core.celery_config import app

    # Configure test broker (in-memory)
    app.conf.update(
        broker_url='memory://',
        result_backend='cache+memory://',
        task_always_eager=True,
        task_eager_propagates=True
    )

    return app


@pytest.fixture
def mock_task_result_success():
    """Mock successful task result"""
    result = MagicMock(spec=AsyncResult)
    result.id = 'test-task-success-123'
    result.state = 'SUCCESS'
    result.status = 'SUCCESS'
    result.successful.return_value = True
    result.failed.return_value = False
    result.ready.return_value = True
    result.get.return_value = {'result': 'success'}
    return result


@pytest.fixture
def mock_task_result_failure():
    """Mock failed task result"""
    result = MagicMock(spec=AsyncResult)
    result.id = 'test-task-failure-123'
    result.state = 'FAILURE'
    result.status = 'FAILURE'
    result.successful.return_value = False
    result.failed.return_value = True
    result.ready.return_value = True
    result.get.side_effect = Exception('Task failed')
    return result


@pytest.fixture
def mock_task_result_pending():
    """Mock pending task result"""
    result = MagicMock(spec=AsyncResult)
    result.id = 'test-task-pending-123'
    result.state = 'PENDING'
    result.status = 'PENDING'
    result.successful.return_value = False
    result.failed.return_value = False
    result.ready.return_value = False
    return result


@pytest.fixture
def mock_task_result_retry():
    """Mock retrying task result"""
    result = MagicMock(spec=AsyncResult)
    result.id = 'test-task-retry-123'
    result.state = 'RETRY'
    result.status = 'RETRY'
    result.successful.return_value = False
    result.failed.return_value = False
    result.ready.return_value = False
    return result


@pytest.fixture(autouse=True)
def disable_celery_redis(settings):
    """
    Disable Redis for Celery in tests.
    Use in-memory broker instead.
    """
    settings.CELERY_BROKER_URL = 'memory://'
    settings.CELERY_RESULT_BACKEND = 'cache+memory://'


@pytest.fixture
def mock_periodic_task():
    """Mock Django Celery Beat periodic task"""
    with patch('django_celery_beat.models.PeriodicTask') as mock:
        mock_instance = MagicMock()
        mock_instance.name = 'test-periodic-task'
        mock_instance.task = 'core.tasks.test_task'
        mock_instance.enabled = True
        mock.objects.create.return_value = mock_instance
        yield mock


@pytest.fixture
def run_task_sync():
    """
    Helper to run Celery tasks synchronously in tests.
    Usage:
        def test_my_task(run_task_sync):
            result = run_task_sync(my_task, arg1, arg2, kwarg1=value)
    """
    def _run_task(task, *args, **kwargs):
        """Run task synchronously and return result"""
        return task.apply(args=args, kwargs=kwargs).get()

    return _run_task
