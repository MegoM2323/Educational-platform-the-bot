import { test, expect } from '@playwright/test';

test('Materials page shows dashboard sidebar layout', async ({ page }) => {
  // Assume logged-in student via storage state or env; fallback to manual login
  const frontend = process.env.FRONTEND_URL || 'http://localhost:5173';
  await page.goto(frontend + '/auth');

  const email = process.env.STUDENT_EMAIL || 'student@example.com';
  const password = process.env.STUDENT_PASSWORD || 'studentpass';

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Пароль').fill(password);
  await page.getByRole('button', { name: 'Войти' }).click();

  await page.goto(frontend + '/dashboard/student/materials');

  // Sidebar trigger exists
  await expect(page.locator('button[aria-label="Toggle Sidebar"]')).toBeVisible();

  // Page heading exists
  await expect(page.getByRole('heading', { name: 'Учебные материалы' })).toBeVisible();
});


