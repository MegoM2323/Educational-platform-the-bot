import { test, expect, request, APIRequestContext, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';
const API_BASE = 'http://localhost:8000';

async function apiLogin(request: APIRequestContext, identifier: string, password: string) {
  const payload = identifier.includes('@')
    ? { email: identifier, password }
    : { username: identifier, password };
  const res = await request.post(`${API_BASE}/api/auth/login/`, { data: payload });
  expect(res.ok()).toBeTruthy();
  const json = await res.json();
  expect((json as any).token).toBeTruthy();
  expect((json as any).user).toBeTruthy();
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

test.describe('Поток оплаты: тьютор создаёт ученика, родитель оплачивает', () => {
  test.setTimeout(120_000);

  test('parent payment after tutor-created student and assignment', async ({ browser, request }) => {
    // 1) Логин тьютора (через backend API токен)
    const tutorCreds = await apiLogin(request, 'test_tutor@example.com', 'test123');

    const context = await browser.newContext();
    const page = await context.newPage();
    await setAuth(page, tutorCreds.user, tutorCreds.token);

    // 2) Тьютор создаёт ученика с родителем через UI
    await page.goto(`${BASE_URL}/dashboard/tutor/students`);
    await page.getByRole('button', { name: 'Создать ученика' }).click();

    await page.getByLabel('Имя *').fill('Павел');
    await page.getByLabel('Фамилия *').fill('Петров');
    await page.getByLabel('Класс *').fill('6Б');
    await page.getByLabel('Цель (необязательно)').fill('Подтянуть математику');

    await page.getByLabel('Имя родителя *').fill('Мария');
    await page.getByLabel('Фамилия родителя *').fill('Петрова');
    await page.getByLabel('Email родителя (необязательно)`).fill('maria.parent@example.com');
    await page.getByLabel('Телефон родителя (необязательно)').fill('+79990000001');

    await page.getByRole('button', { name: 'Создать' }).click();

    // 3) Считываем сгенерированные логин/пароль ребёнка и родителя из диалога
    const credsDialog = page.getByRole('dialog', { name: 'Сгенерированные учетные данные' });
    await expect(credsDialog).toBeVisible();

    const parentLogin = await credsDialog
      .locator('text=Родитель')
      .locator('xpath=..')
      .locator('text=Логин:')
      .locator('xpath=following-sibling::*')
      .first()
      .textContent();
    const parentPassword = await credsDialog
      .locator('text=Родитель')
      .locator('xpath=..')
      .locator('text=Пароль:')
      .locator('xpath=following-sibling::*')
      .first()
      .textContent();

    expect(parentLogin && parentPassword).toBeTruthy();

    await credsDialog.getByRole('button', { name: 'Закрыть' }).click();

    // 4) Назначаем предмет и (опционально) преподавателя
    await page.getByRole('button', { name: 'Назначить предмет' }).first().click();
    // subject-select
    await page.click('[aria-label="subject-select"]');
    const listbox = page.locator('[role="listbox"] [role="option"]');
    await expect(listbox.first()).toBeVisible();
    await listbox.first().click();
    // teacher-select (если показан)
    const teacherTrigger = page.locator('[aria-label="teacher-select"]');
    if (await teacherTrigger.isVisible()) {
      await teacherTrigger.click();
      const teacherOptions = page.locator('[role="listbox"] [role="option"]');
      if (await teacherOptions.count()) {
        await teacherOptions.first().click();
      } else {
        await page.keyboard.press('Escape');
      }
    }
    await page.getByRole('button', { name: 'Назначить' }).click();

    // 5) Вход как родитель и инициирование оплаты
    await page.goto(`${BASE_URL}`);
    await page.getByRole('button', { name: 'Логин' }).click();
    await page.getByLabel('Имя пользователя').fill(parentLogin!.trim());
    await page.getByLabel('Пароль').fill(parentPassword!.trim());
    await page.getByRole('button', { name: 'Войти' }).click();

    await page.goto(`${BASE_URL}/dashboard/parent`);
    const payBtn = page.getByRole('button', { name: /Оплатить|Просрочено|Оплачено/ }).first();
    await payBtn.click();

    // Проверяем, что произошёл переход вне фронта (редирект к провайдеру или ссылка оплаты)
    await page.waitForLoadState('domcontentloaded');
    const afterUrl = page.url();
    expect(afterUrl.startsWith(BASE_URL)).toBeFalsy();
  });
});


