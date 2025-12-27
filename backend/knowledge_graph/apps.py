from django.apps import AppConfig


class KnowledgeGraphConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "knowledge_graph"

    def ready(self):
        """Регистрация signals при запуске приложения"""
        import knowledge_graph.signals
