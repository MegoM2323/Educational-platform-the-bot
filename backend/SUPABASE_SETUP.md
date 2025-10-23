# Настройка Supabase для Django Backend

## Переменные окружения

Создайте файл `.env` в папке `backend/` со следующими переменными:

```env
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Supabase settings
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# YooKassa settings (если используется)
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
YOOKASSA_WEBHOOK_URL=https://your-domain.com/webhook/

# Telegram Bot settings (если используется)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## Получение ключей Supabase

1. Перейдите в [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите ваш проект
3. Перейдите в Settings > API
4. Скопируйте:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_KEY`
   - **service_role** → `SUPABASE_SERVICE_ROLE_KEY`

## Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

## API Endpoints

### Регистрация
```
POST /api/accounts/supabase/register/
```

**Тело запроса:**
```json
{
    "email": "user@example.com",
    "password": "password123",
    "password_confirm": "password123",
    "first_name": "Иван",
    "last_name": "Иванов",
    "phone": "+7900123456",
    "role": "student"
}
```

### Вход
```
POST /api/accounts/supabase/login/
```

**Тело запроса:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

### Получение профиля
```
GET /api/accounts/supabase/profile/
Authorization: Bearer <access_token>
```

### Обновление профиля
```
PUT /api/accounts/supabase/profile/update/
Authorization: Bearer <access_token>
```

**Тело запроса:**
```json
{
    "full_name": "Иван Иванов",
    "phone": "+7900123456",
    "avatar_url": "https://example.com/avatar.jpg"
}
```

### Выход
```
POST /api/accounts/supabase/logout/
```

## Роли пользователей

- `student` - Студент
- `teacher` - Преподаватель
- `tutor` - Тьютор
- `parent` - Родитель

## Безопасность

- Все API endpoints защищены CORS настройками
- Используется JWT токены для аутентификации
- Row Level Security (RLS) настроен в Supabase
- Service Role Key используется только для административных операций
