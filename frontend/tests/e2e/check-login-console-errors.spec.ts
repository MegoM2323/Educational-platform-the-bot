import { test } from '@playwright/test';

test('Check login console errors', async ({ page }) => {
  const consoleMessages: string[] = [];

  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    consoleMessages.push(`[${type.toUpperCase()}] ${text}`);
    console.log(`[${type.toUpperCase()}] ${text}`);
  });

  page.on('pageerror', error => {
    console.log(`[PAGE ERROR] ${error.message}`);
    consoleMessages.push(`[PAGE ERROR] ${error.message}`);
  });

  console.log('=== Navigating to login page ===');
  await page.goto('http://localhost:8080/auth');
  await page.waitForLoadState('networkidle');

  console.log('\n=== Filling credentials ===');
  await page.locator('input[type="email"]').fill('student@test.com');
  await page.locator('input[type="password"]').fill('testpass123');

  console.log('\n=== Clicking login button ===');
  await page.locator('button:has-text("Войти")').click();

  // Wait for response and any errors
  await page.waitForTimeout(4000);

  console.log('\n=== All console messages ===');
  console.log(`Total messages: ${consoleMessages.length}`);

  const errors = consoleMessages.filter(m => m.includes('[ERROR]') || m.includes('[WARN]'));
  console.log(`\nErrors/Warnings (${errors.length}):`);
  errors.forEach(e => console.log(e));
});
