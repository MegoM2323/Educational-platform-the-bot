import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';

test('Login API Diagnosis', async ({ page }) => {
  console.log('\n========== LOGIN API DIAGNOSIS ==========\n');

  const apiCalls: any[] = [];
  const consoleMessages: any[] = [];

  // Capture all console messages
  page.on('console', (msg) => {
    consoleMessages.push({ type: msg.type(), text: msg.text() });
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });

  // Capture all API calls
  page.on('response', async (response) => {
    const url = response.url();
    const call = {
      url,
      status: response.status(),
      method: response.request().method(),
      body: null as any,
    };

    // Log API calls
    if (url.includes('/api/')) {
      console.log(`\n📡 API CALL: ${call.method} ${url}`);
      console.log(`   Status: ${call.status}`);

      // Try to read response body
      try {
        const contentType = response.headers()['content-type'] || '';
        if (contentType.includes('application/json')) {
          call.body = await response.json();
          console.log(`   Response:`, JSON.stringify(call.body, null, 2));
        } else {
          const text = await response.text();
          console.log(`   Response: ${text.substring(0, 200)}`);
        }
      } catch (e) {
        console.log(`   (Could not read response body)`);
      }

      apiCalls.push(call);
    }
  });

  // Capture request bodies
  page.on('request', (request) => {
    if (request.url().includes('/api/')) {
      const postData = request.postData();
      if (postData) {
        console.log(`\n📤 REQUEST BODY for ${request.method()} ${request.url()}:`);
        console.log(postData);
      }
    }
  });

  // Navigate to auth page
  console.log('1. Navigating to /auth...');
  await page.goto(`${BASE_URL}/auth`);
  await page.waitForLoadState('networkidle');

  // Fill login form
  console.log('\n2. Filling login form...');
  await page.getByTestId('login-email-input').fill('test_student@test.com');
  await page.getByTestId('login-password-input').fill('test123');

  // Click login button
  console.log('\n3. Clicking login button...');
  await page.getByTestId('login-submit-button').click();

  // Wait for navigation or error
  console.log('\n4. Waiting for response...');
  await page.waitForTimeout(5000);

  const currentUrl = page.url();
  console.log(`\n5. Current URL after login: ${currentUrl}`);

  // Check for toast messages
  const toasts = await page.locator('[data-sonner-toast]').allTextContents();
  console.log(`\n6. Toast messages: ${toasts.length > 0 ? JSON.stringify(toasts) : 'None'}`);

  // Check localStorage
  const authToken = await page.evaluate(() => localStorage.getItem('authToken'));
  const userData = await page.evaluate(() => localStorage.getItem('userData'));
  console.log(`\n7. LocalStorage authToken: ${authToken ? 'EXISTS' : 'NULL'}`);
  console.log(`   LocalStorage userData: ${userData ? 'EXISTS' : 'NULL'}`);

  // Summary
  console.log('\n========== API CALLS SUMMARY ==========');
  apiCalls.forEach((call) => {
    console.log(`${call.method} ${call.url} - ${call.status}`);
    if (call.body) {
      console.log(`  Response: ${JSON.stringify(call.body).substring(0, 100)}...`);
    }
  });

  console.log('\n========== CONSOLE ERRORS ==========');
  const errors = consoleMessages.filter((m) => m.type === 'error');
  errors.forEach((err) => console.log(err.text));

  console.log('\n========================================\n');
});
