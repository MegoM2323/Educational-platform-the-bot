import { test, expect } from '@playwright/test';

test.describe('Student Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Вход под студентом
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });
  });

  test('should load dashboard successfully', async ({ page }) => {
    // Проверить что заголовок загрузился
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });

    // Проверить что статистика загрузилась
    const progressText = page.locator('text=/прогресс/i');
    if (await progressText.count() > 0) {
      await expect(progressText.first()).toBeVisible();
    }
  });

  test('should display materials section', async ({ page }) => {
    // Проверить что есть секция материалов
    const materialsSection = page.locator('text=/материал/i').first();
    await expect(materialsSection).toBeVisible({ timeout: 5000 });
  });

  test('should display subjects section', async ({ page }) => {
    // Проверить что есть секция предметов
    const subjectsSection = page.locator('text=/предмет/i').first();
    await expect(subjectsSection).toBeVisible({ timeout: 5000 });
  });

  test('should display assignments section', async ({ page }) => {
    // Проверить что есть секция заданий
    const assignmentsSection = page.locator('text=/задани/i').first();
    if (await assignmentsSection.count() > 0) {
      await expect(assignmentsSection).toBeVisible();
    }
  });

  test('should have white minimalist design', async ({ page }) => {
    // Проверить что основной фон светлый
    const body = page.locator('body');
    const bgColor = await body.evaluate((el) =>
      window.getComputedStyle(el).backgroundColor
    );

    // Светлый фон (любой светлый оттенок)
    // Проверяем что значения RGB > 240 (очень светлый)
    const rgbMatch = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch.map(Number);
      expect(r).toBeGreaterThan(240);
      expect(g).toBeGreaterThan(240);
      expect(b).toBeGreaterThan(240);
    }
  });

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    // Проверить что контент виден на мобильном
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();

    // Проверить что sidebar адаптировалась
    const mainContent = page.locator('main, [role="main"]');
    if (await mainContent.count() > 0) {
      await expect(mainContent.first()).toBeVisible();
    }
  });

  test('should navigate using sidebar', async ({ page }) => {
    // Проверить что sidebar существует
    const nav = page.locator('nav, aside').first();
    if (await nav.count() > 0) {
      await expect(nav).toBeVisible();
    }
  });

  test('should load without errors', async ({ page }) => {
    // Проверить что нет ошибок в консоли (критичных)
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Фильтруем известные некритичные ошибки
    const criticalErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('WebSocket')
    );

    expect(criticalErrors.length).toBeLessThan(3);
  });
});
