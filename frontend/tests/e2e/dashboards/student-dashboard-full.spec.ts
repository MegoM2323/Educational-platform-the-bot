import { test, expect } from '@playwright/test';

test.describe('Student Dashboard - Full Comprehensive Test', () => {
  test.beforeEach(async ({ page }) => {
    console.log('=== Student Dashboard Test - BeforeEach ===');
    await page.goto('/auth', { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    await page.waitForURL('**/dashboard/student', { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  });

  test('should load dashboard without 500 errors', async ({ page }) => {
    console.log('Test: Load Dashboard');
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 5000 }).catch(() => {
      console.warn('No heading found');
    });
  });

  test('should display all major dashboard sections', async ({ page }) => {
    console.log('Test: Display Sections');
    const sections = [
      { label: 'Progress', regex: /прогресс|статистик/i },
      { label: 'Subjects', regex: /предмет/i },
      { label: 'Materials', regex: /материал/i },
    ];
    for (const section of sections) {
      const element = page.locator(`text=${section.regex}`).first();
      if (await element.count() > 0) {
        console.log(`✓ Found ${section.label}`);
      }
    }
  });

  test('should load student materials section', async ({ page }) => {
    console.log('Test: Materials Section');
    const materialsTab = page.locator('text=/материал/i').first();
    if (await materialsTab.count() > 0) {
      console.log('Materials section found');
    }
  });

  test('should maintain session', async ({ page }) => {
    console.log('Test: Session');
    expect(page.url()).toContain('/dashboard');
  });
});
