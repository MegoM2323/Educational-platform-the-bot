import logging
import os
from django.test import TestCase, RequestFactory, override_settings
from unittest.mock import patch, MagicMock
from config.middleware.error_logging_middleware import ErrorLoggingMiddleware


class ErrorLoggingMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ErrorLoggingMiddleware(lambda r: None)
        self.logger = logging.getLogger("django.request")

    @patch.object(logging.getLogger("django.request"), "error")
    def test_500_error_logs_full_traceback(self, mock_error_logger):
        """Test that 500 errors log full traceback with exc_info=True."""
        request = self.factory.get("/test-endpoint")
        exception = Exception("Test 500 error")

        self.middleware.process_exception(request, exception)

        self.assertTrue(mock_error_logger.called)
        call_args = mock_error_logger.call_args
        self.assertIn("exc_info=True", str(call_args) or call_args.kwargs.get("exc_info"))

    @patch.object(logging.getLogger("django.request"), "warning")
    def test_400_error_logs_warning(self, mock_warning_logger):
        """Test that 400 errors log warning instead of error."""
        request = self.factory.get("/test-endpoint")
        exception = ValueError("Test 400 error")
        exception.status_code = 400

        self.middleware.process_exception(request, exception)

        self.assertTrue(mock_warning_logger.called)

    @patch.object(logging.getLogger("django.request"), "error")
    def test_error_logging_includes_request_details(self, mock_error_logger):
        """Test that error logs include request method and path."""
        request = self.factory.post("/api/test")
        exception = Exception("Test error")

        self.middleware.process_exception(request, exception)

        call_kwargs = mock_error_logger.call_args.kwargs
        extra = call_kwargs.get("extra", {})

        self.assertEqual(extra.get("request_method"), "POST")
        self.assertEqual(extra.get("request_path"), "/api/test")
        self.assertEqual(extra.get("status_code"), 500)

    def test_logs_directory_exists(self):
        """Test that logs directory is created."""
        from django.conf import settings

        logs_dir = os.path.join(settings.BASE_DIR, "logs")
        self.assertTrue(
            os.path.exists(logs_dir),
            f"Logs directory {logs_dir} should exist",
        )
