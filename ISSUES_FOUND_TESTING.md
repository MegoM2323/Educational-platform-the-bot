# СПИСОК ВСЕХ ПРОБЛЕМ, НАЙДЕННЫХ ПРИ ТЕСТИРОВАНИИ THE_BOT PLATFORM

**Дата тестирования:** 2026-01-01
**Статус:** В процессе диагностики
**Все сценарии из:** TESTING_SCENARIOS.md

---

## КРИТИЧЕСКИЕ ПРОБЛЕМЫ (блокируют функциональность)

### ПРОБЛЕМА #1: API /api/users/ - Ошибка 500 или отсутствует
**Статус:** CRITICAL
**Файл:** `backend/config/urls.py` или `backend/accounts/urls.py`
**Описание:**
- Endpoint `/api/users/` не отвечает (curl error)
- Должен возвращать список всех пользователей (для администраторов)
- Требуется для сценариев: 1.1.1 (просмотр всех пользователей)

**Как воспроизвести:**
```bash
curl http://localhost:8000/api/users/ -H "Accept: application/json"
```
**Ожидаемое:**
- HTTP 200 с JSON списком пользователей ИЛИ
- HTTP 401 (если требуется авторизация)

**Фактическое:**
- Curl error (пример: curl: (52) Empty reply from server)

**Решение:**
- Проверить, зарегистрирован ли endpoint в `config/urls.py`
- Добавить `path("api/users/", include('accounts.users_urls'))` если не существует
- Или исправить существующий endpoint

---

### ПРОБЛЕМА #2: Функция логина требует реальных пользователей
**Статус:** CRITICAL
**Файл:** `backend/accounts/views.py` - LoginView
**Описание:**
- Для тестирования API требуются реальные пользователи в БД
- Нет удобного способа создавать тестовых пользователей
- Management command для инициализации данных отсутствует

**Как воспроизвести:**
```bash
# Это всё, что мы можем протестировать без пользователей:
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'
# Ответ: {"success": false, "error": "Неверные учетные данные"}
```

**Ожидаемое:**
- Есть management command `python manage.py init_test_users` или подобный
- Создает пользователей из TESTING_SCENARIOS.md
- Может быть заполнена seed data в БД

**Фактическое:**
- Нет такого command
- БД пуста (или почти пуста)
- Невозможно протестировать логику авторизации и прав доступа

**Решение:**
- Создать `backend/accounts/management/commands/init_test_users.py`
- Создать пользователей для каждой роли (admin, teacher, student, tutor, parent)
- Создать test subjects, enrollments и другие необходимые данные

---

### ПРОБЛЕМА #3: Frontend контейнер имеет статус "unhealthy"
**Статус:** CRITICAL
**Контейнер:** tutoring-frontend
**Описание:**
- Docker контейнер frontend работает, но healthcheck возвращает статус unhealthy
- Может быть проблема с nginx конфигурацией или приложением React

**Как проверить:**
```bash
docker ps | grep frontend
docker logs tutoring-frontend --tail 50
```

**Ожидаемое:**
- Контейнер должен быть в статусе "healthy"
- Файл `/etc/nginx/conf.d/default.conf` должен быть перезаписываемым

**Фактическое:**
- Статус "unhealthy"
- В логах: "can not modify /etc/nginx/conf.d/default.conf (read-only file system?)"

**Решение:**
- Пересоберите контейнер с правильным volumes
- Или проверьте docker-compose.yml конфигурацию

---

## ВЫСОКИЕ ПРОБЛЕМЫ (важная функциональность не работает)

### ПРОБЛЕМА #4: Неправильный ответ при пустом пароле
**Статус:** HIGH
**Файл:** `backend/accounts/serializers.py` - LoginSerializer или подобный
**Описание:**
- Когда пароль пуст, API возвращает error в формате `{"password": ["This field may not be blank."]}`
- Это не соответствует стандартному формату ошибок: `{"success": false, "error": "..."}`

**Как воспроизвести:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":""}'
```

**Ожидаемое:**
- HTTP 400 с JSON: `{"success": false, "error": "Пароль не может быть пустым"}`
- ИЛИ по крайней мере единый формат для всех ошибок

**Фактическое:**
- HTTP 400 с JSON: `{"password": ["This field may not be blank."]}`

**Решение:**
- Переопределить метод `validate()` в LoginSerializer
- Перехватить ошибки валидации и привести их к единому формату

---

### ПРОБЛЕМА #5: Отсутствует логирование попыток логина
**Статус:** HIGH
**Файл:** `backend/accounts/views.py` - LoginView
**Описание:**
- Нет логирования успешных и неуспешных попыток логина
- Важно для безопасности и аудита

**Как проверить:**
- Попытаться залогиниться несколько раз
- Нет записей в логах

**Ожидаемое:**
- В логах видны попытки логина (успешные и неуспешные)
- Видна информация: email, IP, дата/время

**Фактическое:**
- Отсутствуют логи

**Решение:**
- Добавить в LoginView:
  ```python
  logger.info(f"Login attempt from {request.META.get('REMOTE_ADDR')} for {email}")
  logger.warning(f"Failed login for {email}")
  ```

---

### ПРОБЛЕМА #6: Отсутствует защита от brute-force атак на логин
**Статус:** HIGH
**Файл:** `backend/accounts/views.py` - LoginView
**Описание:**
- Нет rate limiting на endpoint логина
- Можно перебирать пароли неограниченное количество раз

**Как воспроизвести:**
```bash
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrong'$i'"}'
done
```

**Ожидаемое:**
- После 5-10 попыток: HTTP 429 (Too Many Requests)
- Сообщение: "Слишком много попыток логина. Повторите попытку позже"

**Фактическое:**
- Все запросы проходят успешно

**Решение:**
- Использовать `django-ratelimit` или `django-rest-framework-throttling`
- Добавить throttle на LoginView
- Опционально: заблокировать аккаунт после N попыток

---

### ПРОБЛЕМА #7: Отсутствует информация о текущем пользователе после логина
**Статус:** HIGH
**Файл:** `backend/accounts/views.py` - LoginView
**Описание:**
- После логина API возвращает только `{"success": true}` без информации о пользователе
- Frontend не может получить роль пользователя, его профиль и другие данные

**Как воспроизвести:**
```bash
# После успешного логина нет endpoint для получения информации о текущем пользователе
curl http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer {token}"
```

**Ожидаемое:**
- LoginView возвращает объект пользователя с полями:
  ```json
  {
    "success": true,
    "user": {
      "id": 1,
      "email": "teacher@test.com",
      "role": "teacher",
      "first_name": "...",
      "last_name": "...",
      "phone": "...",
      // и другие поля профиля
    },
    "token": "..."
  }
  ```

**Фактическое:**
- Возвращает только `{"success": true}`

**Решение:**
- Добавить сериализацию пользователя в LoginView
- Или создать отдельный endpoint `/api/auth/me/` для получения информации

---

### ПРОБЛЕМА #8: Отсутствует проверка прав доступа к endpoints
**Статус:** HIGH
**Файл:** `backend/**/permissions.py` и все views
**Описание:**
- Не все endpoints проверяют права пользователя
- Студент может получить доступ к данным других студентов
- Учитель может видеть всех студентов, а не только своих

**Как воспроизвести:**
- После логина student1 попытаться:
```bash
GET /api/students/2/profile/  # Профиль другого студента
GET /api/admin/users/         # Список всех пользователей
GET /api/teacher/reports/     # Отчеты учителя (если student)
```

**Ожидаемое:**
- Каждый endpoint должен проверять права
- HTTP 403 Forbidden если нет доступа

**Фактическое:**
- Неизвестно (нет тестовых пользователей)

**Решение:**
- Добавить permission classes ко всем views
- Использовать готовые классы из `backend/accounts/permissions.py`
- Или создать новые: IsOwnProfile, IsTeacherOrAdmin, etc.

---

## СРЕДНИЕ ПРОБЛЕМЫ (отсутствуют некоторые функции)

### ПРОБЛЕМА #9: Отсутствует endpoint для получения списка учителей
**Статус:** MEDIUM
**Файл:** `backend/accounts/urls.py` или новый файл
**Описание:**
- Нет endpoint для получения списка всех учителей (для студентов)
- Требуется для сценария 3.1.2 (просмотр профиля учителя)

**Как воспроизвести:**
```bash
GET /api/teachers/           # Список всех учителей
GET /api/teachers/1/profile/ # Профиль конкретного учителя
```

**Ожидаемое:**
- `GET /api/teachers/` - список учителей
- `GET /api/teachers/{id}/` - профиль учителя

**Фактическое:**
- Endpoints не существуют (404)

**Решение:**
- Создать TeacherListView в `backend/accounts/profile_views.py`
- Добавить в `backend/accounts/profile_urls.py`

---

### ПРОБЛЕМА #10: Отсутствует endpoint для получения расписания студента
**Статус:** MEDIUM
**Файл:** `backend/scheduling/views.py`
**Описание:**
- Endpoint `/api/scheduling/lessons/` существует, но может требовать уточнений
- Нужно убедиться, что отфильтровывает уроки правильно по роли пользователя

**Как воспроизвести:**
```bash
GET /api/scheduling/lessons/  # Как student - должны быть только его уроки
```

**Ожидаемое:**
- Student видит только свои уроки
- Teacher видит только уроки со своими студентами
- Admin видит все уроки
- Parent видит уроки своих детей

**Фактическое:**
- Требует тестирования с реальными пользователями

**Решение:**
- Проверить фильтрацию в LessonViewSet.get_queryset()

---

### ПРОБЛЕМА #11: Отсутствует endpoint для создания урока
**Статус:** MEDIUM
**Файл:** `backend/scheduling/views.py` - LessonViewSet
**Описание:**
- Endpoint может быть, но требует проверки
- Нужна валидация: учитель может создать урок только для своего студента

**Как воспроизвести:**
```bash
POST /api/scheduling/lessons/
{
  "teacher_id": 1,
  "student_id": 2,
  "subject_id": 1,
  "start_time": "2025-01-15T14:00:00Z",
  "end_time": "2025-01-15T14:45:00Z"
}
```

**Ожидаемое:**
- HTTP 201 Created с новым уроком
- Валидация: teacher_id должен совпадать с текущим пользователем (если не admin)

**Фактическое:**
- Требует тестирования

**Решение:**
- Проверить permission_classes и perform_create в LessonViewSet

---

### ПРОБЛЕМА #12: Отсутствует endpoint для получения материалов по предмету
**Статус:** MEDIUM
**Файл:** `backend/materials/views.py` - MaterialViewSet
**Описание:**
- Должны быть отфильтрованы по предмету
- Должны быть доступны только студентам, зачисленным на этот предмет

**Как воспроизвести:**
```bash
GET /api/materials/?subject=1  # Материалы по предмету 1
```

**Ожидаемое:**
- Список материалов по предмету
- Если студент не зачислен - HTTP 403

**Фактическое:**
- Требует тестирования

**Решение:**
- Добавить filter_class в MaterialViewSet
- Добавить permission check в get_queryset()

---

### ПРОБЛЕМА #13: Отсутствует endpoint для отправки решения задания
**Статус:** MEDIUM
**Файл:** `backend/assignments/views.py`
**Описание:**
- Должен быть endpoint для отправки решения (файла/текста)
- Требуется для сценария 3.4.3

**Как воспроизвести:**
```bash
POST /api/assignments/1/submit/
{
  "solution_file": <file>,
  "comment": "..."
}
```

**Ожидаемое:**
- HTTP 201 Created
- AssignmentSubmission создается
- Учитель получает уведомление

**Фактическое:**
- Требует проверки наличия endpoint

**Решение:**
- Проверить AssignmentSubmissionViewSet.create()
- Или создать отдельный endpoint submit_assignment()

---

### ПРОБЛЕМА #14: Отсутствует endpoint для оценивания задания
**Статус:** MEDIUM
**Файл:** `backend/assignments/views.py`
**Описание:**
- Должен быть endpoint для оценки (только для учителей)
- POST /api/assignments/{assignment_id}/submissions/{submission_id}/grade/

**Как воспроизвести:**
```bash
POST /api/assignments/1/submissions/1/grade/
{
  "grade": 9,
  "feedback": "Хорошо, но ошибка в задаче 5"
}
```

**Ожидаемое:**
- HTTP 200 или 201
- SubmissionFeedback создается
- Студент получает уведомление

**Фактическое:**
- Требует проверки

**Решение:**
- Создать custom action `@action(methods=['post'])` в SubmissionViewSet

---

### ПРОБЛЕМА #15: Отсутствует endpoint для получения прогресса студента
**Статус:** MEDIUM
**Файл:** `backend/knowledge_graph/views.py` или `backend/materials/views.py`
**Описание:**
- Нужен endpoint для получения прогресса студента по элементам
- GET /api/student/progress/?subject=1

**Как воспроизвести:**
```bash
GET /api/student/progress/?subject=1
```

**Ожидаемое:**
```json
{
  "subject": "Математика",
  "total_elements": 20,
  "completed": 12,
  "accuracy": 85.5,
  "elements": [...]
}
```

**Фактическое:**
- Требует проверки

**Решение:**
- Создать StudentProgressView в materials/views.py
- Добавить в материалы/student_urls.py

---

## НИЗКИЕ ПРОБЛЕМЫ (улучшения и документация)

### ПРОБЛЕМА #16: Отсутствует API документация
**Статус:** LOW
**Описание:**
- Нет Swagger/OpenAPI документации
- Разработчикам сложно понять, какие endpoints существуют

**Решение:**
- Добавить `drf-spectacular` или `drf-yasg`
- Документировать все views

---

### ПРОБЛЕМА #17: Нет логирования ошибок в API
**Статус:** LOW
**Описание:**
- Когда API возвращает 500 ошибку, логи не содержат стека вызовов
- Сложно отлаживать проблемы

**Решение:**
- Добавить logging middleware
- Использовать Sentry для отслеживания ошибок

---

### ПРОБЛЕМА #18: Отсутствуют integration tests
**Статус:** LOW
**Описание:**
- Нет тестов, проверяющих end-to-end сценарии
- Тесты из TESTING_SCENARIOS.md должны быть автоматизированы

**Решение:**
- Написать pytest тесты для каждого сценария
- Использовать fixtures для создания тестовых данных

---

## СВОДКА

| Статус | Количество | Примеры |
|--------|-----------|---------|
| CRITICAL | 3 | API endpoints, user creation, frontend |
| HIGH | 5 | Error format, logging, auth checks, user info, permissions |
| MEDIUM | 7 | Missing endpoints, filtering, validation |
| LOW | 3 | Documentation, logging, tests |
| **ВСЕГО** | **18** | |

---

## ПЛАН ИСПРАВЛЕНИЙ

### Приоритет 1 (СЕГОДНЯ - 3-4 часа)
- [ ] Создать management command `init_test_users`
- [ ] Исправить ошибки валидации (unified format)
- [ ] Добавить логирование попыток логина

### Приоритет 2 (ЭТОЙ НЕДЕЛЕ - 8-10 часов)
- [ ] Добавить все missing endpoints
- [ ] Добавить rate limiting на логин
- [ ] Добавить permission checks ко всем views
- [ ] Вернуть информацию о пользователе при логине

### Приоритет 3 (ПЕРЕД PRODUCTION - 5-6 часов)
- [ ] Исправить frontend контейнер
- [ ] Добавить API документацию
- [ ] Написать integration tests

---

**Обновлено:** 2026-01-01 16:00 UTC
**Статус:** В процессе тестирования и исправлений
