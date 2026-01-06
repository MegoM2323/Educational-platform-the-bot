# TUTOR_CABINET_REGRESSION_FIX: Critical API Issues

## Статус: Planning

## Проблемы
1. POST /api/chat/ returns 500 (TypeError: created_by duplicate)
2. GET /api/accounts/students/ returns 403 (Permission denied)
3. GET /api/invoices/ returns 404 (URL not mounted)
4. GET /api/assignments/ returns 404 (ViewSet not registered)
5. Additional 404 endpoints (student detail, user update, tutor profile)

## Параллельная группа 1: Исправления (5 независимых задач)

### T001: Fix ChatRoom serializer (chat/serializers.py + chat/views.py) - coder
- Issue: perform_create() передает created_by, но create() уже устанавливает его
- Fix: Удалить параметр created_by из serializer.save() в perform_create()
- OR: Удалить created_by из create() метода
- Файлы: backend/chat/views.py (line 63), backend/chat/serializers.py (line 166)

### T002: Fix TutorStudentsViewSet permissions - coder
- Issue: GET /api/accounts/students/ возвращает 403
- Fix: Проверить permission_classes, добавить list action если нужно
- Файлы: backend/accounts/tutor_views.py (TutorStudentsViewSet)

### T003: Verify invoices URLs mounting - coder
- Issue: /api/invoices/ returns 404
- Verify: include() в config/urls.py (есть на line 45), router registered
- Файлы: backend/invoices/urls.py, backend/config/urls.py

### T004: Verify assignments URLs mounting - coder
- Issue: /api/assignments/ returns 404
- Verify: include() в config/urls.py (есть на line 34), ViewSet registered
- Файлы: backend/assignments/urls.py, backend/config/urls.py

### T005: Verify remaining 404 endpoints - coder
- Issue: Student detail, user update, tutor profile return 404
- Verify: endpoints defined in views and urls
- Файлы: backend/accounts/views.py, backend/accounts/profile_views.py, backend/accounts/urls.py

## Параллельная группа 2: Review & Testing

### T101: Code review - reviewer
- Проверить что все исправления не нарушают существующий код
- Убедиться что permissions остались корректны
- Проверить что URL routing правильный

### T102: Test & validation - tester
- POST /api/chat/ создает комнату
- GET /api/accounts/students/ возвращает 200
- GET /api/invoices/ возвращает 200
- GET /api/assignments/ возвращает 200
- Все остальные endpoints доступны

## Ожидаемый результат
✓ Все 5 исправлений выполнены параллельно
✓ Код прошел review
✓ Тесты pass
✓ Все endpoints работают
