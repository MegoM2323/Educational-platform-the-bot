"""
Конфигурация приложения accounts.
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Конфигурация приложения accounts."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Инициализируем Django signals после того как приложение будет готово.

        Это гарантирует что все модели загружены перед импортом signals.
        """
        from . import signals  # noqa: F401
