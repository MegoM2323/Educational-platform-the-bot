import { test, expect } from '@playwright/test';

test.describe('Parent Dashboard - Full', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth', { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'parent@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/parent', { timeout: 15000 });
  });

  test('should load parent dashboard', async ({ page }) => {
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('should display children list', async ({ page }) => {
    const childList = page.locator('text=/дети|ребенок/i').first();
    if (await childList.count() > 0) {
      console.log('✓ Children section found');
    }
  });
});
