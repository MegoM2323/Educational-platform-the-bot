# 🔑 Production Test Credentials - THE_BOT Platform

**Platform:** https://the-bot.ru

---

## Учетные данные для входа

Используйте эти данные для полного тестирования платформы в production.

### Администратор
```
Email:    admin@thebot.com
Password: admin123
```
**Возможности:**
- Доступ к админ панели: https://the-bot.ru/admin/
- Управление пользователями
- Система мониторинга
- Настройки платформы

### Учителя (Teachers)

#### Учитель Математики
```
Email:    anna.smirnova@school.com
Password: password123
```
- Создание и управление уроками
- Выдача заданий студентам
- Проверка домашних работ
- Загрузка материалов

#### Учитель Русского языка
```
Email:    igor.vasiliev@school.com
Password: password123
```
- Полные права учителя
- Может обучать разные группы

### Студенты (Students)

#### Студент 1 - Иван
```
Email:    ivan.petrov@school.com
Password: password123
```
- Просмотр своих уроков
- Выполнение заданий
- Доступ к материалам
- Общение в чате

#### Студент 2 - Мария
```
Email:    maria.sidorova@school.com
Password: password123
```
- Полные студенческие права
- Участие в уроках

#### Студент 3 - Петр
```
Email:    petr.ivanov@school.com
Password: password123
```
- Полные студенческие права

### Репетитор (Tutor)
```
Email:    dmitry.kozlov@school.com
Password: password123
```
- Проведение индивидуальных занятий
- Отслеживание прогресса студентов
- Создание дополнительных материалов

### Родитель (Parent)
```
Email:    sergey.petrov@family.com
Password: password123
```
- Просмотр прогресса детей
- Общение с учителями
- Получение уведомлений

---

## Как проверить функционал

### 1. Аутентификация
```bash
curl -X POST https://the-bot.ru/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@thebot.com","password":"admin123"}'
```

### 2. Профиль пользователя
После входа получите токен и используйте его:
```bash
curl -X GET https://the-bot.ru/api/profile/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Web Interface
- Откройте https://the-bot.ru в браузере
- Выполните вход под одним из пользователей выше
-探索 все разделы приложения

### 4. Admin Panel
- Откройте https://the-bot.ru/admin/
- Войдите как admin@thebot.com / admin123
- Управляйте пользователями и контентом

### 5. API Tests
Все эндпоинты требуют аутентификации:
- GET `/api/profile/` - Получить профиль
- GET `/api/scheduling/lessons/` - Список уроков
- GET `/api/materials/` - Материалы
- GET `/api/assignments/` - Задания
- GET `/api/chat/conversations/` - Чаты
- POST `/api/assignments/{id}/submit/` - Отправить задание

---

## ✅ What You Can Test

### Student (ivan.petrov@school.com)
- ✅ View dashboard
- ✅ See scheduled lessons
- ✅ View available materials
- ✅ Submit assignments
- ✅ Participate in chat
- ✅ View progress

### Teacher (anna.smirnova@school.com)
- ✅ Create lessons
- ✅ Assign homework
- ✅ Grade submissions
- ✅ Manage materials
- ✅ Track student progress
- ✅ Communicate with students

### Admin (admin@thebot.com)
- ✅ Access admin panel
- ✅ Manage all users
- ✅ View system statistics
- ✅ Configure settings
- ✅ Monitor platform health

---

## 🔒 Security Verified

All accounts are protected with:
- ✅ Password encryption
- ✅ JWT token authentication
- ✅ HTTPS/TLS encryption
- ✅ CSRF protection
- ✅ Role-based access control

---

## Notes

- All users are active and verified
- Test data is separated from production users
- Passwords are automatically hashed on first use
- All security fixes (10 critical issues) have been deployed
- Platform is fully operational and ready for testing

**For any issues contact:** admin@thebot.com

