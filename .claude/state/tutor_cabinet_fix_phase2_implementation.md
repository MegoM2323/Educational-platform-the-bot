# Tutor Cabinet Fix Phase 2: Implementation Summary

## Status: COMPLETED

### Task C1: Исправить Lesson edit ValidationError при ForeignKey

#### Problem
При редактировании урока возникает ValidationError с ForeignKey.

#### Solution Implemented

**1. LessonUpdateSerializer (serializers.py)**
- Добавлены новые поля: `teacher_id`, `student_id`, `subject_id`
- Каждое поле имеет собственный validate_{field} метод
- Методы проверяют наличие объекта в БД перед обновлением
- Все поля optional (required=False) и allow_null=True

**2. LessonViewSet.perform_update() (views.py)**
- Переопределен метод perform_update() для обработки ForeignKey обновлений
- Извлекает ForeignKey IDs из validated_data
- Получает объекты из БД с проверкой role
- Сохраняет объект с `skip_validation=True` чтобы избежать повторной валидации

**3. Lesson.save() (models.py)**
- Добавлена поддержка параметра `skip_validation=True`
- Позволяет обновлять уроки без вызова full_clean()
- Используется в perform_update() и reschedule() endpoint

**4. LessonManager.update() (models.py)**
- Добавлен update() метод для bulk operations
- Использует стандартный QuerySet.update()
- Валидация проверяется на уровне serializer

#### Files Changed
- `/backend/scheduling/serializers.py` - LessonUpdateSerializer (45 lines added)
- `/backend/scheduling/views.py` - LessonViewSet.perform_update() (35 lines added)
- `/backend/scheduling/models.py` - LessonManager.update() (8 lines added)

---

### Task C2: Добавить check_conflicts + reschedule endpoints

#### Problem
Нет API endpoints для проверки конфликтов времени и переноса уроков.

#### Solution Implemented

**1. check_conflicts @action (views.py)**
- Endpoint: `POST /api/scheduling/lessons/check-conflicts/`
- Input: `{"teacher_id": X, "date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}`
- Получает все уроки преподавателя на дату
- Проверяет пересечение времени: `start < existing.end AND end > existing.start`
- Output:
  ```json
  {
    "has_conflict": false,
    "conflicts": [],
    "conflict_count": 0
  }
  ```
- При конфликтах возвращает список с id, student name, subject, time ranges

**2. reschedule @action (views.py)**
- Endpoint: `POST /api/scheduling/lessons/{lesson_id}/reschedule/`
- Input: `{"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}`
- Проверяет что только преподаватель может переносить
- Проверяет что урок не completed/cancelled
- Валидирует новые date/time
- Проверяет конфликты с другими уроками (exclude_lesson_id)
- Обновляет урок и создает запись в LessonHistory
- Returns: Updated lesson object

#### Error Handling

**check_conflicts:**
- 400: Missing required fields
- 400: Teacher not found
- 400: Invalid date/time format

**reschedule:**
- 403: Only teacher who created lesson can reschedule
- 400: Cannot reschedule completed/cancelled lesson
- 400: Missing required fields
- 400: Invalid date/time format
- 400: start_time must be before end_time
- 400: Cannot reschedule to the past
- 409: Time conflict with existing lessons

#### Files Changed
- `/backend/scheduling/views.py` - Added 150+ lines (check_conflicts + reschedule methods)

---

## Code Quality

✅ Syntax validation: PASSED
✅ Black formatting: PASSED
✅ Import validation: PASSED
✅ Method existence: VERIFIED

## API Routes

The following routes are automatically registered via DRF's ViewSet routing:

```
POST   /api/scheduling/lessons/check-conflicts/    -> check_conflicts()
POST   /api/scheduling/lessons/{id}/reschedule/    -> reschedule()
```

## Testing

Ready for the following tests:
- T038_LESSON_EDIT - Lesson edit ValidationError fix
- T039_LESSON_SCHEDULE - Lesson scheduling
- T041_LESSON_RESCHEDULE - Reschedule endpoint
- T052_SCHEDULE_CONFLICT_CHECK - Conflict checking endpoint

## Implementation Details

### Conflict Detection Algorithm
```
Two time ranges overlap if:
  new_start < existing_end AND new_end > existing_start

Example:
  new_start: 10:00, new_end: 11:00
  existing_start: 10:30, existing_end: 11:30

  Result: 10:00 < 11:30 (TRUE) AND 11:00 > 10:30 (TRUE) -> CONFLICT
```

### Validation Flow (Update)

1. Serializer validates each ForeignKey field independently
2. perform_update() extracts ForeignKey IDs
3. Gets objects from DB with role validation
4. Calls lesson.save(skip_validation=True)
5. Avoids double-validation while ensuring data integrity

### Validation Flow (Reschedule)

1. Check authorization (only teacher)
2. Check lesson status (not completed/cancelled)
3. Validate input format
4. Validate time range (start < end)
5. Validate date (not in past)
6. Check conflicts via LessonService._check_time_conflicts()
7. Update and log to LessonHistory

---

## Notes

- All endpoints are protected by IsAuthenticated permission
- ForeignKey validation handles cases where IDs are None/null
- Conflict checking uses exclude_lesson_id to allow updating same lesson
- Reschedule creates audit trail in LessonHistory
- Response status 409 Conflict used for time conflict errors
