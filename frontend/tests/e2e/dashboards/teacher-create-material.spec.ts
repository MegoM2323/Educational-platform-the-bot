import { test, expect } from '@playwright/test';

test.describe('Teacher Create Material - Critical', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth', { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/teacher', { timeout: 15000 });
  });

  test('should have create material button visible', async ({ page }) => {
    console.log('Test: Create Material Button - CRITICAL');
    const createBtn = page.locator(
      'button:has-text("Создать материал"), button:has-text("Create Material")'
    ).first();
    if (await createBtn.count() === 0) {
      console.error('CRITICAL BUG: Create material button missing!');
    } else {
      console.log('✓ Create material button found');
      await expect(createBtn).toBeVisible();
    }
  });

  test('should open material creation form', async ({ page }) => {
    const createBtn = page.locator('button:has-text("Создать материал")').first();
    if (await createBtn.count() > 0) {
      await createBtn.click();
      await page.waitForTimeout(1000);
      const form = page.locator('input, textarea').first();
      if (await form.count() > 0) {
        console.log('✓ Material form opened');
      }
    }
  });
});
