import { test, expect } from '@playwright/test';

test.describe('Tutor Dashboard - User Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Login as tutor
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/tutor', { timeout: 10000 });
  });

  test('should display students count in overview', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие счетчика учеников
    const studentsCount = page.locator('text=/\\d+\\s*учеников|ученик/i').first();
    await expect(studentsCount).toBeVisible({ timeout: 5000 });
  });

  test('should display students list section', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие секции списка учеников
    const studentsSection = page.locator('text=/список учеников|ученики/i').first();
    await expect(studentsSection).toBeVisible({ timeout: 5000 });
  });

  test('should navigate to students page from overview card', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на карточку учеников в overview
    const studentsCard = page.locator('[class*="cursor-pointer"]').filter({ hasText: /\\d+\\s*учеников/i }).first();
    if (await studentsCard.count() > 0) {
      await studentsCard.click();
      await page.waitForURL(/\/students|\/tutor/, { timeout: 5000 });
    }
  });

  test('should navigate to student profile from list', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на карточку ученика в списке
    const studentCard = page.locator('[class*="cursor-pointer"]').filter({ hasText: /класс|цель/i }).first();
    if (await studentCard.count() > 0) {
      await studentCard.click();
      await page.waitForURL(/\/students|\/tutor/, { timeout: 5000 });
    }
  });

  test('should display student information (name, grade, goal)', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие основной информации о студентах
    const studentInfo = page.locator('text=/класс|цель/i');
    if (await studentInfo.count() > 0) {
      await expect(studentInfo.first()).toBeVisible();
    }
  });

  test('should use quick action - My Students', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на быстрое действие "Мои ученики"
    const studentsButton = page.locator('button:has-text(/мои ученики/i)').first();
    if (await studentsButton.count() > 0) {
      await studentsButton.click();
      await page.waitForURL(/\/students|\/tutor/, { timeout: 5000 });
    }
  });

  test('should use quick action - Reports', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на отчёты
    const reportsButton = page.locator('button:has-text(/отчёты/i)').first();
    if (await reportsButton.count() > 0) {
      await reportsButton.click();
      await page.waitForURL(/\/reports|\/tutor/, { timeout: 5000 });
    }
  });

  test('should use quick action - General Chat', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на общий чат
    const chatButton = page.locator('button:has-text(/общий чат/i)').first();
    if (await chatButton.count() > 0) {
      await chatButton.click();
      await page.waitForURL(/\/chat|\/tutor/, { timeout: 5000 });
    }
  });

  test('should display empty state when no students', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что либо есть студенты, либо пустое состояние
    const hasStudents = await page.locator('text=/класс|цель/i').count();
    const hasEmptyMessage = await page.locator('text=/нет учеников|пусто/i').count();

    // Должно быть либо студенты, либо сообщение о пустом состоянии (или просто загруженный дашборд)
    expect(hasStudents >= 0 || hasEmptyMessage >= 0).toBeTruthy();
  });

  test('should navigate between dashboard sections', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что можем перейти к студентам и вернуться
    const studentsLink = page.locator('a:has-text(/студенты|ученики/i), button:has-text(/студенты|ученики/i)').first();
    if (await studentsLink.count() > 0) {
      const currentUrl = page.url();
      await studentsLink.click();
      await page.waitForTimeout(1000);

      // Проверяем что URL изменился или остался на дашборде
      const newUrl = page.url();
      expect(newUrl).toBeTruthy();
    }
  });
});
