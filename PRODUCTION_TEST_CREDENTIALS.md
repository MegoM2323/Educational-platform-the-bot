# 🔑 Production Test Credentials - THE_BOT Platform

**Platform:** https://the-bot.ru

---

## Учетные данные для входа

**Все пароли:** `password123`

Используйте эти данные для полного тестирования платформы в production.

### 🔐 Администратор
```
Email:    admin@tutoring.com
Password: password123
Имя:      Администратор Системы
```
**Возможности:**
- Доступ к админ панели: https://the-bot.ru/admin/
- Управление пользователями
- Система мониторинга
- Настройки платформы

### 👨‍🏫 Преподаватели (Teachers)

#### Преподаватель 1 - Иван Петров
```
Email:    ivan.petrov@tutoring.com
Password: password123
```
- Создание и управление уроками
- Выдача заданий студентам
- Проверка домашних работ
- Загрузка материалов

#### Преподаватель 2 - Мария Сидорова
```
Email:    maria.sidorova@tutoring.com
Password: password123
```
- Полные права преподавателя
- Может обучать разные группы
- Управление расписанием

#### Преподаватель 3 - Алексей Козлов
```
Email:    alexey.kozlov@tutoring.com
Password: password123
```
- Полные права преподавателя
- Опытный наставник

### 👨‍🎓 Студенты (Students)

#### Студент 1 - Анна Иванова (10 кредитов)
```
Email:    anna.ivanova@student.com
Password: password123
```
- Просмотр своих уроков
- Выполнение заданий
- Доступ к материалам
- Общение в чате

#### Студент 2 - Дмитрий Смирнов (8 кредитов)
```
Email:    dmitry.smirnov@student.com
Password: password123
```
- Полные студенческие права
- Участие в уроках

#### Студент 3 - Елена Волкова (12 кредитов)
```
Email:    elena.volkova@student.com
Password: password123
```
- Полные студенческие права
- Прилежная студентка

#### Студент 4 - Павел Морозов (5 кредитов)
```
Email:    pavel.morozov@student.com
Password: password123
```
- Полные студенческие права
- Новый ученик

#### Студент 5 - Ольга Новикова (3 кредита)
```
Email:    olga.novikova@student.com
Password: password123
```
- Полные студенческие права
- Начинающий студент

---

## Как проверить функционал

### 1. Аутентификация
```bash
curl -X POST https://the-bot.ru/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tutoring.com","password":"password123"}'
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
- Изучите все разделы приложения

### 4. Admin Panel
- Откройте https://the-bot.ru/admin/
- Войдите как admin@tutoring.com / password123
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

### Student (anna.ivanova@student.com)
- ✅ View dashboard
- ✅ See scheduled lessons
- ✅ View available materials
- ✅ Submit assignments
- ✅ Participate in chat
- ✅ View progress
- ✅ Check credit balance (10 кредитов)

### Teacher (ivan.petrov@tutoring.com)
- ✅ Create lessons
- ✅ Assign homework
- ✅ Grade submissions
- ✅ Manage materials
- ✅ Track student progress
- ✅ Communicate with students
- ✅ View schedule

### Admin (admin@tutoring.com)
- ✅ Access admin panel
- ✅ Manage all users (1 admin, 3 teachers, 5 students)
- ✅ View system statistics
- ✅ Configure settings
- ✅ Monitor platform health
- ✅ View all bookings and transactions

---

## 🔒 Security Verified

All accounts are protected with:
- ✅ Password encryption
- ✅ JWT token authentication
- ✅ HTTPS/TLS encryption
- ✅ CSRF protection
- ✅ Role-based access control

---

## 📊 Test Data Statistics

- **1 Administrator** (admin@tutoring.com)
- **3 Teachers** with full access to lessons and materials
- **5 Students** with different credit balances (3-12 credits)
- **107 lessons** (past and future, with and without homework)
- **Booking history** and transaction records
- **7 schedule templates** for tutoring sessions
- **Chat system** and message broadcasting

## Notes

- All users are active and verified
- Test data includes realistic tutoring scenarios
- Passwords are automatically hashed
- All security fixes (10 critical issues) have been deployed
- Platform is fully operational and ready for testing
- Students have different credit balances to test various scenarios
- Teachers can manage multiple student groups

**For any issues contact:** admin@tutoring.com

