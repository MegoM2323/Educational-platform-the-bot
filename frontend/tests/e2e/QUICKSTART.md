# Быстрый старт - E2E Тесты взаимодействий пользователей

## Шаг 1: Установка зависимостей

```bash
cd frontend
npm install
npx playwright install
```

## Шаг 2: Подготовка тестовых пользователей

Убедитесь что в БД созданы тестовые пользователи с паролем `TestPass123!`:

- student@test.com
- teacher@test.com
- tutor@test.com
- parent@test.com
- admin@test.com

### Создание через Django shell:

```bash
cd backend
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, TeacherProfile, ParentProfile

User = get_user_model()

# Создать студента
student = User.objects.create_user(
    email='student@test.com',
    username='student',
    password='TestPass123!',
    first_name='Test',
    last_name='Student',
    role='student'
)
StudentProfile.objects.create(user=student, grade='10', goal='Подготовка к ЕГЭ')

# Создать учителя
teacher = User.objects.create_user(
    email='teacher@test.com',
    username='teacher',
    password='TestPass123!',
    first_name='Test',
    last_name='Teacher',
    role='teacher'
)

# Создать тьютора
tutor = User.objects.create_user(
    email='tutor@test.com',
    username='tutor',
    password='TestPass123!',
    first_name='Test',
    last_name='Tutor',
    role='tutor'
)

# Создать родителя
parent = User.objects.create_user(
    email='parent@test.com',
    username='parent',
    password='TestPass123!',
    first_name='Test',
    last_name='Parent',
    role='parent'
)
ParentProfile.objects.create(user=parent)

# Создать админа
admin = User.objects.create_user(
    email='admin@test.com',
    username='admin',
    password='TestPass123!',
    first_name='Admin',
    last_name='User',
    role='student',
    is_staff=True,
    is_superuser=True
)

print("Все тестовые пользователи созданы!")
```

## Шаг 3: Запуск серверов

### Терминал 1 - Backend
```bash
cd backend
source ../.venv/bin/activate
python manage.py runserver 8000
```

### Терминал 2 - Frontend
```bash
cd frontend
npm run dev -- --port 8080
```

## Шаг 4: Запуск тестов

```bash
cd frontend

# Запуск всех комплексных тестов взаимодействий
npm run test:e2e:interactions

# Запуск с видимым браузером (полезно для отладки)
npm run test:e2e:interactions:headed

# Запуск в режиме отладки (пошагово)
npm run test:e2e:interactions:debug

# Запуск в UI режиме Playwright
npm run test:e2e:ui
```

## Шаг 5: Просмотр результатов

```bash
# Открыть HTML отчет
npm run test:e2e:report
```

## Типичные проблемы

### 1. Ошибка "Backend недоступен"

**Проблема:** Backend сервер не запущен
**Решение:** Запустите backend на порту 8000

```bash
cd backend
python manage.py runserver 8000
```

### 2. Ошибка "Frontend недоступен"

**Проблема:** Frontend сервер не запущен
**Решение:** Запустите frontend на порту 8080

```bash
cd frontend
npm run dev -- --port 8080
```

### 3. Ошибка "User not found" при логине

**Проблема:** Тестовые пользователи не созданы
**Решение:** Выполните Шаг 2 (создание тестовых пользователей)

### 4. Ошибка "Timeout waiting for..."

**Проблема:** Слишком короткие таймауты
**Решение:**
1. Проверьте что серверы запущены и отвечают
2. Увеличьте таймауты в `playwright.config.ts`

### 5. Тесты падают на загрузке файлов

**Проблема:** Недостаточно прав для создания временных файлов
**Решение:** Проверьте права доступа к директории `/tmp/`

## Быстрая проверка работоспособности

Запустите только первый тест для быстрой проверки:

```bash
npx playwright test -g "Admin logs in"
```

Если этот тест проходит - значит все настроено правильно!

## Структура тестов

Тесты выполняются последовательно (serial) в следующем порядке:

1. **Admin Flow** - Создание структуры платформы
2. **Tutor Flow** - Управление студентами
3. **Teacher Flow** - Работа с материалами и заданиями
4. **Student Flow** - Взаимодействие с контентом
5. **Parent Flow** - Мониторинг и оплата
6. **Cross-User** - Проверка файловых взаимодействий

Каждая группа тестов независима и может запускаться отдельно.

## Полезные команды

```bash
# Только Chrome
npx playwright test --project=chromium tests/e2e/user-interactions.spec.ts

# Только Firefox
npx playwright test --project=firefox tests/e2e/user-interactions.spec.ts

# Запуск конкретной группы тестов
npx playwright test -g "Teacher Flow"

# Запуск с максимальной детализацией логов
DEBUG=pw:api npx playwright test tests/e2e/user-interactions.spec.ts

# Просмотр трейса последнего запуска
npx playwright show-trace test-results/*/trace.zip
```

## Следующие шаги

После успешного запуска тестов:

1. Изучите отчет в HTML формате
2. Просмотрите скриншоты неудачных тестов
3. Посмотрите видео записи тестов
4. Добавьте дополнительные проверки в существующие тесты
5. Создайте новые тесты для специфичных сценариев

## Полная документация

Подробная документация находится в файле [README.md](./README.md)
