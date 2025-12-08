#!/bin/bash
set -e

# ============================================================================
# Development Mode: Локальная разработка с SQLite БД
# ============================================================================

# Принудительно устанавливаем development режим
export ENVIRONMENT=development

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}======================================================================"
echo -e "🚀 THE BOT Platform - Development Mode"
echo -e "======================================================================${NC}"
echo -e "  Режим: ${GREEN}Development${NC}"
echo -e "  База данных: ${GREEN}SQLite (backend/db.sqlite3)${NC}"
echo -e "  Защита: ${YELLOW}Продакшн БД недоступна в этом режиме${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="python3"

cd "$PROJECT_ROOT"

# Функция для убийства процессов на портах
kill_port_processes() {
    local port=$1
    local service_name=$2

    echo -e "${YELLOW}🔍 Проверка порта $port ($service_name)...${NC}"

    # Находим процессы на порту
    local pids=$(lsof -ti:$port 2>/dev/null)

    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  На порту $port найдены процессы: $pids${NC}"
        echo -e "${RED}🛑 Убиваем процессы на порту $port...${NC}"

        # Убиваем процессы
        for pid in $pids; do
            echo "   Убиваем процесс $pid..."
            kill -9 $pid 2>/dev/null || true
        done

        # Ждем немного
        sleep 2

        # Проверяем, что процессы убиты
        local remaining_pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo -e "${RED}❌ Не удалось убить все процессы на порту $port${NC}"
            echo "   Оставшиеся процессы: $remaining_pids"
        else
            echo -e "${GREEN}✅ Порт $port освобожден${NC}"
        fi
    else
        echo -e "${GREEN}✅ Порт $port свободен${NC}"
    fi
}

# Убиваем процессы на портах 8000 и 8080
kill_port_processes 8000 "Django Backend"
kill_port_processes 8080 "React Frontend"

# Проверяем, что мы в правильной директории
if [ ! -f "$BACKEND_DIR/manage.py" ]; then
    echo -e "${RED}❌ Ошибка: Запустите скрипт из корневой директории проекта${NC}"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}❌ Виртуальное окружение не найдено. Создаем...${NC}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Активируем виртуальное окружение Python
echo -e "${BLUE}📦 Активация виртуального окружения Python...${NC}"
source "$VENV_DIR/bin/activate"

# Исправляем проблему с Twisted/OpenSSL
echo -e "${YELLOW}🔧 Проверка и исправление версий Twisted/OpenSSL...${NC}"
cd "$BACKEND_DIR"

# Проверяем текущие версии
TWISTED_VERSION=$("$VENV_DIR/bin/pip" show Twisted 2>/dev/null | grep "Version:" | cut -d' ' -f2)
PYOPENSSL_VERSION=$("$VENV_DIR/bin/pip" show pyOpenSSL 2>/dev/null | grep "Version:" | cut -d' ' -f2)

echo "  Текущие версии:"
echo "    Twisted: $TWISTED_VERSION"
echo "    pyOpenSSL: $PYOPENSSL_VERSION"

# Исправляем если версии проблемные
if [[ "$TWISTED_VERSION" == "25."* ]] || [[ "$PYOPENSSL_VERSION" == "25."* ]]; then
    echo -e "${YELLOW}⚠️  Обнаружены проблемные версии. Исправляем...${NC}"
    "$VENV_DIR/bin/pip" install --upgrade --force-reinstall \
        'Twisted==24.10.0' \
        'pyOpenSSL==24.2.1' \
        'cryptography==43.0.3' \
        --quiet
    echo -e "${GREEN}✅ Версии исправлены${NC}"
else
    echo -e "${GREEN}✅ Версии совместимы${NC}"
fi

# Устанавливаем остальные зависимости
echo -e "${BLUE}📦 Установка зависимостей бекенда...${NC}"
"$VENV_DIR/bin/pip" install -r requirements.txt --quiet

# Проверяем доступность конфигурации БД через Django
echo -e "${BLUE}🧪 Проверка параметров БД...${NC}"
"$VENV_DIR/bin/python" - <<'PY'
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
os.environ.setdefault('ENVIRONMENT', 'development')  # Принудительно development
try:
    import django
    django.setup()
    from django.conf import settings
    db = settings.DATABASES['default']

    # SQLite требует только ENGINE и NAME
    if 'sqlite' in db.get('ENGINE', '').lower():
        required = ['ENGINE', 'NAME']
        db_type = 'SQLite'
        db_info = db['NAME']
    else:
        # PostgreSQL/MySQL требуют все параметры
        required = ['ENGINE','NAME','USER','HOST']
        db_type = 'PostgreSQL'
        db_info = f"{db.get('HOST')}:{db.get('PORT','')} / {db['NAME']}"

    missing = [k for k in required if not db.get(k)]
    if missing:
        print(f"❌ Недостаточно параметров БД: {missing}")
        sys.exit(2)
    print(f"✅ БД ({db_type}): {db_info}")
except Exception as e:
    print("❌ Ошибка конфигурации БД:", e)
    sys.exit(2)
PY
if [ $? -ne 0 ]; then
    echo -e "${RED}   Проверьте .env и убедитесь что ENVIRONMENT=development${NC}"
    exit 1
fi

# Применяем миграции
echo -e "${BLUE}🗄️  Применение миграций Django...${NC}"
"$VENV_DIR/bin/python" manage.py migrate --verbosity 0

# Создаем суперпользователя (если не существует)
echo -e "${BLUE}👤 Проверка суперпользователя...${NC}"
"$VENV_DIR/bin/python" manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser(
        username='admin@example.com',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User',
        role='teacher'
    )
    print('✅ Суперпользователь создан: admin@example.com / admin123')
else:
    print('✅ Суперпользователь уже существует')
" 2>/dev/null

# Запускаем Django ASGI сервер (Daphne) для WebSocket поддержки
echo -e "${BLUE}🌐 Запуск Django ASGI сервера (Daphne) на порту 8000...${NC}"
"$VENV_DIR/bin/daphne" -b 0.0.0.0 -p 8000 config.asgi:application &
DJANGO_PID=$!

# Ждем немного, чтобы Django запустился
sleep 3

# Проверяем Redis и запускаем Celery
echo -e "${BLUE}🔍 Проверка Redis для Celery...${NC}"
if redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis доступен${NC}"

    # Убиваем старые процессы Celery
    pkill -f "celery worker" 2>/dev/null || true
    pkill -f "celery beat" 2>/dev/null || true
    sleep 1

    # Запускаем Celery worker
    echo -e "${BLUE}🔧 Запуск Celery worker...${NC}"
    "$VENV_DIR/bin/celery" -A core worker --loglevel=error --concurrency=2 --logfile=/tmp/celery_worker.log &
    CELERY_WORKER_PID=$!

    # Запускаем Celery beat
    echo -e "${BLUE}⏰ Запуск Celery beat (рекуррентные задачи)...${NC}"
    "$VENV_DIR/bin/celery" -A core beat --loglevel=error --logfile=/tmp/celery_beat.log &
    CELERY_BEAT_PID=$!

    echo -e "${GREEN}✅ Celery запущен (worker: $CELERY_WORKER_PID, beat: $CELERY_BEAT_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  Redis недоступен, Celery не запущен${NC}"
    echo "   Рекуррентные платежи работать не будут"
    echo "   Для запуска Redis: sudo systemctl start redis"
    CELERY_WORKER_PID=""
    CELERY_BEAT_PID=""
fi

# Возвращаемся в корневую директорию
cd "$PROJECT_ROOT"

# Устанавливаем зависимости фронтенда
echo -e "${BLUE}📦 Установка зависимостей фронтенда...${NC}"
cd "$FRONTEND_DIR"

# Проверяем наличие node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Установка npm пакетов...${NC}"
    npm install --silent
else
    echo -e "${GREEN}✅ npm пакеты уже установлены${NC}"
fi

# Запускаем фронтенд сервер
echo -e "${BLUE}🎨 Запуск фронтенд сервера на порту 8080...${NC}"
npm run dev -- --port 8080 &
FRONTEND_PID=$!

# Возвращаемся в корневую директорию
cd "$PROJECT_ROOT"

echo ""
echo -e "${GREEN}======================================================================"
echo -e "✅ Серверы запущены успешно!"
echo -e "======================================================================${NC}"
echo -e "🌐 Django Backend: ${BLUE}http://localhost:8000${NC}"
echo -e "🎨 React Frontend: ${BLUE}http://localhost:8080${NC}"
echo -e "👤 Админ панель: ${BLUE}http://localhost:8000/admin${NC}"
echo -e "📊 API endpoints: ${BLUE}http://localhost:8000/api/${NC}"
if [ ! -z "$CELERY_WORKER_PID" ]; then
    echo -e "⏰ Celery: ${GREEN}Рекуррентные задачи активны${NC} (платежи каждые 5 мин)"
    echo -e "   Логи: tail -f /tmp/celery_worker.log"
fi
echo -e "${GREEN}======================================================================${NC}"
echo ""
echo -e "${YELLOW}🔧 Для остановки серверов нажмите Ctrl+C${NC}"
echo ""

# Функция для корректного завершения
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Остановка серверов...${NC}"

    # Останавливаем процессы
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID 2>/dev/null
        echo -e "   ${GREEN}Django сервер остановлен${NC}"
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "   ${GREEN}Frontend сервер остановлен${NC}"
    fi

    # Останавливаем Celery
    if [ ! -z "$CELERY_WORKER_PID" ]; then
        kill $CELERY_WORKER_PID 2>/dev/null
        echo -e "   ${GREEN}Celery worker остановлен${NC}"
    fi

    if [ ! -z "$CELERY_BEAT_PID" ]; then
        kill $CELERY_BEAT_PID 2>/dev/null
        echo -e "   ${GREEN}Celery beat остановлен${NC}"
    fi

    # Убиваем оставшиеся процессы Celery
    pkill -f "celery worker" 2>/dev/null || true
    pkill -f "celery beat" 2>/dev/null || true

    # Дополнительно убиваем процессы на портах
    kill_port_processes 8000 "Django Backend"
    kill_port_processes 8080 "React Frontend"

    echo -e "${GREEN}✅ Все серверы остановлены${NC}"
    exit 0
}

# Перехватываем сигнал завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения
wait