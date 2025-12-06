"""
Unit tests for Pachca notification Celery task.

Tests async task execution, retry logic, error handling, and monitoring.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from celery.exceptions import Retry

from chat.tasks import send_pachca_forum_notification_task, monitor_pachca_failures


@pytest.fixture
def mock_message(db):
    """Create mock Message instance"""
    from accounts.models import User
    from chat.models import Message, ChatRoom

    sender = User.objects.create_user(
        username='sender_user',
        email='sender@test.com',
        password='password123',
        role='student',
        first_name='Ivan',
        last_name='Ivanov'
    )

    chat_room = ChatRoom.objects.create(
        name='Test Chat',
        type=ChatRoom.Type.FORUM_SUBJECT,
        created_by=sender
    )

    message = Message.objects.create(
        room=chat_room,
        sender=sender,
        content='Test message content'
    )

    return message


@pytest.fixture
def mock_chat_room(db):
    """Create mock ChatRoom instance"""
    from accounts.models import User
    from chat.models import ChatRoom

    creator = User.objects.create_user(
        username='creator_user',
        email='creator@test.com',
        password='password123',
        role='teacher',
        first_name='Maria',
        last_name='Petrova'
    )

    return ChatRoom.objects.create(
        name='Forum Chat',
        type=ChatRoom.Type.FORUM_SUBJECT,
        created_by=creator
    )


@pytest.mark.django_db
class TestPachcaNotificationTask:
    """Tests for send_pachca_forum_notification_task"""

    @patch('chat.services.pachca_service.PachcaService')
    def test_task_success_notification_sent(self, mock_pachca_service_class, mock_message, mock_chat_room):
        """Test task successfully sends notification"""
        # Mock PachcaService
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.notify_new_forum_message.return_value = None
        mock_pachca_service_class.return_value = mock_service

        # Execute task
        result = send_pachca_forum_notification_task(
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        # Verify
        assert result['success'] is True
        assert result['notification_sent'] is True
        assert result['attempt'] == 1
        mock_service.notify_new_forum_message.assert_called_once()

    @patch('chat.services.pachca_service.PachcaService')
    def test_task_skips_when_not_configured(self, mock_pachca_service_class, mock_message):
        """Test task skips notification when Pachca not configured"""
        # Mock PachcaService as not configured
        mock_service = MagicMock()
        mock_service.is_configured.return_value = False
        mock_pachca_service_class.return_value = mock_service

        # Execute task
        result = send_pachca_forum_notification_task(
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        # Verify
        assert result['success'] is True
        assert result['notification_sent'] is False
        assert 'not configured' in result['message']
        mock_service.notify_new_forum_message.assert_not_called()

    def test_task_handles_message_not_found(self, db):
        """Test task handles missing message gracefully"""
        result = send_pachca_forum_notification_task(
            message_id=99999,  # Non-existent
            chat_room_id=1
        )

        assert result['success'] is False
        assert 'not found' in result['message']
        assert result['notification_sent'] is False

    def test_task_handles_chat_room_not_found(self, mock_message):
        """Test task handles missing chat room gracefully"""
        result = send_pachca_forum_notification_task(
            message_id=mock_message.id,
            chat_room_id=99999  # Non-existent
        )

        assert result['success'] is False
        assert 'not found' in result['message']
        assert result['notification_sent'] is False

    @patch('chat.services.pachca_service.PachcaService')
    @patch('core.monitoring.log_system_event')
    def test_task_logs_success_event(self, mock_log_event, mock_pachca_service_class, mock_message):
        """Test task logs success to monitoring system"""
        # Mock service
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_pachca_service_class.return_value = mock_service

        # Execute task
        send_pachca_forum_notification_task(
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        # Verify logging
        mock_log_event.assert_called()
        call_args = mock_log_event.call_args_list
        success_call = [c for c in call_args if 'pachca_notification_sent' in str(c)]
        assert len(success_call) > 0

    @patch('chat.services.pachca_service.PachcaService')
    @patch('core.monitoring.log_system_event')
    def test_task_logs_error_event(self, mock_log_event, mock_pachca_service_class, mock_message):
        """Test task logs errors to monitoring system"""
        # Mock service to raise exception
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.notify_new_forum_message.side_effect = Exception("API Error")
        mock_pachca_service_class.return_value = mock_service

        # Create a mock for the task's self (bind=True)
        mock_self = MagicMock()
        mock_self.request.retries = 2  # Simulate 3rd attempt (final)
        mock_self.max_retries = 3

        # Execute task with exception
        try:
            send_pachca_forum_notification_task(
                mock_self,
                message_id=mock_message.id,
                chat_room_id=mock_message.room.id
            )
        except Exception:
            pass

        # Verify error logged
        error_calls = [c for c in mock_log_event.call_args_list if 'failed' in str(c)]
        assert len(error_calls) > 0


@pytest.mark.django_db
class TestPachcaTaskRetryLogic:
    """Tests for Celery retry mechanism"""

    @patch('chat.services.pachca_service.PachcaService')
    def test_task_retries_on_transient_failure(self, mock_pachca_service_class, mock_message):
        """Test task retries on transient errors"""
        # Mock service to fail then succeed
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.notify_new_forum_message.side_effect = [
            Exception("Transient error"),
            None  # Success on retry
        ]
        mock_pachca_service_class.return_value = mock_service

        # Create mock for task self (simulating Celery bind=True)
        mock_self = MagicMock()
        mock_self.request.retries = 0  # First attempt
        mock_self.max_retries = 3

        # First attempt should raise to trigger retry
        with pytest.raises(Exception):
            send_pachca_forum_notification_task(
                mock_self,
                message_id=mock_message.id,
                chat_room_id=mock_message.room.id
            )

    @patch('chat.services.pachca_service.PachcaService')
    @patch('core.monitoring.log_system_event')
    def test_task_logs_retry_attempt(self, mock_log_event, mock_pachca_service_class, mock_message):
        """Test task logs retry attempts"""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.notify_new_forum_message.side_effect = Exception("Error")
        mock_pachca_service_class.return_value = mock_service

        mock_self = MagicMock()
        mock_self.request.retries = 1  # Second attempt
        mock_self.max_retries = 3

        with pytest.raises(Exception):
            send_pachca_forum_notification_task(
                mock_self,
                message_id=mock_message.id,
                chat_room_id=mock_message.room.id
            )

        # Verify retry logged
        retry_calls = [c for c in mock_log_event.call_args_list if 'retry' in str(c)]
        assert len(retry_calls) > 0

    @patch('chat.services.pachca_service.PachcaService')
    @patch('core.monitoring.log_system_event')
    def test_task_logs_final_failure(self, mock_log_event, mock_pachca_service_class, mock_message):
        """Test task logs critical event on final failure"""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.notify_new_forum_message.side_effect = Exception("Permanent error")
        mock_pachca_service_class.return_value = mock_service

        mock_self = MagicMock()
        mock_self.request.retries = 2  # Final attempt (3rd)
        mock_self.max_retries = 3

        # Final attempt should return failure, not raise
        result = send_pachca_forum_notification_task(
            mock_self,
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        assert result['success'] is False
        assert result['notification_sent'] is False

        # Verify critical event logged
        critical_calls = [c for c in mock_log_event.call_args_list if 'critical' in str(c) or 'final' in str(c)]
        assert len(critical_calls) > 0

    @patch('chat.services.pachca_service.PachcaService')
    def test_task_includes_attempt_number_in_result(self, mock_pachca_service_class, mock_message):
        """Test task result includes attempt number"""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_pachca_service_class.return_value = mock_service

        mock_self = MagicMock()
        mock_self.request.retries = 2  # 3rd attempt
        mock_self.max_retries = 3

        result = send_pachca_forum_notification_task(
            mock_self,
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        assert result['attempt'] == 3  # retries + 1


@pytest.mark.django_db
class TestPachcaTaskLogging:
    """Tests for structured logging"""

    @patch('chat.services.pachca_service.PachcaService')
    @patch('chat.tasks.logger')
    def test_task_logs_message_and_chat_ids(self, mock_logger, mock_pachca_service_class, mock_message):
        """Test task logs include message and chat IDs"""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_pachca_service_class.return_value = mock_service

        send_pachca_forum_notification_task(
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        # Check info logs
        info_calls = mock_logger.info.call_args_list
        assert len(info_calls) > 0

        # Verify IDs are in log messages
        log_messages = [str(call) for call in info_calls]
        assert any(str(mock_message.id) in msg for msg in log_messages)

    @patch('chat.services.pachca_service.PachcaService')
    @patch('chat.tasks.logger')
    def test_task_logs_error_type_on_failure(self, mock_logger, mock_pachca_service_class, mock_message):
        """Test error logs include exception type"""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.notify_new_forum_message.side_effect = ValueError("Invalid data")
        mock_pachca_service_class.return_value = mock_service

        mock_self = MagicMock()
        mock_self.request.retries = 2  # Final attempt
        mock_self.max_retries = 3

        send_pachca_forum_notification_task(
            mock_self,
            message_id=mock_message.id,
            chat_room_id=mock_message.room.id
        )

        # Check error logs
        error_calls = mock_logger.error.call_args_list + mock_logger.critical.call_args_list
        assert len(error_calls) > 0


@pytest.mark.django_db
class TestPachcaMonitoringTask:
    """Tests for monitor_pachca_failures task"""

    @patch('chat.tasks.log_system_event')
    @patch('core.monitoring.system_monitor')
    def test_monitoring_task_runs_successfully(self, mock_monitor, mock_log_event):
        """Test monitoring task executes without errors"""
        mock_monitor.get_system_metrics.return_value = {
            'cpu': {'usage_percent': 50},
            'memory': {'used_percent': 60}
        }

        result = monitor_pachca_failures()

        assert result['success'] is True
        mock_log_event.assert_called()

    @patch('chat.tasks.log_system_event')
    @patch('core.monitoring.system_monitor')
    def test_monitoring_task_handles_errors(self, mock_monitor, mock_log_event):
        """Test monitoring task handles errors gracefully"""
        mock_monitor.get_system_metrics.side_effect = Exception("Monitor error")

        result = monitor_pachca_failures()

        assert result['success'] is False
        assert 'error' in result['message'].lower()

    @patch('chat.tasks.log_system_event')
    def test_monitoring_task_logs_completion(self, mock_log_event):
        """Test monitoring task logs completion event"""
        monitor_pachca_failures()

        # Verify monitoring event logged
        calls = mock_log_event.call_args_list
        monitoring_calls = [c for c in calls if 'monitoring' in str(c)]
        assert len(monitoring_calls) > 0


@pytest.mark.django_db
class TestSignalCeleryIntegration:
    """Tests for signal → Celery task integration"""

    @patch('chat.tasks.send_pachca_forum_notification_task.apply_async')
    def test_signal_dispatches_celery_task(self, mock_task_async, mock_message):
        """Test signal dispatches Celery task on message creation"""
        from chat.signals import send_forum_notification

        # Trigger signal
        send_forum_notification(
            sender=type(mock_message),
            instance=mock_message,
            created=True
        )

        # Verify task dispatched
        mock_task_async.assert_called_once()
        call_kwargs = mock_task_async.call_args
        assert call_kwargs[1]['args'] == [mock_message.id, mock_message.room.id]
        assert 'countdown' in call_kwargs[1]

    @patch('chat.tasks.send_pachca_forum_notification_task.apply_async')
    @patch('chat.signals.logger')
    def test_signal_logs_task_dispatch(self, mock_logger, mock_task_async, mock_message):
        """Test signal logs task dispatch"""
        from chat.signals import send_forum_notification

        send_forum_notification(
            sender=type(mock_message),
            instance=mock_message,
            created=True
        )

        # Verify info log
        info_calls = mock_logger.info.call_args_list
        assert len(info_calls) > 0
        assert any('queued' in str(call) for call in info_calls)

    @patch('chat.tasks.send_pachca_forum_notification_task.apply_async')
    @patch('chat.signals.logger')
    def test_signal_handles_task_dispatch_failure(self, mock_logger, mock_task_async, mock_message):
        """Test signal handles Celery task dispatch failure"""
        from chat.signals import send_forum_notification

        # Mock task dispatch failure
        mock_task_async.side_effect = Exception("Celery error")

        # Should not raise
        send_forum_notification(
            sender=type(mock_message),
            instance=mock_message,
            created=True
        )

        # Verify error logged
        error_calls = mock_logger.error.call_args_list
        assert len(error_calls) > 0
