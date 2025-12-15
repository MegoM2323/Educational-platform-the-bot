"""
Root-level pytest configuration to set ENVIRONMENT=test BEFORE Django loads
This file is loaded by pytest BEFORE any other conftest.py files
"""
import os
import sys

# ============================================================================
# КРИТИЧНО: Установить ENVIRONMENT=test ДО ЛЮБЫХ ИМПОРТОВ Django
# ============================================================================
# Это переопределяет значение из .env файла (development)
# Django settings.py должен видеть ENVIRONMENT=test при инициализации
os.environ['ENVIRONMENT'] = 'test'

# Удалить продакшн БД переменные если они были загружены из .env
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']
if 'DIRECT_URL' in os.environ:
    del os.environ['DIRECT_URL']

# Добавить backend/ в sys.path для абсолютных импортов (backend.chat.models)
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
