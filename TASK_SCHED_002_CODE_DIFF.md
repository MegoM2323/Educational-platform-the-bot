# T_SCHED_002: Code Changes Diff

## File 1: Backend Service Layer

**Path**: `backend/scheduling/services/recurring_service.py`
**Lines Modified**: 131-149
**Lines Added**: 18
**Type**: Bug Fix

### Before (Original Code)
```python
109    @staticmethod
110    def generate_lessons(
111        recurring_lesson: RecurringLesson, force_regenerate: bool = False
112    ) -> dict:
113        """
114        Генерировать уроки из шаблона повторения с проверкой конфликтов.
115
116        Args:
117            recurring_lesson: Шаблон повторяющегося занятия
118            force_regenerate: Пересоздать все уроки (удалить существующие)
119
120        Returns:
121            Словарь с результатами:
122            {
123                'created': [Lesson, ...],          # успешно созданные уроки
124                'conflicts': {                     # даты с конфликтами
125                    date: 'conflict reason'
126                },
127                'skipped': [date, ...],            # даты, где уроки уже существуют
128                'total': int                       # всего дат в расписании
129            }
130        """
131        if not recurring_lesson.is_active:
132            raise ValidationError("Шаблон повторения неактивен")
133
-       # Получить даты повторений
134        dates = RecurrenceGenerator.generate_dates(
135            start_date=recurring_lesson.start_date,
136            pattern=recurring_lesson.pattern,
137            ...
```

### After (Fixed Code)
```python
109    @staticmethod
110    def generate_lessons(
111        recurring_lesson: RecurringLesson, force_regenerate: bool = False
112    ) -> dict:
113        """
114        Генерировать уроки из шаблона повторения с проверкой конфликтов.
115
116        Args:
117            recurring_lesson: Шаблон повторяющегося занятия
118            force_regenerate: Пересоздать все уроки (удалить существующие)
119
120        Returns:
121            Словарь с результатами:
122            {
123                'created': [Lesson, ...],          # успешно созданные уроки
124                'conflicts': {                     # даты с конфликтами
125                    date: 'conflict reason'
126                },
127                'skipped': [date, ...],            # даты, где уроки уже существуют
128                'total': int                       # всего дат в расписании
129            }
130        """
131        if not recurring_lesson.is_active:
132            raise ValidationError("Шаблон повторения неактивен")
133
+       # Валидировать что преподаватель учит студента этому предмету ПЕРЕД bulk созданием
+       # Это предотвращает создание orphaned уроков при деактивированном enrollment
+       try:
+           SubjectEnrollment.objects.get(
+               teacher=recurring_lesson.teacher,
+               student=recurring_lesson.student,
+               subject=recurring_lesson.subject,
+               is_active=True,
+           )
+       except SubjectEnrollment.DoesNotExist:
+           raise ValidationError(
+               f"Преподаватель {recurring_lesson.teacher.get_full_name()} не учит "
+               f"{recurring_lesson.subject.name} студента {recurring_lesson.student.get_full_name()}"
+           )
+
        # Получить даты повторений
134        dates = RecurrenceGenerator.generate_dates(
135            start_date=recurring_lesson.start_date,
136            pattern=recurring_lesson.pattern,
137            ...
```

### Unified Diff
```diff
@@ -130,6 +130,20 @@ class RecurringLessonService:
         if not recurring_lesson.is_active:
             raise ValidationError("Шаблон повторения неактивен")

+        # Валидировать что преподаватель учит студента этому предмету ПЕРЕД bulk созданием
+        # Это предотвращает создание orphaned уроков при деактивированном enrollment
+        try:
+            SubjectEnrollment.objects.get(
+                teacher=recurring_lesson.teacher,
+                student=recurring_lesson.student,
+                subject=recurring_lesson.subject,
+                is_active=True,
+            )
+        except SubjectEnrollment.DoesNotExist:
+            raise ValidationError(
+                f"Преподаватель {recurring_lesson.teacher.get_full_name()} не учит "
+                f"{recurring_lesson.subject.name} студента {recurring_lesson.student.get_full_name()}"
+            )
+
         # Получить даты повторений
         dates = RecurrenceGenerator.generate_dates(
             start_date=recurring_lesson.start_date,
```

---

## File 2: Test Suite

**Path**: `backend/scheduling/tests_extended.py`
**Lines Modified**: 142-168 (test 1), 169-221 (new tests)
**Lines Added**: 68 (2 new test methods + assertions)
**Type**: Test Coverage

### Modified: test_generate_lessons (Lines 142-168)

#### Before
```python
142    def test_generate_lessons(self, teacher, student, subject, enrollment):
143        """Тест генерации уроков из шаблона"""
144        recurring_lesson = RecurringLesson.objects.create(
145            teacher=teacher,
146            student=student,
147            subject=subject,
148            start_date=date.today() + timedelta(days=1),
149            end_date=date.today() + timedelta(days=30),
150            start_time=time(10, 0),
151            end_time=time(11, 0),
152            pattern="weekly",
153            interval=1,
154            weekdays=[0, 2, 4],
155            is_active=True,
156        )
157
-       lessons = RecurringLessonService.generate_lessons(recurring_lesson)
+
-       assert len(lessons) > 0
+       result = RecurringLessonService.generate_lessons(recurring_lesson)
+
+       assert result['total'] > 0
+       assert len(result['created']) > 0
        # Проверить что все уроки созданы правильно
-       for lesson in lessons:
+       for lesson in result['created']:
            assert lesson.teacher == teacher
            assert lesson.student == student
            assert lesson.subject == subject
            assert lesson.start_time == time(10, 0)
            assert lesson.end_time == time(11, 0)
```

### New: test_generate_lessons_without_enrollment_fails (Lines 170-191)

```python
+   def test_generate_lessons_without_enrollment_fails(self, teacher, student, subject):
+       """Тест что генерация уроков без валидного enrollment не допускается"""
+       # Не создаем enrollment - это основная проверка
+       recurring_lesson = RecurringLesson.objects.create(
+           teacher=teacher,
+           student=student,
+           subject=subject,
+           start_date=date.today() + timedelta(days=1),
+           end_date=date.today() + timedelta(days=30),
+           start_time=time(10, 0),
+           end_time=time(11, 0),
+           pattern="weekly",
+           interval=1,
+           weekdays=[0, 2, 4],
+           is_active=True,
+       )
+
+       # Попытка генерировать уроки должна выбросить ValidationError
+       with pytest.raises(ValidationError) as exc_info:
+           RecurringLessonService.generate_lessons(recurring_lesson)
+
+       assert "не учит" in str(exc_info.value)
```

### New: test_generate_lessons_with_inactive_enrollment_fails (Lines 193-221)

```python
+   def test_generate_lessons_with_inactive_enrollment_fails(self, teacher, student, subject):
+       """Тест что генерация уроков с неактивным enrollment не допускается"""
+       # Создаем неактивный enrollment
+       SubjectEnrollment.objects.create(
+           teacher=teacher,
+           student=student,
+           subject=subject,
+           is_active=False,  # НЕАКТИВНО
+       )
+
+       recurring_lesson = RecurringLesson.objects.create(
+           teacher=teacher,
+           student=student,
+           subject=subject,
+           start_date=date.today() + timedelta(days=1),
+           end_date=date.today() + timedelta(days=30),
+           start_time=time(10, 0),
+           end_time=time(11, 0),
+           pattern="weekly",
+           interval=1,
+           weekdays=[0, 2, 4],
+           is_active=True,
+       )
+
+       # Попытка генерировать уроки должна выбросить ValidationError
+       with pytest.raises(ValidationError) as exc_info:
+           RecurringLessonService.generate_lessons(recurring_lesson)
+
+       assert "не учит" in str(exc_info.value)
```

### Unified Diff
```diff
@@ -142,19 +142,83 @@ class TestRecurringLessonService:
                 is_active=True,
             )

-        lessons = RecurringLessonService.generate_lessons(recurring_lesson)
+        result = RecurringLessonService.generate_lessons(recurring_lesson)

-        assert len(lessons) > 0
+        assert result['total'] > 0
+        assert len(result['created']) > 0
         # Проверить что все уроки созданы правильно
-        for lesson in lessons:
+        for lesson in result['created']:
             assert lesson.teacher == teacher
             assert lesson.student == student
             assert lesson.subject == subject
             assert lesson.start_time == time(10, 0)
             assert lesson.end_time == time(11, 0)

+    def test_generate_lessons_without_enrollment_fails(self, teacher, student, subject):
+        """Тест что генерация уроков без валидного enrollment не допускается"""
+        # Не создаем enrollment - это основная проверка
+        recurring_lesson = RecurringLesson.objects.create(
+            teacher=teacher,
+            student=student,
+            subject=subject,
+            start_date=date.today() + timedelta(days=1),
+            end_date=date.today() + timedelta(days=30),
+            start_time=time(10, 0),
+            end_time=time(11, 0),
+            pattern="weekly",
+            interval=1,
+            weekdays=[0, 2, 4],
+            is_active=True,
+        )
+
+        # Попытка генерировать уроки должна выбросить ValidationError
+        with pytest.raises(ValidationError) as exc_info:
+            RecurringLessonService.generate_lessons(recurring_lesson)
+
+        assert "не учит" in str(exc_info.value)
+
+    def test_generate_lessons_with_inactive_enrollment_fails(self, teacher, student, subject):
+        """Тест что генерация уроков с неактивным enrollment не допускается"""
+        # Создаем неактивный enrollment
+        SubjectEnrollment.objects.create(
+            teacher=teacher,
+            student=student,
+            subject=subject,
+            is_active=False,  # НЕАКТИВНО
+        )
+
+        recurring_lesson = RecurringLesson.objects.create(
+            teacher=teacher,
+            student=student,
+            subject=subject,
+            start_date=date.today() + timedelta(days=1),
+            end_date=date.today() + timedelta(days=30),
+            start_time=time(10, 0),
+            end_time=time(11, 0),
+            pattern="weekly",
+            interval=1,
+            weekdays=[0, 2, 4],
+            is_active=True,
+        )
+
+        # Попытка генерировать уроки должна выбросить ValidationError
+        with pytest.raises(ValidationError) as exc_info:
+            RecurringLessonService.generate_lessons(recurring_lesson)
+
+        assert "не учит" in str(exc_info.value)

 @pytest.mark.django_db
 class TestSchedulingService:
```

---

## Summary of Changes

| File | Type | Lines Added | Lines Modified | Summary |
|------|------|-------------|-----------------|---------|
| `recurring_service.py` | Code | 18 | 0 | Added enrollment validation before bulk lesson creation |
| `tests_extended.py` | Tests | 68 | 27 | Modified 1 test, added 2 new tests for validation |
| **Total** | - | **86** | **27** | **Complete fix with comprehensive test coverage** |

---

## How to Apply This Fix

### Option 1: Manual Patch
```bash
cd backend
patch -p1 < TASK_SCHED_002.patch
```

### Option 2: Git
```bash
git add backend/scheduling/services/recurring_service.py
git add backend/scheduling/tests_extended.py
git commit -m "Fix T_SCHED_002: Prevent orphaned lessons via enrollment validation"
```

### Option 3: Direct Edit
1. Open `backend/scheduling/services/recurring_service.py`
2. Find `def generate_lessons(` (line 110)
3. After `raise ValidationError("Шаблон повторения неактивен")` (line 132)
4. Insert the 18-line enrollment validation block (lines 134-147)
5. Update tests in `backend/scheduling/tests_extended.py`

---

## Verification

```bash
# Run tests
cd backend
pytest scheduling/tests_extended.py::TestRecurringLessonService -v

# Expected output:
# test_create_recurring_lesson PASSED
# test_generate_lessons PASSED
# test_generate_lessons_without_enrollment_fails PASSED
# test_generate_lessons_with_inactive_enrollment_fails PASSED
```

---

## No Breaking Changes to:
- Method signature
- Return types
- Public API
- Database schema
- Configuration files

---

## Status: READY FOR COMMIT ✓

