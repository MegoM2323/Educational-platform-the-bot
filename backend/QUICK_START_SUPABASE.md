# Быстрый старт с Supabase

## 1. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

## 2. Настройка переменных окружения

Создайте файл `.env` в папке `backend/`:

```env
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Supabase settings
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

### Получение ключей Supabase:

1. Перейдите в [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите ваш проект
3. Перейдите в Settings > API
4. Скопируйте:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_KEY`
   - **service_role** → `SUPABASE_SERVICE_ROLE_KEY`

## 3. Запуск сервера

```bash
python manage.py runserver
```

## 4. Тестирование

### Тест подключения к Supabase:

```bash
python test_supabase_registration.py
```

### Тест API endpoints:

```bash
python test_api.py
```

### Синхронизация пользователей:

```bash
# Тест подключения
python manage.py sync_supabase --action test-connection

# Синхронизация всех пользователей
python manage.py sync_supabase --action sync-all

# Синхронизация конкретного пользователя
python manage.py sync_supabase --action sync-user --user-id <user-id>
```

## 5. API Endpoints

### Регистрация
```bash
curl -X POST http://localhost:8000/api/accounts/supabase/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "password_confirm": "password123",
    "first_name": "Иван",
    "last_name": "Иванов",
    "phone": "+7900123456",
    "role": "student"
  }'
```

### Вход
```bash
curl -X POST http://localhost:8000/api/accounts/supabase/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Получение профиля
```bash
curl -X GET http://localhost:8000/api/accounts/supabase/profile/ \
  -H "Authorization: Bearer <access_token>"
```

### Обновление профиля
```bash
curl -X PUT http://localhost:8000/api/accounts/supabase/profile/update/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Новое Имя",
    "phone": "+7900999999"
  }'
```

## 6. Структура проекта

```
backend/
├── accounts/
│   ├── supabase_service.py      # Основной сервис Supabase
│   ├── supabase_sync.py         # Синхронизация данных
│   ├── serializers.py           # Сериализаторы для API
│   ├── views.py                 # API представления
│   └── management/
│       └── commands/
│           └── sync_supabase.py # Команда синхронизации
├── test_supabase_registration.py # Тест подключения
├── test_api.py                  # Тест API endpoints
└── SUPABASE_SETUP.md            # Подробная документация
```

## 7. Роли пользователей

- `student` - Студент
- `teacher` - Преподаватель  
- `tutor` - Тьютор
- `parent` - Родитель

## 8. Безопасность

- Все API endpoints защищены CORS настройками
- Используется JWT токены для аутентификации
- Row Level Security (RLS) настроен в Supabase
- Service Role Key используется только для административных операций

## 9. Устранение неполадок

### Ошибка "SUPABASE_URL не установлен"
- Проверьте файл `.env` в папке `backend/`
- Убедитесь, что переменные SUPABASE_URL и SUPABASE_KEY установлены

### Ошибка подключения к Supabase
- Проверьте правильность URL и ключей
- Убедитесь, что проект Supabase активен

### Ошибка регистрации
- Проверьте настройки RLS в Supabase
- Убедитесь, что триггеры для создания профилей настроены

## 10. Следующие шаги

1. Настройте фронтенд для работы с новыми API endpoints
2. Добавьте обработку ошибок в UI
3. Настройте уведомления о регистрации
4. Добавьте валидацию данных на фронтенде
