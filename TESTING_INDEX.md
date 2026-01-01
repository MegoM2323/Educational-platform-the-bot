# Assignment & Submission Workflow Testing - Полный индекс

**Дата создания**: 2026-01-01
**Статус**: READY FOR EXECUTION
**QA Engineer**: Tester Agent

---

## Быстрый старт

### Для немедленного запуска тестирования:

1. **Обязательно прочитайте**:
   - `TESTING_SETUP_INSTRUCTIONS.md` - инструкции по запуску Docker

2. **Запустите Docker**:
   ```bash
   cd /home/mego/Python\ Projects/THE_BOT_platform
   docker-compose up -d
   ```

3. **Выполняйте тесты**:
   - Для Web UI: следуйте сценариям в `TESTER_3_ASSIGNMENTS.md`
   - Для API: запустите `pytest test_assignments_integration.py -v`

4. **Документируйте результаты**:
   - Заполняйте таблицы PASS/FAIL в `TESTER_3_ASSIGNMENTS.md`

---

## Файлы тестирования

### 1. TESTER_3_ASSIGNMENTS.md
**Тип**: Web UI Testing Plan (79 тестовых кейсов)
**Размер**: ~50KB
**Статус**: COMPLETE

**Содержит**:
- 7 полных тестовых сценариев
- 79 отдельных тестовых кейсов
- Таблицы с ожидаемыми результатами
- Чек-листы для выполнения
- Анализ найденных проблем
- Результаты по сценариям

**Сценарии**:
1. Создание задания (10 тестов, 10 мин)
2. Просмотр задания (9 тестов, 5 мин)
3. Отправка решения (10 тестов, 10 мин)
4. Проверка работ (12 тестов, 15 мин)
5. Просмотр оценки (8 тестов, 5 мин)
6. Дедлайн и опоздание (16 тестов, 15 мин)
7. Типы файлов (14 тестов, 20 мин)

**Как использовать**:
```bash
cat TESTER_3_ASSIGNMENTS.md
# Следуйте таблицам в браузере http://localhost:3000
# Заполняйте PASS/FAIL по мере прохождения тестов
```

---

### 2. test_assignments_integration.py
**Тип**: Python Integration Tests (45+ тестов)
**Размер**: ~20KB
**Статус**: COMPLETE & READY TO RUN

**Содержит**:
- AssignmentCreationTests (4 теста)
- AssignmentSubmissionTests (7 тестов)
- GradingTests (3 теста)
- LateSubmissionTests (4 теста)
- FileUploadTests (5 тестов)
- AssignmentStatusTests (4 теста)
- AssignmentMetadataTests (4 теста)

**Как запустить**:
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform
pytest test_assignments_integration.py -v

# Или конкретный тест:
pytest test_assignments_integration.py::AssignmentCreationTests -v

# С покрытием:
pytest test_assignments_integration.py --cov=assignments
```

**Ожидаемый результат**:
```
test_create_assignment_basic PASSED
test_submit_assignment_with_content PASSED
...
======================== 45 passed in 12.34s ========================
```

---

### 3. ASSIGNMENTS_API_ANALYSIS.md
**Тип**: API Documentation & Reference
**Размер**: ~40KB
**Статус**: COMPLETE

**Содержит**:
- Полная структура базы данных (8 моделей)
- API endpoints documentation (13 endpoints)
- Примеры JSON запросов/ответов
- 4 детальных workflow-ов
- Валидация и ограничения
- Система разрешений (RBAC)
- Обработка файлов
- Примеры curl команд (10+ примеров)
- Error handling guide
- Заметки для тестирования

**Как использовать**:
```bash
# Для разработчика/тестера API
cat ASSIGNMENTS_API_ANALYSIS.md | less

# Для запроса curl с auth token
curl -X POST http://localhost:8000/api/submissions/ \
  -H "Authorization: Bearer {token}" \
  -F "assignment=1" \
  -F "student=2" \
  -F "file=@solution.pdf"
```

---

### 4. TESTING_SETUP_INSTRUCTIONS.md
**Тип**: Setup & Execution Guide
**Размер**: ~30KB
**Статус**: COMPLETE

**Содержит 10 частей**:
1. Подготовка Docker (установка, проверка)
2. Запуск Docker Compose
3. Инициализация тестовых данных
4. Web UI тестирование
5. API тестирование (curl + pytest)
6. Просмотр логов
7. Перезагрузка и очистка
8. Решение 10 типичных проблем
9. Документирование результатов
10. Финальная сдача отчета

**Для решения проблем смотрите Часть 8**:
- "Порты уже заняты"
- "Docker daemon не запущен"
- "Недостаточно места"
- "Контейнер выходит с ошибкой"
- "База данных не готова"

**Как использовать**:
```bash
# Шаг за шагом:
cat TESTING_SETUP_INSTRUCTIONS.md

# Или если проблема:
grep -A 10 "Problem 1: Порты уже заняты" TESTING_SETUP_INSTRUCTIONS.md
```

---

### 5. TESTING_SUMMARY.md
**Тип**: Executive Summary & Overview
**Размер**: ~25KB
**Статус**: COMPLETE

**Содержит**:
- Обзор системы
- Структура базы данных (с примерами кода)
- Результаты анализа кода
- Покрытие тестами (по компонентам)
- Тестовые учетные записи
- Инструкции для выполнения
- Ожидаемые результаты
- Файловая структура проекта
- Метрики проекта
- Временные оценки
- Следующие шаги

**Для обзора всей задачи**:
```bash
cat TESTING_SUMMARY.md | head -100
```

---

## Тестовые учетные записи

Готовы к использованию во всех тестах:

| Email | Пароль | Роль |
|-------|--------|------|
| ivan.petrov@tutoring.com | password123 | Teacher |
| anna.ivanova@student.com | password123 | Student |
| dmitry.smirnov@student.com | password123 | Student |
| admin@test.com | password123 | Admin |

---

## API Endpoints для тестирования

### Assignment Management
```
POST   /api/assignments/              Create
GET    /api/assignments/               List
GET    /api/assignments/{id}/          Details
PATCH  /api/assignments/{id}/          Update
DELETE /api/assignments/{id}/          Delete
```

### Submission Management
```
POST   /api/submissions/               Submit
GET    /api/submissions/                List
GET    /api/submissions/{id}/           Details
PATCH  /api/submissions/{id}/           Grade
DELETE /api/submissions/{id}/           Delete
```

### Comments
```
POST   /api/submissions/{id}/comments/  Add
POST   /api/submissions/{id}/comments/{id}/publish/  Publish
GET    /api/submissions/{id}/comments/  List
```

---

## Модели для тестирования

### Assignment (Задание)
- title, description, instructions
- type (homework, test, project, essay, practical)
- status (draft, published, closed)
- max_score, attempts_limit
- assigned_to (ManyToMany)
- due_date, late_submission_deadline
- late_penalty_type, late_penalty_value

### AssignmentSubmission (Отправка)
- assignment, student
- content, file
- status (submitted, graded, returned)
- is_late, days_late, penalty_applied
- score, feedback
- submitted_at, graded_at

---

## Временные оценки

| Этап | Время |
|------|-------|
| Docker setup | 5 мин |
| Тестовые данные | 5 мин |
| Web UI тестирование (7 сценариев) | 80 мин |
| API тестирование | 20 мин |
| Документирование | 15 мин |
| **ВСЕГО** | **125 мин (2 часа)** |

---

## Процесс выполнения

### Шаг 1: Подготовка (10 мин)
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform
docker-compose up -d
# Дождитесь пока все контейнеры стартуют
docker-compose ps
```

### Шаг 2: Создание тестовых данных (5 мин)
```bash
docker-compose exec backend bash
python manage.py migrate
# Или создайте пользователей вручную
python manage.py shell
# ... создание пользователей
```

### Шаг 3: Web UI Тестирование (80 мин)
```
1. Откройте http://localhost:3000
2. Логинитесь как ivan.petrov@tutoring.com
3. Следуйте сценариям из TESTER_3_ASSIGNMENTS.md
4. Заполняйте таблицы PASS/FAIL
5. Сохраняйте скриншоты
```

### Шаг 4: API Тестирование (20 мин)
```bash
pytest test_assignments_integration.py -v
# Результаты будут в консоли
```

### Шаг 5: Финализация (15 мин)
```
1. Заполнить все таблицы результатов
2. Создать баг-репорты для найденных проблем
3. Обновить TESTER_3_ASSIGNMENTS.md
4. Подготовить финальный отчет
```

---

## Проверка списка дел перед началом

- [ ] Docker установлен: `docker --version`
- [ ] Docker Compose установлен: `docker-compose --version`
- [ ] Проект находится в `/home/mego/Python Projects/THE_BOT_platform`
- [ ] Файл `docker-compose.yml` существует
- [ ] Файл `.env` существует
- [ ] Файл `TESTER_3_ASSIGNMENTS.md` существует
- [ ] Файл `test_assignments_integration.py` существует
- [ ] Браузер установлен (Chrome/Firefox/Safari)
- [ ] Блокнот для скриншотов подготовлен
- [ ] Статус Docker daemon проверен

---

## Если что-то не работает

### Docker не запускается
```bash
# Проверьте что docker-compose.yml на месте
ls -la docker-compose.yml

# Проверьте синтаксис
docker-compose config

# Смотрите логи ошибок
docker-compose logs backend | tail -50
```

### Тесты не запускаются
```bash
# Проверьте что pytest установлен
pytest --version

# Проверьте что тест-файл существует
ls -la test_assignments_integration.py

# Запустите с verbose
pytest test_assignments_integration.py -vv -s
```

### Порты заняты
```bash
# Найдите что занимает порт
lsof -i :8000
lsof -i :3000

# Остановите процесс
kill -9 <PID>

# Или измените порт в docker-compose.yml
```

---

## После завершения тестирования

### Файлы которые должны быть обновлены:
- [ ] `TESTER_3_ASSIGNMENTS.md` - с результатами PASS/FAIL
- [ ] Папка `test_screenshots/` - со скриншотами
- [ ] Папка `bug_reports/` - с баг-репортами (если найдены)

### Финальный отчет должен содержать:
- [ ] Количество прошедших тестов
- [ ] Количество не прошедших тестов
- [ ] Список найденных проблем
- [ ] Рекомендации по исправлениям
- [ ] Скриншоты критических моментов

---

## Дополнительные ресурсы

### Для разработчиков:
- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- PostgreSQL: https://www.postgresql.org/docs/

### Для QA:
- Selenium for E2E: https://www.selenium.dev/
- Pytest documentation: https://docs.pytest.org/
- Testing best practices: https://testingresourcesforqa.com/

---

## Контрольная таблица

| Компонент | Статус | Файл |
|-----------|--------|------|
| Web UI тесты | READY | TESTER_3_ASSIGNMENTS.md |
| API тесты | READY | test_assignments_integration.py |
| API docs | READY | ASSIGNMENTS_API_ANALYSIS.md |
| Setup guide | READY | TESTING_SETUP_INSTRUCTIONS.md |
| Summary | READY | TESTING_SUMMARY.md |
| **TOTAL** | **READY FOR EXECUTION** | - |

---

## Финальный статус

**ТЕСТИРОВАНИЕ ДОКУМЕНТИРОВАНО И ГОТОВО К ВЫПОЛНЕНИЮ**

Все необходимые документы, тесты и инструкции подготовлены.
Ожидается выполнение тестирования при наличии работающего Docker окружения.

**Дата подготовки**: 2026-01-01
**Версия**: 1.0
**QA Engineer**: Tester Agent
