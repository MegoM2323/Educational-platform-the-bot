import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';

test('Debug: Login and check console/network', async ({ page }) => {
  const consoleLogs: string[] = [];
  const networkErrors: string[] = [];

  // Capture console logs
  page.on('console', msg => {
    const text = `[${msg.type()}] ${msg.text()}`;
    consoleLogs.push(text);
    console.log(text);
  });

  // Capture failed requests
  page.on('requestfailed', request => {
    const error = `NETWORK ERROR: ${request.method()} ${request.url()} - ${request.failure()?.errorText}`;
    networkErrors.push(error);
    console.log(error);
  });

  // Capture API responses
  page.on('response', async response => {
    if (response.url().includes('/api/')) {
      const status = response.status();
      const url = response.url();
      console.log(`API Response: ${status} ${url}`);

      if (status >= 400) {
        try {
          const body = await response.text();
          console.log(`ERROR Response body: ${body.substring(0, 500)}`);
        } catch {}
      }
    }
  });

  // Navigate to login
  console.log('=== Navigating to /auth ===');
  await page.goto(`${BASE_URL}/auth`);
  await page.waitForLoadState('networkidle');

  // Login
  console.log('=== Filling credentials ===');
  await page.locator('input[type="email"]').fill('student@test.com');
  await page.locator('input[type="password"]').fill('testpass123');

  console.log('=== Clicking login button ===');
  await page.locator('button:has-text("Войти")').click();

  // Wait for navigation or error
  console.log('=== Waiting for navigation ===');
  try {
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });
    console.log('✅ URL changed to dashboard');
  } catch (e) {
    console.log('❌ URL did NOT change to dashboard');
    console.log('Current URL:', page.url());
  }

  // Wait a bit to capture all network requests
  await page.waitForTimeout(5000);

  // Check what's on the page
  const bodyText = await page.locator('body').textContent();
  console.log(`\n=== PAGE CONTENT ===`);
  console.log(`Body length: ${bodyText?.length || 0} chars`);
  console.log(`Body text: ${bodyText?.substring(0, 200)}`);

  // Check localStorage
  const accessToken = await page.evaluate(() => localStorage.getItem('access_token'));
  const refreshToken = await page.evaluate(() => localStorage.getItem('refresh_token'));
  const user = await page.evaluate(() => localStorage.getItem('user'));

  console.log(`\n=== LOCALSTORAGE ===`);
  console.log(`access_token: ${accessToken ? 'EXISTS (length: ' + accessToken.length + ')' : 'MISSING'}`);
  console.log(`refresh_token: ${refreshToken ? 'EXISTS' : 'MISSING'}`);
  console.log(`user: ${user ? user.substring(0, 100) : 'MISSING'}`);

  // Save screenshot
  await page.screenshot({ path: '/tmp/debug-login.png', fullPage: true });
  console.log('\nScreenshot saved: /tmp/debug-login.png');

  // Summary
  console.log(`\n=== SUMMARY ===`);
  console.log(`Console logs: ${consoleLogs.length}`);
  console.log(`Network errors: ${networkErrors.length}`);
  if (networkErrors.length > 0) {
    console.log('Network errors:', networkErrors);
  }
});
