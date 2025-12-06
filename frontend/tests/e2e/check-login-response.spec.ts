import { test } from '@playwright/test';

test('Check login response and token storage', async ({ page }) => {
  page.on('response', async response => {
    if (response.url().includes('/api/auth/login/')) {
      const status = response.status();
      console.log(`\n=== LOGIN API RESPONSE ===`);
      console.log(`Status: ${status}`);

      try {
        const body = await response.json();
        console.log('Response body:', JSON.stringify(body, null, 2));
      } catch (e) {
        const text = await response.text();
        console.log('Response text:', text);
      }
    }
  });

  console.log('=== Navigating to login page ===');
  await page.goto('http://localhost:8080/auth');
  await page.waitForLoadState('networkidle');

  console.log('=== Filling credentials ===');
  await page.locator('input[type="email"]').fill('student@test.com');
  await page.locator('input[type="password"]').fill('testpass123');

  console.log('=== Clicking login button ===');
  await page.locator('button:has-text("Войти")').click();

  // Wait for API call to complete
  await page.waitForTimeout(3000);

  console.log('\n=== Checking localStorage ===');
  const tokens = await page.evaluate(() => ({
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
    user: localStorage.getItem('user'),
    authToken: localStorage.getItem('authToken'),
    userData: localStorage.getItem('userData'),
  }));

  console.log('LocalStorage content:');
  for (const [key, value] of Object.entries(tokens)) {
    if (value) {
      console.log(`  ${key}: ${value.substring(0, 50)}...`);
    } else {
      console.log(`  ${key}: MISSING`);
    }
  }

  console.log('\n=== Current URL ===');
  console.log(page.url());

  console.log('\n=== Page body text ===');
  const body = await page.locator('body').textContent();
  console.log(body?.substring(0, 200));
});
