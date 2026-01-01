# Инструкции по запуску тестирования Assignment & Submission Workflow

## Для QA Engineer / Tester

---

## Часть 1: Подготовка окружения

### Шаг 1: Убедитесь что Docker установлен
```bash
docker --version
docker-compose --version
```

Если не установлен:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# CentOS/RHEL
sudo yum install docker docker-compose

# macOS
brew install docker docker-compose
```

### Шаг 2: Запустите Docker daemon (если не запущен)
```bash
# Linux
sudo systemctl start docker
sudo systemctl enable docker

# macOS
open /Applications/Docker.app

# Windows
Start Docker Desktop application
```

### Шаг 3: Проверьте права доступа
```bash
# Проверьте что вы можете запускать docker без sudo
docker ps

# Если вы получили ошибку "permission denied", добавьте себя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

---

## Часть 2: Запуск приложения

### Шаг 1: Перейдите в корневую директорию проекта
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform
```

### Шаг 2: Проверьте что все файлы на месте
```bash
ls -la
# Должны быть:
# - docker-compose.yml
# - .env
# - backend/
# - frontend/
```

### Шаг 3: Запустите Docker Compose
```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL (port 5433)
- Redis (port 6379)
- Backend Django (port 8000)
- Frontend React (port 3000)

### Шаг 4: Дождитесь загрузки сервисов (1-2 минуты)
```bash
docker-compose ps
# Все статусы должны быть "Up"

# Или смотрите логи
docker-compose logs -f backend
```

### Шаг 5: Проверьте что сервисы работают
```bash
# Backend API
curl -s http://localhost:8000/api/system/health/ | python -m json.tool

# Frontend
curl -s http://localhost:3000/ | head -20
```

Ожидаемый результат:
```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected"
}
```

---

## Часть 3: Подготовка тестовых данных

### Шаг 1: Зайдите в backend контейнер
```bash
docker-compose exec backend bash
```

### Шаг 2: Запустите миграции (если нужно)
```bash
python manage.py migrate
```

### Шаг 3: Создайте тестовых пользователей
```bash
python manage.py shell

# В Python shell:
from django.contrib.auth import get_user_model
User = get_user_model()

# Создание учителя
teacher = User.objects.create_user(
    email='ivan.petrov@tutoring.com',
    password='password123',
    role='teacher',
    first_name='Ivan',
    last_name='Petrov'
)
print(f"Teacher created: {teacher.email}")

# Создание студентов
student1 = User.objects.create_user(
    email='anna.ivanova@student.com',
    password='password123',
    role='student',
    first_name='Anna',
    last_name='Ivanova'
)
print(f"Student 1 created: {student1.email}")

student2 = User.objects.create_user(
    email='dmitry.smirnov@student.com',
    password='password123',
    role='student',
    first_name='Dmitry',
    last_name='Smirnov'
)
print(f"Student 2 created: {student2.email}")

exit()
```

### Шаг 4: Выйдите из контейнера
```bash
exit
```

---

## Часть 4: Web UI Тестирование

### Открытие браузера
```
Frontend: http://localhost:3000
Backend API: http://localhost:8000/api/
```

### Логинитесь первый раз (как учитель)
1. Откройте http://localhost:3000
2. Нажмите "Login" или "Вход"
3. Email: ivan.petrov@tutoring.com
4. Password: password123
5. Нажмите "Sign In" или "Вход"

### Следуйте сценариям из TESTER_3_ASSIGNMENTS.md
- Сценарий 1: Создание задания
- Сценарий 2: Просмотр задания
- Сценарий 3: Отправка решения
- Сценарий 4: Проверка работ
- Сценарий 5: Просмотр оценки
- Сценарий 6: Дедлайн и опоздание
- Сценарий 7: Типы файлов

### Заполняйте таблицы результатов
На каждом шаге:
1. Выполните действие
2. Проверьте ожидаемый результат
3. Заполните "PASS" или "FAIL" в таблице
4. Если FAIL - снимите скриншот и опишите проблему

---

## Часть 5: API тестирование

### Вариант А: Запустить интеграционные тесты (Python)
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Установите зависимости (если нужно)
pip install pytest django djangorestframework

# Запустите тесты
pytest test_assignments_integration.py -v

# Результат должен быть:
# PASSED: test_create_assignment_basic
# PASSED: test_submit_assignment_with_content
# ...
```

### Вариант B: Ручное API тестирование (curl)

#### 1. Получите токен
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivan.petrov@tutoring.com",
    "password": "password123"
  }'

# Сохраните token из ответа
TOKEN="ваш_токен_здесь"
```

#### 2. Создайте задание
```bash
curl -X POST http://localhost:8000/api/assignments/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Домашняя работа: Уравнения",
    "description": "Решите 5 уравнений из учебника",
    "instructions": "Используйте методы",
    "type": "homework",
    "status": "published",
    "max_score": 100,
    "due_date": "2026-01-03T23:59:00Z",
    "start_date": "2026-01-01T00:00:00Z",
    "assigned_to": [2, 3]
  }'
```

#### 3. Отправьте решение
```bash
# Сначала получите студента token
STUDENT_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "anna.ivanova@student.com",
    "password": "password123"
  }' | grep -o '"token":"[^"]*' | cut -d'"' -f4)

# Отправьте решение
curl -X POST http://localhost:8000/api/submissions/ \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -F "assignment=1" \
  -F "student=2" \
  -F "content=Мое решение: 1) x=5, 2) x=10" \
  -F "file=@test_file.txt"
```

#### 4. Оцените работу
```bash
curl -X PATCH http://localhost:8000/api/submissions/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "score": 85,
    "feedback": "Хорошо решено, не хватает объяснений",
    "status": "graded"
  }'
```

---

## Часть 6: Просмотр логов

### Смотрите логи backend
```bash
# Все логи
docker-compose logs backend

# Последние логи (в режиме follow)
docker-compose logs -f backend

# Последние 50 строк
docker-compose logs --tail=50 backend
```

### Проверьте ошибки в базе данных
```bash
docker-compose exec backend bash
python manage.py shell

# В shell:
from assignments.models import Assignment
Assignment.objects.all().count()
# Должно показать количество созданных заданий
```

---

## Часть 7: Перезагрузка и очистка

### Перезагрузите контейнеры (если что-то зависло)
```bash
docker-compose restart
```

### Остановите приложение
```bash
docker-compose down
```

### Полная очистка (осторожно! удалит БД)
```bash
docker-compose down -v
# Потом снова запустите:
docker-compose up -d
```

---

## Часть 8: Решение проблем

### Problem 1: Порты уже заняты
```
Error: bind: address already in use
```

**Решение**:
```bash
# Найдите какой процесс занимает порт 8000
lsof -i :8000
# Или для 3000
lsof -i :3000

# Остановите процесс
kill -9 <PID>

# Или измените порт в docker-compose.yml
```

### Problem 2: Docker daemon не запущен
```
Cannot connect to the Docker daemon
```

**Решение**:
```bash
# Linux
sudo systemctl start docker

# macOS
open /Applications/Docker.app

# Проверьте
docker ps
```

### Problem 3: Недостаточно места на диске
```
no space left on device
```

**Решение**:
```bash
# Очистите старые контейнеры и образы
docker system prune -a

# Или просто очистите неиспользуемое
docker system prune
```

### Problem 4: Контейнер выходит с ошибкой
```bash
# Смотрите логи
docker-compose logs backend

# Перестройте образ
docker-compose build --no-cache
docker-compose up -d
```

### Problem 5: База данных не готова
```
Error connecting to database
```

**Решение**:
```bash
# Дождитесь пока БД стартует (может 1-2 минуты)
docker-compose logs postgres
# Когда появится "database system is ready to accept connections"

# Затем снова запустите backend
docker-compose up -d
```

---

## Часть 9: Документирование результатов

### После каждого тестирования
1. **Скриншоты**:
   - Сохраняйте в папку: `/home/mego/Python Projects/THE_BOT_platform/test_screenshots/`
   - Называйте: `scenario_X_step_Y.png`

2. **Обновляйте TESTER_3_ASSIGNMENTS.md**:
   - Меняйте "PENDING" на "PASS" или "FAIL"
   - Добавляйте комментарии

3. **Создавайте баг-репорты**:
   - Если FAIL, создайте файл: `BUG_REPORT_<ID>.md`
   - Включите: описание, шаги воспроизведения, скриншот, логи

### Пример баг-репорта
```markdown
# BUG_001: Невозможно загрузить большой файл

## Описание
При попытке загрузить файл размером >20MB система не показывает ошибку, файл просто не загружается.

## Шаги воспроизведения
1. Логин как student
2. Открыть задание
3. Нажать "Choose File"
4. Выбрать файл >20MB (например, 50MB)
5. Нажать "Submit"

## Ожидаемый результат
Файл должен загрузиться или показать понятную ошибку о лимите размера.

## Фактический результат
Файл не загружается, ошибка не показывается.

## Логи
```
[ERROR] File too large: 52428800 bytes (max: 20971520)
```

## Скриншот
[screenshot.png]
```

---

## Часть 10: Финальная сдача отчета

### Файлы которые должны быть
1. ✓ `TESTER_3_ASSIGNMENTS.md` - заполненный отчет с результатами
2. ✓ `test_assignments_integration.py` - интеграционные тесты
3. ✓ `ASSIGNMENTS_API_ANALYSIS.md` - анализ API
4. ✓ `test_screenshots/` - папка со скриншотами
5. ✓ `BUG_REPORTS/` - папка с баг-репортами (если найдены)

### Результаты тестирования должны содержать
- [ ] Все 7 сценариев протестированы
- [ ] Таблицы результатов заполнены
- [ ] PASS/FAIL статусы установлены
- [ ] Скриншоты прикреплены для важных функций
- [ ] Найденные баги задокументированы
- [ ] API тесты запущены и результаты записаны

---

## Чек-лист QA Engineer перед финальной сдачей

### Тестирование Web UI
- [ ] Сценарий 1 пройден (Создание задания)
- [ ] Сценарий 2 пройден (Просмотр задания)
- [ ] Сценарий 3 пройден (Отправка решения)
- [ ] Сценарий 4 пройден (Проверка работ)
- [ ] Сценарий 5 пройден (Просмотр оценки)
- [ ] Сценарий 6 пройден (Дедлайн)
- [ ] Сценарий 7 пройден (Типы файлов)

### Документация
- [ ] TESTER_3_ASSIGNMENTS.md заполнен
- [ ] Таблица результатов обновлена
- [ ] Проблемы описаны подробно
- [ ] Скриншоты сохранены

### API Тестирование
- [ ] test_assignments_integration.py запущен
- [ ] Результаты тестов записаны
- [ ] Curl команды протестированы вручную

### Финальная проверка
- [ ] Все файлы на месте
- [ ] Нет конфиденциальных данных в отчетах
- [ ] Отчет читаемый и структурированный

---

## Контакты и поддержка

Если у вас есть вопросы или проблемы:

1. **Проверьте логи**: `docker-compose logs backend`
2. **Перезагрузите**: `docker-compose restart`
3. **Проверьте подключение**: `curl http://localhost:8000/api/`
4. **Создайте issue** с полным описанием и логами

---

## Время выполнения

Ожидаемое время выполнения каждого сценария:
- Сценарий 1 (Создание): 5-10 минут
- Сценарий 2 (Просмотр): 3-5 минут
- Сценарий 3 (Отправка): 5-10 минут
- Сценарий 4 (Проверка): 10-15 минут
- Сценарий 5 (Оценка): 3-5 минут
- Сценарий 6 (Дедлайн): 10-15 минут
- Сценарий 7 (Файлы): 15-20 минут

**Итого**: 50-80 минут на Web UI тестирование
+ 20-30 минут на API тестирование
+ 15 минут на документирование

**Всего**: 85-125 минут (1.5-2 часа)

---

Удачи в тестировании!
