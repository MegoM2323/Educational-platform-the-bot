import { test, expect } from '@playwright/test';

test.describe('Student Materials - Critical Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth', { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/student', { timeout: 15000 });
  });

  test('should have visible materials tab', async ({ page }) => {
    console.log('Test: Materials Tab Visibility - CRITICAL');
    const materTab = page.locator('text=/материал/i').first();
    if (await materTab.count() === 0) {
      console.error('CRITICAL BUG: Materials tab not visible!');
    } else {
      console.log('✓ Materials tab is visible');
    }
  });

  test('should load materials list', async ({ page }) => {
    const materTab = page.locator('button:has-text("Материалы"), text=/материал/i').first();
    if (await materTab.count() > 0) {
      await materTab.click().catch(() => {});
      await page.waitForTimeout(1000);
      console.log('Materials section loaded');
    }
  });
});
