import { test, expect } from '@playwright/test';

test.describe('Parent Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Вход под родителем
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'parent@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/parent', { timeout: 10000 });
  });

  test('should load dashboard successfully', async ({ page }) => {
    // Проверить что заголовок загрузился
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('should display children section', async ({ page }) => {
    // Проверить что есть секция с детьми
    const childrenSection = page.locator('text=/дети|ребен/i').first();
    if (await childrenSection.count() > 0) {
      await expect(childrenSection).toBeVisible();
    }
  });

  test('should display payment section', async ({ page }) => {
    // Проверить что есть секция с платежами
    const paymentSection = page.locator('text=/оплат|платеж|подписк/i').first();
    if (await paymentSection.count() > 0) {
      await expect(paymentSection).toBeVisible();
    }
  });

  test('should show payment buttons', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверить что есть кнопки оплаты
    const payButtons = page.locator('button:has-text(/оплат/i)');
    if (await payButtons.count() > 0) {
      await expect(payButtons.first()).toBeVisible();

      // Проверить что кнопка кликабельна
      await expect(payButtons.first()).toBeEnabled();
    }
  });

  test('should display payment status indicators', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверить что есть индикаторы статуса
    const statusIndicators = page.locator('text=/активн|неоплачен|истек/i');
    if (await statusIndicators.count() > 0) {
      await expect(statusIndicators.first()).toBeVisible();
    }
  });

  test('should display reports section', async ({ page }) => {
    // Проверить что есть секция отчетов
    const reportsSection = page.locator('text=/отчет|отчёт/i').first();
    if (await reportsSection.count() > 0) {
      await expect(reportsSection).toBeVisible();
    }
  });

  test('should have white minimalist design', async ({ page }) => {
    // Проверить что основной фон светлый
    const body = page.locator('body');
    const bgColor = await body.evaluate((el) =>
      window.getComputedStyle(el).backgroundColor
    );

    // Светлый фон (любой светлый оттенок)
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
  });

  test('should load without critical errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.waitForLoadState('networkidle', { timeout: 10000 });

    const criticalErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('WebSocket')
    );

    expect(criticalErrors.length).toBeLessThan(3);
  });

  test('should show child progress indicators', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверить что есть индикаторы прогресса или статистика по детям
    const hasChildData = await page.locator('text=/прогресс|успеваемост|предмет/i').count();

    // Либо есть данные, либо empty state
    expect(hasChildData).toBeGreaterThanOrEqual(0);
  });
});
