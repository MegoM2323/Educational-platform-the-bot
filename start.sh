#!/bin/bash

# Единый скрипт для запуска THE BOT Platform
# Автоматически убивает процессы на портах 8000 и 5173 перед запуском

echo "🚀 Запуск THE BOT Platform"
echo "=================================================="

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

# Убиваем процессы на портах 8000 и 5173
kill_port_processes 8000 "Django Backend"
kill_port_processes 5173 "React Frontend"

# Проверяем, что мы в правильной директории
if [ ! -f "backend/manage.py" ]; then
    echo "❌ Ошибка: Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаем..."
    python -m venv venv
fi

# Активируем виртуальное окружение Python
echo "📦 Активация виртуального окружения Python..."
source venv/bin/activate

# Устанавливаем зависимости бекенда
echo "📦 Установка зависимостей бекенда..."
cd backend
pip install -r requirements.txt

# Применяем миграции
echo "🗄️  Применение миграций Django..."
python manage.py migrate

# Создаем суперпользователя (если не существует)
echo "👤 Проверка суперпользователя..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser(
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
if [ -f "../.env" ]; then
    echo "🤖 Проверка настроек Telegram..."
    if grep -q "TELEGRAM_BOT_TOKEN" ../.env; then
        echo "✅ Настройки Telegram найдены"
        echo "🧪 Тестирование Telegram интеграции..."
        python manage.py test_telegram --test-message 2>/dev/null || echo "⚠️  Telegram тест не выполнен (возможно, не настроен)"
    else
        echo "⚠️  Настройки Telegram не найдены в .env файле"
    fi
else
    echo "⚠️  Файл .env не найден (Telegram интеграция пропущена)"
fi

# Запускаем Django сервер в фоне
echo "🌐 Запуск Django сервера на порту 8000..."
python manage.py runserver 8000 &
DJANGO_PID=$!

# Ждем немного, чтобы Django запустился
sleep 3

# Возвращаемся в корневую директорию
cd ..

# Устанавливаем зависимости фронтенда
echo "📦 Установка зависимостей фронтенда..."
cd frontend

# Проверяем наличие node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Установка npm пакетов..."
    npm install
else
    echo "✅ npm пакеты уже установлены"
fi

# Запускаем фронтенд сервер
echo "🎨 Запуск фронтенд сервера на порту 5173..."
npm run dev &
FRONTEND_PID=$!

# Возвращаемся в корневую директорию
cd ..

echo ""
echo "✅ Серверы запущены!"
echo "🌐 Django Backend: http://localhost:8000"
echo "🎨 React Frontend: http://localhost:8083 (или другой порт, если 5173 занят)"
echo "👤 Админ панель: http://localhost:8000/admin"
echo "📊 API endpoints: http://localhost:8000/api/"
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
    
    # Дополнительно убиваем процессы на портах
    kill_port_processes 8000 "Django Backend"
    kill_port_processes 5173 "React Frontend"
    
    echo "✅ Все серверы остановлены"
    exit 0
}

# Перехватываем сигнал завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения
wait
