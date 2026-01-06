# CRIT_001: Исправить создание пользователя через POST /api/accounts/users/

## Статус: T001 done, T002 pending

## Проблема
POST /api/accounts/users/ возвращает 405 Method Not Allowed. Блокирует валидацию входных данных и создание пользователей через API.

## Корневая причина
- Путь `/api/accounts/users/` в urls.py определён только для GET (функция `list_users`)
- Создание пользователей доступно только через `/api/accounts/users/create/` (функция `create_user_with_profile`)
- Нарушает REST соглашение: POST на `/users/` должен создавать пользователя

## Решение
Добавить POST обработчик к `/api/accounts/users/` с логикой создания пользователя.

Стратегия: Переоформить `create_user_with_profile` как обработчик ОБОИХ методов:
- GET /api/accounts/users/ - список пользователей (существующая функция `list_users`)
- POST /api/accounts/users/ - создание пользователя (существующая функция `create_user_with_profile`)

## Параллельная группа 1: Реализация (2 независимые задачи)

### T001: Создать класс-view для /api/accounts/users/ - coder
- Создать новый class-based view UserManagementView(APIView) в staff_views.py
- Метод GET: вызвать list_users логику
- Метод POST: вызвать create_user_with_profile логику
- Требуемые permissions: IsStaffOrAdmin
- Authentication: TokenAuthentication, SessionAuthentication
- Обновить urls.py: заменить `path("users/", views.list_users)` на `path("users/", UserManagementView.as_view())`
- Удалить путь `/users/create/` (deprecated - использовать POST /users/ вместо)

### T002: Проверить и обновить тесты - coder
- Найти все тесты которые делают POST на `/api/accounts/users/create/`
- Обновить их на POST `/api/accounts/users/`
- Убедиться что GET /api/accounts/users/ всё ещё работает
- STATUS: PENDING

## Параллельная группа 2: Review & Testing

### T101: Code review - reviewer
- Проверить что оба метода работают в одном классе
- Убедиться что permissions корректны для обоих методов
- Проверить что authentication остался на обе методы
- Проверить что логика валидации не нарушена

### T102: Запустить тесты - tester
- Проверить что GET /api/accounts/users/ возвращает список
- Проверить что POST /api/accounts/users/ создаёт пользователя (201)
- Проверить валидацию: email duplicate (400)
- Проверить валидацию: пароль < 8 символов (400)
- Проверить валидацию: роль не в (student, teacher, tutor, parent) (400)
- Проверить что возвращается credentials при создании

## Ожидаемый результат
✓ POST /api/accounts/users/ создаёт пользователя с 201 Created
✓ GET /api/accounts/users/ возвращает список пользователей
✓ Валидация email (duplicate, формат)
✓ Валидация пароля (минимум 8 символов)
✓ Валидация роли (student, teacher, tutor, parent)
✓ Профиль создаётся через signals
✓ Тесты проходят
✓ LGTM от reviewer
