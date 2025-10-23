#!/bin/bash

# Скрипт для запуска проекта с поддержкой Telegram интеграции

echo "🚀 Запуск THE BOT Platform с Telegram интеграцией"
echo "=================================================="

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env в корне проекта с настройками:"
    echo ""
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    echo "TELEGRAM_CHAT_ID=your_channel_id_here"
    echo "SECRET_KEY=your_secret_key_here"
    echo ""
    exit 1
fi

# Активируем виртуальное окружение
echo "📦 Активация виртуального окружения..."
source venv/bin/activate

# Переходим в папку backend
cd backend

# Применяем миграции
echo "🗄️  Применение миграций..."
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

# Тестируем Telegram интеграцию
echo "🤖 Тестирование Telegram интеграции..."
python manage.py test_telegram --test-message --test-application

# Запускаем Django сервер
echo "🌐 Запуск Django сервера..."
echo "Админка: http://localhost:8000/admin/"
echo "API: http://localhost:8000/api/"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

python manage.py runserver
