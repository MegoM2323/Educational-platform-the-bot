"""
Root-level pytest configuration to set ENVIRONMENT=test BEFORE Django loads
"""
import os
import sys
from pathlib import Path

# КРИТИЧНО: Установить ДО загрузки pytest и pytest-django
os.environ["ENVIRONMENT"] = "test"

# Удалить продакшн БД переменные если они были загружены из .env
for var in ["DATABASE_URL", "DIRECT_URL"]:
    if var in os.environ:
        del os.environ[var]

# Добавить backend/ в sys.path для абсолютных импортов
backend_path = str(Path(__file__).parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
