"""
Конфигурация приложения accounts.
"""
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    """Конфигурация приложения accounts."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Инициализируем Django signals после того как приложение будет готово.

        Это гарантирует что все модели загружены перед импортом signals.
        """
        try:
            from . import signals  # noqa: F401
            logger.debug("[AccountsConfig] Signals loaded successfully")
        except Exception as exc:
            logger.error(
                f"[AccountsConfig] Failed to load signals: {exc}",
                exc_info=True
            )
