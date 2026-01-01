"""
Инициализация приложения core
"""
# Импортируем Celery app, чтобы он был доступен при запуске Django
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery не установлен - для создания пользователей в production
    celery_app = None
    __all__ = ()

