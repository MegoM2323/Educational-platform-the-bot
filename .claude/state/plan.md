# План: Исправить Assignments & Grading тесты до 100% pass rate

## Summary
Исправить модели, сериализаторы и представления в приложении assignments для прохождения всех 39 тестов в test_assignments_and_grading_20260107.py.

## Выявленные проблемы

### 1. Неправильная модель SubjectEnrollment в тестах
**Проблема:** `SubjectEnrollment() got unexpected keyword arguments: 'tutor'`
**Файл:** backend/materials/models.py
**Причина:** Тест передает `tutor=tutor_with_profile` но модель не принимает этот параметр
**Решение:** Проверить структуру SubjectEnrollment и добавить поле `tutor` если его нет, или изменить тест на правильный параметр

### 2. Неправильные поля в Assignment модели
**Проблема:** `Assignment() got unexpected keyword arguments: 'subject', 'assignment_type'`
**Файл:** backend/assignments/models.py
**Решение:** Assignment модель должна иметь поля:
- `subject` (ForeignKey на Subject)
- `assignment_type` (choices: homework, test, project, essay, practical)
- `max_score` или `max_points`
- `deadline` или `due_date`

### 3. Endpoints возвращают 405 Method Not Allowed
**Проблемы:**
- POST /api/assignments/ не работает (405)
- POST /api/assignments/assignments/ не работает (405)
- PATCH /api/assignments/{id}/ не работает (405)
- DELETE /api/assignments/{id}/ не работает (405)
**Решение:** Убедиться что ViewSet имеет правильные методы (create, update, partial_update, destroy)

## Параллельные Task Группы

### Группа 1: Модели (Materials & Assignments)

#### Task T001: Проверить/исправить модель SubjectEnrollment
**Files:** backend/materials/models.py
**Changes:**
- Проверить что SubjectEnrollment имеет поле `tutor`
- Если нет - добавить ForeignKey на User с role=TUTOR
- Убедиться что создание с tutor=user работает

#### Task T002: Проверить/исправить модель Assignment
**Files:** backend/assignments/models.py
**Changes:**
- Убедиться что есть поля: subject, assignment_type, max_score, deadline, author, status
- assignment_type choices: homework, test, project, essay, practical
- status choices: draft, published, archived
- Все миграции применены

### Группа 2: Сериализаторы

#### Task T003: Проверить AssignmentSerializer
**Files:** backend/assignments/serializers.py
**Changes:**
- Включить все required fields: title, description, subject, assignment_type, max_score, deadline
- Валидаторы работают (deadline > now, max_score > 0, title not empty)
- read_only: id, author, created_at, updated_at

#### Task T004: Проверить AssignmentSubmissionSerializer
**Files:** backend/assignments/serializers.py
**Changes:**
- Включить все поля: assignment, student, submitted_at, content, status, score, feedback
- Status choices: submitted, graded, needs_revision, resubmitted
- Score валидируется (0 <= score <= assignment.max_score)

### Группа 3: Views/ViewSets

#### Task T005: Исправить AssignmentViewSet endpoints
**Files:** backend/assignments/views_main.py
**Changes:**
- Убедиться что есть методы: list(), create(), retrieve(), update(), partial_update(), destroy()
- create() создает Assignment с текущим пользователем как author
- Нужны пермиссионы: IsAuthenticated + IsTeacher/IsTutor для create/edit/delete
- Нужны фильтры, сортировка, пагинация

#### Task T006: Исправить AssignmentSubmissionViewSet endpoints
**Files:** backend/assignments/views_main.py
**Changes:**
- list() возвращает submissions с фильтром по assignment
- create() позволяет студенту отправить работу
- Нужен endpoint grade() для оценивания
- Нужен endpoint add_feedback() для обратной связи
- Нужен endpoint mark_reviewed() для отметки проверено
- Нужен endpoint return_for_rework() для возврата на доработку

#### Task T007: Исправить URL регистрацию
**Files:** backend/assignments/urls.py, backend/config/urls.py
**Changes:**
- Убедиться что ViewSets зарегистрированы в router
- Проверить что пути /api/assignments/ и /api/assignments/assignments/ работают
- Все custom actions зарегистрированы

## Success Criteria
- Все 39 тестов в test_assignments_and_grading_20260107.py должны быть PASSED
- Все 31 тест в test_tutor_cabinet_assignments_t056_t072_20260107.py должны оставаться PASSED
- Нет регрессии в других тестах

## Test Files
```bash
pytest backend/tests/tutor_cabinet/test_assignments_and_grading_20260107.py -v
pytest backend/tests/tutor_cabinet/test_tutor_cabinet_assignments_t056_t072_20260107.py -v
```
