import { test } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';

test('Debug: Login API call details', async ({ page }) => {
  // Capture ALL requests
  page.on('request', request => {
    const url = request.url();
    if (url.includes('/api/')) {
      console.log(`>>> REQUEST: ${request.method()} ${url}`);
      if (request.method() === 'POST') {
        try {
          const postData = request.postData();
          console.log(`    POST data: ${postData}`);
        } catch {}
      }
    }
  });

  // Capture ALL responses
  page.on('response', async response => {
    const url = response.url();
    if (url.includes('/api/')) {
      const status = response.status();
      console.log(`<<< RESPONSE: ${status} ${url}`);

      try {
        const body = await response.text();
        console.log(`    Response body: ${body.substring(0, 300)}`);
      } catch {}
    }
  });

  // Navigate to login
  console.log('\n=== Step 1: Navigate to /auth ===');
  await page.goto(`${BASE_URL}/auth`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);

  // Check initial state
  console.log('\n=== Step 2: Check initial localStorage ===');
  let tokens = await page.evaluate(() => ({
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
    user: localStorage.getItem('user'),
  }));
  console.log('Initial localStorage:', {
    access: tokens.access ? 'EXISTS' : 'MISSING',
    refresh: tokens.refresh ? 'EXISTS' : 'MISSING',
    user: tokens.user ? tokens.user.substring(0, 50) : 'MISSING'
  });

  // Fill and submit form
  console.log('\n=== Step 3: Fill login form ===');
  await page.locator('input[type="email"]').fill('student@test.com');
  await page.locator('input[type="password"]').fill('testpass123');

  console.log('\n=== Step 4: Click login button and wait ===');
  await page.locator('button:has-text("Войти")').click();

  // Wait a bit for API call
  await page.waitForTimeout(2000);

  // Check localStorage after login attempt
  console.log('\n=== Step 5: Check localStorage after login ===');
  tokens = await page.evaluate(() => ({
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
    user: localStorage.getItem('user'),
  }));
  console.log('After login localStorage:', {
    access: tokens.access ? `EXISTS (${tokens.access.substring(0, 20)}...)` : 'MISSING',
    refresh: tokens.refresh ? 'EXISTS' : 'MISSING',
    user: tokens.user ? tokens.user : 'MISSING'
  });

  // Check current URL
  console.log('\n=== Step 6: Current state ===');
  console.log('Current URL:', page.url());

  const bodyText = await page.locator('body').textContent();
  console.log('Body text:', bodyText?.substring(0, 100));

  await page.screenshot({ path: '/tmp/debug-login-detailed.png', fullPage: true });
  console.log('\nScreenshot saved');
});
