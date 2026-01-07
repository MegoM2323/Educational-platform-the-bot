# План: Исправить 405 Method Not Allowed ошибки в assignment endpoints

## Проблема
Тесты ожидают list-level endpoints (без pk), но ViewSets используют неправильные @action decorators или маршрутизацию.

## Failin Endpoints
1. `POST /api/assignments/assign/` → должна быть detail=False или собственный path
2. `POST /api/assignments/grading-rubric/` → должна быть detail=False
3. `POST /api/assignments/apply-template/` → должна быть detail=False
4. `POST /api/assignments/submissions/` → используется router.register, должен работать
5. `POST /api/assignments/questions/` → используется router.register, должен работать

## Текущая ситуация
- AssignmentViewSet.assign() имеет detail=True (строка 146) → это /api/assignments/{pk}/assign/
- AssignmentSubmissionViewSet зарегистрирован как router.register(r"submissions", ...) → должен работать с POST
- AssignmentQuestionViewSet зарегистрирован как router.register(r"questions", ...) → должен работать с POST

## Решение
### Task 1: Анализ и исправление AssignmentViewSet endpoints
- Проверить @action decorators для assign(), assign_grades(), grading_rubric(), apply_template()
- Изменить detail=True на detail=False для list-level endpoints
- Или создать собственные path в urls.py для этих endpoints
- Файлы: backend/assignments/views_main.py, backend/assignments/urls.py

### Task 2: Проверить AssignmentSubmissionViewSet
- Убедиться что ModelViewSet правильно наследует create() метод
- Проверить get_permissions() и validate в create()
- Файл: backend/assignments/views_main.py

### Task 3: Проверить AssignmentQuestionViewSet
- Убедиться что ModelViewSet правильно наследует create() метод
- Проверить get_permissions() и validate в create()
- Файл: backend/assignments/views_main.py

## Success Criteria
- POST /api/assignments/assign/ → 200/201 (не 405)
- POST /api/assignments/grading-rubric/ → 200/201 (не 405)
- POST /api/assignments/apply-template/ → 200/201 (не 405)
- POST /api/assignments/submissions/ → 201 (не 405)
- POST /api/assignments/questions/ → 201 (не 405)
