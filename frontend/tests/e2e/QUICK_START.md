# Quick Start - E2E Тесты Admin Panel

Быстрый старт для запуска E2E тестов Django Admin Panel.

## Подготовка (одноразово)

### 1. Установка Playwright

```bash
cd frontend
npm install
npx playwright install
```

### 2. Создание админ пользователя

```bash
cd backend
source ../.venv/bin/activate
python manage.py createsuperuser
```

Введите credentials:
- **Email:** `admin@example.com`
- **Password:** `admin123`

### 3. Запуск Django сервера

```bash
# Из корня проекта
./start.sh
```

Или вручную:
```bash
cd backend
source ../.venv/bin/activate
python manage.py runserver 8000
```

## Запуск тестов

### Основные команды

```bash
# Все админ тесты
npm run test:e2e:admin:all

# Только основные тесты
npm run test:e2e:admin

# Только интеграционные тесты
npm run test:e2e:admin:integration

# С визуальным интерфейсом
npm run test:e2e:ui

# С отображением браузера
npm run test:e2e:headed

# Просмотр отчета
npm run test:e2e:report
```

### Расширенные команды

```bash
# Конкретный браузер
npx playwright test tests/e2e/admin-panel.spec.ts --project=chromium

# Конкретный тест
npx playwright test -g "Admin can login"

# Debug режим
npx playwright test tests/e2e/admin-panel.spec.ts --debug

# Параллельные воркеры
npx playwright test tests/e2e/admin-panel.spec.ts --workers=4
```

## Что тестируется

### ✅ admin-panel.spec.ts (40+ тестов)
- Аутентификация
- CRUD пользователей (Student, Teacher, Tutor, Parent)
- Создание и управление предметами
- Зачисление студентов
- Поиск и фильтры
- UI/UX и стили
- Права доступа
- Массовые операции

### ✅ admin-panel-integration.spec.ts (10+ тестов)
- Полные workflow
- Обработка ошибок
- Валидация данных
- Bulk операции

## Структура результатов

```
playwright-report/          # HTML отчет
test-results/               # Скриншоты, видео, трейсы
  ├── screenshots/
  ├── videos/
  └── traces/
```

## Troubleshooting

### Тесты не запускаются

1. Проверьте Django сервер:
   ```bash
   curl http://localhost:8000/admin/
   ```

2. Проверьте credentials:
   ```bash
   cd backend
   python manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> User.objects.filter(email='admin@example.com').exists()
   ```

3. Переустановите Playwright:
   ```bash
   npx playwright install --force
   ```

### Тесты падают с timeout

1. Увеличьте timeout в `playwright.config.ts`:
   ```typescript
   timeout: 60 * 1000, // 60 секунд
   ```

2. Проверьте загрузку сервера:
   ```bash
   # Должен вернуть 200 OK
   curl -I http://localhost:8000/admin/
   ```

### CSS не загружается

```bash
cd backend
python manage.py collectstatic --noinput
```

## Полезные ссылки

- Полная документация: `ADMIN_TESTS_README.md`
- Helper функции: `helpers/admin-helpers.ts`
- Playwright документация: https://playwright.dev/

## Быстрый тест

Проверка, что все работает:

```bash
# 1. Запустите Django
./start.sh

# 2. В новом терминале
cd frontend
npm run test:e2e:admin -- -g "Admin can login"
```

Если тест прошел ✅ - все настроено правильно!

## Следующие шаги

1. Прочитайте `ADMIN_TESTS_README.md` для полной документации
2. Изучите `helpers/admin-helpers.ts` для переиспользования функций
3. Добавьте свои тесты, используя существующие паттерны

---

**Вопросы?** Проверьте `ADMIN_TESTS_README.md` раздел "Troubleshooting"
