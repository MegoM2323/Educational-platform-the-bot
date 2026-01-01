# ЧЕКЛИСТ ПРОБЛЕМ ПЛАТФОРМЫ THE_BOT

## СТАТУС: 13 ПРОБЛЕМ ВЫЯВЛЕНО

---

## ИСПРАВЛЕННЫЕ ПРОБЛЕМЫ ✓

### [✓] Проблема #1: CheckConstraint Django 6.0

- **Статус:** FIXED
- **Файлы:**
  - `/backend/invoices/models.py` (lines 159-175)
  - `/backend/invoices/migrations/0001_initial.py` (lines 314-354)
- **Изменение:** `check=` → `condition=`
- **Количество изменений:** 8
- **Проверить:**
  ```bash
  docker exec thebot-backend python manage.py migrate invoices
  ```

---

### [✓] Проблема #2: Login Authentication Fallback

- **Статус:** FIXED
- **Файл:** `/backend/accounts/views.py` (lines 82-88)
- **Изменение:** Добавлен fallback на `user.check_password()`
- **Проверить:**
  ```bash
  # После логина пользователь должен получить token
  curl -X POST http://localhost:8000/api/auth/login/ -d '{"email":"user@test.com","password":"password"}'
  ```

---

### [✓] Проблема #3: Chat Migration Permission

- **Статус:** FIXED
- **Миграция:** `chat/migrations/0011_alter_chatroom_enrollment.py`
- **Действие:** Увеличены права доступа на папку migrations
- **Проверить:**
  ```bash
  docker exec thebot-backend python manage.py migrate chat
  ```

---

## ТРЕБУЮТ ИСПРАВЛЕНИЯ ❌

---

## КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### ❌ ISSUE #1: Admin Role Display Incorrect

**Приоритет:** CRITICAL (Блокирует админ-панель)
**Статус:** OPEN

**Описание:**
При логине суперпользователя возвращается роль "parent" вместо "admin".

**Файлы:**
- `/backend/accounts/models.py` - проверить User.Role и defaults
- `/backend/accounts/serializers.py` - UserSerializer роль mapping

**Шаги воспроизведения:**
```bash
# 1. Создать superuser
docker exec thebot-backend python manage.py createsuperuser

# 2. Залогиниться
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# 3. Проверить response - role должен быть "admin"
# Фактическое: role = "parent"
```

**Fix Checklist:**
- [ ] Проверить User model и роль по умолчанию
- [ ] Убедиться что `is_superuser=True` соответствует `role='admin'`
- [ ] Добавить logic в login_view для синхронизации:
```python
if authenticated_user.is_superuser and authenticated_user.role != 'admin':
    authenticated_user.role = 'admin'
    authenticated_user.save()
```
- [ ] Проверить UserSerializer для правильного маппинга role
- [ ] Тестировать: логин superuser → role=admin

---

### ❌ ISSUE #2: Frontend Container Unhealthy

**Приоритет:** CRITICAL
**Статус:** OPEN
**Контейнер:** tutoring-frontend

**Описание:**
```
tutoring-frontend     Up 3 hours (unhealthy)
```

**Диагностика:**
```bash
# Check logs
docker logs tutoring-frontend --tail 100

# Check health status
docker inspect tutoring-frontend | grep -A 15 "Health"

# Check running process
docker exec tutoring-frontend ps aux | grep node

# Check network
docker exec tutoring-frontend curl http://localhost:3000
```

**Вероятные причины:**
1. React приложение не запущено/упало
2. Health check endpoint недоступен
3. Зависимость npm не установлена
4. Порт конфликтует

**Fix Checklist:**
- [ ] Проверить логи: `docker logs tutoring-frontend`
- [ ] Проверить процесс: `docker exec tutoring-frontend ps`
- [ ] Проверить здоровье: `docker exec tutoring-frontend curl -f http://localhost:3000`
- [ ] Перезагрузить: `docker restart tutoring-frontend`
- [ ] Если не поможет - пересоздать: `docker-compose down && docker-compose up`
- [ ] Тестировать: контейнер должен быть (healthy)

---

## ВЫСОКИЕ ПРОБЛЕМЫ

### ❌ ISSUE #3: Missing Admin Schedule Endpoint

**Приоритет:** HIGH
**Статус:** OPEN
**Endpoint:** `GET /api/admin/schedule/`

**Ошибка:**
```
HTTP 404 Not Found
Page not found at /api/admin/schedule/
```

**Проверить:**
```bash
curl -X GET http://localhost:8000/api/admin/schedule/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN"
```

**Файлы для проверки:**
1. `/backend/scheduling/admin_urls.py` - содержит ли нужные views?
2. `/backend/config/urls.py` (line 16) - корректен ли path?
3. Соответствующие views - имеют ли @api_view и @permission_classes?

**Fix Checklist:**
- [ ] Проверить что admin_urls.py содержит schedule endpoints
- [ ] Убедиться что URL включена в config/urls.py
- [ ] Проверить что view декорирована с @api_view(['GET'])
- [ ] Добавить @permission_classes([IsStaffOrAdmin]) если отсутствует
- [ ] Тестировать endpoint с admin token
- [ ] Документировать expected response structure

---

### ❌ ISSUE #4: Missing Student Dashboard Endpoint

**Приоритет:** HIGH
**Статус:** OPEN
**Endpoint:** `GET /api/student/dashboard/`

**Ошибка:**
```
HTTP 404 Not Found
Page not found at /api/student/dashboard/
```

**Проверить:**
```bash
curl -X GET http://localhost:8000/api/student/dashboard/ \
  -H "Authorization: Token YOUR_STUDENT_TOKEN"
```

**Файлы для проверки:**
1. `/backend/materials/student_urls.py` - содержит ли endpoint?
2. `/backend/materials/student_dashboard_views.py` - существует ли view?

**Fix Checklist:**
- [ ] Проверить student_urls.py
- [ ] Если нет endpoint - создать view student_dashboard_view()
- [ ] Добавить @api_view(['GET'])
- [ ] Добавить @permission_classes([IsStudentOrTeacher]) или аналог
- [ ] Добавить в URLconf
- [ ] Тестировать endpoint с student token
- [ ] Документировать response format

---

### ❌ ISSUE #5: Test User Creation Infrastructure Missing

**Приоритет:** HIGH
**Статус:** OPEN

**Описание:**
Нет удобного способа создать тестовых пользователей для разработки/тестирования.

**Проблема:**
```bash
# Требует интерактивного ввода
docker exec thebot-backend python manage.py createsuperuser

# Не работает с флагом --noinput
docker exec thebot-backend python manage.py createsuperuser --noinput
  # TypeError или ошибка пароля
```

**Fix Checklist:**
- [ ] Создать management command: `backend/accounts/management/commands/create_test_users.py`
- [ ] Реализовать:
```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1)
        parser.add_argument('--roles', nargs='+', default=['student', 'teacher', 'tutor', 'parent', 'admin'])

    def handle(self, *args, **options):
        for role in options['roles']:
            for i in range(options['count']):
                email = f"{role}{i}@test.com"
                password = "TestPass123!"
                # Create user with proper set_password()
                user = User.objects.create_user(...)
                # Create profile if needed
                # Log success
```
- [ ] Проверить что пароли правильно хешируются
- [ ] Убедиться что `is_active=True`
- [ ] Убедиться что role установлена правильно
- [ ] Тестировать логин для каждого пользователя
- [ ] Добавить в docker-entrypoint.sh для автоматического создания

---

## СРЕДНИЕ ПРОБЛЕМЫ

### ❌ ISSUE #6: Rate Limiting on Login

**Приоритет:** MEDIUM
**Статус:** OPEN
**Файл:** `/backend/accounts/views.py` (line 34)

**Текущее ограничение:** 5 попыток входа в минуту с одного IP

**Поведение:**
```
After 6 attempts within 1 minute:
HTTP 403 Forbidden
django_ratelimit.exceptions.Ratelimited
```

**Fix Checklist:**
- [ ] Для development: рассмотреть отключение или увеличение лимита
- [ ] Для production: убедиться что значение адекватно (5/m хорошо)
- [ ] Документировать в API docs
- [ ] Добавить в .env переменную для конфигурации
- [ ] Тестировать: убедиться что 5 попыток работают, 6я блокируется

**Конфигурация:**
```python
# Текущее
@ratelimit(key="ip", rate="5/m", method="POST")

# Для dev (опционально)
if DEBUG:
    @ratelimit(key="ip", rate="100/m", method="POST")
```

---

### ❌ ISSUE #7: Supabase Mock Mode Not Logged

**Приоритет:** MEDIUM
**Статус:** OPEN
**Файл:** `/backend/accounts/supabase_service.py`

**Описание:**
Нет явного логирования того, что Supabase находится в mock режиме. Это может скрывать проблемы в production.

**Текущее:**
```python
self.is_mock = True  # Development
```

**Fix Checklist:**
- [ ] Добавить явное логирование при инициализации SupabaseAuthService:
```python
def __init__(self):
    if not SUPABASE_URL or not SUPABASE_KEY:
        self.is_mock = True
        logger.warning("⚠️ Supabase is in MOCK MODE - using local authentication only")
    else:
        self.is_mock = False
        logger.info("✓ Supabase real mode enabled")
```
- [ ] Убедиться что SUPABASE_URL и SUPABASE_KEY корректны для production
- [ ] Проверить config/settings.py на наличие этих переменных
- [ ] Тестировать: логи должны отображать mode при запуске

---

### ❌ ISSUE #8: Admin Endpoints Permission Checks

**Приоритет:** MEDIUM
**Статус:** OPEN

**Описание:**
Не все admin endpoints имеют проверку прав доступа.

**Проверить:**
```bash
# List endpoints WITHOUT @permission_classes
cd backend && grep -r "^def.*request" accounts/views.py | \
  while read line; do
    func=$(echo "$line" | cut -d':' -f2)
    file=$(echo "$line" | cut -d':' -f1)
    grep -B 5 "$func" "$file" | grep -q "permission_classes" || echo "Missing: $func"
  done
```

**Пример:**
```python
# BAD - нет @permission_classes
@api_view(["GET"])
def get_admin_data(request):
    return Response(data)

# GOOD - есть проверка прав
@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_admin_data(request):
    return Response(data)
```

**Fix Checklist:**
- [ ] Найти все endpoints в `accounts/views.py` и `accounts/staff_views.py`
- [ ] Убедиться что каждый admin endpoint имеет @permission_classes
- [ ] Использовать `IsStaffOrAdmin` из staff_views.py или создать custom класс
- [ ] Для sensitive операций использовать более строгие checks
- [ ] Тестировать: пользователь без прав должен получить 403

---

### ❌ ISSUE #9: Missing Role-Based Endpoints

**Приоритет:** MEDIUM
**Статус:** OPEN

**Описание:**
Недостаточно endpoints для разных ролей.

**Проверить:**
```bash
# По каждой роли должны быть endpoints
# student  - /api/student/... (dashboard, progress, etc)
# teacher  - /api/teacher/... (classroom, grades, etc)
# tutor    - /api/tutor/... (students, schedule, etc)
# parent   - /api/parent/... (child progress, communication)
# admin    - /api/admin/... (users, system, etc)
```

**Текущее состояние:**
- ✓ /api/student/ - существует
- ✓ /api/teacher/ - существует
- ✓ /api/tutor/ - существует
- ? /api/parent/ - проверить
- ✓ /api/admin/ - существует

**Fix Checklist:**
- [ ] Проверить что все endpoints существуют
- [ ] Убедиться что каждый role имеет dedicated endpoints
- [ ] Убедиться что endpoints return role-specific data
- [ ] Документировать endpoint list для каждой роли

---

### ❌ ISSUE #10: Permission Classes Consistency

**Приоритет:** MEDIUM
**Статус:** OPEN

**Описание:**
Permission classes применяются непоследовательно разными endpoints.

**Примеры:**
- Некоторые используют `IsStaffOrAdmin`
- Некоторые используют `IsAdminUser`
- Некоторые используют custom classes
- Некоторые не используют ничего

**Fix Checklist:**
- [ ] Определить стандартный набор permission classes
- [ ] Создать в `accounts/permissions.py`:
  - `IsAdmin` - only superuser
  - `IsStaffOrAdmin` - staff or superuser
  - `IsTeacher` - role == 'teacher'
  - `IsStudent` - role == 'student'
  - `IsTutor` - role == 'tutor'
  - `IsParent` - role == 'parent'
  - `IsOwnerOrAdmin` - owns resource or admin
- [ ] Применить консистентно ко всем endpoints
- [ ] Документировать permission requirements для каждого endpoint

---

### ❌ ISSUE #11: Endpoint Documentation Missing

**Приоритет:** MEDIUM
**Статус:** OPEN

**Описание:**
Нет документации по доступным endpoints и требованиям к ним.

**Fix Checklist:**
- [ ] Создать `/backend/API_ENDPOINTS.md` с полным списком
- [ ] Для каждого endpoint документировать:
  - Method (GET/POST/PUT/DELETE)
  - Path (/api/...)
  - Required permissions
  - Request body (if applicable)
  - Response format
  - Error codes
- [ ] Использовать Swagger/OpenAPI для auto-documentation
- [ ] Добавить `/api/docs/` endpoint для browseable API docs

---

### ❌ ISSUE #12: Error Response Format Inconsistency

**Приоритет:** MEDIUM
**Статус:** OPEN

**Описание:**
Разные endpoints возвращают разные форматы ошибок.

**Примеры:**
```json
// Format 1: some endpoints
{"success": false, "error": "message"}

// Format 2: other endpoints
{"detail": "message"}

// Format 3: DRF default
{"field": ["error message"]}

// Format 4: some endpoints
{"error_code": 400, "error_message": "..."}
```

**Fix Checklist:**
- [ ] Выбрать единый формат ошибок
- [ ] Рекомендуемый:
```json
{
  "success": false,
  "error": "human readable message",
  "error_code": "ENUM_CODE",
  "details": {}
}
```
- [ ] Создать custom exception handlers в DRF
- [ ] Применить ко всем endpoints
- [ ] Документировать error codes

---

### ❌ ISSUE #13: Missing Integration Tests

**Приоритет:** MEDIUM
**Статус:** OPEN

**Описание:**
Нет интеграционных тестов для auth flow.

**Fix Checklist:**
- [ ] Создать `/backend/accounts/tests/test_auth_integration.py`
- [ ] Написать тесты для:
  - Login success с правильным password
  - Login failure с неправильным password
  - Login failure с неexistent user
  - Token создается после login
  - Token работает для authenticated requests
  - Token expire/refresh
  - Logout работает
  - Роль корректно возвращается
- [ ] Запустить: `pytest backend/accounts/tests/test_auth_integration.py -v`
- [ ] Убедиться что все тесты проходят

---

## SUMMARY TABLE

| # | Issue | Priority | Status | Est. Time |
|---|-------|----------|--------|-----------|
| 1 | Admin Role Display | CRITICAL | OPEN | 30 min |
| 2 | Frontend Unhealthy | CRITICAL | OPEN | 1-2 hours |
| 3 | Missing Schedule Endpoint | HIGH | OPEN | 30 min |
| 4 | Missing Dashboard Endpoint | HIGH | OPEN | 30 min |
| 5 | Test User Creation | HIGH | OPEN | 1 hour |
| 6 | Rate Limiting Config | MEDIUM | OPEN | 15 min |
| 7 | Supabase Logging | MEDIUM | OPEN | 15 min |
| 8 | Permission Checks | MEDIUM | OPEN | 2 hours |
| 9 | Role Endpoints | MEDIUM | OPEN | 1 hour |
| 10 | Permission Consistency | MEDIUM | OPEN | 2 hours |
| 11 | Documentation | MEDIUM | OPEN | 1 hour |
| 12 | Error Format | MEDIUM | OPEN | 1-2 hours |
| 13 | Integration Tests | MEDIUM | OPEN | 2-3 hours |

**Total Estimated Time:** 16-23 hours

---

## TESTING CHECKLIST

После каждого исправления:

```bash
# 1. Run migrations
docker exec thebot-backend python manage.py migrate

# 2. Run tests
docker exec thebot-backend pytest -v

# 3. Test the specific feature
curl -X GET http://localhost:8000/{endpoint} \
  -H "Authorization: Token {token}"

# 4. Check logs
docker logs thebot-backend --tail 50

# 5. Check no regressions
# - Verify other endpoints still work
# - Verify permissions still enforce
# - Verify data integrity
```

---

**Last Updated:** 2026-01-01
**Next Review:** After each issue fixed
