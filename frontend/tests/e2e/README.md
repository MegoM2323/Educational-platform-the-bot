# E2E Тесты - Комплексные взаимодействия пользователей

## Описание

Этот каталог содержит комплексные End-to-End тесты для платформы THE_BOT, которые проверяют взаимодействия между всеми типами пользователей:

- **Admin** - Создание структуры платформы (тьюторы, учителя, предметы)
- **Tutor** - Управление студентами, назначение предметов и учителей
- **Teacher** - Создание материалов, заданий, планов занятий, оценивание
- **Student** - Работа с материалами, сдача заданий, общение с учителями
- **Parent** - Просмотр прогресса детей, отчетов, оплата предметов

## Структура файлов

```
tests/e2e/
├── helpers/
│   ├── auth.ts           # Функции для аутентификации
│   ├── files.ts          # Функции для работы с файлами
│   └── utils.ts          # Вспомогательные утилиты
├── user-interactions.spec.ts  # Комплексный сценарий взаимодействий
├── auth.spec.ts          # Тесты аутентификации
├── admin.spec.ts         # Тесты админ панели
└── README.md             # Эта документация
```

## Требования

1. **Backend сервер** должен быть запущен на `http://localhost:8000`
2. **Frontend сервер** должен быть запущен на `http://localhost:8080`
3. **Тестовые пользователи** должны быть созданы в БД:
   - student@test.com (пароль: TestPass123!)
   - teacher@test.com (пароль: TestPass123!)
   - tutor@test.com (пароль: TestPass123!)
   - parent@test.com (пароль: TestPass123!)
   - admin@test.com (пароль: TestPass123!)

## Установка Playwright

```bash
# В директории frontend
npm install @playwright/test --save-dev

# Установка браузеров
npx playwright install
```

## Запуск тестов

### Запуск всех E2E тестов

```bash
npm run test:e2e
```

### Запуск в UI режиме (интерактивно)

```bash
npm run test:e2e:ui
```

### Запуск в headed режиме (видно браузер)

```bash
npm run test:e2e:headed
```

### Запуск только комплексных тестов взаимодействий

```bash
npx playwright test tests/e2e/user-interactions.spec.ts
```

### Запуск в определенном браузере

```bash
# Только Chrome
npx playwright test --project=chromium

# Только Firefox
npx playwright test --project=firefox

# Только Safari
npx playwright test --project=webkit
```

### Запуск с отладкой

```bash
# Запустить с паузами на ошибках
npx playwright test --debug

# Запустить конкретный тест
npx playwright test -g "Admin logs in"
```

### Просмотр отчета

```bash
npm run test:e2e:report
```

## Покрытие тестами

### A. Admin Flow
- ✅ A1. Вход в систему
- ✅ A2. Создание тьютора через админ панель
- ✅ A3. Создание учителя через админ панель
- ✅ A4. Назначение предметов учителям

### B. Tutor Flow
- ✅ B1. Вход в систему
- ✅ B2. Создание аккаунта студента
- ✅ B3. Назначение предметов студенту
- ✅ B4. Назначение учителей на предметы студента
- ✅ B5. Создание отчета для родителя

### C. Teacher Flow
- ✅ C1. Вход в систему
- ✅ C2. Создание плана занятий
- ✅ C3. Загрузка PDF файла плана занятий
- ✅ C4. Создание учебного материала с файлом
- ✅ C5. Создание задания для студента
- ✅ C6. Оценивание работы студента
- ✅ C7. Создание отчета для тьютора

### D. Student Flow
- ✅ D1. Вход в систему
- ✅ D2. Просмотр плана занятий
- ✅ D3. Открытие PDF файла плана занятий
- ✅ D4. Скачивание учебного материала
- ✅ D5. Сдача задания с файлом
- ✅ D6. Отправка сообщения учителю в чате

### E. Parent Flow
- ✅ E1. Вход в систему
- ✅ E2. Просмотр прогресса ребенка
- ✅ E3. Чтение отчета от тьютора
- ✅ E4. Инициирование оплаты предмета
- ✅ E5. Просмотр истории платежей

### F. Cross-User File Interactions
- ✅ F1. Учитель загружает отчет, тьютор открывает его
- ✅ F2. Учитель создает план, студент скачивает его
- ✅ F3. Студент сдает работу, учитель скачивает и оценивает

## Helper Functions

### Аутентификация (helpers/auth.ts)

```typescript
import { loginAs, logout, TEST_USERS } from './helpers/auth';

// Вход как студент
await loginAs(page, 'student');

// Вход как учитель
await loginAs(page, 'teacher');

// Выход из системы
await logout(page);
```

### Работа с файлами (helpers/files.ts)

```typescript
import { createTestPDF, uploadFile, downloadFile } from './helpers/files';

// Создать тестовый PDF
const pdfPath = await createTestPDF('my-test.pdf');

// Загрузить файл
await uploadFile(page, 'input[type="file"]', pdfPath);

// Скачать файл
const downloadPath = await downloadFile(page, 'button:has-text("Скачать")');
```

### Утилиты (helpers/utils.ts)

```typescript
import {
  waitForToast,
  expectSuccessMessage,
  expectPageHasText,
  waitForLoadingComplete
} from './helpers/utils';

// Ждать toast уведомление
await waitForToast(page, /успешно/i);

// Проверить сообщение об успехе
await expectSuccessMessage(page);

// Проверить что на странице есть текст
await expectPageHasText(page, /материалы/i);

// Подождать окончания загрузки
await waitForLoadingComplete(page);
```

## Рекомендации по написанию тестов

1. **Используйте data-testid** для стабильных селекторов:
   ```html
   <button data-testid="submit-button">Отправить</button>
   ```
   ```typescript
   await page.click('[data-testid="submit-button"]');
   ```

2. **Добавляйте ожидания** перед взаимодействием:
   ```typescript
   await page.waitForSelector('button', { state: 'visible' });
   await page.click('button');
   ```

3. **Используйте page.waitForLoadState()** после навигации:
   ```typescript
   await page.goto('/dashboard');
   await page.waitForLoadState('networkidle');
   ```

4. **Делайте скриншоты при ошибках**:
   ```typescript
   try {
     await page.click('button');
   } catch (error) {
     await page.screenshot({ path: 'error-screenshot.png' });
     throw error;
   }
   ```

5. **Очищайте данные после тестов**:
   ```typescript
   test.afterAll(async () => {
     cleanupTestFiles(testFiles);
   });
   ```

## Отладка тестов

### Запуск с пошаговой отладкой

```bash
npx playwright test --debug tests/e2e/user-interactions.spec.ts
```

### Просмотр трейса

```bash
# Запустить с трейсом
npx playwright test --trace on

# Открыть трейс
npx playwright show-trace trace.zip
```

### Просмотр видео

После запуска тестов видео сохраняются в `test-results/` для упавших тестов.

## CI/CD Integration

Пример для GitHub Actions:

```yaml
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npm run test:e2e

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: test-results/
```

## Troubleshooting

### Проблема: Тесты падают с timeout

**Решение:** Увеличьте таймауты в `playwright.config.ts`:
```typescript
use: {
  actionTimeout: 30000,
  navigationTimeout: 60000,
}
```

### Проблема: Не находятся элементы на странице

**Решение:**
1. Запустите тест в headed режиме: `npm run test:e2e:headed`
2. Проверьте селекторы в браузере
3. Используйте более надежные селекторы (role, text, data-testid)

### Проблема: Backend недоступен

**Решение:**
1. Убедитесь что backend запущен: `http://localhost:8000`
2. Проверьте что БД доступна
3. Проверьте наличие тестовых пользователей

### Проблема: Файлы не загружаются

**Решение:**
1. Проверьте права доступа к временной директории
2. Убедитесь что существует директория `backend/media/`
3. Проверьте настройки Django MEDIA_ROOT

## Дополнительные ресурсы

- [Playwright Documentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Guide](https://playwright.dev/docs/debug)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
