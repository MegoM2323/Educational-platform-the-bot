"""
Environment-aware configuration service for THE BOT Platform.

This module centralizes all environment-dependent URL and configuration management,
replacing hardcoded values throughout the codebase.

Usage:
    from core.environment import EnvConfig

    config = EnvConfig()
    frontend_url = config.get_frontend_url()
    api_url = config.get_api_url()
    websocket_url = config.get_websocket_url()
    allowed_hosts = config.get_allowed_hosts()
"""

import os
import logging
from typing import List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class EnvConfig:
    """Centralized environment-aware configuration service."""

    # Environment modes
    DEVELOPMENT = 'development'
    PRODUCTION = 'production'
    TEST = 'test'

    # Production domain constants
    PRODUCTION_DOMAIN = 'the-bot.ru'
    PRODUCTION_DOMAIN_WWW = 'www.the-bot.ru'
    PRODUCTION_IP = '5.129.249.206'

    # Development constants
    DEV_LOCALHOST = 'localhost'
    DEV_LOOPBACK = '127.0.0.1'
    DEV_HOST_PORT = '8000'
    DEV_FRONTEND_PORT = '8080'

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.environment = os.getenv('ENVIRONMENT', self.DEVELOPMENT).lower()
        self.debug = os.getenv('DEBUG', 'True').lower() == 'true'

        # Validate environment mode
        if self.environment not in (self.DEVELOPMENT, self.PRODUCTION, self.TEST):
            logger.warning(
                f"Unknown ENVIRONMENT value: {self.environment}. "
                f"Using default: {self.DEVELOPMENT}"
            )
            self.environment = self.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == self.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == self.DEVELOPMENT

    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.environment == self.TEST

    def get_frontend_url(self) -> str:
        """
        Get the frontend URL based on environment.

        Returns:
            str: Frontend URL (e.g., http://localhost:8080 or https://the-bot.ru)
        """
        # First try environment variable (for explicit configuration)
        env_frontend_url = os.getenv('FRONTEND_URL')
        if env_frontend_url:
            return env_frontend_url

        # Default based on environment
        if self.is_production():
            return f'https://{self.PRODUCTION_DOMAIN}'
        elif self.is_test():
            return f'http://{self.DEV_LOCALHOST}:8080'
        else:  # development
            return f'http://{self.DEV_LOCALHOST}:{self.DEV_FRONTEND_PORT}'

    def get_api_url(self) -> str:
        """
        Get the API base URL based on environment.

        Returns:
            str: API URL (e.g., http://localhost:8000/api or https://the-bot.ru/api)
        """
        # For frontend use of API URL (VITE_DJANGO_API_URL)
        env_api_url = os.getenv('VITE_DJANGO_API_URL')
        if env_api_url:
            return env_api_url

        # Construct based on environment
        if self.is_production():
            return f'https://{self.PRODUCTION_DOMAIN}/api'
        elif self.is_test():
            return f'http://{self.DEV_LOCALHOST}:{self.DEV_HOST_PORT}/api'
        else:  # development
            return f'http://{self.DEV_LOCALHOST}:{self.DEV_HOST_PORT}/api'

    def get_websocket_url(self) -> str:
        """
        Get the WebSocket URL based on environment.

        Returns:
            str: WebSocket URL (e.g., ws://localhost:8000/ws or wss://the-bot.ru/ws)
        """
        # First try environment variable
        env_ws_url = os.getenv('WEBSOCKET_URL')
        if env_ws_url:
            return env_ws_url

        # Also check Vite variable (frontend)
        env_ws_url = os.getenv('VITE_WEBSOCKET_URL')
        if env_ws_url:
            return env_ws_url

        # Construct based on environment
        if self.is_production():
            return f'wss://{self.PRODUCTION_DOMAIN}/ws/'
        elif self.is_test():
            return f'ws://{self.DEV_LOCALHOST}:{self.DEV_HOST_PORT}/ws/'
        else:  # development
            return f'ws://{self.DEV_LOCALHOST}:{self.DEV_HOST_PORT}/ws/'

    def get_yookassa_api_url(self) -> str:
        """
        Get the YooKassa API base URL.

        Returns:
            str: YooKassa API URL (always production, regardless of environment)
        """
        return os.getenv(
            'YOOKASSA_API_BASE_URL',
            'https://api.yookassa.ru/v3'
        )

    def get_pachca_api_url(self) -> str:
        """
        Get the Pachca API base URL.

        Returns:
            str: Pachca API URL
        """
        return os.getenv(
            'PACHCA_BASE_URL',
            'https://api.pachca.com/api/shared/v1'
        )

    def get_allowed_hosts(self) -> List[str]:
        """
        Get the list of allowed hosts for this environment.

        Returns:
            List[str]: List of allowed hosts (from ALLOWED_HOSTS env var or sensible defaults)
        """
        # Try environment variable first
        env_hosts = os.getenv('ALLOWED_HOSTS')
        if env_hosts:
            return [h.strip() for h in env_hosts.split(',') if h.strip()]

        # Construct based on environment
        if self.is_production():
            return [
                self.PRODUCTION_DOMAIN,
                self.PRODUCTION_DOMAIN_WWW,
                self.PRODUCTION_IP,
                'localhost',
                self.DEV_LOOPBACK,
                'testserver',
            ]
        elif self.is_test():
            return [
                'localhost',
                self.DEV_LOOPBACK,
                'testserver',
            ]
        else:  # development
            return [
                self.DEV_LOOPBACK,
                'localhost',
                'testserver',
            ]

    def get_cors_allowed_origins(self) -> List[str]:
        """
        Get the list of CORS allowed origins for this environment.

        Returns:
            List[str]: List of allowed origins for CORS
        """
        if self.is_production():
            return [
                f'https://{self.PRODUCTION_DOMAIN}',
                f'https://www.{self.PRODUCTION_DOMAIN}',
                f'http://{self.PRODUCTION_DOMAIN}',  # HTTP to HTTPS redirect
                f'http://www.{self.PRODUCTION_DOMAIN}',
                f'http://{self.PRODUCTION_IP}',
                f'https://{self.PRODUCTION_IP}',
            ]
        elif self.is_test():
            return [
                f'http://localhost:3000',
                f'http://localhost:5173',
                f'http://localhost:8080',
                f'http://localhost:8081',
                f'http://{self.DEV_LOOPBACK}:3000',
                f'http://{self.DEV_LOOPBACK}:5173',
                f'http://{self.DEV_LOOPBACK}:8080',
                f'http://{self.DEV_LOOPBACK}:8081',
                f'http://localhost:8000',
                f'http://{self.DEV_LOOPBACK}:8000',
            ]
        else:  # development
            return [
                f'http://localhost:3000',
                f'http://localhost:5173',
                f'http://localhost:8080',
                f'http://localhost:8081',
                f'http://{self.DEV_LOOPBACK}:3000',
                f'http://{self.DEV_LOOPBACK}:5173',
                f'http://{self.DEV_LOOPBACK}:8080',
                f'http://{self.DEV_LOOPBACK}:8081',
                f'http://localhost:8000',
                f'http://{self.DEV_LOOPBACK}:8000',
            ]

    def get_session_cookie_domain(self) -> Optional[str]:
        """
        Get the session cookie domain for this environment.

        Returns:
            Optional[str]: Cookie domain (or None for development/test)
        """
        if self.is_production():
            return f'.{self.PRODUCTION_DOMAIN}'
        return None

    def get_csrf_cookie_domain(self) -> Optional[str]:
        """
        Get the CSRF cookie domain for this environment.

        Returns:
            Optional[str]: Cookie domain (or None for development/test)
        """
        if self.is_production():
            return f'.{self.PRODUCTION_DOMAIN}'
        return None

    def validate_production(self) -> None:
        """
        Validate that production settings are safe.

        Raises:
            RuntimeError: If production settings are misconfigured
        """
        if not self.is_production():
            return

        # Check that FRONTEND_URL is not localhost
        frontend_url = self.get_frontend_url()
        if 'localhost' in frontend_url or self.DEV_LOOPBACK in frontend_url:
            raise RuntimeError(
                f"Production mode detected, but FRONTEND_URL is set to localhost: {frontend_url}. "
                f"Please set FRONTEND_URL in .env to your production frontend URL "
                f"(e.g., https://{self.PRODUCTION_DOMAIN})"
            )

        # Check that SECRET_KEY is configured and not default
        secret_key = getattr(settings, 'SECRET_KEY', '')
        if not secret_key or secret_key.startswith('django-insecure-'):
            raise RuntimeError(
                "Production mode detected, but SECRET_KEY is not properly configured. "
                "Generate a secure key using: python -c 'from django.core.management.utils import "
                "get_random_secret_key; print(get_random_secret_key())'"
            )

        # Check that DEBUG is False
        if self.debug or os.getenv('DEBUG', 'False').lower() == 'true':
            logger.warning(
                "Production mode detected, but DEBUG is set to True. "
                "This is a security risk. Set DEBUG=False in .env for production."
            )

    def get_redis_url(self) -> str:
        """
        Get the Redis URL for caching and Celery.

        Returns:
            str: Redis URL
        """
        return os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')

    def get_log_level(self) -> str:
        """
        Get the appropriate logging level for this environment.

        Returns:
            str: Logging level (DEBUG for dev, WARNING for prod)
        """
        if self.is_production():
            return 'WARNING'
        else:
            return 'DEBUG'

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"<EnvConfig "
            f"environment={self.environment} "
            f"debug={self.debug} "
            f"frontend_url={self.get_frontend_url()} "
            f">"
        )


# Global singleton instance for convenience
_global_config: Optional[EnvConfig] = None


def get_env_config() -> EnvConfig:
    """
    Get the global environment configuration instance.

    Returns:
        EnvConfig: Global configuration instance
    """
    global _global_config
    if _global_config is None:
        _global_config = EnvConfig()
    return _global_config


def reset_env_config() -> None:
    """Reset the global configuration instance (useful for testing)."""
    global _global_config
    _global_config = None
