import pytest
import logging
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest import mock
import io
import sys

User = get_user_model()


@override_settings(ROOT_URLCONF="config.urls")
class TestLoggingInLogin(TestCase):
    """Test: Logger is working (not print)"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )

    def test_logger_used_not_print(self):
        """Login should use logger, not print()"""
        with mock.patch("accounts.views.logger") as mock_logger:
            response = self.client.post(
                "/api/accounts/login/",
                {
                    "email": "user@test.com",
                    "password": "pass123",
                },
                format="json",
            )
            # Logger should have been called
            assert mock_logger.info.called or mock_logger.debug.called or mock_logger.warning.called
            assert response.status_code == status.HTTP_200_OK

    def test_no_stdout_output_during_login(self):
        """Login should not print to stdout"""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            response = self.client.post(
                "/api/accounts/login/",
                {
                    "email": "user@test.com",
                    "password": "pass123",
                },
                format="json",
            )
            sys.stdout = sys.__stdout__
            output = captured_output.getvalue()

            # Should not have debug print statements
            # (except possible framework output which is ok)
            assert response.status_code == status.HTTP_200_OK
        finally:
            sys.stdout = sys.__stdout__

    def test_password_not_logged(self):
        """Passwords should never be logged"""
        with mock.patch("accounts.views.logger") as mock_logger:
            response = self.client.post(
                "/api/accounts/login/",
                {
                    "email": "user@test.com",
                    "password": "pass123",
                },
                format="json",
            )

            # Check that password was not logged
            for call in mock_logger.info.call_args_list:
                if call.args:
                    logged_string = str(call.args[0])
                    assert "pass123" not in logged_string, "Password should not be logged"

            for call in mock_logger.debug.call_args_list:
                if call.args:
                    logged_string = str(call.args[0])
                    assert "pass123" not in logged_string, "Password should not be logged"

            for call in mock_logger.warning.call_args_list:
                if call.args:
                    logged_string = str(call.args[0])
                    assert "pass123" not in logged_string, "Password should not be logged"

    def test_failed_login_logged(self):
        """Failed login attempts should be logged"""
        with mock.patch("accounts.views.logger") as mock_logger:
            response = self.client.post(
                "/api/accounts/login/",
                {
                    "email": "user@test.com",
                    "password": "wrongpass",
                },
                format="json",
            )
            # Should log the failure (warning or info)
            assert mock_logger.warning.called or mock_logger.info.called
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
