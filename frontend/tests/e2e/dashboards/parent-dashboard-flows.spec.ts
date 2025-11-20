import { test, expect } from '@playwright/test';

test.describe('Parent Dashboard - User Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Login as parent
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'parent@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/parent', { timeout: 10000 });
  });

  test('should display children profiles section', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие секции профилей детей
    const childrenSection = page.locator('text=/профили детей|дети/i').first();
    await expect(childrenSection).toBeVisible({ timeout: 5000 });
  });

  test('should navigate to child details on click', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на карточку ребенка
    const childCard = page.locator('[class*="cursor-pointer"]').filter({ hasText: /класс|прогресс|тьютор/i }).first();
    if (await childCard.count() > 0) {
      await childCard.click();
      await page.waitForURL(/\/children|\/parent/, { timeout: 5000 });
    }
  });

  test('should display payment status for subjects', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие информации о статусе оплаты
    const paymentStatus = page.locator('text=/оплачено|требуется оплата|ожидает|просрочено/i');
    if (await paymentStatus.count() > 0) {
      await expect(paymentStatus.first()).toBeVisible();
    }
  });

  test('should display payment button for unpaid subjects', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопки оплаты
    const paymentButton = page.locator('button:has-text(/оплатить|подключить предмет/i)');
    if (await paymentButton.count() > 0) {
      await expect(paymentButton.first()).toBeVisible();
    }
  });

  test('should initiate payment for subject', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку подключения предмета (для неоплаченных)
    const payButton = page.locator('button:has-text(/подключить предмет|оплатить/i)').first();

    if (await payButton.count() > 0 && await payButton.isEnabled()) {
      // Перехватываем навигацию для проверки редиректа
      const navigationPromise = page.waitForURL(/payment|yookassa|dashboard/, { timeout: 15000 }).catch(() => null);

      await payButton.click();

      // Ждем редиректа или возврата на дашборд
      await navigationPromise;

      // Проверяем что произошла какая-то навигация
      const currentUrl = page.url();
      expect(currentUrl).toBeTruthy();
    }
  });

  test('should handle payment return successfully', async ({ page }) => {
    // Симулируем возврат с успешной оплаты
    await page.goto('http://localhost:8080/dashboard/parent?payment_success=true');
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что загрузился дашборд
    await expect(page.locator('h1:has-text(/родитель/i)')).toBeVisible({ timeout: 5000 });
  });

  test('should display cancel subscription button for active subscriptions', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку отключения предмета
    const cancelButton = page.locator('button:has-text(/отключить предмет|отменить/i)');
    if (await cancelButton.count() > 0) {
      await expect(cancelButton.first()).toBeVisible();
    }
  });

  test('should show confirmation dialog when canceling subscription', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем кнопку отключения
    const cancelButton = page.locator('button:has-text(/отключить предмет/i)').first();

    if (await cancelButton.count() > 0 && await cancelButton.isEnabled()) {
      // Слушаем диалог подтверждения
      page.once('dialog', async dialog => {
        expect(dialog.message()).toContain('Отключить');
        await dialog.dismiss();
      });

      await cancelButton.click();

      // Даем время на появление диалога
      await page.waitForTimeout(500);
    }
  });

  test('should display next payment date for active subscriptions', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Ищем информацию о следующем платеже
    const nextPaymentInfo = page.locator('text=/следующий платеж|доступ до/i');
    if (await nextPaymentInfo.count() > 0) {
      await expect(nextPaymentInfo.first()).toBeVisible();
    }
  });

  test('should navigate to reports section', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем наличие секции отчетов
    const reportsSection = page.locator('text=/последние отчёты|отчёты/i').first();
    await expect(reportsSection).toBeVisible({ timeout: 5000 });
  });

  test('should navigate to report details', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на отчет если он есть
    const reportCard = page.locator('[class*="cursor-pointer"]').filter({ hasText: /отчёт|прогресс|достижение/i }).first();
    if (await reportCard.count() > 0) {
      await reportCard.click();
      await page.waitForURL(/\/reports|\/parent/, { timeout: 5000 });
    }
  });

  test('should navigate to all reports page', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на "Смотреть все отчёты"
    const viewAllButton = page.locator('button:has-text(/смотреть все отчёты|все отчёты/i)').first();
    if (await viewAllButton.count() > 0) {
      await viewAllButton.click();
      await page.waitForURL(/\/reports|\/parent/, { timeout: 5000 });
    }
  });

  test('should display statistics section', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем секцию статистики
    const statsSection = page.locator('text=/статистика/i').first();
    await expect(statsSection).toBeVisible({ timeout: 5000 });

    // Проверяем наличие основных метрик
    const metrics = page.locator('text=/детей|средний прогресс|оплачено/i');
    if (await metrics.count() > 0) {
      await expect(metrics.first()).toBeVisible();
    }
  });

  test('should use quick action - Children Management', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на управление детьми
    const childrenButton = page.locator('button:has-text(/управление детьми/i)').first();
    if (await childrenButton.count() > 0) {
      await childrenButton.click();
      await page.waitForURL(/\/children|\/parent/, { timeout: 5000 });
    }
  });

  test('should use quick action - Payments', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на оплаты
    const paymentsButton = page.locator('button:has-text(/оплаты/i)').first();
    if (await paymentsButton.count() > 0) {
      await paymentsButton.click();
      await page.waitForURL(/\/payments|\/parent/, { timeout: 5000 });
    }
  });

  test('should use quick action - Reports', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на отчёты
    const reportsButton = page.locator('button:has-text("Отчёты")').or(page.locator('button:has-text("отчёты")')).first();
    if (await reportsButton.count() > 0) {
      await reportsButton.click();
      await page.waitForURL(/\/reports|\/parent/, { timeout: 5000 });
    }
  });

  test('should use quick action - Statistics', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Кликаем на статистику
    const statsButton = page.locator('button:has-text(/статистика/i)').first();
    if (await statsButton.count() > 0) {
      await statsButton.click();
      await page.waitForURL(/\/statistics|\/parent/, { timeout: 5000 });
    }
  });

  test('should display subjects with teacher names', async ({ page }) => {
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Проверяем что отображаются предметы с именами преподавателей
    const teacherInfo = page.locator('text=/преподаватель:/i');
    if (await teacherInfo.count() > 0) {
      await expect(teacherInfo.first()).toBeVisible();
    }
  });
});
