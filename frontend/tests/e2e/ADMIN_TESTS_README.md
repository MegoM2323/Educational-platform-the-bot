# E2E Тесты Django Admin Panel

Полное покрытие E2E тестами для Django Admin панели с проверкой создания пользователей, предметов и зачислений через веб-интерфейс.

## Структура файлов

```
frontend/tests/e2e/
├── admin-panel.spec.ts                 # Основные тесты админ панели
├── admin-panel-integration.spec.ts     # Интеграционные тесты
├── helpers/
│   └── admin-helpers.ts                # Helper функции для переиспользования
└── ADMIN_TESTS_README.md              # Эта документация
```

## Тестовое покрытие

### `admin-panel.spec.ts` - Основные тесты

#### 1. **Authentication (Аутентификация)**
- ✅ Вход в админ панель с валидными credentials
- ✅ Проверка навигации после логина
- ✅ Отображение ошибки при неверных credentials
- ✅ Выход из системы

#### 2. **User Management (Управление пользователями)**
- ✅ Создание нового тьютора
- ✅ Создание нового преподавателя
- ✅ Создание нового студента
- ✅ Создание нового родителя
- ✅ Редактирование существующего пользователя
- ✅ Удаление пользователя

#### 3. **Subject Management (Управление предметами)**
- ✅ Создание нового предмета
- ✅ Назначение преподавателя на предмет

#### 4. **Enrollment Management (Управление зачислениями)**
- ✅ Доступ к странице зачислений
- ✅ Просмотр формы зачисления

#### 5. **File Upload (Загрузка файлов)**
- ✅ Доступ к странице материалов
- ✅ Просмотр формы загрузки материала
- ⏭️ Загрузка PDF файла (пропущен, требует тестовый файл)

#### 6. **Search and Filter (Поиск и фильтры)**
- ✅ Поиск пользователей
- ✅ Фильтрация пользователей по ролям

#### 7. **UI/UX**
- ✅ Проверка корректности стилей админ панели
- ✅ Загрузка всех статических файлов
- ✅ Отзывчивость интерфейса (responsive)
- ✅ Работа breadcrumbs навигации

#### 8. **Permissions (Права доступа)**
- ✅ Доступ админа ко всем разделам
- ✅ Доступ к странице редактирования пользователя

#### 9. **Bulk Actions (Массовые операции)**
- ✅ Выбор нескольких пользователей
- ✅ Отображение dropdown массовых действий

### `admin-panel-integration.spec.ts` - Интеграционные тесты

#### 1. **Complete Workflows (Полные рабочие процессы)**
- ✅ Создание преподавателя → предмета → назначение
- ✅ Создание студента, родителя, тьютора → зачисление
- ✅ Создание нескольких студентов → зачисление на один предмет
- ✅ Создание преподавателя → назначение на несколько предметов

#### 2. **Error Handling (Обработка ошибок)**
- ✅ Невозможность создать дубликат пользователя с одинаковым email
- ✅ Невозможность дважды назначить преподавателя на один предмет

#### 3. **Data Validation (Валидация данных)**
- ✅ Валидация обязательных полей пользователя
- ✅ Валидация обязательного имени предмета

#### 4. **Bulk Operations (Массовые операции)**
- ✅ Удаление нескольких пользователей одновременно

## Установка и запуск

### 1. Установка Playwright

```bash
# Если еще не установлен
cd frontend
npm install --save-dev @playwright/test

# Установка браузеров
npx playwright install
```

### 2. Подготовка окружения

Убедитесь, что:
- Django сервер запущен на `http://localhost:8000`
- Создан суперпользователь с credentials:
  - Email: `admin@example.com`
  - Password: `admin123`

Создать суперпользователя:
```bash
cd backend
python manage.py createsuperuser
# Введите admin@example.com и admin123
```

### 3. Запуск тестов

#### Запуск всех админ тестов:
```bash
npx playwright test frontend/tests/e2e/admin-panel.spec.ts
```

#### Запуск интеграционных тестов:
```bash
npx playwright test frontend/tests/e2e/admin-panel-integration.spec.ts
```

#### Запуск всех E2E тестов:
```bash
npx playwright test frontend/tests/e2e/
```

#### Запуск в UI режиме (с визуализацией):
```bash
npx playwright test --ui
```

#### Запуск в headed режиме (видно браузер):
```bash
npx playwright test frontend/tests/e2e/admin-panel.spec.ts --headed
```

#### Запуск конкретного теста:
```bash
npx playwright test -g "Admin can login to Django admin panel"
```

#### Запуск в конкретном браузере:
```bash
# Chromium
npx playwright test --project=chromium

# Firefox
npx playwright test --project=firefox

# WebKit
npx playwright test --project=webkit
```

### 4. Просмотр отчетов

После запуска тестов:
```bash
npx playwright show-report
```

## Helper функции

В файле `helpers/admin-helpers.ts` доступны следующие helper функции:

### Аутентификация
- `loginAsAdmin(page)` - Вход в админ панель
- `logoutFromAdmin(page)` - Выход из админ панели

### Управление пользователями
- `createUser(page, userData)` - Создание пользователя
- `deleteUser(page, username)` - Удаление пользователя
- `editUser(page, username, updates)` - Редактирование пользователя

### Управление предметами
- `createSubject(page, subjectData)` - Создание предмета
- `deleteSubject(page, subjectName)` - Удаление предмета
- `assignTeacherToSubject(page, teacherEmail, subjectName)` - Назначение преподавателя

### Зачисления
- `enrollStudentToSubject(page, studentEmail, subjectName, teacherEmail)` - Зачисление студента

### Utility функции
- `hasSuccessMessage(page)` - Проверка сообщения об успехе
- `hasErrorMessage(page)` - Проверка сообщения об ошибке
- `searchInAdmin(page, query)` - Поиск в админке
- `applyFilter(page, filterName, filterValue)` - Применение фильтра
- `getRecordCount(page)` - Получение количества записей
- `selectAllRecords(page)` - Выбор всех записей
- `applyBulkAction(page, action)` - Применение массового действия
- `generateTestEmail(prefix)` - Генерация тестового email
- `generateTestName(prefix)` - Генерация тестового имени

### Пример использования helpers:

```typescript
import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  createUser,
  deleteUser,
  generateTestEmail,
  hasSuccessMessage,
} from './helpers/admin-helpers';

test('My custom test', async ({ page }) => {
  await loginAsAdmin(page);

  const email = generateTestEmail('custom');

  await createUser(page, {
    username: email,
    email: email,
    firstName: 'Test',
    lastName: 'User',
    role: 'student',
  });

  expect(await hasSuccessMessage(page)).toBeTruthy();

  await deleteUser(page, email);
});
```

## Конфигурация

Настройки в `playwright.config.ts`:

```typescript
{
  testDir: './frontend/tests',
  timeout: 30 * 1000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  baseURL: 'http://localhost:8080',
}
```

## Важные замечания

### Credentials
Тесты используют следующие credentials для входа:
```typescript
username: 'admin@example.com'
password: 'admin123'
```

Эти данные настроены в `helpers/admin-helpers.ts` и могут быть изменены там.

### Cleanup
Все тесты автоматически очищают созданные данные через `finally` блоки. Это гарантирует, что тестовые данные не останутся в базе даже при падении теста.

### Timeouts
- Общий timeout теста: 30 секунд
- Timeout ожидания элемента: 5 секунд
- Навигационный timeout: 30 секунд

### Параллельность
Тесты выполняются параллельно по умолчанию. В CI окружении используется последовательное выполнение (`workers: 1`).

## Отладка тестов

### 1. Запуск с UI
```bash
npx playwright test --ui
```

### 2. Запуск в debug режиме
```bash
npx playwright test --debug
```

### 3. Просмотр трейсов
```bash
npx playwright show-trace test-results/trace.zip
```

### 4. Скриншоты и видео
- Скриншоты сохраняются при падении теста
- Видео сохраняется при падении теста
- Файлы находятся в `test-results/`

## CI/CD Integration

Для интеграции с CI/CD добавьте в пайплайн:

```yaml
- name: Install dependencies
  run: npm ci

- name: Install Playwright Browsers
  run: npx playwright install --with-deps

- name: Run Django server
  run: ./start.sh &

- name: Wait for server
  run: npx wait-on http://localhost:8000

- name: Run Admin E2E tests
  run: npx playwright test frontend/tests/e2e/admin-panel.spec.ts

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Известные ограничения

1. **File Upload тесты**: Тест загрузки PDF файла пропущен (`test.skip`), так как требует подготовки тестового файла
2. **Зависимость от данных**: Некоторые тесты предполагают наличие хотя бы одного учителя или предмета в системе
3. **Локализация**: Тесты учитывают русскую и английскую локализацию Django admin

## Расширение тестов

Для добавления новых тестов:

1. Используйте существующие helper функции из `admin-helpers.ts`
2. Следуйте паттерну `try/finally` для cleanup
3. Используйте `generateTestEmail()` и `generateTestName()` для уникальных имен
4. Добавляйте проверки сообщений успеха/ошибки

Пример:

```typescript
test('My new test', async ({ page }) => {
  const email = generateTestEmail('mytest');

  try {
    await loginAsAdmin(page);

    // Ваш тестовый код
    await createUser(page, { /* ... */ });

    expect(await hasSuccessMessage(page)).toBeTruthy();

  } finally {
    // Cleanup
    await deleteUser(page, email);
  }
});
```

## Troubleshooting

### Тест падает с timeout
- Увеличьте timeout в конфигурации
- Проверьте, что Django сервер запущен
- Проверьте сетевое соединение

### Элемент не найден
- Проверьте селектор в DevTools
- Убедитесь, что страница полностью загрузилась
- Добавьте `await page.waitForTimeout(1000)` если нужно

### Cleanup не работает
- Проверьте, что `deleteUser` или `deleteSubject` вызываются в `finally` блоке
- Убедитесь, что используется правильный username/name

### CSS не загружается
- Проверьте, что Django `collectstatic` выполнен
- Убедитесь, что `STATIC_URL` настроен правильно
- Проверьте консоль браузера на 404 ошибки

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи Django сервера
2. Просмотрите трейсы Playwright
3. Запустите тест в headed режиме для визуальной отладки
