# Конфигурация переменных окружения

## 📁 Структура конфигурации

Теперь у вас **один глобальный `.env` файл** в корне проекта, который содержит все настройки для Django backend и React frontend.

### Расположение файлов:
```
THE_BOT_platform/
├── .env                    # 🎯 ГЛАВНЫЙ файл конфигурации
├── .env.backup            # Резервная копия
├── env.example            # Пример конфигурации
├── backend/               # Django backend
└── frontend/              # React frontend
```

## 🔧 Содержимое .env файла

### Django Backend настройки:
```env
# Django Settings
DEBUG=False
SECRET_KEY=django-insecure-production-key
ALLOWED_HOSTS=['127.0.0.1', 'localhost', '5.129.249.206']

# YooKassa Settings
YOOKASSA_SHOP_ID=1168002
YOOKASSA_SECRET_KEY=live_JvKNgChsKuteOF8PPlBy5W4G_yH5mKejs8U-4PN67L0
YOOKASSA_WEBHOOK_URL=https://the-bot.ru/yookassa-webhook

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN=7592367580:AAHBQSZBxfr0LAZPbr30pJqPAMZI7fMQQAo
TELEGRAM_CHAT_ID=-1003138593404

# Supabase Settings
SUPABASE_URL=https://sobptsqfzgycmauglqzk.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Frontend настройки:
```env
# Frontend Settings
VITE_DJANGO_API_URL=http://localhost:8000/api
```

## 🚀 Как это работает

### 1. Django Backend
- Читает переменные из `.env` файла в корне проекта
- Использует `python-dotenv` для загрузки переменных
- Настройки доступны через `os.getenv()`

### 2. React Frontend
- Vite настроен для чтения переменных из корневого `.env` файла
- Переменные с префиксом `VITE_` автоматически доступны в коде
- Конфигурация в `vite.config.ts` загружает переменные из `../.env`

## 📝 Преимущества новой структуры

✅ **Один файл конфигурации** - все настройки в одном месте  
✅ **Нет дублирования** - переменные не повторяются  
✅ **Легче поддерживать** - изменения в одном файле  
✅ **Безопасность** - все секреты в одном защищенном файле  
✅ **Простота развертывания** - один файл для копирования  

## 🔄 Миграция с старой структуры

Если у вас была старая структура с двумя `.env` файлами:

1. **Удален** `frontend/.env` файл
2. **Объединены** все переменные в корневой `.env`
3. **Обновлен** `vite.config.ts` для чтения из корневого файла
4. **Обновлен** `start_dev.sh` для проверки глобального файла

## 🛠️ Настройка для разработки

### 1. Скопируйте пример конфигурации:
```bash
cp env.example .env
```

### 2. Отредактируйте настройки:
```bash
nano .env
```

### 3. Запустите проект:
```bash
./start_dev.sh
```

## 🔒 Безопасность

- **НЕ коммитьте** `.env` файл в Git
- **Используйте** `.env.example` для документации
- **Создавайте** отдельные `.env` файлы для разных окружений
- **Регулярно ротируйте** секретные ключи

## 📋 Переменные окружения

### Обязательные для работы:
- `SECRET_KEY` - секретный ключ Django
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `TELEGRAM_CHAT_ID` - ID канала Telegram
- `VITE_DJANGO_API_URL` - URL Django API для фронтенда

### Опциональные:
- `DEBUG` - режим отладки Django
- `ALLOWED_HOSTS` - разрешенные хосты
- `SUPABASE_*` - настройки Supabase
- `YOOKASSA_*` - настройки YooKassa

## 🎯 Результат

Теперь у вас **единая точка конфигурации** для всего проекта! 🎉
