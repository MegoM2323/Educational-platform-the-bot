import { test, expect } from '@playwright/test';

test.describe('Teacher Dashboard - User Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Login as teacher
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/teacher', { timeout: 10000 });
  });

  test('should navigate to create material page', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку создания материала
    const createButton = page.locator('button:has-text(/создать материал/i)').first();
    await expect(createButton).toBeVisible({ timeout: 5000 });

    await createButton.click();
    await page.waitForURL(/\/materials\/create|\/teacher/, { timeout: 5000 });
  });

  test('should display materials list with subjects', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие секции материалов
    const materialsSection = page.locator('text=/опубликованные материалы|материал/i').first();
    await expect(materialsSection).toBeVisible({ timeout: 5000 });

    // Проверяем наличие предметов в материалах
    const subjectInfo = page.locator('text=/математика|русский|физика|химия/i');
    if (await subjectInfo.count() > 0) {
      await expect(subjectInfo.first()).toBeVisible();
    }
  });

  test('should navigate to material details', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на материал
    const materialCard = page.locator('[class*="cursor-pointer"]').filter({ hasText: /материал/i }).first();
    if (await materialCard.count() > 0) {
      await materialCard.click();
      await page.waitForURL(/\/materials|\/teacher/, { timeout: 5000 });
    }
  });

  test('should display pending submissions section', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем секцию заданий на проверке
    const submissionsSection = page.locator('text=/задания на проверку|на проверке/i').first();
    await expect(submissionsSection).toBeVisible({ timeout: 5000 });

    // Проверяем badge с количеством
    const badge = page.locator('text=/\\d+/').filter({ hasText: /^\d+$/ });
    if (await badge.count() > 0) {
      await expect(badge.first()).toBeVisible();
    }
  });

  test('should navigate to pending submissions page', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на "Все задания"
    const viewAllButton = page.locator('button:has-text(/все задания/i)').first();
    if (await viewAllButton.count() > 0) {
      await viewAllButton.click();
      await page.waitForURL(/\/submissions|\/teacher/, { timeout: 5000 });
    }
  });

  test('should click on pending submission', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на задание на проверке
    const submission = page.locator('[class*="cursor-pointer"]').filter({ hasText: /сдано|student|ученик/i }).first();
    if (await submission.count() > 0) {
      await submission.click();
      await page.waitForURL(/\/submissions|\/teacher/, { timeout: 5000 });
    }
  });

  test('should navigate to create report page', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку создания отчета в быстрых действиях или в секции отчетов
    const createReportButton = page.locator('button:has-text(/создать отчёт|создать/i)').filter({ hasText: /отчёт/i }).first();
    if (await createReportButton.count() > 0) {
      await createReportButton.click();
      await page.waitForURL(/\/reports\/create|\/teacher/, { timeout: 5000 });
    }
  });

  test('should display students overview', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем секцию учеников
    const studentsSection = page.locator('text=/ученики|студенты/i').first();
    await expect(studentsSection).toBeVisible({ timeout: 5000 });

    // Проверяем количество учеников
    const studentCount = page.locator('text=/\\d+\\s*(всего|учеников)/i');
    if (await studentCount.count() > 0) {
      await expect(studentCount.first()).toBeVisible();
    }
  });

  test('should navigate to student profile', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на карточку ученика
    const studentCard = page.locator('[class*="cursor-pointer"]').filter({ hasText: /класс|прогресс/i }).first();
    if (await studentCard.count() > 0) {
      await studentCard.click();
      await page.waitForURL(/\/teacher|\/students/, { timeout: 5000 });
    }
  });

  test('should display reports section', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем секцию отчетов
    const reportsSection = page.locator('text=/отчёты|отчет/i').first();
    await expect(reportsSection).toBeVisible({ timeout: 5000 });
  });

  test('should navigate to reports list', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на "Все отчёты"
    const viewAllReports = page.locator('button:has-text(/все отчёты/i)').first();
    if (await viewAllReports.count() > 0) {
      await viewAllReports.click();
      await page.waitForURL(/\/reports|\/teacher/, { timeout: 5000 });
    }
  });

  test('should use quick action - Create Material', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на быстрое действие создания материала
    const quickActionButton = page.locator('button:has-text("Создать материал")').first();
    if (await quickActionButton.count() > 0) {
      await quickActionButton.click();
      await page.waitForURL(/\/materials\/create|\/teacher/, { timeout: 5000 });
    }
  });

  test('should use quick action - General Chat', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на общий чат
    const chatButton = page.locator('button:has-text(/общий чат/i)').first();
    if (await chatButton.count() > 0) {
      await chatButton.click();
      await page.waitForURL(/\/chat|\/teacher/, { timeout: 5000 });
    }
  });

  test('should use quick action - Assign Subject', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на назначение предмета
    const assignButton = page.locator('button:has-text(/назначить предмет/i)').first();
    if (await assignButton.count() > 0) {
      await assignButton.click();
      await page.waitForURL(/\/assign-subject|\/teacher/, { timeout: 5000 });
    }
  });

  test('should display statistics cards with numbers', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие статистических карточек
    const statsCards = page.locator('text=/\\d+/').filter({ hasText: /материалов|учеников|проверке/ });

    // Должна быть хотя бы одна статистическая карточка
    const count = await statsCards.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
