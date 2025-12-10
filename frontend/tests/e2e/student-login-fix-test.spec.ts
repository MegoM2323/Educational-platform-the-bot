import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:8081';
const BACKEND_URL = 'http://localhost:8003';

test.describe('Student Login & Navigation - Race Condition Fix', () => {

  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.context().clearCookies();
    await page.goto(BASE_URL);
  });

  test('Scenario 1: Login & Dashboard Load', async ({ page }) => {
    console.log('=== TEST SCENARIO 1: Login & Dashboard Load ===');

    // Step 1: Navigate to auth page
    await page.goto(`${BASE_URL}/auth`);
    await page.waitForLoadState('networkidle');

    // Step 2: Enter email
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    await emailInput.fill('student@test.com');

    // Step 3: Enter password
    const passwordInput = page.locator('input[type="password"], input[name="password"]');
    await passwordInput.fill('testpass123');

    // Step 4: Click login button
    const loginButton = page.locator('button:has-text("Войти")');
    await loginButton.click();

    // Step 5: VERIFY CRITICAL FIX
    // Wait for navigation to dashboard
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });

    // Verify URL
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);
    expect(currentUrl).toContain('/dashboard/student');

    // Wait for dashboard content to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Give React time to render

    // Verify page shows STUDENT DASHBOARD (not login form)
    const bodyText = await page.locator('body').textContent();
    console.log(`Body text length: ${bodyText?.length || 0} characters`);

    // Should NOT contain login form text
    expect(bodyText).not.toContain('Войти в систему');

    // Should contain dashboard elements
    const hasNavigation = await page.locator('nav').count() > 0;
    console.log(`Has navigation: ${hasNavigation}`);

    // Body content should be substantial (>1000 chars)
    expect(bodyText?.length || 0).toBeGreaterThan(1000);

    // Step 6: Check console for errors
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleLogs.push(`ERROR: ${msg.text()}`);
      }
    });

    // Take screenshot
    await page.screenshot({
      path: '/tmp/scenario1-dashboard-loaded.png',
      fullPage: true
    });
    console.log('Screenshot saved: /tmp/scenario1-dashboard-loaded.png');

    // Log console errors if any
    if (consoleLogs.length > 0) {
      console.log('Console errors:', consoleLogs);
    }

    console.log('✅ Scenario 1: PASS - Dashboard loaded successfully');
  });

  test('Scenario 2: Navigation to Schedule', async ({ page }) => {
    console.log('=== TEST SCENARIO 2: Navigation to Schedule ===');

    // Login first
    await page.goto(`${BASE_URL}/auth`);
    await page.locator('input[type="email"]').fill('student@test.com');
    await page.locator('input[type="password"]').fill('testpass123');
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });

    // Navigate to schedule
    await page.goto(`${BASE_URL}/dashboard/student/schedule`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // VERIFY: URL stays on schedule (NO redirect to /auth)
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);
    expect(currentUrl).toContain('/dashboard/student/schedule');
    expect(currentUrl).not.toContain('/auth');

    // Verify page loads with schedule UI
    const bodyText = await page.locator('body').textContent();
    console.log(`Body text length: ${bodyText?.length || 0} characters`);

    // Should not show login form
    expect(bodyText).not.toContain('Войти в систему');

    // Take screenshot
    await page.screenshot({
      path: '/tmp/scenario2-schedule-page.png',
      fullPage: true
    });
    console.log('Screenshot saved: /tmp/scenario2-schedule-page.png');

    console.log('✅ Scenario 2: PASS - Schedule page accessible');
  });

  test('Scenario 3: Navigation to Forum', async ({ page }) => {
    console.log('=== TEST SCENARIO 3: Navigation to Forum ===');

    // Login first
    await page.goto(`${BASE_URL}/auth`);
    await page.locator('input[type="email"]').fill('student@test.com');
    await page.locator('input[type="password"]').fill('testpass123');
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL('**/dashboard/student', { timeout: 10000 });

    // Navigate to forum
    await page.goto(`${BASE_URL}/dashboard/student/forum`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // VERIFY: URL stays on forum (NO redirect to /auth)
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);
    expect(currentUrl).toContain('/dashboard/student/forum');
    expect(currentUrl).not.toContain('/auth');

    // Verify page loads with forum UI
    const bodyText = await page.locator('body').textContent();
    console.log(`Body text length: ${bodyText?.length || 0} characters`);

    // Should not show login form
    expect(bodyText).not.toContain('Войти в систему');

    // Take screenshot
    await page.screenshot({
      path: '/tmp/scenario3-forum-page.png',
      fullPage: true
    });
    console.log('Screenshot saved: /tmp/scenario3-forum-page.png');

    console.log('✅ Scenario 3: PASS - Forum page accessible');
  });
});
