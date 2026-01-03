# Структура тестов THE_BOT_platform

## Организация по функциональным блокам

### 1. ACCOUNTS
- **Статус**: ✓ Готовы (373 PASSED)
- **Файлы**:
  - test_user_model_full.py - User модель (111 тестов)
  - test_profiles_full.py - StudentProfile, TeacherProfile, TutorProfile, ParentProfile (58 тестов)
  - test_user_serializer_full.py - UserSerializer
  - Старые тесты (исправлены и адаптированы)

### 2. SCHEDULING
- **Статус**: ✓ Готовы (220 PASSED)
- **Файлы**:
  - test_lesson_model_full.py - Lesson модель (87 тестов)
  - test_lesson_serializer_full.py - LessonSerializer
  - Старые тесты (12 исправлены)

### 3. MATERIALS
- **Статус**: ✓ Готовы (409+ PASSED)
- **Файлы**:
  - test_subject_model_full.py - Subject модель (59 тестов)
  - test_subject_enrollment_model_full.py - SubjectEnrollment (50 тестов)
  - Старые тесты (адаптированы)

### 4. ASSIGNMENTS
- **Статус**: ◐ В работе (409 PASSED, 132 FAILED, 47 ERROR)
- **Файлы**:
  - test_assignment_model_full.py - Assignment модель
  - test_submission_model_full.py - AssignmentSubmission (73 теста)
  - Старые тесты (адаптируются)

### 5. CHAT
- **Статус**: ◐ В работе (302 PASSED, 85 FAILED)
- **Файлы**:
  - test_chatroom_model_full.py - ChatRoom модель (45 тестов)
  - test_message_model_full.py - Message модель (69 тестов)
  - Старые тесты (адаптируются)

### 6. NOTIFICATIONS
- **Статус**: ◐ В работе (новые тесты готовы)
- **Файлы**:
  - test_notification_model_full.py - Notification модель (69 тестов)
  - test_template_model_full.py - NotificationTemplate (64 теста)
  - Старые тесты (адаптируются)

### 7. REPORTS
- **Статус**: ▢ Планируется
- **Файлы**:
  - test_report_model_full.py
  - test_report_schedule_full.py

## Методология

Каждый блок проходит цикл:
1. **Написание comprehensive тестов** для моделей
2. **Запуск тестов** и анализ ошибок
3. **Исправление** кода/моделей/factories под тесты
4. **Повтор** пока не будет 0 ошибок
5. **Документирование** структуры

## Factories

Все factories находятся в:
- /backend/tests/factories.py (основные)
- /backend/tests/unit/*/conftest.py (локальные fixtures)

## Запуск тестов

```bash
# Все тесты
pytest tests/unit/ -q

# По функциональному блоку
pytest tests/unit/accounts/ -q
pytest tests/unit/scheduling/ -q
pytest tests/unit/materials/ -q
pytest tests/unit/assignments/ -q
pytest tests/unit/chat/ -q
pytest tests/unit/notifications/ -q
pytest tests/unit/reports/ -q
```
