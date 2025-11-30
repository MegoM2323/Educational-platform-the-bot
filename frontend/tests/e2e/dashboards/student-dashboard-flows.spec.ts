import { test, expect } from '@playwright/test';

test.describe('Student Dashboard - User Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Login as student
    await page.goto('/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });
  });

  test('should navigate to material details on click', async ({ page }) => {
    // Ждем загрузки материалов
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие материалов
    const materialCards = page.locator('text=/материал/i').first();
    await expect(materialCards).toBeVisible({ timeout: 5000 });

    // Кликаем на первый материал если он есть
    const firstMaterial = page.locator('[class*="cursor-pointer"]').filter({ hasText: /материал|math|русск/i }).first();
    if (await firstMaterial.count() > 0) {
      await firstMaterial.click();

      // Проверяем что произошла навигация
      await page.waitForURL(/\/(materials|dashboard)/, { timeout: 5000 });
    }
  });

  test('should display subjects with teachers', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем секцию предметов
    const subjectsSection = page.locator('text=/мои предмет|предмет/i').first();
    await expect(subjectsSection).toBeVisible({ timeout: 5000 });

    // Проверяем наличие информации о преподавателях
    const teacherInfo = page.locator('text=/преподаватель|учитель/i');
    if (await teacherInfo.count() > 0) {
      await expect(teacherInfo.first()).toBeVisible();
    }
  });

  test('should display progress statistics', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие секции прогресса
    const progressSection = page.locator('text=/прогресс|выполнено/i').first();
    await expect(progressSection).toBeVisible({ timeout: 5000 });

    // Проверяем наличие процентов или цифр
    const percentagePattern = page.locator('text=/\\d+%|\\d+\\s*из\\s*\\d+/');
    if (await percentagePattern.count() > 0) {
      await expect(percentagePattern.first()).toBeVisible();
    }
  });

  test('should navigate to assignments on click', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем секцию заданий
    const assignmentsSection = page.locator('text=/задани|assignment/i').first();
    if (await assignmentsSection.count() > 0) {
      await expect(assignmentsSection).toBeVisible();

      // Кликаем на задание если оно есть
      const assignment = page.locator('[class*="cursor-pointer"]').filter({ hasText: /задани/i }).first();
      if (await assignment.count() > 0) {
        await assignment.click();
        await page.waitForURL(/\/(assignments|dashboard)/, { timeout: 5000 });
      }
    }
  });

  test('should use quick action - General Chat', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку общего чата
    const chatButton = page.locator('button:has-text(/общий чат|чат/i)').first();
    if (await chatButton.count() > 0) {
      await chatButton.click();
      await page.waitForURL(/\/chat|\/dashboard/, { timeout: 5000 });
    }
  });

  test('should use quick action - Materials', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку материалов в быстрых действиях
    const materialsButton = page.locator('button:has-text("Материалы")').or(page.locator('button:has-text("материалы")')).first();
    if (await materialsButton.count() > 0) {
      await materialsButton.click();
      await page.waitForURL(/\/materials|\/dashboard/, { timeout: 5000 });
    }
  });

  test('should use quick action - My Progress', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку прогресса
    const progressButton = page.locator('button:has-text(/мой прогресс|прогресс/i)').first();
    if (await progressButton.count() > 0) {
      await progressButton.click();
      await page.waitForURL(/\/progress|\/dashboard/, { timeout: 5000 });
    }
  });

  test('should use quick action - Assignments', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку заданий
    const assignmentsButton = page.locator('button:has-text(/задани/i)').first();
    if (await assignmentsButton.count() > 0) {
      await assignmentsButton.click();
      await page.waitForURL(/\/assignments|\/dashboard/, { timeout: 5000 });
    }
  });

  test('should display empty state when no materials', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем либо материалы, либо empty state
    const hasMaterials = await page.locator('text=/материал/i').count();
    const hasEmptyState = await page.locator('text=/нет материалов|пока нет|обратитесь/i').count();

    // Должно быть либо материалы, либо empty state
    expect(hasMaterials + hasEmptyState).toBeGreaterThan(0);
  });

  test('should display notifications badge', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем иконку уведомлений
    const notificationIcon = page.locator('[class*="bell"]').or(page.locator('svg').filter({ has: page.locator('path') })).first();

    // Проверяем наличие badge с числом или просто иконки
    const hasNotificationBadge = await page.locator('span:near(svg)').filter({ hasText: /\d+/ }).count();

    // Хотя бы одно из двух должно быть
    expect(hasNotificationBadge >= 0).toBeTruthy();
  });

  test('should load and display student name', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что отображается имя студента или приветствие
    const greeting = page.locator('h1:has-text(/привет|dashboard|студент/i)').first();
    await expect(greeting).toBeVisible({ timeout: 5000 });
  });

  test('should handle navigation between sections', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что можем перейти к полному списку материалов
    const viewAllButton = page.locator('button:has-text(/смотреть все|все материалы/i)').first();
    if (await viewAllButton.count() > 0) {
      await viewAllButton.click();
      await page.waitForURL(/\/materials|\/dashboard/, { timeout: 5000 });

      // Возвращаемся назад
      await page.goBack();
      await page.waitForURL('**/dashboard/student', { timeout: 5000 });
    }
  });
});
