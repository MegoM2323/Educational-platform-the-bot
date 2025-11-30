"""
Tests for the environment configuration module.

Tests environment-aware URL generation and configuration for different modes:
- development (localhost)
- production (the-bot.ru)
- test (localhost in memory)
"""

import os
import pytest
from django.test import TestCase
from core.environment import EnvConfig, get_env_config, reset_env_config


class TestEnvConfigDevelopmentMode(TestCase):
    """Test EnvConfig in development mode."""

    def setUp(self) -> None:
        """Set up test environment."""
        os.environ['ENVIRONMENT'] = 'development'
        # Clear any override environment variables
        for key in ['FRONTEND_URL', 'VITE_DJANGO_API_URL', 'WEBSOCKET_URL',
                   'VITE_WEBSOCKET_URL', 'ALLOWED_HOSTS']:
            if key in os.environ:
                del os.environ[key]
        reset_env_config()
        self.config = EnvConfig()

    def test_is_development(self) -> None:
        """Test development mode detection."""
        assert self.config.is_development() is True
        assert self.config.is_production() is False
        assert self.config.is_test() is False

    def test_frontend_url_development(self) -> None:
        """Test frontend URL in development."""
        assert self.config.get_frontend_url() == 'http://localhost:8080'

    def test_api_url_development(self) -> None:
        """Test API URL in development."""
        api_url = self.config.get_api_url()
        assert 'api' in api_url
        assert '8000' in api_url
        assert 'http' in api_url

    def test_websocket_url_development(self) -> None:
        """Test WebSocket URL in development."""
        ws_url = self.config.get_websocket_url()
        assert 'ws' in ws_url
        assert '8000' in ws_url
        assert 'localhost' in ws_url or '127.0.0.1' in ws_url

    def test_allowed_hosts_development(self) -> None:
        """Test allowed hosts in development."""
        hosts = self.config.get_allowed_hosts()
        assert '127.0.0.1' in hosts
        assert 'localhost' in hosts
        assert 'testserver' in hosts
        assert 'the-bot.ru' not in hosts

    def test_cors_origins_development(self) -> None:
        """Test CORS origins in development."""
        origins = self.config.get_cors_allowed_origins()
        assert 'http://localhost:3000' in origins
        assert 'http://localhost:8080' in origins
        assert 'http://127.0.0.1:8000' in origins
        assert 'https://the-bot.ru' not in origins

    def test_session_cookie_domain_development(self) -> None:
        """Test session cookie domain in development."""
        assert self.config.get_session_cookie_domain() is None

    def test_csrf_cookie_domain_development(self) -> None:
        """Test CSRF cookie domain in development."""
        assert self.config.get_csrf_cookie_domain() is None

    def test_yookassa_api_url(self) -> None:
        """Test YooKassa API URL."""
        assert self.config.get_yookassa_api_url() == 'https://api.yookassa.ru/v3'

    def test_pachca_api_url(self) -> None:
        """Test Pachca API URL."""
        assert self.config.get_pachca_api_url() == 'https://api.pachca.com/api/shared/v1'


class TestEnvConfigProductionMode(TestCase):
    """Test EnvConfig in production mode."""

    def setUp(self) -> None:
        """Set up test environment."""
        os.environ['ENVIRONMENT'] = 'production'
        # Clear any override environment variables
        for key in ['FRONTEND_URL', 'VITE_DJANGO_API_URL', 'WEBSOCKET_URL',
                   'VITE_WEBSOCKET_URL', 'ALLOWED_HOSTS']:
            if key in os.environ:
                del os.environ[key]
        reset_env_config()
        self.config = EnvConfig()

    def test_is_production(self) -> None:
        """Test production mode detection."""
        assert self.config.is_production() is True
        assert self.config.is_development() is False
        assert self.config.is_test() is False

    def test_frontend_url_production(self) -> None:
        """Test frontend URL in production."""
        assert self.config.get_frontend_url() == 'https://the-bot.ru'

    def test_api_url_production(self) -> None:
        """Test API URL in production."""
        assert self.config.get_api_url() == 'https://the-bot.ru/api'

    def test_websocket_url_production(self) -> None:
        """Test WebSocket URL in production."""
        assert self.config.get_websocket_url() == 'wss://the-bot.ru/ws/'



    def test_allowed_hosts_production(self) -> None:
        """Test allowed hosts in production."""
        hosts = self.config.get_allowed_hosts()
        assert 'the-bot.ru' in hosts
        assert 'www.the-bot.ru' in hosts
        assert '5.129.249.206' in hosts
        assert 'testserver' in hosts

    def test_cors_origins_production(self) -> None:
        """Test CORS origins in production."""
        origins = self.config.get_cors_allowed_origins()
        assert 'https://the-bot.ru' in origins
        assert 'https://www.the-bot.ru' in origins
        assert 'http://the-bot.ru' in origins  # HTTP to HTTPS redirect
        assert 'http://localhost:8080' not in origins

    def test_session_cookie_domain_production(self) -> None:
        """Test session cookie domain in production."""
        assert self.config.get_session_cookie_domain() == '.the-bot.ru'

    def test_csrf_cookie_domain_production(self) -> None:
        """Test CSRF cookie domain in production."""
        assert self.config.get_csrf_cookie_domain() == '.the-bot.ru'


class TestEnvConfigTestMode(TestCase):
    """Test EnvConfig in test mode."""

    def setUp(self) -> None:
        """Set up test environment."""
        os.environ['ENVIRONMENT'] = 'test'
        # Clear any override environment variables
        for key in ['FRONTEND_URL', 'VITE_DJANGO_API_URL', 'WEBSOCKET_URL',
                   'VITE_WEBSOCKET_URL', 'ALLOWED_HOSTS']:
            if key in os.environ:
                del os.environ[key]
        reset_env_config()
        self.config = EnvConfig()

    def test_is_test(self) -> None:
        """Test test mode detection."""
        assert self.config.is_test() is True
        assert self.config.is_development() is False
        assert self.config.is_production() is False

    def test_frontend_url_test(self) -> None:
        """Test frontend URL in test mode."""
        assert self.config.get_frontend_url() == 'http://localhost:8080'

    def test_api_url_test(self) -> None:
        """Test API URL in test mode."""
        api_url = self.config.get_api_url()
        assert 'api' in api_url
        assert '8000' in api_url
        assert 'http' in api_url

    def test_websocket_url_test(self) -> None:
        """Test WebSocket URL in test mode."""
        ws_url = self.config.get_websocket_url()
        assert 'ws' in ws_url
        assert '8000' in ws_url
        assert 'localhost' in ws_url or '127.0.0.1' in ws_url

    def test_allowed_hosts_test(self) -> None:
        """Test allowed hosts in test mode."""
        hosts = self.config.get_allowed_hosts()
        assert 'localhost' in hosts
        assert '127.0.0.1' in hosts
        assert 'testserver' in hosts
        assert 'the-bot.ru' not in hosts


class TestEnvConfigEnvironmentVariableOverrides(TestCase):
    """Test environment variable overrides."""

    def setUp(self) -> None:
        """Set up test environment."""
        os.environ['ENVIRONMENT'] = 'development'
        reset_env_config()

    def test_frontend_url_override(self) -> None:
        """Test FRONTEND_URL environment variable override."""
        os.environ['FRONTEND_URL'] = 'http://custom.local:3000'
        reset_env_config()
        config = EnvConfig()
        assert config.get_frontend_url() == 'http://custom.local:3000'

    def test_api_url_override(self) -> None:
        """Test VITE_DJANGO_API_URL environment variable override."""
        os.environ['VITE_DJANGO_API_URL'] = 'http://custom.local:8001/api'
        reset_env_config()
        config = EnvConfig()
        assert config.get_api_url() == 'http://custom.local:8001/api'

    def test_websocket_url_override(self) -> None:
        """Test WEBSOCKET_URL environment variable override."""
        os.environ['WEBSOCKET_URL'] = 'ws://custom.local:8001/ws'
        reset_env_config()
        config = EnvConfig()
        assert config.get_websocket_url() == 'ws://custom.local:8001/ws'

    def test_websocket_url_override_vite(self) -> None:
        """Test VITE_WEBSOCKET_URL environment variable override."""
        os.environ['VITE_WEBSOCKET_URL'] = 'ws://custom.local:8002/ws'
        reset_env_config()
        config = EnvConfig()
        assert config.get_websocket_url() == 'ws://custom.local:8002/ws'

    def test_allowed_hosts_override(self) -> None:
        """Test ALLOWED_HOSTS environment variable override."""
        os.environ['ALLOWED_HOSTS'] = 'example.com,www.example.com,localhost'
        reset_env_config()
        config = EnvConfig()
        hosts = config.get_allowed_hosts()
        assert 'example.com' in hosts
        assert 'www.example.com' in hosts
        assert 'localhost' in hosts

    def tearDown(self) -> None:
        """Clean up test environment."""
        for key in ['FRONTEND_URL', 'VITE_DJANGO_API_URL', 'WEBSOCKET_URL',
                   'VITE_WEBSOCKET_URL', 'ALLOWED_HOSTS']:
            if key in os.environ:
                del os.environ[key]


class TestEnvConfigGlobalInstance(TestCase):
    """Test global configuration instance."""

    def setUp(self) -> None:
        """Set up test environment."""
        os.environ['ENVIRONMENT'] = 'development'
        reset_env_config()

    def test_get_env_config(self) -> None:
        """Test getting global config instance."""
        config1 = get_env_config()
        config2 = get_env_config()
        assert config1 is config2  # Should be same instance

    def test_reset_env_config(self) -> None:
        """Test resetting global config instance."""
        config1 = get_env_config()
        reset_env_config()
        config2 = get_env_config()
        assert config1 is not config2  # Should be different instances


class TestEnvConfigProductionValidation(TestCase):
    """Test production configuration validation."""

    def setUp(self) -> None:
        """Set up test environment."""
        os.environ['ENVIRONMENT'] = 'production'
        reset_env_config()

    def test_validate_production_with_localhost_fails(self) -> None:
        """Test that production validation fails with localhost FRONTEND_URL."""
        os.environ['FRONTEND_URL'] = 'http://localhost:8080'
        reset_env_config()
        config = EnvConfig()

        with pytest.raises(RuntimeError, match='localhost'):
            config.validate_production()

    def test_validate_production_checks_mode(self) -> None:
        """Test that validation only runs in production mode."""
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['FRONTEND_URL'] = 'http://localhost:8080'
        reset_env_config()
        config = EnvConfig()

        # Should not raise an exception in development mode
        try:
            config.validate_production()
        except RuntimeError:
            pytest.fail('validate_production() should not validate in non-production mode')
