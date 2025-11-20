import { test, expect } from '@playwright/test';

test.describe('Teacher Reports UI', () => {
  test('should open reports page and show header', async ({ page }) => {
    // Предполагаем, что есть маршрут /dashboard/teacher/reports
    await page.goto('/');
    // Эта часть зависит от существующей навигации. Проверяем страницу Reports учителя напрямую, если настроен роутер.
    await page.goto('/teacher/reports');
    await expect(page.getByText('Отчёты по предмету')).toBeVisible();
  });
});


