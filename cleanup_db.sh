#!/usr/bin/env bash
# Скрипт для очистки базы данных от мусорных данных

cd "$(dirname "$0")/backend"
../.venv/bin/python manage.py cleanup_database "$@"

