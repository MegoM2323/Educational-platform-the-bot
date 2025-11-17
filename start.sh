#!/bin/bash

# Единый скрипт для запуска THE BOT Platform
# Автоматически убивает процессы на портах 8000 и 8080 перед запуском

echo "🚀 Запуск THE BOT Platform"
echo "=================================================="

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
    
    echo "🔍 Проверка порта $port ($service_name)..."
    
    # Находим процессы на порту
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        echo "⚠️  На порту $port найдены процессы: $pids"
        echo "🛑 Убиваем процессы на порту $port..."
        
        # Убиваем процессы
        for pid in $pids; do
            echo "   Убиваем процесс $pid..."
            kill -9 $pid 2>/dev/null
        done
        
        # Ждем немного
        sleep 2
        
        # Проверяем, что процессы убиты
        local remaining_pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo "❌ Не удалось убить все процессы на порту $port"
            echo "   Оставшиеся процессы: $remaining_pids"
        else
            echo "✅ Порт $port освобожден"
        fi
    else
        echo "✅ Порт $port свободен"
    fi
}

# Убиваем процессы на портах 8000 и 8080
kill_port_processes 8000 "Django Backend"
kill_port_processes 8080 "React Frontend"

# Проверяем, что мы в правильной директории
if [ ! -f "$BACKEND_DIR/manage.py" ]; then
    echo "❌ Ошибка: Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаем..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Активируем виртуальное окружение Python
echo "📦 Активация виртуального окружения Python..."
source "$VENV_DIR/bin/activate"

# Устанавливаем зависимости бекенда
echo "📦 Установка зависимостей бекенда..."
cd "$BACKEND_DIR"
"$VENV_DIR/bin/pip" install -r requirements.txt

# Проверяем доступность конфигурации БД через Django (независимо от shell env)
echo "🧪 Проверка параметров БД..."
"$VENV_DIR/bin/python" - <<'PY'
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
try:
    import django
    django.setup()
    from django.conf import settings
    db = settings.DATABASES['default']
    required = ['ENGINE','NAME','USER','HOST']
    missing = [k for k in required if not db.get(k)]
    if missing:
        print(f"❌ Недостаточно параметров БД: {missing}")
        sys.exit(2)
    print(f"✅ БД: {db['HOST']}:{db.get('PORT','')} / {db['NAME']}")
except Exception as e:
    print("❌ Ошибка конфигурации БД:", e)
    sys.exit(2)
PY
if [ $? -ne 0 ]; then
    echo "   Проверьте .env: DATABASE_URL или SUPABASE_DB_* и формат строк (без комментариев на той же строке)."
    exit 1
fi

# Применяем миграции
echo "🗄️  Применение миграций Django..."
"$VENV_DIR/bin/python" manage.py migrate

# Создаем суперпользователя (если не существует)
echo "👤 Проверка суперпользователя..."
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
"

# Проверяем настройки Telegram (если есть .env файл)
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "🤖 Проверка настроек Telegram..."
    if grep -q "TELEGRAM_BOT_TOKEN" "$PROJECT_ROOT/.env"; then
        echo "✅ Настройки Telegram найдены"
        echo "🧪 Тестирование Telegram интеграции..."
        "$VENV_DIR/bin/python" manage.py test_telegram --test-message 2>/dev/null || echo "⚠️  Telegram тест не выполнен (возможно, не настроен)"
    else
        echo "⚠️  Настройки Telegram не найдены в .env файле"
    fi
else
    echo "⚠️  Файл .env не найден (Telegram интеграция пропущена)"
fi

# Запускаем Django сервер в фоне
echo "🌐 Запуск Django сервера на порту 8000..."
"$VENV_DIR/bin/python" manage.py runserver 8000 &
DJANGO_PID=$!

# Ждем немного, чтобы Django запустился
sleep 3

# Проверяем Redis и запускаем Celery
echo "🔍 Проверка Redis для Celery..."
if redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis доступен"
    
    # Убиваем старые процессы Celery
    pkill -f "celery worker" 2>/dev/null || true
    pkill -f "celery beat" 2>/dev/null || true
    sleep 1
    
    # Запускаем Celery worker
    echo "🔧 Запуск Celery worker..."
    "$VENV_DIR/bin/celery" -A core worker --loglevel=info --concurrency=2 --logfile=/tmp/celery_worker.log &
    CELERY_WORKER_PID=$!
    
    # Запускаем Celery beat
    echo "⏰ Запуск Celery beat (рекуррентные задачи)..."
    "$VENV_DIR/bin/celery" -A core beat --loglevel=info --logfile=/tmp/celery_beat.log &
    CELERY_BEAT_PID=$!
    
    echo "✅ Celery запущен (worker: $CELERY_WORKER_PID, beat: $CELERY_BEAT_PID)"
else
    echo "⚠️  Redis недоступен, Celery не запущен"
    echo "   Рекуррентные платежи работать не будут"
    echo "   Для запуска Redis: sudo systemctl start redis"
    CELERY_WORKER_PID=""
    CELERY_BEAT_PID=""
fi

# Возвращаемся в корневую директорию
cd "$PROJECT_ROOT"

# Устанавливаем зависимости фронтенда
echo "📦 Установка зависимостей фронтенда..."
cd "$FRONTEND_DIR"

# Проверяем наличие node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Установка npm пакетов..."
    npm install
else
    echo "✅ npm пакеты уже установлены"
fi

# Запускаем фронтенд сервер
echo "🎨 Запуск фронтенд сервера на порту 8080..."
npm run dev -- --port 8080 &
FRONTEND_PID=$!

# Возвращаемся в корневую директорию
cd "$PROJECT_ROOT"

echo ""
echo "✅ Серверы запущены!"
echo "🌐 Django Backend: http://localhost:8000"
echo "🎨 React Frontend: http://localhost:8080"
echo "👤 Админ панель: http://localhost:8000/admin"
echo "📊 API endpoints: http://localhost:8000/api/"
if [ ! -z "$CELERY_WORKER_PID" ]; then
    echo "⏰ Celery: Рекуррентные задачи активны (платежи каждые 5 мин)"
    echo "   Логи: tail -f /tmp/celery_worker.log"
fi
echo ""
echo "🔧 Для остановки серверов нажмите Ctrl+C"
echo ""

# Функция для корректного завершения
cleanup() {
    echo ""
    echo "🛑 Остановка серверов..."
    
    # Останавливаем процессы
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID 2>/dev/null
        echo "   Django сервер остановлен"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "   Frontend сервер остановлен"
    fi
    
    # Останавливаем Celery
    if [ ! -z "$CELERY_WORKER_PID" ]; then
        kill $CELERY_WORKER_PID 2>/dev/null
        echo "   Celery worker остановлен"
    fi
    
    if [ ! -z "$CELERY_BEAT_PID" ]; then
        kill $CELERY_BEAT_PID 2>/dev/null
        echo "   Celery beat остановлен"
    fi
    
    # Убиваем оставшиеся процессы Celery
    pkill -f "celery worker" 2>/dev/null || true
    pkill -f "celery beat" 2>/dev/null || true
    
    # Дополнительно убиваем процессы на портах
    kill_port_processes 8000 "Django Backend"
    kill_port_processes 8080 "React Frontend"
    
    echo "✅ Все серверы остановлены"
    exit 0
}

# Перехватываем сигнал завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения
wait
