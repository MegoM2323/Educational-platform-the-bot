import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"

    def ready(self) -> None:
        """Import signal handlers when app is ready."""
        try:
            import chat.signals  # noqa: F401
        except Exception as e:
            logger.warning(f"Could not import chat.signals: {e}")
