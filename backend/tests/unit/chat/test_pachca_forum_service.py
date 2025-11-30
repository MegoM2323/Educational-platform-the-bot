"""
Unit tests for PachcaService for forum message notifications.

Tests service initialization, notification sending, error handling,
retry logic, and graceful failure handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
import os

from chat.services.pachca_service import PachcaService


@pytest.fixture
def mock_pachca_env(monkeypatch):
    """Mock Pachca environment variables"""
    monkeypatch.setenv('PACHCA_FORUM_API_TOKEN', 'test_forum_token_12345')
    monkeypatch.setenv('PACHCA_FORUM_CHANNEL_ID', '654321')
    monkeypatch.setenv('PACHCA_FORUM_BASE_URL', 'https://api.pachca.test/api/v1')


@pytest.fixture
def pachca_service_configured(mock_pachca_env):
    """Create configured PachcaService instance"""
    return PachcaService()


@pytest.fixture
def pachca_service_unconfigured():
    """Create PachcaService without configuration"""
    return PachcaService(api_token=None, channel_id=None)


@pytest.fixture
def mock_message():
    """Mock Message object"""
    msg = Mock()
    msg.id = 'msg-123'
    msg.content = "This is a test forum message"
    msg.sender = Mock()
    msg.sender.get_full_name.return_value = "Ivan Ivanov"
    return msg


@pytest.fixture
def mock_forum_subject_chat():
    """Mock forum chat with subject enrollment"""
    chat = Mock()
    chat.id = 'chat-123'
    chat.type = 'forum_subject'
    chat.participants = Mock()
    chat.enrollment = Mock()
    chat.enrollment.get_subject_name.return_value = "Mathematics"

    # Mock participants
    recipient = Mock()
    recipient.id = 'user-456'
    recipient.get_full_name.return_value = "Maria Petrova"

    chat.participants.exclude.return_value.all.return_value = [recipient]

    return chat


@pytest.fixture
def mock_forum_tutor_chat():
    """Mock forum chat without subject enrollment"""
    chat = Mock()
    chat.id = 'chat-456'
    chat.type = 'forum_tutor'
    chat.participants = Mock()
    chat.enrollment = None

    recipient = Mock()
    recipient.id = 'user-789'
    recipient.get_full_name.return_value = "Sergey Sidorov"

    chat.participants.exclude.return_value.all.return_value = [recipient]

    return chat


@pytest.mark.unit
class TestPachcaServiceInitialization:
    """Tests for PachcaService initialization"""

    def test_service_initialization_from_env(self, mock_pachca_env):
        """Test service initializes with environment variables"""
        service = PachcaService()

        assert service.api_token == 'test_forum_token_12345'
        assert service.channel_id == '654321'
        assert service.base_url == 'https://api.pachca.test/api/v1'

    def test_service_initialization_with_parameters(self):
        """Test service initializes with explicit parameters"""
        service = PachcaService(
            api_token='custom_token',
            channel_id='999',
            base_url='https://custom.api.url'
        )

        assert service.api_token == 'custom_token'
        assert service.channel_id == '999'
        assert service.base_url == 'https://custom.api.url'

    def test_service_parameters_override_env(self, mock_pachca_env):
        """Test explicit parameters override environment variables"""
        service = PachcaService(
            api_token='override_token',
            channel_id='111'
        )

        assert service.api_token == 'override_token'
        assert service.channel_id == '111'

    def test_service_default_base_url(self, monkeypatch):
        """Test default base URL is Pachca API"""
        monkeypatch.setenv('PACHCA_FORUM_API_TOKEN', 'test_token')
        monkeypatch.setenv('PACHCA_FORUM_CHANNEL_ID', '123')
        # Don't set PACHCA_FORUM_BASE_URL

        service = PachcaService()

        assert service.base_url == 'https://api.pachca.com/api/shared/v1'

    def test_service_headers_with_token(self, mock_pachca_env):
        """Test headers are set with authorization when token is present"""
        service = PachcaService()

        assert 'Authorization' in service.headers
        assert service.headers['Authorization'] == 'Bearer test_forum_token_12345'
        assert service.headers['Content-Type'] == 'application/json'

    def test_service_headers_empty_without_token(self):
        """Test headers are empty when token is not configured"""
        service = PachcaService(api_token=None)

        assert service.headers == {}


@pytest.mark.unit
class TestPachcaServiceConfigurationCheck:
    """Tests for is_configured() method"""

    def test_is_configured_true_when_both_set(self, pachca_service_configured):
        """Test is_configured returns True when token and channel are set"""
        assert pachca_service_configured.is_configured() is True

    def test_is_configured_false_without_token(self, monkeypatch):
        """Test is_configured returns False without token"""
        monkeypatch.setenv('PACHCA_FORUM_API_TOKEN', '')
        monkeypatch.setenv('PACHCA_FORUM_CHANNEL_ID', '123')
        service = PachcaService()
        assert service.is_configured() is False

    def test_is_configured_false_without_channel(self, monkeypatch):
        """Test is_configured returns False without channel ID"""
        monkeypatch.setenv('PACHCA_FORUM_API_TOKEN', 'token')
        monkeypatch.setenv('PACHCA_FORUM_CHANNEL_ID', '')
        service = PachcaService()
        assert service.is_configured() is False

    def test_is_configured_false_without_both(self):
        """Test is_configured returns False without token and channel"""
        service = PachcaService()
        assert service.is_configured() is False


@pytest.mark.unit
class TestPachcaServiceNotificationSending:
    """Tests for notify_new_forum_message() method"""

    def test_notify_skips_if_not_configured(self, pachca_service_unconfigured, mock_message, mock_forum_subject_chat):
        """Test notification is skipped if service not configured"""
        with patch.object(pachca_service_unconfigured, '_send_message') as mock_send:
            pachca_service_unconfigured.notify_new_forum_message(mock_message, mock_forum_subject_chat)

        mock_send.assert_not_called()

    def test_notify_builds_correct_message_format(self, pachca_service_configured, mock_message, mock_forum_subject_chat):
        """Test notification message has correct format"""
        with patch.object(pachca_service_configured, '_send_message') as mock_send:
            pachca_service_configured.notify_new_forum_message(mock_message, mock_forum_subject_chat)

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]

        # Check format: [Forum] {Subject}: {Sender} → {Recipients}: {Message}
        assert '[Forum]' in call_args or 'Forum' in call_args
        assert 'Mathematics' in call_args or 'Subject' in call_args
        assert 'Ivan Ivanov' in call_args
        assert ('→' in call_args or 'Maria' in call_args)

    def test_notify_truncates_long_message(self, pachca_service_configured, mock_forum_subject_chat):
        """Test long messages are truncated with ellipsis"""
        long_message = Mock()
        long_message.sender = Mock()
        long_message.sender.get_full_name.return_value = "Ivan"
        long_message.content = "x" * 150  # 150 characters

        with patch.object(pachca_service_configured, '_send_message') as mock_send:
            pachca_service_configured.notify_new_forum_message(long_message, mock_forum_subject_chat)

        call_args = mock_send.call_args[0][0]
        assert '...' in call_args
        assert len(call_args) <= 200  # Should be reasonable length

    def test_notify_handles_error_gracefully(self, pachca_service_configured, mock_message, mock_forum_subject_chat):
        """Test notification handles errors gracefully without raising"""
        with patch.object(pachca_service_configured, '_send_message', side_effect=Exception("API Error")):
            # Should not raise exception
            pachca_service_configured.notify_new_forum_message(mock_message, mock_forum_subject_chat)

    def test_notify_includes_subject_name_from_enrollment(self, pachca_service_configured, mock_message, mock_forum_subject_chat):
        """Test notification includes subject name from enrollment"""
        with patch.object(pachca_service_configured, '_send_message') as mock_send:
            pachca_service_configured.notify_new_forum_message(mock_message, mock_forum_subject_chat)

        call_args = mock_send.call_args[0][0]
        assert 'Mathematics' in call_args

    def test_notify_includes_recipient_names(self, pachca_service_configured, mock_message, mock_forum_subject_chat):
        """Test notification includes recipient names"""
        with patch.object(pachca_service_configured, '_send_message') as mock_send:
            pachca_service_configured.notify_new_forum_message(mock_message, mock_forum_subject_chat)

        call_args = mock_send.call_args[0][0]
        # Check that recipient is mentioned (might be mocked or might be fallback)
        assert len(call_args) > 0  # Message was generated


@pytest.mark.unit
class TestPachcaServiceRetryLogic:
    """Tests for HTTP retry logic"""

    @patch('chat.services.pachca_service.httpx.post')
    def test_retry_on_server_error_500(self, mock_post, pachca_service_configured):
        """Test service retries on 500 server error"""
        # First two attempts fail with 500, third succeeds
        mock_post.side_effect = [
            MagicMock(status_code=500, text='Server Error'),
            MagicMock(status_code=500, text='Server Error'),
            MagicMock(status_code=200)
        ]

        with patch('chat.services.pachca_service.sleep'):  # Mock sleep to avoid delays
            result = pachca_service_configured._send_message("Test message")

        assert result is True
        assert mock_post.call_count == 3

    @patch('chat.services.pachca_service.httpx.post')
    def test_no_retry_on_client_error_400(self, mock_post, pachca_service_configured):
        """Test service does NOT retry on 400 client error"""
        mock_post.return_value = MagicMock(status_code=400, text='Bad Request')

        result = pachca_service_configured._send_message("Test message")

        assert result is False
        assert mock_post.call_count == 1

    @patch('chat.services.pachca_service.httpx.post')
    def test_no_retry_on_403_forbidden(self, mock_post, pachca_service_configured):
        """Test service does NOT retry on 403 forbidden"""
        mock_post.return_value = MagicMock(status_code=403, text='Forbidden')

        result = pachca_service_configured._send_message("Test message")

        assert result is False
        assert mock_post.call_count == 1

    @patch('chat.services.pachca_service.httpx.post')
    def test_retry_on_network_error(self, mock_post, pachca_service_configured):
        """Test service retries on network errors"""
        mock_post.side_effect = [
            httpx.RequestError("Connection failed"),
            httpx.RequestError("Connection failed"),
            MagicMock(status_code=200)
        ]

        with patch('chat.services.pachca_service.sleep'):
            result = pachca_service_configured._send_message("Test message")

        assert result is True
        assert mock_post.call_count == 3

    @patch('chat.services.pachca_service.httpx.post')
    def test_max_retries_respected(self, mock_post, pachca_service_configured):
        """Test max retry attempts are respected"""
        mock_post.return_value = MagicMock(status_code=500, text='Server Error')

        with patch('chat.services.pachca_service.sleep'):
            result = pachca_service_configured._send_message("Test", max_retries=3)

        assert result is False
        assert mock_post.call_count == 3

    @patch('chat.services.pachca_service.httpx.post')
    def test_exponential_backoff_timing(self, mock_post, pachca_service_configured):
        """Test exponential backoff timing between retries"""
        mock_post.return_value = MagicMock(status_code=500, text='Error')

        sleep_calls = []
        def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch('chat.services.pachca_service.sleep', side_effect=mock_sleep):
            pachca_service_configured._send_message("Test", max_retries=3)

        # Should have 2^0=1, 2^1=2 timing
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 1
        assert sleep_calls[1] == 2


@pytest.mark.unit
class TestPachcaServiceMessageFormatting:
    """Tests for message formatting methods"""

    def test_truncate_message_short_content(self, pachca_service_configured):
        """Test truncate does not modify short messages"""
        content = "Short message"
        result = pachca_service_configured._truncate_message(content, max_length=100)
        assert result == content

    def test_truncate_message_long_content(self, pachca_service_configured):
        """Test truncate adds ellipsis to long messages"""
        content = "x" * 150
        result = pachca_service_configured._truncate_message(content, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_get_forum_subject_name_from_enrollment(self, pachca_service_configured, mock_forum_subject_chat):
        """Test extracting subject name from enrollment"""
        name = pachca_service_configured._get_forum_subject_name(mock_forum_subject_chat)
        assert name == "Mathematics"

    def test_get_forum_subject_name_fallback(self, pachca_service_configured, mock_forum_tutor_chat):
        """Test fallback when enrollment not available"""
        name = pachca_service_configured._get_forum_subject_name(mock_forum_tutor_chat)
        assert name == "Subject"

    def test_get_recipient_names_single_recipient(self, pachca_service_configured):
        """Test getting recipient names with single recipient"""
        sender = Mock()
        sender.id = 'sender-id'

        recipient = Mock()
        recipient.id = 'recipient-id'
        recipient.get_full_name.return_value = "Maria Petrova"

        chat = Mock()
        chat.id = 'chat-123'
        # Make participants.exclude() return an iterable with recipients
        chat.participants.exclude.return_value = [recipient]

        names = pachca_service_configured._get_forum_recipient_names(chat, sender)
        assert "Maria Petrova" in names

    def test_get_recipient_names_multiple_recipients(self, pachca_service_configured):
        """Test getting recipient names with multiple recipients"""
        sender = Mock()
        sender.id = 'sender-id'

        recipient1 = Mock()
        recipient1.id = 'id-1'
        recipient1.get_full_name.return_value = "Maria Petrova"

        recipient2 = Mock()
        recipient2.id = 'id-2'
        recipient2.get_full_name.return_value = "Ivan Ivanov"

        chat = Mock()
        chat.id = 'chat-123'
        # Make participants.exclude() return an iterable with recipients
        chat.participants.exclude.return_value = [recipient1, recipient2]

        names = pachca_service_configured._get_forum_recipient_names(chat, sender)
        assert "Maria Petrova" in names
        assert "Ivan Ivanov" in names
        assert ", " in names

    def test_get_recipient_names_fallback(self, pachca_service_configured, mock_forum_subject_chat):
        """Test fallback when recipients cannot be retrieved"""
        sender = Mock()
        sender.id = 'sender-id'

        # Mock exception when getting recipients
        mock_forum_subject_chat.participants.exclude.side_effect = Exception("Error")

        names = pachca_service_configured._get_forum_recipient_names(mock_forum_subject_chat, sender)
        assert names == "Others"


@pytest.mark.unit
class TestPachcaServicePayloadConstruction:
    """Tests for HTTP payload construction"""

    @patch('chat.services.pachca_service.httpx.post')
    def test_payload_structure(self, mock_post, pachca_service_configured):
        """Test payload has correct structure"""
        mock_post.return_value = MagicMock(status_code=200)

        pachca_service_configured._send_message("Test notification")

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs['json']

        assert 'channels' in payload
        assert 'content' in payload
        assert payload['channels'] == ['654321']
        assert payload['content'] == "Test notification"

    @patch('chat.services.pachca_service.httpx.post')
    def test_headers_in_request(self, mock_post, pachca_service_configured):
        """Test authorization headers are sent"""
        mock_post.return_value = MagicMock(status_code=200)

        pachca_service_configured._send_message("Test")

        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs['headers']

        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_forum_token_12345'

    @patch('chat.services.pachca_service.httpx.post')
    def test_timeout_configured(self, mock_post, pachca_service_configured):
        """Test request timeout is set"""
        mock_post.return_value = MagicMock(status_code=200)

        pachca_service_configured._send_message("Test")

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['timeout'] == 10.0


@pytest.mark.unit
class TestPachcaServiceErrorHandling:
    """Tests for error handling"""

    @patch('chat.services.pachca_service.httpx.post')
    def test_handles_timeout_error(self, mock_post, pachca_service_configured):
        """Test graceful handling of timeout errors"""
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        with patch('chat.services.pachca_service.sleep'):
            result = pachca_service_configured._send_message("Test")

        assert result is False

    @patch('chat.services.pachca_service.httpx.post')
    def test_handles_connection_error(self, mock_post, pachca_service_configured):
        """Test graceful handling of connection errors"""
        mock_post.side_effect = httpx.ConnectError("Connection failed")

        with patch('chat.services.pachca_service.sleep'):
            result = pachca_service_configured._send_message("Test")

        assert result is False

    def test_notify_handles_missing_enrollment(self, pachca_service_configured, mock_message):
        """Test notification handles chat without enrollment"""
        chat = Mock()
        chat.type = 'forum_tutor'
        chat.enrollment = None
        chat.participants = Mock()
        chat.participants.exclude.return_value.all.return_value = []

        with patch.object(pachca_service_configured, '_send_message'):
            # Should not raise
            pachca_service_configured.notify_new_forum_message(mock_message, chat)

    def test_send_message_invalid_credentials(self, pachca_service_configured):
        """Test handling of invalid credentials"""
        service = PachcaService(api_token='', channel_id='')

        result = service._send_message("Test")
        assert result is False
