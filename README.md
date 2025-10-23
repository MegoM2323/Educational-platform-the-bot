# THE_BOT_platform

Полнофункциональная платформама для образовательного бота с разделением на backend (Django) и frontend (React).

## Структура проекта

```
THE_BOT_platform/
├── backend/          # Django backend
│   ├── accounts/     # Приложение для управления пользователями
│   ├── payments/     # Приложение для обработки платежей
│   ├── config/       # Настройки Django
│   └── manage.py     # Django management script
├── frontend/         # React frontend
│   ├── src/          # Исходный код React
│   ├── public/       # Статические файлы
│   └── package.json  # Зависимости Node.js
└── venv/            # Python виртуальное окружение
```

## Технологии

### Backend
- **Django 5.2.7** - веб-фреймворк
- **Django REST Framework** - API
- **Django Allauth** - аутентификация
- **PostgreSQL/MySQL** - база данных
- **Celery** - фоновые задачи
- **Redis** - кэширование

### Frontend
- **React 18** - UI библиотека
- **TypeScript** - типизация
- **Vite** - сборщик
- **shadcn/ui** - UI компоненты
- **Tailwind CSS** - стилизация
- **React Router** - маршрутизация
- **TanStack Query** - управление состоянием

## Установка и запуск

### Backend (Django)

```bash
# Активация виртуального окружения
source venv/bin/activate

# Переход в папку backend
cd backend

# Установка зависимостей
pip install -r requirements.txt

# Применение миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Запуск сервера разработки
python manage.py runserver
```

### Frontend (React)

```bash
# Переход в папку frontend
cd frontend

# Установка зависимостей
npm install

# Запуск сервера разработки
npm run dev
```

## API Endpoints

Backend предоставляет REST API для frontend:

- `/api/auth/` - аутентификация
- `/api/payments/` - обработка платежей
- `/api/users/` - управление пользователями

## Разработка

1. Backend запускается на `http://localhost:8000`
2. Frontend запускается на `http://localhost:5173`
3. API доступно по адресу `http://localhost:8000/api/`

## Развертывание

Используйте `backend/deploy.sh` для развертывания на продакшене.

