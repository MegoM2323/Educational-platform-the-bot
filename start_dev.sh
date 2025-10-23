#!/bin/bash

# Скрипт для запуска development окружения
# Запускает Django backend и React frontend одновременно

echo "🚀 Запуск THE_BOT_platform development окружения..."

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаем..."
    python -m venv venv
fi

# Активируем виртуальное окружение
echo "📦 Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем зависимости для backend
echo "🔧 Установка зависимостей backend..."
cd backend
pip install -r requirements.txt

# Применяем миграции
echo "🗄️ Применение миграций..."
python manage.py migrate

# Создаем суперпользователя если его нет
echo "👤 Проверка суперпользователя..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Создание суперпользователя...')
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Суперпользователь создан: admin/admin123')
else:
    print('Суперпользователь уже существует')
"

# Проверяем настройки Telegram
echo "🤖 Проверка настроек Telegram..."
if [ -f "../.env" ] && grep -q "TELEGRAM_BOT_TOKEN" ../.env; then
    echo "✅ Настройки Telegram найдены"
    echo "🧪 Тестирование Telegram интеграции..."
    python manage.py test_telegram --test-message
else
    echo "⚠️  Настройки Telegram не найдены"
    echo "Создайте файл .env в корне проекта с настройками:"
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    echo "TELEGRAM_CHAT_ID=your_channel_id_here"
fi

# Возвращаемся в корень проекта
cd ..

# Проверяем наличие node_modules для frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Установка зависимостей frontend..."
    cd frontend
    npm install
    cd ..
fi

# Проверяем наличие глобального .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Глобальный .env файл не найден!"
    echo "Создайте файл .env в корне проекта с настройками:"
    echo "VITE_DJANGO_API_URL=http://localhost:8000/api"
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    echo "TELEGRAM_CHAT_ID=your_channel_id_here"
    echo "SECRET_KEY=your-secret-key-here"
    exit 1
fi

echo "✅ Глобальный .env файл найден"

echo "🎯 Запуск серверов..."

# Запускаем Django backend в фоне
echo "🐍 Запуск Django backend на http://localhost:8000"
cd backend
python manage.py runserver &
DJANGO_PID=$!

# Возвращаемся в корень и запускаем React frontend
cd ../frontend
echo "⚛️ Запуск React frontend на http://localhost:5173"
npm run dev &
REACT_PID=$!

# Функция для корректного завершения процессов
cleanup() {
    echo "🛑 Остановка серверов..."
    kill $DJANGO_PID $REACT_PID 2>/dev/null
    exit 0
}

# Перехватываем сигналы для корректного завершения
trap cleanup SIGINT SIGTERM

echo "✅ Серверы запущены!"
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000/api"
echo "📊 Django Admin: http://localhost:8000/admin"
echo ""
echo "Нажмите Ctrl+C для остановки серверов"

# Ждем завершения процессов
wait

