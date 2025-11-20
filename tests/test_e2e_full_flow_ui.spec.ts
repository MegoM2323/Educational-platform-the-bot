import { test, expect, request, APIRequestContext, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';
const API_BASE = 'http://localhost:8000';

async function apiLogin(request: APIRequestContext, identifier: string, password: string) {
  // Backend ожидает либо email либо username
  const payload = identifier.includes('@')
    ? { email: identifier, password }
    : { username: identifier, password };
  const res = await request.post(`${API_BASE}/api/auth/login/`, { data: payload });
  expect(res.ok()).toBeTruthy();
  const json = await res.json();
  expect(json.token).toBeTruthy();
  expect(json.user).toBeTruthy();
  return json as { token: string; user: any };
}

async function setAuth(page: Page, user: any, token: string) {
  const ttlMs = 24 * 60 * 60 * 1000;
  const expiry = Date.now() + ttlMs;
  await page.addInitScript((u, t, e) => {
    localStorage.setItem('authToken', t);
    localStorage.setItem('userData', JSON.stringify(u));
    localStorage.setItem('token_expiry', String(e));
  }, user, token, expiry);
}

async function switchAuth(page: Page, user: any, token: string) {
  const ttlMs = 24 * 60 * 60 * 1000;
  const expiry = Date.now() + ttlMs;
  await page.evaluate(([u, t, e]) => {
    localStorage.setItem('authToken', t as string);
    localStorage.setItem('userData', JSON.stringify(u));
    localStorage.setItem('token_expiry', String(e));
  }, [user, token, expiry]);
}

// Помощник: выбрать первый предмет в селекте по aria-label
async function selectFirstOption(page: Page, triggerSelector: string) {
  await page.click(triggerSelector);
  const menu = page.locator('[role="listbox"]');
  await expect(menu).toBeVisible();
  const first = menu.locator('[role="option"]').first();
  await first.click();
}

// Основной e2e сценарий
// Предпосылки: подняты backend (localhost:8000) и frontend (localhost:8080),
// есть базовые тестовые пользователи: test_tutor@example.com / test123, test_teacher@example.com / test123
// (см. backend/accounts/management/commands/reset_to_known_test_dataset.py)

test.describe('Полный поток: тьютор ➜ ученик+родитель ➜ назначение ➜ материал ➜ ДЗ ➜ оплата', () => {
  test.setTimeout(180_000);

  test('end-to-end UI', async ({ browser, request }) => {
    // 1) Логин тьютора (backend token)
    const tutorCreds = await apiLogin(request, 'test_tutor@example.com', 'test123');

    const context = await browser.newContext();
    const page = await context.newPage();
    await setAuth(page, tutorCreds.user, tutorCreds.token);

    // 2) Тьютор: создаёт ученика и родителя
    await page.goto(`${BASE_URL}/dashboard/tutor/students`);

    await page.getByRole('button', { name: 'Создать ученика' }).click();

    // Заполняем форму
    await page.getByLabel('Имя *').fill('Иван');
    await page.getByLabel('Фамилия *').fill('Иванов');
    await page.getByLabel('Класс *').fill('7А');
    await page.getByLabel('Цель (необязательно)').fill('Подготовка к экзаменам');

    await page.getByLabel('Имя родителя *').fill('Анна');
    await page.getByLabel('Фамилия родителя *').fill('Иванова');
    await page.getByLabel('Email родителя (необязательно)').fill('anna.parent@example.com');
    await page.getByLabel('Телефон родителя (необязательно)').fill('+79991234567');

    await page.getByRole('button', { name: 'Создать' }).click();

    // Ожидаем диалог с учётными данными
    const credsDialog = page.getByRole('dialog', { name: 'Сгенерированные учетные данные' });
    await expect(credsDialog).toBeVisible();

    const studentLogin = await credsDialog.locator('text=Ученик').locator('xpath=..').locator('text=Логин:').locator('xpath=following-sibling::*').first().textContent().catch(() => null);
    const studentPassword = await credsDialog.locator('text=Ученик').locator('xpath=..').locator('text=Пароль:').locator('xpath=following-sibling::*').first().textContent().catch(() => null);
    const parentLogin = await credsDialog.locator('text=Родитель').locator('xpath=..').locator('text=Логин:').locator('xpath=following-sibling::*').first().textContent().catch(() => null);
    const parentPassword = await credsDialog.locator('text=Родитель').locator('xpath=..').locator('text=Пароль:').locator('xpath=following-sibling::*').first().textContent().catch(() => null);

    expect(studentLogin && studentPassword && parentLogin && parentPassword).toBeTruthy();

    // Закрыть диалог
    await credsDialog.getByRole('button', { name: 'Закрыть' }).click();

    // 3) Назначение предмета через диалог "Назначить предмет" у карточки ученика
    // Берём первую карточку "Мои ученики" и кликаем "Назначить предмет"
    await page.getByRole('button', { name: 'Назначить предмет' }).first().click();

    // Выбираем предмет (первый в списке)
    await selectFirstOption(page, '[aria-label="subject-select"]');

    // Опционально: если есть список преподавателей — выберем первого
    const teacherTrigger = page.locator('[aria-label="teacher-select"]');
    if (await teacherTrigger.isVisible()) {
      await teacherTrigger.click();
      const teacherOptions = page.locator('[role="listbox"] [role="option"]');
      if (await teacherOptions.count() > 0) {
        await teacherOptions.first().click();
      } else {
        // Нет доступных преподавателей — сервис на бэке подберёт автоматически, если они есть в системе
        await page.keyboard.press('Escape');
      }
    }

    await page.getByRole('button', { name: 'Назначить' }).click();

    // 4) Логин под преподавателем и создание материала для ученика
    const teacherCreds = await apiLogin(request, 'test_teacher@example.com', 'test123');
    await switchAuth(page, teacherCreds.user, teacherCreds.token);
    await page.goto(`${BASE_URL}/dashboard/teacher`);
    await page.getByRole('button', { name: 'Создать материал' }).click();

    // На странице создания материала
    await expect(page).toHaveURL(/\/dashboard\/teacher\/materials\/create/);

    await page.getByLabel('Заголовок').fill('Домашнее задание: Алгебра — линейные уравнения');
    await page.getByLabel('Описание').fill('Решить 10 задач на линейные уравнения');

    // Выбор предмета
    const subjectSelect = page.locator('label:has-text("Предмет")').locator('xpath=following-sibling::*').locator('[role="combobox"]');
    await subjectSelect.click();
    await page.locator('[role="listbox"] [role="option"]').first().click();

    // Тип: Домашнее задание, если доступно
    const typeSelect = page.locator('label:has-text("Тип")').locator('xpath=following-sibling::*').locator('[role="combobox"]');
    if (await typeSelect.isVisible()) {
      await typeSelect.click();
      const option = page.locator('[role="option"]', { hasText: 'Домашнее задание' });
      if (await option.count()) {
        await option.first().click();
      } else {
        await page.keyboard.press('Escape');
      }
    }

    // Назначить материал конкретному ученику — выбираем первого в списке "Назначить ученикам"
    const assignedTo = page.getByText('Назначить ученикам');
    if (await assignedTo.count()) {
      await assignedTo.first().click();
      const listbox = page.locator('[role="listbox"] [role="option"]');
      if (await listbox.count()) {
        await listbox.first().click();
      } else {
        await page.keyboard.press('Escape');
      }
    }

    // Сохранить/Опубликовать материал
    const createBtn = page.getByRole('button', { name: /Создать|Опубликовать/ });
    await createBtn.click();

    // Убедиться, что был редирект или показан тост об успехе
    await expect(page).toHaveURL(/\/dashboard\/teacher\/(materials|$)/, { timeout: 15000 });

    // 5) Логин под учеником (через форму) и отправка ДЗ
    await page.goto(`${BASE_URL}`);
    await page.getByRole('button', { name: 'Логин' }).click(); // переключить на вход по логину
    await page.getByLabel('Имя пользователя').fill(studentLogin!.trim());
    await page.getByLabel('Пароль').fill(studentPassword!.trim());
    await page.getByRole('button', { name: 'Войти' }).click();

    // Переход в материалы ученика
    await page.goto(`${BASE_URL}/dashboard/student/materials`);
    // Открыть первый материал и нажать "Ответить"
    const answerBtn = page.getByRole('button', { name: 'Ответить' }).first();
    await answerBtn.click();

    // Диалог отправки ответа
    const submitDialog = page.getByRole('dialog', { name: /Отправить ответ|Отправить домашнее задание/ });
    await expect(submitDialog).toBeVisible();
    // Ввод текста ответа
    const textArea = submitDialog.getByRole('textbox');
    await textArea.fill('Решение: х = 5, у = -3. Все задачи решены.');
    await submitDialog.getByRole('button', { name: 'Отправить' }).click();

    // Проверяем, что диалог закрылся
    await expect(submitDialog).toBeHidden({ timeout: 10000 });

    // 6) Логин под родителем (через форму) и оплата обучения
    await page.goto(`${BASE_URL}`);
    await page.getByRole('button', { name: 'Логин' }).click();
    await page.getByLabel('Имя пользователя').fill(parentLogin!.trim());
    await page.getByLabel('Пароль').fill(parentPassword!.trim());
    await page.getByRole('button', { name: 'Войти' }).click();

    await page.goto(`${BASE_URL}/dashboard/parent`);

    // На карточке ребёнка нажимаем "Оплатить" для первого предмета
    const payBtn = page.getByRole('button', { name: /Оплатить|Просрочено|Оплачено/ }).first();
    await payBtn.click();

    // Ожидаем переход на страницу оплаты (обычно redirect на платёжный провайдер)
    // Допускаем как прямой redirect, так и открытие в том же окне
    await page.waitForLoadState('domcontentloaded');

    // Валидируем, что произошла попытка перейти на внешнюю оплату или вернулся URL оплаты
    const current = page.url();
    // Если backend возвращает прямую ссылку на платёжного провайдера, URL будет не BASE_URL
    expect(current.startsWith(BASE_URL)).toBeFalsy();
  });
});



