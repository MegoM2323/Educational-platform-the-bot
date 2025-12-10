import { test, expect } from '@playwright/test';

test.describe('T604: Simple Tutor Profile Test', () => {
  test('Check if profile page is accessible via direct navigation', async ({ page, context }) => {
    console.log('\n' + '='.repeat(60));
    console.log('T604: Simple Tutor Profile Test');
    console.log('='.repeat(60));

    // Disable proxy for API requests
    const origFetch = context.request;

    // Log all network responses
    page.on('response', response => {
      const status = response.status();
      const url = response.url();
      if (status >= 400 && url.includes('localhost')) {
        console.log(`  [${status}] ${url}`);
      }
    });

    // Log console messages
    page.on('console', msg => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        console.log(`  [${msg.type().toUpperCase()}] ${msg.text()}`);
      }
    });

    // Test 1: Get token via API
    console.log('\n[TEST 1] Login via API to get token');
    const loginResp = await page.request.post('http://127.0.0.1:8000/api/auth/login/', {
      data: {
        email: 'tutor@test.com',
        password: 'TestPass123!'
      }
    });

    console.log(`  Response status: ${loginResp.status()}`);
    if (!loginResp.ok()) {
      console.log('  ❌ Login failed via API');
      const body = await loginResp.text();
      console.log(`  Response body: ${body}`);
      throw new Error('API login failed');
    }

    const loginData = await loginResp.json();
    console.log(`  Login response keys: ${Object.keys(loginData).join(', ')}`);

    // Get token from response
    let token = loginData.data?.access || loginData.access || loginData.token;
    if (!token && loginData.data && typeof loginData.data === 'object') {
      token = Object.values(loginData.data).find(v => typeof v === 'string' && v.length > 20);
    }

    if (!token) {
      console.log('  ❌ No token found in response');
      console.log(`  Full response: ${JSON.stringify(loginData)}`);
      throw new Error('No token in response');
    }

    console.log(`  ✅ Token obtained: ${token.substring(0, 20)}...`);

    // Test 2: Try to load profile page with token in header
    console.log('\n[TEST 2] Navigate to /profile/tutor with auth header');

    // Set auth header for all requests
    await context.addInitScript(`
      window.localStorage.setItem('auth_token', '${token}');
      window.localStorage.setItem('user_id', '1');
    `);

    await page.goto('http://localhost:8081/profile/tutor', { waitUntil: 'networkidle' });

    const pageUrl = page.url();
    console.log(`  URL: ${pageUrl}`);

    if (pageUrl.includes('/profile/tutor') || pageUrl.includes('/profile')) {
      console.log('  ✅ Profile page loaded');
    } else if (pageUrl.includes('/auth')) {
      console.log('  ❌ Still on auth page');
    }

    // Screenshot
    await page.screenshot({ path: '/tmp/qa_tutor_screenshots/simple_test_profile.png' });

    // Test 3: Check for form content
    console.log('\n[TEST 3] Check page content');
    const content = await page.content();

    if (content.includes('specialization') || content.includes('специализа')) {
      console.log('  ✅ Form content found');
    } else {
      console.log('  ⚠️ Form content NOT found');
      console.log('  First 500 chars:', content.substring(0, 500));
    }

    // Test 4: Look for form fields
    console.log('\n[TEST 4] Look for form fields');
    const inputs = page.locator('input, textarea');
    const count = await inputs.count();
    console.log(`  Found ${count} input/textarea elements`);

    if (count > 0) {
      for (let i = 0; i < Math.min(count, 5); i++) {
        const el = inputs.nth(i);
        const name = await el.getAttribute('name');
        const placeholder = await el.getAttribute('placeholder');
        console.log(`    ${i + 1}. name="${name}" placeholder="${placeholder}"`);
      }
    }

    // Test 5: Call API to get profile data
    console.log('\n[TEST 5] Get profile data via API');
    const profileResp = await page.request.get('http://127.0.0.1:8000/api/profile/tutor/', {
      headers: {
        'Authorization': `Token ${token}`
      }
    });

    console.log(`  Response status: ${profileResp.status()}`);
    if (profileResp.ok()) {
      const profileData = await profileResp.json();
      console.log(`  ✅ Profile data received`);
      console.log(`  Keys: ${Object.keys(profileData).join(', ')}`);
    } else {
      console.log(`  ❌ Profile API failed`);
      const body = await profileResp.text();
      console.log(`  Response: ${body.substring(0, 200)}`);
    }

    console.log('\n' + '='.repeat(60));
  });
});
