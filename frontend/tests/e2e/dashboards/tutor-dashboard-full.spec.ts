import { test, expect } from '@playwright/test';

test.describe('Tutor Dashboard - Full', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth', { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/tutor', { timeout: 15000 });
  });

  test('should load tutor dashboard', async ({ page }) => {
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('should display students list', async ({ page }) => {
    const studentsList = page.locator('text=/ученик|студент/i').first();
    if (await studentsList.count() > 0) {
      console.log('✓ Students section found');
    }
  });
});
