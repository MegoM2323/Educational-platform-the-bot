from django.apps import AppConfig


class AssignmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assignments'

    def ready(self):
        """
        Register signals when app is ready.

        T_ASSIGN_013: Register cache invalidation signals
        T_ASSIGN_006: Register scheduling signals
        T_ASSIGN_010: Register history and versioning signals
        """
        # Import signals to register them
        import assignments.signals  # noqa: F401
        import assignments.signals.history  # noqa: F401
