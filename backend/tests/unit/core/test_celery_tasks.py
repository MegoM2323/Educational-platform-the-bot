"""
Unit-тесты для Celery задач приложения core
"""
import pytest
import os
import json
from unittest.mock import MagicMock, patch, call, mock_open
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.test import override_settings
from io import StringIO

from core.tasks import (
    create_daily_backup,
    cleanup_old_backups,
    check_system_health_task,
    verify_data_integrity_task,
    log_system_metrics,
    process_subscription_payments
)


@pytest.mark.unit
@pytest.mark.celery
class TestCreateDailyBackup:
    """Тесты для задачи создания ежедневного бэкапа"""

    def test_create_daily_backup_success(self, db):
        """Тест успешного создания бэкапа"""
        mock_backup_info = {
            'id': 'backup_20240101_120000',
            'filename': 'db_backup_20240101_120000.sql',
            'path': '/tmp/backups/db_backup_20240101_120000.sql',
            'created_at': timezone.now().isoformat(),
            'description': 'Automatic backup',
            'size': 1024000,
            'type': 'database'
        }

        with patch('core.tasks.create_automatic_backup', return_value=mock_backup_info) as mock_create:
            result = create_daily_backup.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['backup_id'] == 'backup_20240101_120000'
            assert 'Daily backup created successfully' in task_result['message']
            mock_create.assert_called_once()

    def test_create_daily_backup_failure(self, db):
        """Тест неудачного создания бэкапа"""
        with patch('core.tasks.create_automatic_backup', return_value=None):
            result = create_daily_backup.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert 'Failed to create daily backup' in task_result['message']

    def test_create_daily_backup_exception(self, db):
        """Тест обработки исключений при создании бэкапа"""
        error_message = "Database connection error"

        with patch('core.tasks.create_automatic_backup', side_effect=Exception(error_message)):
            result = create_daily_backup.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert error_message in task_result['message']

    def test_create_daily_backup_logs_event(self, db):
        """Тест логирования системных событий"""
        mock_backup_info = {
            'id': 'backup_20240101_120000',
            'filename': 'db_backup_20240101_120000.sql',
            'path': '/tmp/backups/db_backup_20240101_120000.sql',
            'created_at': timezone.now().isoformat(),
            'description': 'Automatic backup',
            'size': 1024000,
            'type': 'database'
        }

        with patch('core.tasks.create_automatic_backup', return_value=mock_backup_info), \
             patch('core.tasks.log_system_event') as mock_log:

            result = create_daily_backup.delay()
            result.get()

            # Проверяем, что событие было залогировано
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 'daily_backup_created'
            assert 'backup_id' in call_args[1]['metadata']


@pytest.mark.unit
@pytest.mark.celery
class TestCleanupOldBackups:
    """Тесты для задачи очистки старых бэкапов"""

    def test_cleanup_old_backups_success(self, db, tmpdir):
        """Тест успешной очистки старых бэкапов"""
        # Создаем временные бэкапы
        backup_dir = tmpdir.mkdir("backups")
        max_backups = 5

        # Создаем список из 10 бэкапов (должно удалиться 5)
        backups = []
        for i in range(10):
            backup_id = f"backup_{i:02d}"
            backup_path = str(backup_dir.join(f"backup_{i:02d}.sql"))

            # Создаем файл
            with open(backup_path, 'w') as f:
                f.write("backup data")

            backups.append({
                'id': backup_id,
                'path': backup_path,
                'created_at': (timezone.now() - timedelta(days=10-i)).isoformat()
            })

        # Сортируем backups по дате (новые первые)
        backups.sort(key=lambda x: x['created_at'], reverse=True)

        with patch('core.tasks.backup_manager.list_backups', return_value=backups), \
             patch('core.tasks.backup_manager.max_backups', max_backups):

            result = cleanup_old_backups.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['deleted_count'] == 5

    def test_cleanup_no_old_backups(self, db):
        """Тест когда нет старых бэкапов для удаления"""
        backups = [
            {'id': 'backup_01', 'path': '/tmp/backup_01.sql', 'created_at': timezone.now().isoformat()},
            {'id': 'backup_02', 'path': '/tmp/backup_02.sql', 'created_at': timezone.now().isoformat()}
        ]

        with patch('core.tasks.backup_manager.list_backups', return_value=backups), \
             patch('core.tasks.backup_manager.max_backups', 30):

            result = cleanup_old_backups.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['deleted_count'] == 0
            assert 'No old backups to clean up' in task_result['message']

    def test_cleanup_old_backups_exception(self, db):
        """Тест обработки исключений при очистке"""
        with patch('core.tasks.backup_manager.list_backups', side_effect=Exception("File system error")):
            result = cleanup_old_backups.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert 'File system error' in task_result['message']


@pytest.mark.unit
@pytest.mark.celery
class TestCheckSystemHealthTask:
    """Тесты для задачи проверки здоровья системы"""

    def test_check_system_health_success_healthy(self, db):
        """Тест проверки здоровья системы - все в норме"""
        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'usage_percent': 50, 'status': 'healthy'},
            'memory': {'used_percent': 60, 'status': 'healthy'},
            'disk': {'used_percent': 45, 'status': 'healthy'},
            'database': {'response_time_ms': 100, 'status': 'healthy'}
        }

        with patch('core.tasks.system_monitor.get_system_metrics', return_value=mock_metrics), \
             patch('core.tasks.system_monitor.get_performance_alerts', return_value=[]):

            result = check_system_health_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['critical_alerts'] == 0
            assert task_result['warning_alerts'] == 0
            assert task_result['total_alerts'] == 0

    def test_check_system_health_with_warnings(self, db):
        """Тест проверки здоровья системы с предупреждениями"""
        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'usage_percent': 85, 'status': 'warning'},
            'memory': {'used_percent': 60, 'status': 'healthy'}
        }

        mock_alerts = [
            {
                'type': 'cpu_high',
                'severity': 'warning',
                'message': 'CPU usage is 85%',
                'component': 'cpu'
            }
        ]

        with patch('core.tasks.system_monitor.get_system_metrics', return_value=mock_metrics), \
             patch('core.tasks.system_monitor.get_performance_alerts', return_value=mock_alerts), \
             patch('core.tasks.log_system_event') as mock_log:

            result = check_system_health_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['warning_alerts'] == 1
            assert task_result['critical_alerts'] == 0

            # Проверяем, что warning был залогирован
            mock_log.assert_called()

    def test_check_system_health_with_critical_alerts(self, db):
        """Тест проверки здоровья системы с критическими предупреждениями"""
        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'usage_percent': 95, 'status': 'critical'}
        }

        mock_alerts = [
            {
                'type': 'cpu_high',
                'severity': 'critical',
                'message': 'CPU usage is 95%',
                'component': 'cpu'
            },
            {
                'type': 'memory_high',
                'severity': 'critical',
                'message': 'Memory usage is 92%',
                'component': 'memory'
            }
        ]

        with patch('core.tasks.system_monitor.get_system_metrics', return_value=mock_metrics), \
             patch('core.tasks.system_monitor.get_performance_alerts', return_value=mock_alerts), \
             patch('core.tasks.log_system_event') as mock_log:

            result = check_system_health_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['critical_alerts'] == 2
            assert task_result['warning_alerts'] == 0

            # Проверяем, что оба critical alerts были залогированы
            assert mock_log.call_count == 2

    def test_check_system_health_exception(self, db):
        """Тест обработки исключений при проверке здоровья"""
        with patch('core.tasks.system_monitor.get_system_metrics', side_effect=Exception("Monitor error")):
            result = check_system_health_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert 'Monitor error' in task_result['message']


@pytest.mark.unit
@pytest.mark.celery
class TestVerifyDataIntegrityTask:
    """Тесты для задачи проверки целостности данных"""

    def test_verify_data_integrity_healthy(self, db):
        """Тест проверки целостности данных - все в норме"""
        mock_integrity_status = {
            'overall_status': 'healthy',
            'orphaned_records': [],
            'missing_relations': [],
            'data_consistency': []
        }

        with patch('core.backup_utils.verify_data_integrity', return_value=mock_integrity_status):
            result = verify_data_integrity_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['integrity_status'] == 'healthy'
            assert task_result['issues_found'] is False

    def test_verify_data_integrity_issues_found(self, db):
        """Тест проверки целостности данных - найдены проблемы"""
        mock_integrity_status = {
            'overall_status': 'issues_found',
            'orphaned_records': [
                {
                    'type': 'users_without_profiles',
                    'count': 3,
                    'details': [(1, 'user1', 'student'), (2, 'user2', 'teacher')]
                }
            ],
            'missing_relations': [],
            'data_consistency': [
                {
                    'type': 'students_without_parents',
                    'count': 2,
                    'details': [(5, 10, 'student5')]
                }
            ]
        }

        with patch('core.backup_utils.verify_data_integrity', return_value=mock_integrity_status), \
             patch('core.tasks.log_system_event') as mock_log:

            result = verify_data_integrity_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['integrity_status'] == 'issues_found'
            assert task_result['issues_found'] is True

            # Проверяем, что событие было залогировано
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 'data_integrity_issues'

    def test_verify_data_integrity_exception(self, db):
        """Тест обработки исключений при проверке целостности"""
        with patch('core.backup_utils.verify_data_integrity', side_effect=Exception("Database query error")):
            result = verify_data_integrity_task.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert 'Database query error' in task_result['message']


@pytest.mark.unit
@pytest.mark.celery
class TestLogSystemMetrics:
    """Тесты для задачи логирования системных метрик"""

    def test_log_system_metrics_success(self, db):
        """Тест успешного логирования метрик"""
        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'usage_percent': 45.5},
            'memory': {'used_percent': 62.3},
            'disk': {'used_percent': 50.1},
            'database': {'response_time_ms': 123.45}
        }

        with patch('core.tasks.system_monitor.get_system_metrics', return_value=mock_metrics), \
             patch('core.tasks.log_system_event') as mock_log:

            result = log_system_metrics.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['cpu_usage'] == 45.5
            assert task_result['memory_usage'] == 62.3
            assert task_result['disk_usage'] == 50.1
            assert task_result['db_response_time'] == 123.45

            # Проверяем, что метрики были залогированы
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 'system_metrics'
            assert 'cpu_usage' in call_args[1]['metadata']

    def test_log_system_metrics_missing_data(self, db):
        """Тест логирования метрик с отсутствующими данными"""
        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {},
            'memory': {}
        }

        with patch('core.tasks.system_monitor.get_system_metrics', return_value=mock_metrics):
            result = log_system_metrics.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert task_result['cpu_usage'] == 0
            assert task_result['memory_usage'] == 0

    def test_log_system_metrics_exception(self, db):
        """Тест обработки исключений при логировании метрик"""
        with patch('core.tasks.system_monitor.get_system_metrics', side_effect=Exception("Metrics error")):
            result = log_system_metrics.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert 'Metrics error' in task_result['message']


@pytest.mark.unit
@pytest.mark.celery
class TestProcessSubscriptionPayments:
    """Тесты для задачи обработки регулярных платежей"""

    def test_process_subscription_payments_success(self, db):
        """Тест успешной обработки платежей"""
        mock_output = """
        Найдено 5 подписок для обработки
        Создан платеж 1 для подписки 1: Студент: Test Student, Предмет: Math, Сумма: 5000 руб.
        Обработка завершена: обработано 5, ошибок 0
        """

        with patch('django.core.management.call_command') as mock_call_command:
            # Мокируем вывод команды
            def mock_command_side_effect(*args, **kwargs):
                stdout = kwargs.get('stdout')
                if stdout:
                    stdout.write(mock_output)

            mock_call_command.side_effect = mock_command_side_effect

            result = process_subscription_payments.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is True
            assert 'Subscription payments processing completed' in task_result['message']
            assert mock_output.strip() in task_result['output']

            # Проверяем, что команда была вызвана правильно
            mock_call_command.assert_called_once_with('process_subscription_payments', stdout=unittest.mock.ANY)

    def test_process_subscription_payments_exception(self, db):
        """Тест обработки исключений при обработке платежей"""
        with patch('django.core.management.call_command', side_effect=Exception("Payment processing error")):
            result = process_subscription_payments.delay()

            assert result.successful()
            task_result = result.get()

            assert task_result['success'] is False
            assert 'Payment processing error' in task_result['message']

    def test_process_subscription_payments_logs_event(self, db):
        """Тест логирования события обработки платежей"""
        mock_output = "Processed 3 payments"

        with patch('django.core.management.call_command') as mock_call_command, \
             patch('core.tasks.log_system_event') as mock_log:

            def mock_command_side_effect(*args, **kwargs):
                stdout = kwargs.get('stdout')
                if stdout:
                    stdout.write(mock_output)

            mock_call_command.side_effect = mock_command_side_effect

            result = process_subscription_payments.delay()
            result.get()

            # Проверяем, что событие было залогировано
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 'subscription_payments_processed'


@pytest.mark.unit
@pytest.mark.celery
class TestCeleryTaskRetry:
    """Тесты для retry logic Celery задач"""

    def test_task_retry_on_temporary_failure(self, db):
        """Тест retry при временных ошибках (в eager mode просто проверяем exception handling)"""
        # В eager mode retry не работает как обычно, но мы можем проверить обработку ошибок
        with patch('core.tasks.create_automatic_backup', side_effect=Exception("Temporary error")):
            result = create_daily_backup.delay()

            # Задача должна вернуть результат с ошибкой, а не упасть
            assert result.successful()
            task_result = result.get()
            assert task_result['success'] is False


# Импортируем unittest.mock для использования в тестах
import unittest.mock
