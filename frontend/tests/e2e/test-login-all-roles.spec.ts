import { test, expect } from '@playwright/test';

const BASE_URL = '';

const TEST_USERS = [
  { email: 'teacher@test.com', password: 'TestPass123!', role: 'Преподаватель' },
  { email: 'tutor@test.com', password: 'TestPass123!', role: 'Тьютор' },
  { email: 'parent@test.com', password: 'TestPass123!', role: 'Родитель' },
];

TEST_USERS.forEach(({ email, password, role }) => {
  test(`Login and navigate to profile - ${role} (${email})`, async ({ page }) => {
    console.log(`\n📋 Testing ${role} login...`);

    // Navigate to auth page
    await page.goto(`${BASE_URL}/auth`);
    await page.waitForLoadState('networkidle');
    console.log(`✅ Auth page loaded`);

    // Fill email using data-testid
    const emailInput = page.getByTestId('login-email-input');
    await emailInput.fill(email);
    console.log(`✅ Email filled: ${email}`);

    // Fill password using data-testid
    const passwordInput = page.getByTestId('login-password-input');
    await passwordInput.fill(password);
    console.log(`✅ Password filled`);

    // Click login button using data-testid
    const loginButton = page.getByTestId('login-submit-button');
    await loginButton.click();
    console.log(`✅ Login button clicked`);

    // Wait for URL change to dashboard
    try {
      await page.waitForURL(/\/dashboard\/(student|teacher|tutor|parent)/, { timeout: 15000 });
      console.log(`✅ Redirected to dashboard`);
    } catch (e) {
      console.error(`❌ Failed to redirect to dashboard: ${e}`);
      const currentUrl = page.url();
      console.error(`Current URL: ${currentUrl}`);
      throw e;
    }

    // Check that we're on dashboard (not on auth page)
    const url = page.url();
    expect(url).toContain('/dashboard');
    console.log(`✅ Successfully navigated to dashboard: ${url}`);

    console.log(`✅ ${role} (${email}) login test PASSED\n`);
  });
});
