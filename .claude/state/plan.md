# Исправление JWT validation для material endpoints

## Статус: implementation

## Задача
Исправить JWT authentication broken на material endpoints. Все authenticated requests к `/api/materials/materials/{id}/` возвращают 401 даже с валидным Bearer token.

## Корневая проблема
JWT authentication class отсутствует в DEFAULT_AUTHENTICATION_CLASSES в settings.py. Текущий конфиг поддерживает только TokenAuthentication и SessionAuthentication, но не поддерживает JWT Bearer tokens.

## Параллельная группа 1: Реализация (4 независимые задачи)

### T001: Добавить JWT authentication в settings.py - DONE
- Line 672-675: Добавить "rest_framework_simplejwt.authentication.JWTAuthentication" в DEFAULT_AUTHENTICATION_CLASSES
- Позиция: ПЕРВЫМ в списке (до TokenAuthentication)
- Необходимо поддерживать обе схемы (JWT и Token для обратной совместимости)
- STATUS: COMPLETED ✓

### T002: Обновить material viewsets - DONE
- MaterialViewSet, SubjectViewSet: убедиться что используют authentication_classes
- Если не используют - явно указать в классе с приоритетом JWT
- Проверить что все endpoints с @action имеют корректные permission_classes
- STATUS: COMPLETED ✓

### T003: Добавить IsAuthenticated для read-only endpoints - IN PROGRESS
- MaterialDetailView, MaterialListView: требуют IsAuthenticated
- Добавить StudentEnrollmentPermission для endpoints требующих проверки зачисления
- Обновить permission_classes в views.py согласно требованиям ролей
- STATUS: 50% (добавлена StudentEnrollmentPermission в MaterialViewSet)

### T004: Проверить и исправить permissions.py - PENDING
- StudentEnrollmentPermission: проверить что has_permission корректно работает
- Убедиться что все permission checks поддерживают JWT токены (не проверяют только Token)
- Исправить логику проверки authenticated в has_permission

## Параллельная группа 2: Review & Testing

### T101: Code review - reviewer
- Проверить что JWT добавлен ПЕРВЫМ в список authentication
- Убедиться что all endpoints имеют явные permission_classes
- Проверить что TokenAuthentication остался для обратной совместимости
- Проверить что permission classes не ломают другие endpoints

### T102: Запустить failing tests - tester
- T008_AUTH_ROLE_HIERARCHY
- T115_TUTOR_TEACHER_INTERACTION
- T139_SECURITY_AUTH_HEADER
- Проверить что все тесты с 401 теперь проходят
- Убедиться что новые permission classes не ломают существующие тесты

## Ожидаемый результат
✓ JWT authentication добавлена в settings.py
✓ Material endpoints принимают Bearer tokens
✓ Permission classes соответствуют ролям (student/tutor/teacher/admin)
✓ Все failing tests (T008, T115, T139) проходят
✓ Обратная совместимость с TokenAuthentication сохранена
✓ Тесты pass
✓ LGTM от reviewer
