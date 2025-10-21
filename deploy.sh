#!/bin/bash

# Единый скрипт деплоя Django проекта
# Использование: ./deploy.sh

SERVER="mg@5.129.249.206"
PROJECT_PATH="/home/mg/THE_BOT_platform"

echo "🚀 Деплой Django проекта на сервер через пользователя mg"

# 1. Создать архив проекта
echo "📦 Создаем архив проекта..."
tar -czf project.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='db.sqlite3' \
    --exclude='server.log' \
    --exclude='.env' \
    .

# 2. Загрузить архив на сервер
echo "📤 Загружаем архив на сервер..."
scp project.tar.gz $SERVER:~/

# 3. Выполнить команды на сервере
echo "🔧 Настраиваем сервер..."
ssh $SERVER << 'EOF'
    set -e
    
    echo "📥 Распаковываем проект..."
    # Создать директорию проекта
    mkdir -p /home/mg/THE_BOT_platform
    cd /home/mg/THE_BOT_platform
    
    # Распаковать архив
    tar -xzf ~/project.tar.gz -C .
    rm ~/project.tar.gz
    
    echo "🐍 Настраиваем Python окружение..."
    # Создать виртуальное окружение
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Установить зависимости
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "⚙️ Настраиваем Django..."
    # Создать .env файл
    cat > .env << EOL
DEBUG=False
SECRET_KEY=django-insecure-production-key-change-me
ALLOWED_HOSTS=*
YOOMONEY_RECEIVER=your-receiver-id
YOOMONEY_SECRET=your-secret-key
EOL
    
    echo "🗄️ Настраиваем базу данных..."
    # Создать SQLite базу (проще для деплоя)
    python manage.py migrate
    
    echo "🛑 Останавливаем старые процессы..."
    pkill -f "manage.py runserver" 2>/dev/null || true
    
    echo "🚀 Запускаем сервер..."
    nohup python manage.py runserver 0.0.0.0:8000 > server.log 2>&1 &
    
    # Подождать и проверить
    sleep 3
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo "✅ Сервер успешно запущен!"
        echo "🌐 Доступен по адресу: http://5.129.249.206:8000"
        echo "📊 Логи: tail -f /home/mg/THE_BOT_platform/server.log"
    else
        echo "❌ Ошибка запуска сервера. Проверьте логи:"
        tail -20 server.log
    fi
EOF

# 4. Удалить локальный архив
rm project.tar.gz

echo "🎉 Деплой завершен!"
echo ""
echo "📋 Полезные команды:"
echo "  ssh $SERVER 'cd $PROJECT_PATH && tail -f server.log'  # Логи"
echo "  ssh $SERVER 'cd $PROJECT_PATH && pkill -f manage.py'  # Остановить"
echo "  ssh $SERVER 'cd $PROJECT_PATH && nohup python manage.py runserver 0.0.0.0:8000 > server.log 2>&1 &'  # Запустить"
echo ""
echo "🌐 Откройте в браузере: http://5.129.249.206:8000"
