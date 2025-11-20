import { test, expect } from '@playwright/test';

test('Parent can log in and see parent dashboard', async ({ page }) => {
  // Visit app
  await page.goto(process.env.FRONTEND_URL || 'http://localhost:5173');

  // Go to auth page
  await page.goto((process.env.FRONTEND_URL || 'http://localhost:5173') + '/auth');

  // Fill credentials from env or fixtures
  const email = process.env.PARENT_EMAIL || 'parent@example.com';
  const password = process.env.PARENT_PASSWORD || 'parentpass';

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Пароль').fill(password);
  await page.getByRole('button', { name: 'Войти' }).click();

  // Expect redirected to parent dashboard
  await expect(page).toHaveURL(/\/dashboard\/parent/);
  await expect(page.getByRole('heading', { name: 'Личный кабинет родителя' })).toBeVisible();
});


