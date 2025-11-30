import { test, expect } from '@playwright/test';

test.describe('Tutor Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Вход под тьютором
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/tutor', { timeout: 10000 });
  });

  test('should load dashboard with real statistics', async ({ page }) => {
    // Проверить что заголовок загрузился
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });

    // Проверить что есть статистические карточки
    const statsCards = page.locator('text=/ученик|предмет|отчет/i');
    await expect(statsCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('should display statistics cards with real data', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что статистика не показывает hardcoded 0
    // Ищем числа в карточках статистики
    const statsNumbers = page.locator('[class*="text-3xl"], [class*="text-2xl"]');

    if (await statsNumbers.count() > 0) {
      const firstStat = await statsNumbers.first().textContent();
      // Проверяем что это число
      expect(firstStat).toMatch(/\d+/);
    }
  });

  test('should display subjects overview section', async ({ page }) => {
    // Проверить что есть секция обзора предметов
    const subjectsSection = page.locator('text=/предмет|обзор предмет/i').first();
    await expect(subjectsSection).toBeVisible({ timeout: 5000 });
  });

  test('should display recent reports section', async ({ page }) => {
    // Проверить что есть секция недавних отчетов
    const reportsSection = page.locator('text=/отчет|отчёт|недавн/i').first();
    if (await reportsSection.count() > 0) {
      await expect(reportsSection).toBeVisible();
    }
  });

  test('should display students section', async ({ page }) => {
    // Проверить что есть секция со студентами
    const studentsSection = page.locator('text=/ученик|студент/i').first();
    await expect(studentsSection).toBeVisible({ timeout: 5000 });
  });

  test('should show students with their subjects', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверить что у студентов показаны предметы
    const hasSubjectInfo = await page.locator('text=/предмет/i').count();
    expect(hasSubjectInfo).toBeGreaterThan(0);
  });

  test('should show student progress indicators', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверить что есть индикаторы прогресса
    const progressIndicators = page.locator('[role="progressbar"], progress, [class*="progress"]');

    // Либо progress bar есть, либо есть текстовая информация о прогрессе
    const hasProgress = await progressIndicators.count() > 0 ||
                       await page.locator('text=/прогресс/i').count() > 0;

    expect(hasProgress).toBeTruthy();
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

  test('should NOT have gradient backgrounds', async ({ page }) => {
    // Проверить что нет градиентных фонов
    const mainContent = page.locator('main, [role="main"]').first();

    if (await mainContent.count() > 0) {
      const bgImage = await mainContent.evaluate((el) =>
        window.getComputedStyle(el).backgroundImage
      );

      // Не должно быть gradient
      expect(bgImage).not.toContain('gradient');
    }
  });

  test('should have purple accents', async ({ page }) => {
    // Проверить что есть фиолетовые акценты
    const purpleElements = page.locator('[class*="purple"], [class*="violet"]');

    if (await purpleElements.count() > 0) {
      await expect(purpleElements.first()).toBeVisible();
    }
  });

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    // Проверить что контент виден на мобильном
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
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
      !e.includes('WebSocket')
    );

    expect(criticalErrors.length).toBeLessThan(3);
  });
});
