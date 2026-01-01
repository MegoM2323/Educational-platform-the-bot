# Assignment & Submission Workflow - Подробный анализ API

## Обзор системы

THE_BOT Platform содержит полнофункциональную систему управления заданиями с поддержкой:
- Создания и управления заданиями
- Отправки решений студентами
- Оценивания работ учителями
- Отслеживания опозданий
- Версионирования отправок
- Плагиат-детекции
- Комментариев и обратной связи

---

## Структура базы данных

### Основные модели

```python
# assignment/models.py

class Assignment(models.Model):
    """Задание для студентов"""
    title: CharField(200)
    description: TextField
    instructions: TextField
    author: ForeignKey(User)  # Учитель

    # Типы и статусы
    type: CharField(choices=['homework', 'test', 'project', 'essay', 'practical'])
    status: CharField(choices=['draft', 'published', 'closed'])

    # Оценивание
    max_score: PositiveInteger = 100
    attempts_limit: PositiveInteger = 1

    # Назначение студентам
    assigned_to: ManyToMany(User)

    # Сроки
    start_date: DateTime
    due_date: DateTime  # Основной дедлайн
    late_submission_deadline: DateTime (nullable)

    # Штраф за опоздание
    late_penalty_type: CharField(choices=['percentage', 'fixed_points'])
    late_penalty_value: Decimal

    # Метаданные
    tags: CharField(500)
    difficulty_level: PositiveInteger (1-5)

    # Временные метки
    created_at: DateTime (auto_now_add)
    updated_at: DateTime (auto_now)


class AssignmentSubmission(models.Model):
    """Отправленное решение"""
    assignment: ForeignKey(Assignment)
    student: ForeignKey(User)

    # Содержимое
    content: TextField  # Текстовый ответ
    file: FileField (upload_to="assignments/submissions/")  # Загруженный файл

    # Статус
    status: CharField(choices=['submitted', 'graded', 'returned'])

    # Опоздание
    is_late: Boolean = False
    days_late: Decimal = 0
    penalty_applied: Decimal (nullable)

    # Оценка (установляется после проверки)
    score: PositiveInteger (nullable)
    max_score: PositiveInteger (nullable)
    feedback: TextField (пустое по умолчанию)

    # Временные метки
    submitted_at: DateTime (auto_now_add)
    graded_at: DateTime (nullable)
    updated_at: DateTime (auto_now)

    class Meta:
        unique_together = ["assignment", "student"]  # Один submission на студента!


class SubmissionFeedback(models.Model):
    """Обратная связь к отправке"""
    submission: ForeignKey(AssignmentSubmission)
    teacher: ForeignKey(User)
    comment: TextField
    is_published: Boolean
    created_at: DateTime


class SubmissionVersion(models.Model):
    """История версий отправок"""
    submission: ForeignKey(AssignmentSubmission)
    version_number: PositiveInteger
    content: TextField
    file: FileField
    created_at: DateTime


class StudentDeadlineExtension(models.Model):
    """Расширение дедлайна для отдельного студента"""
    assignment: ForeignKey(Assignment)
    student: ForeignKey(User)
    extended_due_date: DateTime
    reason: TextField
    created_at: DateTime


class SubmissionExemption(models.Model):
    """Освобождение от задания"""
    assignment: ForeignKey(Assignment)
    student: ForeignKey(User)
    reason: TextField
    created_at: DateTime
```

---

## API Endpoints

### Assignment Management

#### GET /api/assignments/
**Получить список заданий**
- Фильтры: status, type, author, difficulty_level
- Pagination: page, page_size
- Ordering: created_at, due_date, title

```json
GET /api/assignments/?status=published
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Домашняя работа: Уравнения",
      "description": "Решите 5 уравнений",
      "type": "homework",
      "status": "published",
      "max_score": 100,
      "due_date": "2026-01-03T23:59:00Z",
      "author": {
        "id": 1,
        "email": "ivan.petrov@tutoring.com",
        "first_name": "Ivan"
      },
      "assigned_to": [2, 3, 4],
      "created_at": "2026-01-01T12:00:00Z"
    }
  ]
}
```

#### POST /api/assignments/
**Создать новое задание**
- Требует authentication + teacher/admin role

```json
POST /api/assignments/
{
  "title": "Домашняя работа: Уравнения",
  "description": "Решите 5 уравнений из учебника",
  "instructions": "Используйте методы подстановки или исключения",
  "type": "homework",
  "status": "draft",
  "max_score": 100,
  "due_date": "2026-01-03T23:59:00Z",
  "start_date": "2026-01-01T00:00:00Z",
  "assigned_to": [2, 3],
  "attempts_limit": 1,
  "difficulty_level": 2,
  "tags": "equations,homework",
  "late_submission_deadline": "2026-01-05T23:59:00Z",
  "late_penalty_type": "percentage",
  "late_penalty_value": 10.0
}

Response: 201 Created
{
  "id": 1,
  "title": "Домашняя работа: Уравнения",
  ...
}
```

#### GET /api/assignments/{id}/
**Получить детали задания**

#### PATCH /api/assignments/{id}/
**Обновить задание**
- Требует прав (автор или admin)

#### DELETE /api/assignments/{id}/
**Удалить задание**
- Требует прав (автор или admin)

---

### Submission Management

#### POST /api/submissions/
**Отправить решение**
- Требует authentication + student role
- Content-Type: multipart/form-data (если есть файл)

```json
POST /api/submissions/
Content-Type: multipart/form-data

{
  "assignment": 1,
  "student": 2,
  "content": "Решение: 1) x=5, 2) x=10, ...",
  "file": <binary file data>
}

Response: 201 Created
{
  "id": 1,
  "assignment": 1,
  "student": 2,
  "content": "Решение: ...",
  "file": "/media/assignments/submissions/solution_v1.txt",
  "status": "submitted",
  "submitted_at": "2026-01-01T14:30:00Z",
  "is_late": false,
  "score": null,
  "feedback": ""
}
```

#### GET /api/submissions/
**Получить список отправок**
- Фильтры: assignment, student, status, is_late
- Только автор задания, студент или admin могут видеть

```json
GET /api/submissions/?assignment=1
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "student": {
        "id": 2,
        "email": "anna.ivanova@student.com"
      },
      "status": "submitted",
      "submitted_at": "2026-01-01T14:30:00Z",
      "is_late": false
    }
  ]
}
```

#### GET /api/submissions/{id}/
**Получить детали отправки**

#### PATCH /api/submissions/{id}/
**Обновить отправку (оценить)**
- Требует прав учителя/автора
- Используется для выставления оценок

```json
PATCH /api/submissions/1/
{
  "score": 85,
  "feedback": "Хорошо решено, не хватает объяснений",
  "status": "graded"
}

Response: 200 OK
{
  "id": 1,
  "score": 85,
  "feedback": "Хорошо решено...",
  "status": "graded",
  "graded_at": "2026-01-01T15:00:00Z",
  "percentage": 85.0
}
```

#### DELETE /api/submissions/{id}/
**Удалить отправку**

---

### Comments (Комментарии)

#### POST /api/submissions/{submission_id}/comments/
**Добавить комментарий к отправке**

```json
POST /api/submissions/1/comments/
{
  "comment": "Хорошо решено, но проверьте вычисления",
  "is_published": false
}

Response: 201 Created
{
  "id": 1,
  "submission": 1,
  "author": {
    "id": 1,
    "email": "ivan.petrov@tutoring.com"
  },
  "comment": "Хорошо решено...",
  "is_published": false,
  "created_at": "2026-01-01T15:05:00Z"
}
```

#### POST /api/submissions/{submission_id}/comments/{id}/publish/
**Опубликовать комментарий**
- Делает комментарий видным для студента

```json
POST /api/submissions/1/comments/1/publish/
{
  "is_published": true
}
```

---

## Workflow-ы и сценарии

### Сценарий 1: Учитель создает и опубликовывает задание

```
1. POST /api/assignments/
   {
     "title": "...",
     "status": "draft",
     ...
   }

2. PATCH /api/assignments/{id}/
   {
     "status": "published",
     "assigned_to": [2, 3, 4]
   }

3. GET /api/assignments/{id}/
   (проверить что опубликовано)
```

### Сценарий 2: Студент отправляет решение

```
1. GET /api/assignments/{id}/
   (посмотреть детали задания)

2. POST /api/submissions/
   {
     "assignment": {id},
     "student": {student_id},
     "content": "...",
     "file": <binary>
   }

3. GET /api/submissions/?assignment={id}&student={id}
   (проверить что отправлено)
```

### Сценарий 3: Учитель оценивает работу

```
1. GET /api/submissions/?assignment={id}
   (получить все отправки)

2. GET /api/submissions/{submission_id}/
   (посмотреть детали отправки)

3. POST /api/submissions/{submission_id}/comments/
   {
     "comment": "...",
     "is_published": false
   }

4. PATCH /api/submissions/{submission_id}/
   {
     "score": 85,
     "feedback": "...",
     "status": "graded"
   }

5. POST /api/submissions/{submission_id}/comments/{comment_id}/publish/
   (опубликовать комментарии для студента)
```

### Сценарий 4: Студент смотрит оценку

```
1. GET /api/assignments/{id}/
   (посмотреть детали задания)

2. GET /api/submissions/?assignment={id}&student={student_id}
   (получить свою отправку с оценкой)

3. GET /api/submissions/{id}/comments/
   (получить комментарии учителя)
```

---

## Важные особенности

### 1. Уникальность отправок
```python
unique_together = ["assignment", "student"]
```
- Студент может отправить только ONE submission на задание
- Переотправка ПЕРЕПИСЫВАЕТ предыдущую отправку (или создает версию)
- Версионирование отслеживается в SubmissionVersion

### 2. Автоматические временные метки
```python
submitted_at = models.DateTimeField(auto_now_add=True)  # Устанавливается при создании
graded_at = models.DateTimeField(blank=True, null=True)  # При первой оценке
```

### 3. Определение опоздания
```python
is_late = submission.submitted_at > assignment.due_date
days_late = (submission.submitted_at - assignment.due_date).days
```

### 4. Вычисляемые поля
```python
@property
def percentage(self):
    if self.max_score and self.score is not None:
        return round((self.score / self.max_score) * 100, 2)
    return None
```

### 5. Файловое хранилище
```python
file = models.FileField(
    upload_to="assignments/submissions/",
    blank=True,
    null=True
)
# Файлы сохраняются в: /media/assignments/submissions/{filename}
```

---

## Валидация и ограничения

### Assignment
- `title` - обязательное, max_length=200
- `description` - обязательное
- `instructions` - обязательное
- `due_date` - обязательное, должно быть > start_date
- `max_score` - обязательное, default=100
- `assigned_to` - может быть пусто (draft задание)
- `status` - обязательное, choices=['draft', 'published', 'closed']

### AssignmentSubmission
- `assignment` - обязательное
- `student` - обязательное
- `submitted_at` - устанавливается автоматически
- `content` или `file` - хотя бы одно должно быть заполнено
- `status` - обязательное, choices=['submitted', 'graded', 'returned']
- `score` - nullable, должно быть >= 0
- `unique_together`: [assignment, student]

---

## Permissions (Разрешения)

### Assignment Creation
- ✓ Teacher может создавать
- ✓ Admin может создавать
- ✗ Student не может создавать

### Assignment Update
- ✓ Автор (учитель) может обновлять
- ✓ Admin может обновлять
- ✗ Другие не могут

### Submission Creation
- ✓ Student может отправлять на назначенное ему задание
- ✓ Teacher может создавать submission для студента (admin)
- ✗ Student не может отправлять на не назначенное задание

### Submission Grading
- ✓ Автор задания (учитель) может оценивать
- ✓ Admin может оценивать
- ✗ Student не может оценивать

### Viewing Submissions
- ✓ Автор задания видит все submissions
- ✓ Student видит только свой submission
- ✓ Admin видит все

---

## Обработка файлов

### Поддерживаемые типы
- Text: .txt, .md, .doc, .docx
- Code: .py, .java, .js, .cpp, .c
- Spreadsheets: .xls, .xlsx, .csv
- Documents: .pdf
- Images: .jpg, .jpeg, .png, .gif, .bmp
- Archives: .zip, .rar, .7z

### Валидация (из models/serializers)
- Максимальный размер: обычно 50MB (настраивается)
- Расширения: могут быть ограничены в settings
- Антивирус-сканирование: опционально через webhooks

### Путь сохранения
```
/media/assignments/submissions/{filename}
```

Примеры:
- `/media/assignments/submissions/solution_20260101_143000.pdf`
- `/media/assignments/submissions/task_answer.docx`

---

## Статистика и аналитика

### Доступные метрики
- Общее количество отправок по заданию
- Процент студентов, отправивших решение
- Среднее время до отправки
- Средний балл
- Количество опозданий

### Endpoints для статистики
```
GET /api/assignments/{id}/statistics/
GET /api/assignments/{id}/submission_statistics/
```

---

## Error Handling

### Возможные ошибки

| Код | Описание | Решение |
|-----|---------|---------|
| 400 | Bad Request (неверные данные) | Проверить JSON |
| 401 | Unauthorized (не авторизован) | Авторизоваться |
| 403 | Forbidden (нет прав) | Проверить роль |
| 404 | Not Found (ресурс не найден) | Проверить ID |
| 409 | Conflict (конфликт) | Например, duplicate submission |
| 413 | Payload Too Large (файл слишком большой) | Уменьшить файл |
| 415 | Unsupported Media Type | Проверить content-type |
| 500 | Server Error | Посмотреть логи |

---

## Примеры запросов (curl)

### Создание задания
```bash
curl -X POST http://localhost:8000/api/assignments/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Домашняя работа",
    "description": "Test",
    "instructions": "Test",
    "type": "homework",
    "status": "published",
    "max_score": 100,
    "due_date": "2026-01-03T23:59:00Z",
    "start_date": "2026-01-01T00:00:00Z",
    "assigned_to": [2, 3]
  }'
```

### Отправка решения с файлом
```bash
curl -X POST http://localhost:8000/api/submissions/ \
  -H "Authorization: Bearer {token}" \
  -F "assignment=1" \
  -F "student=2" \
  -F "content=Мое решение" \
  -F "file=@solution.pdf"
```

### Оценка работы
```bash
curl -X PATCH http://localhost:8000/api/submissions/1/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "score": 85,
    "feedback": "Хорошо!",
    "status": "graded"
  }'
```

---

## Заметки для тестирования

1. **Временные зоны**: Все даты в UTC, но отображаются в местном времени браузера
2. **Файлы**: Требуют Content-Type при загрузке
3. **Permissions**: Проверяются на уровне viewsets
4. **Версионирование**: Может быть не явным - проверить в модели
5. **Кэширование**: Результаты могут быть кэшированы (Redis)
6. **Асинхронные задачи**: Плагиат-проверка может быть в фоне (Celery)

