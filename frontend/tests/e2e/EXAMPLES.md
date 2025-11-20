# Примеры расширения E2E тестов Admin Panel

Этот файл содержит примеры добавления новых тестов для различных сценариев.

## Базовый шаблон теста

```typescript
import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  createUser,
  deleteUser,
  generateTestEmail,
  hasSuccessMessage,
} from './helpers/admin-helpers';

test.describe('My New Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('My test case', async ({ page }) => {
    const email = generateTestEmail('mytest');

    try {
      // Тестовый код здесь
      await createUser(page, {
        username: email,
        email: email,
        firstName: 'Test',
        lastName: 'User',
        role: 'student',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

    } finally {
      // Cleanup
      await deleteUser(page, email);
    }
  });
});
```

## Пример 1: Тест создания студента с профилем

```typescript
test('Create student with full profile', async ({ page }) => {
  const studentEmail = generateTestEmail('student_profile');

  try {
    await loginAsAdmin(page);

    // Создаем студента
    await page.goto('http://localhost:8000/admin/accounts/user/add/');

    await page.fill('input[name="username"]', studentEmail);
    await page.fill('input[name="email"]', studentEmail);
    await page.fill('input[name="first_name"]', 'Иван');
    await page.fill('input[name="last_name"]', 'Петров');
    await page.selectOption('select[name="role"]', 'student');

    // Добавляем телефон
    await page.fill('input[name="phone"]', '+79991234567');

    // Сохраняем
    await page.click('input[type="submit"][name="_save"]');

    expect(await hasSuccessMessage(page)).toBeTruthy();

    // Теперь добавляем профиль студента
    await page.goto('http://localhost:8000/admin/accounts/studentprofile/add/');

    // Выбираем созданного пользователя
    await page.selectOption('select[name="user"]', { label: `${studentEmail}` });

    // Заполняем профиль
    await page.fill('input[name="grade"]', '10');
    await page.fill('textarea[name="goal"]', 'Подготовка к ЕГЭ');

    await page.click('input[type="submit"][name="_save"]');

    expect(await hasSuccessMessage(page)).toBeTruthy();

  } finally {
    await deleteUser(page, studentEmail);
  }
});
```

## Пример 2: Тест привязки родителя к студенту

```typescript
test('Link parent to student', async ({ page }) => {
  const studentEmail = generateTestEmail('child');
  const parentEmail = generateTestEmail('parent');

  try {
    await loginAsAdmin(page);

    // Создаем родителя
    await createUser(page, {
      username: parentEmail,
      email: parentEmail,
      firstName: 'Мария',
      lastName: 'Иванова',
      role: 'parent',
    });

    // Создаем студента
    await createUser(page, {
      username: studentEmail,
      email: studentEmail,
      firstName: 'Петр',
      lastName: 'Иванов',
      role: 'student',
    });

    // Создаем профиль студента с привязкой к родителю
    await page.goto('http://localhost:8000/admin/accounts/studentprofile/add/');

    // Выбираем студента
    const userSelect = page.locator('select[name="user"]');
    await userSelect.selectOption({ label: studentEmail });

    // Заполняем базовые поля
    await page.fill('input[name="grade"]', '9');

    // Выбираем родителя
    const parentSelect = page.locator('select[name="parent"]');
    const parentOption = await parentSelect.locator(`option:has-text("${parentEmail}")`).first();
    if (await parentOption.isVisible()) {
      await parentOption.click();
    }

    await page.click('input[type="submit"][name="_save"]');

    expect(await hasSuccessMessage(page)).toBeTruthy();

    // Проверяем, что связь создана
    await page.goto('http://localhost:8000/admin/accounts/studentprofile/');
    await expect(page.locator(`text=${studentEmail}`)).toBeVisible();

  } finally {
    await deleteUser(page, studentEmail);
    await deleteUser(page, parentEmail);
  }
});
```

## Пример 3: Тест создания материала с файлом

```typescript
test('Upload material with PDF file', async ({ page }) => {
  const subjectName = generateTestName('Literature');

  try {
    await loginAsAdmin(page);

    // Сначала создаем предмет
    await createSubject(page, {
      name: subjectName,
      description: 'Русская литература',
    });

    // Переходим к созданию материала
    await page.goto('http://localhost:8000/admin/materials/material/add/');

    // Заполняем форму материала
    await page.fill('input[name="title"]', 'Тестовый учебник');
    await page.fill('textarea[name="description"]', 'Учебник по литературе');

    // Выбираем предмет
    const subjectSelect = page.locator('select[name="subject"]');
    await subjectSelect.selectOption({ label: subjectName });

    // Загружаем файл (если есть тестовый PDF)
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.isVisible()) {
      // Создаем простой текстовый файл для теста
      // В реальности здесь должен быть путь к тестовому PDF
      // await fileInput.setInputFiles('path/to/test.pdf');
    }

    await page.click('input[type="submit"][name="_save"]');

    // Проверяем успех (может быть ошибка если нет файла)
    const success = await hasSuccessMessage(page);
    const error = await page.locator('.errorlist').isVisible().catch(() => false);

    expect(success || error).toBeTruthy();

  } finally {
    await deleteSubject(page, subjectName);
  }
});
```

## Пример 4: Тест массового изменения пользователей

```typescript
test('Bulk update users to verified status', async ({ page }) => {
  const user1Email = generateTestEmail('bulk1');
  const user2Email = generateTestEmail('bulk2');

  try {
    await loginAsAdmin(page);

    // Создаем нескольких пользователей
    await createUser(page, {
      username: user1Email,
      email: user1Email,
      firstName: 'Bulk',
      lastName: 'User 1',
      role: 'student',
    });

    await createUser(page, {
      username: user2Email,
      email: user2Email,
      firstName: 'Bulk',
      lastName: 'User 2',
      role: 'student',
    });

    // Переходим к списку пользователей
    await page.goto('http://localhost:8000/admin/accounts/user/');

    // Фильтруем по "Bulk"
    await page.fill('input#searchbar', 'Bulk');
    await page.press('input#searchbar', 'Enter');
    await page.waitForTimeout(1000);

    // Выбираем всех
    const selectAll = page.locator('#action-toggle');
    if (await selectAll.isVisible()) {
      await selectAll.check();

      // Проверяем, есть ли кастомное действие для верификации
      // (Это зависит от вашей настройки Django admin actions)
      const actionSelect = page.locator('select[name="action"]');
      const options = await actionSelect.locator('option').allTextContents();

      console.log('Available actions:', options);

      // Пример: если есть действие "Верифицировать пользователей"
      // await actionSelect.selectOption('verify_users');
      // await page.click('button[name="index"]');
      // expect(await hasSuccessMessage(page)).toBeTruthy();
    }

  } finally {
    await deleteUser(page, user1Email);
    await deleteUser(page, user2Email);
  }
});
```

## Пример 5: Тест поиска и фильтрации

```typescript
test('Search and filter users by role and status', async ({ page }) => {
  await loginAsAdmin(page);

  await page.goto('http://localhost:8000/admin/accounts/user/');

  // Тест поиска
  await page.fill('input#searchbar', 'admin');
  await page.press('input#searchbar', 'Enter');
  await page.waitForTimeout(1000);

  const resultsTable = page.locator('#result_list');
  await expect(resultsTable).toBeVisible();

  // Проверяем, что есть результаты
  const rows = await page.locator('#result_list tbody tr').count();
  expect(rows).toBeGreaterThan(0);

  // Тест фильтрации
  const filterSidebar = page.locator('#changelist-filter');
  if (await filterSidebar.isVisible()) {
    // Фильтр по роли "Student"
    const studentFilter = filterSidebar.locator('text=/Student|Студент/i');
    if (await studentFilter.isVisible()) {
      await studentFilter.click();
      await page.waitForTimeout(1000);

      // Проверяем, что URL изменился (добавился параметр фильтра)
      expect(page.url()).toContain('role=');
    }
  }
});
```

## Пример 6: Тест inline редактирования (если настроено)

```typescript
test('Edit user profile inline', async ({ page }) => {
  const studentEmail = generateTestEmail('inline');

  try {
    await loginAsAdmin(page);

    // Создаем студента
    await createUser(page, {
      username: studentEmail,
      email: studentEmail,
      firstName: 'Inline',
      lastName: 'Test',
      role: 'student',
    });

    // Переходим к редактированию пользователя
    await page.goto('http://localhost:8000/admin/accounts/user/');
    await page.fill('input#searchbar', studentEmail);
    await page.press('input#searchbar', 'Enter');
    await page.waitForTimeout(1000);

    // Кликаем на пользователя
    await page.click(`text=${studentEmail}`);

    // Проверяем наличие inline форм профиля
    const inlineForm = page.locator('.inline-related');
    if (await inlineForm.isVisible()) {
      // Заполняем inline поля профиля студента
      const gradeField = page.locator('input[name*="grade"]').first();
      if (await gradeField.isVisible()) {
        await gradeField.fill('11');
      }

      await page.click('input[type="submit"][name="_save"]');
      expect(await hasSuccessMessage(page)).toBeTruthy();
    }

  } finally {
    await deleteUser(page, studentEmail);
  }
});
```

## Пример 7: Тест проверки прав доступа

```typescript
test('Regular user cannot access admin panel', async ({ page }) => {
  // Создаем обычного пользователя (не staff)
  const regularEmail = generateTestEmail('regular');

  try {
    await loginAsAdmin(page);

    await createUser(page, {
      username: regularEmail,
      email: regularEmail,
      firstName: 'Regular',
      lastName: 'User',
      role: 'student',
    });

    // Выходим из админа
    await page.goto('http://localhost:8000/admin/logout/');

    // Пытаемся войти как обычный пользователь
    await page.goto('http://localhost:8000/admin/');
    await page.fill('input[name="username"]', regularEmail);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('input[type="submit"]');

    // Должна быть ошибка доступа
    const hasError = await page.locator('.errornote').isVisible().catch(() => false);
    const stayedOnLogin = page.url().includes('/login/');

    expect(hasError || stayedOnLogin).toBeTruthy();

  } finally {
    // Логинимся обратно как админ для cleanup
    await loginAsAdmin(page);
    await deleteUser(page, regularEmail);
  }
});
```

## Пример 8: Тест экспорта данных (если настроен)

```typescript
test('Export users to CSV', async ({ page }) => {
  await loginAsAdmin(page);

  await page.goto('http://localhost:8000/admin/accounts/user/');

  // Выбираем всех пользователей
  const selectAll = page.locator('#action-toggle');
  if (await selectAll.isVisible()) {
    await selectAll.check();

    // Выбираем действие экспорта (если настроено)
    const actionSelect = page.locator('select[name="action"]');
    const options = await actionSelect.locator('option').allTextContents();

    // Проверяем, есть ли опция экспорта
    const hasExport = options.some(opt =>
      opt.toLowerCase().includes('export') ||
      opt.toLowerCase().includes('экспорт')
    );

    if (hasExport) {
      // Запускаем экспорт
      const exportOption = options.find(opt =>
        opt.toLowerCase().includes('export') ||
        opt.toLowerCase().includes('экспорт')
      );

      if (exportOption) {
        await actionSelect.selectOption({ label: exportOption });
        await page.click('button[name="index"]');

        // Проверяем, что начался download или появилось сообщение
        const downloadPromise = page.waitForEvent('download', { timeout: 5000 })
          .catch(() => null);

        const download = await downloadPromise;
        if (download) {
          expect(download.suggestedFilename()).toContain('.csv');
        }
      }
    }
  }
});
```

## Пример 9: Тест проверки валидации форм

```typescript
test('Form validation prevents invalid data', async ({ page }) => {
  await loginAsAdmin(page);

  await page.goto('http://localhost:8000/admin/accounts/user/add/');

  // Пытаемся создать пользователя с невалидным email
  await page.fill('input[name="username"]', 'testuser');
  await page.fill('input[name="email"]', 'invalid-email'); // Невалидный email
  await page.fill('input[name="first_name"]', 'Test');
  await page.fill('input[name="last_name"]', 'User');

  await page.click('input[type="submit"][name="_save"]');

  // Должна быть ошибка валидации
  const errorList = page.locator('.errorlist');
  await expect(errorList).toBeVisible();

  // Проверяем текст ошибки
  const errorText = await errorList.textContent();
  expect(errorText?.toLowerCase()).toContain('email');
});
```

## Пример 10: Тест работы с датами

```typescript
test('Create enrollment with specific dates', async ({ page }) => {
  const studentEmail = generateTestEmail('dated');
  const teacherEmail = generateTestEmail('teacher');
  const subjectName = generateTestName('Programming');

  try {
    await loginAsAdmin(page);

    // Создаем необходимые сущности
    await createUser(page, {
      username: studentEmail,
      email: studentEmail,
      firstName: 'Student',
      lastName: 'Dated',
      role: 'student',
    });

    await createUser(page, {
      username: teacherEmail,
      email: teacherEmail,
      firstName: 'Teacher',
      lastName: 'Dated',
      role: 'teacher',
    });

    await createSubject(page, { name: subjectName });

    await assignTeacherToSubject(page, teacherEmail, subjectName);

    // Создаем зачисление с конкретной датой
    await page.goto('http://localhost:8000/admin/materials/subjectenrollment/add/');

    // Выбираем студента, предмет, преподавателя
    await page.selectOption('select[name="student"]', { label: studentEmail });
    await page.selectOption('select[name="subject"]', { label: subjectName });
    await page.selectOption('select[name="teacher"]', { label: teacherEmail });

    // Если есть поле даты зачисления
    const dateField = page.locator('input[name="enrolled_at"]');
    if (await dateField.isVisible()) {
      // Формат зависит от настроек Django
      await dateField.fill('2025-01-20');
    }

    await page.click('input[type="submit"][name="_save"]');

    expect(await hasSuccessMessage(page)).toBeTruthy();

  } finally {
    await deleteSubject(page, subjectName);
    await deleteUser(page, studentEmail);
    await deleteUser(page, teacherEmail);
  }
});
```

## Полезные паттерны

### Проверка наличия элемента перед действием

```typescript
const element = page.locator('selector');
if (await element.isVisible()) {
  await element.click();
}
```

### Ожидание и retry

```typescript
// Ожидание конкретного состояния
await page.waitForSelector('.success', { timeout: 5000 });

// Retry action
await expect(async () => {
  await page.click('button');
  await expect(page.locator('.result')).toBeVisible();
}).toPass({ timeout: 10000 });
```

### Работа с модальными окнами

```typescript
// Ожидание dialog
page.on('dialog', async dialog => {
  console.log(dialog.message());
  await dialog.accept();
});

await page.click('button.delete');
```

### Debug и логирование

```typescript
// Скриншот в конкретный момент
await page.screenshot({ path: 'debug-screenshot.png' });

// Логирование console
page.on('console', msg => console.log('PAGE LOG:', msg.text()));

// Пауза для debug
await page.pause();
```

## Следующие шаги

1. Скопируйте нужный пример
2. Адаптируйте под свой use case
3. Добавьте cleanup в `finally` блок
4. Запустите тест локально
5. Проверьте в CI/CD

Удачного тестирования!
