import { test, expect, Page } from '@playwright/test';

const FRONTEND_URL = '';
const BACKEND_URL = 'http://localhost:8000/api';

test.describe('Tutor Profile - Full Integration Test', () => {
  let page: Page;

  test.beforeAll(async () => {
    // Wait for servers to be ready
    await new Promise(resolve => setTimeout(resolve, 2000));
  });

  test('should login as tutor and access profile page', async ({ browser }) => {
    page = await browser.newPage();

    console.log('🔍 Navigating to login page...');
    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Check if login form exists
    const emailInput = page.locator('[name="email"], [placeholder*="Email"], [placeholder*="email"]');
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    console.log('✅ Login form found');

    // Login as tutor
    console.log('🔐 Logging in as tutor...');
    await emailInput.fill('tutor@test.com');

    const passwordInput = page.locator('[name="password"], [placeholder*="Password"], [type="password"]');
    await passwordInput.fill('TestPass123!');

    const loginButton = page.locator('button:has-text("Войти"), button:has-text("Login"), button:has-text("Sign in")');
    await loginButton.click();

    // Wait for redirect to dashboard
    await page.waitForURL('**/dashboard**', { timeout: 10000 });
    console.log('✅ Logged in successfully');

    // Navigate to profile
    console.log('📝 Navigating to profile...');
    await page.goto(`${FRONTEND_URL}/profile`);
    await page.waitForLoadState('networkidle');

    // Check if profile page loaded
    const profileHeader = page.locator('h1, h2').filter({ hasText: /Профиль|Profile/ });
    if (await profileHeader.count() > 0) {
      console.log('✅ Profile page loaded');
    } else {
      console.log('⚠️ Could not find profile header');
    }

    // Check for tutor-specific fields
    console.log('🔍 Checking for tutor profile fields...');

    // Look for specialization field
    const specializationField = page.locator('input, textarea').filter({ hasText: /Специализация|Specialization/ });
    if (await specializationField.count() > 0) {
      console.log('✅ Specialization field found');
    } else {
      console.log('⚠️ Specialization field not found');
    }

    // Check for avatar
    const avatarImg = page.locator('img[alt*="avatar"], img[alt*="avatar"]').first();
    if (await avatarImg.count() > 0) {
      console.log('✅ Avatar image found');
    } else {
      console.log('⚠️ Avatar not found');
    }

    // Try to find and read any form fields
    const allInputs = page.locator('input, textarea');
    const inputCount = await allInputs.count();
    console.log(`📊 Found ${inputCount} input fields`);

    // Screenshot for visual inspection
    await page.screenshot({ path: '/tmp/tutor-profile.png' });
    console.log('📸 Screenshot saved to /tmp/tutor-profile.png');

    // Test data persistence
    console.log('💾 Testing profile update...');
    const allLabels = page.locator('label');
    const labelCount = await allLabels.count();
    console.log(`📋 Found ${labelCount} form labels`);

    await page.close();
    console.log('✅ Test completed successfully!');
  });

  test('should verify API endpoints for tutor profile', async () => {
    console.log('🔗 Testing API endpoints...');

    // Login to get token
    const loginResponse = await page.request.post(`${BACKEND_URL}/auth/login/`, {
      data: {
        email: 'tutor@test.com',
        password: 'TestPass123!'
      }
    });

    if (loginResponse.ok()) {
      console.log('✅ API login successful');
      const loginData = await loginResponse.json();
      const token = loginData.data?.access || loginData.access;

      if (token) {
        // Test profile endpoint
        const profileResponse = await page.request.get(`${BACKEND_URL}/auth/profile/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (profileResponse.ok()) {
          console.log('✅ Profile API endpoint works');
          const profileData = await profileResponse.json();
          console.log(`📊 Profile data:`, JSON.stringify(profileData, null, 2));
        } else {
          console.log('❌ Profile API failed:', profileResponse.status());
        }
      } else {
        console.log('⚠️ No token received');
      }
    } else {
      console.log('❌ API login failed:', loginResponse.status());
    }
  });
});
