#!/bin/bash
# ============================================================================
# Безопасный запуск тестов с изолированной БД
# ============================================================================

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo ""
echo "======================================================================"
echo "🧪 THE BOT Platform - Test Mode"
echo "======================================================================"
echo "  Режим: Test"
echo "  База данных: SQLite in-memory (полная изоляция)"
echo "  Защита: Продакшн БД полностью недоступна"
echo "======================================================================"
echo ""

# Принудительно устанавливаем тестовое окружение
export ENVIRONMENT=test
export DJANGO_SETTINGS_MODULE=config.settings

# Удаляем DATABASE_URL если есть (защита от случайных ошибок)
unset DATABASE_URL

# Загружаем .env.test если существует
if [ -f "$PROJECT_ROOT/.env.test" ]; then
    echo "✅ Загружен .env.test"
    export $(cat "$PROJECT_ROOT/.env.test" | grep -v '^#' | grep -v '^$' | xargs)
    # Переопределяем обратно (на случай если в .env.test что-то другое)
    export ENVIRONMENT=test
fi

# Активируем virtualenv
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "❌ Ошибка: virtualenv не найден в $PROJECT_ROOT/.venv"
    echo "   Создайте virtualenv: python3 -m venv .venv"
    exit 1
fi

source "$PROJECT_ROOT/.venv/bin/activate"

# Запускаем pytest
cd "$BACKEND_DIR"

echo ""
echo "Запуск тестов..."
echo ""

pytest "$@"

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ Все тесты прошли успешно!"
else
    echo "❌ Некоторые тесты упали (код выхода: $exit_code)"
fi
echo ""

exit $exit_code
