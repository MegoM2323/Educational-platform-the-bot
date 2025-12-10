import { test } from '@playwright/test';

test.describe('Dashboard Screenshots', () => {
  test('Student Dashboard screenshot', async ({ page }) => {
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Небольшая задержка для загрузки всех элементов
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: 'docs/screenshots/dashboards/student-dashboard.png',
      fullPage: true
    });
  });

  test('Teacher Dashboard screenshot', async ({ page }) => {
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/teacher', { timeout: 10000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Небольшая задержка для загрузки всех элементов
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: 'docs/screenshots/dashboards/teacher-dashboard.png',
      fullPage: true
    });
  });

  test('Parent Dashboard screenshot', async ({ page }) => {
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'parent@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/parent', { timeout: 10000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Небольшая задержка для загрузки всех элементов
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: 'docs/screenshots/dashboards/parent-dashboard.png',
      fullPage: true
    });
  });

  test('Tutor Dashboard screenshot', async ({ page }) => {
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/tutor', { timeout: 10000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Небольшая задержка для загрузки всех элементов
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: 'docs/screenshots/dashboards/tutor-dashboard.png',
      fullPage: true
    });
  });
});
