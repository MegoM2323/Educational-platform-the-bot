# ИсправлениеSchedulingAPI: Lesson edit ValidationError и Conflict checking

## Статус: implementation

## Задача
Исправить 2 критические проблемы в scheduling API:

### C1: Исправить Lesson edit ValidationError при ForeignKey
**Проблема:** При редактировании урока возникает ValidationError с ForeignKey

**Решение:**
1. ~~В LessonManager добавить update() метод (уже есть create())~~
2. В LessonUpdateSerializer проверить что teacher/student/subject валидны
3. В LessonViewSet переопределить perform_update() для правильной валидации
4. Убедиться что Lesson.save() не вызывает full_clean() при обновлении (или сделать optional)

**Файлы:** backend/scheduling/views.py, models.py, serializers.py
**Тесты:** T038_LESSON_EDIT, T039_LESSON_SCHEDULE

### C2: Добавить check_conflicts + reschedule endpoints
**Проблема:** Нет endpoint для проверки конфликтов и переноса уроков

**Решение:** Добавить 2 @action метода к LessonViewSet:

1. check_conflicts (detail=False):
   - Input: {"teacher_id": X, "date": "2026-01-07", "start_time": "10:00", "end_time": "11:00"}
   - Найти все уроки teacher'а на дату
   - Проверить пересечение времени
   - Output: {"conflicts": [...], "has_conflict": bool}

2. reschedule (detail=True):
   - Input: {"date": "2026-01-07", "start_time": "10:00", "end_time": "11:00"}
   - Проверить конфликты перед переносом
   - Обновить Lesson
   - Output: обновленный урок

**API endpoints:**
- POST /api/scheduling/lessons/check-conflicts/
- POST /api/scheduling/lessons/{lesson_id}/reschedule/

**Тесты:** T041_LESSON_RESCHEDULE, T052_SCHEDULE_CONFLICT_CHECK

## Параллельная группа 1: Implementation (2 независимые задачи)

### Task C1: Lesson edit fix
- [ ] Исправить LessonUpdateSerializer для правильной валидации
- [ ] Обновить perform_update() в LessonViewSet
- [ ] Убедиться что Lesson.save(skip_validation=True) используется при update

### Task C2: Add conflict checking endpoints
- [ ] Добавить check_conflicts @action method
- [ ] Добавить reschedule @action method
- [ ] Зарегистрировать endpoints в urls.py

## Параллельная группа 2: Review & Testing

### T101: Code review
- Проверить что валидация работает правильно
- Убедиться что endpoints вызывают нужные методы
- Проверить что error handling корректный

### T102: Run failing tests
- T038_LESSON_EDIT
- T039_LESSON_SCHEDULE
- T041_LESSON_RESCHEDULE
- T052_SCHEDULE_CONFLICT_CHECK

## Ожидаемый результат
✓ Lesson edit без ValidationError на ForeignKey
✓ API endpoints для check_conflicts и reschedule работают
✓ Все тесты (T038, T039, T041, T052) проходят
✓ Code review пройден (LGTM)
