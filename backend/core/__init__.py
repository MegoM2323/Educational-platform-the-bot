"""
Инициализация приложения core
"""
# Импортируем Celery app, чтобы он был доступен при запуске Django
from .celery import app as celery_app

__all__ = ('celery_app',)

