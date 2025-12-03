from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self) -> None:
        """Import signal handlers when app is ready."""
        try:
            import chat.signals  # noqa: F401
        except Exception as e:
            print(f"Warning: Could not import chat.signals: {e}")
