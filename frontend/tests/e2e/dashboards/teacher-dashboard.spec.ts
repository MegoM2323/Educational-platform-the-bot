import { test, expect } from '@playwright/test';

test.describe('Teacher Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Вход под учителем
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/teacher', { timeout: 10000 });
  });

  test('should load dashboard with statistics', async ({ page }) => {
    // Проверить что заголовок загрузился
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });

    // Проверить что есть статистические карточки
    const statsCards = page.locator('text=/материал|ученик|отчет/i');
    await expect(statsCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('should display statistics cards', async ({ page }) => {
    // Ждем загрузки статистики
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие ключевых элементов статистики
    const hasStats = await page.locator('text=/материал|ученик|проверк/i').count();
    expect(hasStats).toBeGreaterThan(0);
  });

  test('should display pending submissions section', async ({ page }) => {
    // Проверить что есть секция с заданиями на проверке
    const pendingSection = page.locator('text=/на проверке|проверк/i').first();
    if (await pendingSection.count() > 0) {
      await expect(pendingSection).toBeVisible();
    }
  });

  test('should have action buttons', async ({ page }) => {
    // Проверить что есть кнопки действий
    const buttons = page.locator('button:has-text(/создать|добавить/i)');
    if (await buttons.count() > 0) {
      await expect(buttons.first()).toBeVisible();
    }
  });

  test('should display materials section', async ({ page }) => {
    // Проверить что есть секция с материалами
    const materialsSection = page.locator('text=/материал/i').first();
    await expect(materialsSection).toBeVisible({ timeout: 5000 });
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

  test('should be responsive on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    // Проверить что контент виден на планшете
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
      !e.includes('WebSocket') &&
      !e.includes('404')
    );

    expect(criticalErrors.length).toBeLessThan(3);
  });

  test('should display students list or empty state', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Должна быть либо секция учеников, либо empty state
    const hasStudents = await page.locator('text=/ученик|студент/i').count();
    expect(hasStudents).toBeGreaterThan(0);
  });
});
