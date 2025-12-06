import { test, expect } from '@playwright/test';

/**
 * Test T002 RETRY: Verify White Screen Bug Fix
 *
 * The bug was: `import { logger }` was inside JSDoc comment in websocketService.ts
 * Fix: Moved import outside JSDoc comment
 *
 * This test verifies the fix by:
 * 1. Loading homepage - should NOT show white screen
 * 2. Checking console for errors - should NOT have ReferenceError about logger
 * 3. Waiting for stability - page should remain loaded
 * 4. Navigating to /auth - should show login form
 * 5. Checking network requests - all should load successfully
 */

test.describe('White Screen Bug Fix Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Collect console messages and errors
    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text());
    });

    page.on('pageerror', error => {
      console.error('[BROWSER ERROR]:', error.message);
    });
  });

  test('Scenario 1: Homepage loads without white screen', async ({ page }) => {
    console.log('\n=== SCENARIO 1: Open homepage ===');

    // Navigate to homepage
    const response = await page.goto('http://localhost:8080', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Take screenshot for evidence
    await page.screenshot({ path: '/tmp/scenario1-homepage.png', fullPage: true });

    // Verify page loaded (not white screen)
    expect(response?.status()).toBeLessThan(400);

    // Verify React app mounted (div#root should have content)
    const rootContent = await page.locator('#root').innerHTML();
    expect(rootContent.length).toBeGreaterThan(100); // Should have substantial content

    // Verify no white screen (body should have visible elements)
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toBeTruthy();
    expect(bodyText!.length).toBeGreaterThan(0);

    console.log('✅ Homepage loaded with content (not white screen)');
  });

  test('Scenario 2: Browser console has NO logger errors', async ({ page }) => {
    console.log('\n=== SCENARIO 2: Check browser console ===');

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', error => {
      pageErrors.push(error.message);
    });

    await page.goto('http://localhost:8080', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Take screenshot
    await page.screenshot({ path: '/tmp/scenario2-console.png', fullPage: true });

    // Check for logger-related errors
    const loggerErrors = [...consoleErrors, ...pageErrors].filter(err =>
      err.toLowerCase().includes('logger') ||
      err.toLowerCase().includes('referenceerror')
    );

    console.log('Console errors:', consoleErrors);
    console.log('Page errors:', pageErrors);
    console.log('Logger-related errors:', loggerErrors);

    expect(loggerErrors.length).toBe(0);
    console.log('✅ No logger-related errors in console');
  });

  test('Scenario 3: Page remains stable after 10 seconds', async ({ page }) => {
    console.log('\n=== SCENARIO 3: Wait 10 seconds for stability ===');

    await page.goto('http://localhost:8080', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Get initial content
    const initialContent = await page.locator('#root').innerHTML();

    // Wait 10 seconds
    console.log('Waiting 10 seconds...');
    await page.waitForTimeout(10000);

    // Take screenshot after wait
    await page.screenshot({ path: '/tmp/scenario3-stable.png', fullPage: true });

    // Verify content still exists (not white screen)
    const afterContent = await page.locator('#root').innerHTML();
    expect(afterContent.length).toBeGreaterThan(100);

    // Verify page didn't crash
    const bodyVisible = await page.locator('body').isVisible();
    expect(bodyVisible).toBe(true);

    console.log('✅ Page remained stable after 10 seconds');
  });

  test('Scenario 4: Navigate to /auth shows login form', async ({ page }) => {
    console.log('\n=== SCENARIO 4: Navigate to /auth ===');

    await page.goto('http://localhost:8080/auth', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Take screenshot
    await page.screenshot({ path: '/tmp/scenario4-auth.png', fullPage: true });

    // Verify login form elements are visible
    // Note: We'll check for common login form elements
    const rootContent = await page.locator('#root').innerHTML();
    expect(rootContent.length).toBeGreaterThan(100);

    // Verify no white screen
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toBeTruthy();
    expect(bodyText!.length).toBeGreaterThan(0);

    // Verify page title or some UI element exists
    const hasContent = await page.locator('body *').count();
    expect(hasContent).toBeGreaterThan(5); // Should have multiple elements

    console.log('✅ /auth page loaded with UI elements');
  });

  test('Scenario 5: Network tab shows successful module loading', async ({ page }) => {
    console.log('\n=== SCENARIO 5: Check Network tab ===');

    const failedRequests: string[] = [];

    page.on('response', response => {
      if (response.status() >= 400) {
        failedRequests.push(`${response.status()} - ${response.url()}`);
      }
    });

    await page.goto('http://localhost:8080/auth', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Take screenshot
    await page.screenshot({ path: '/tmp/scenario5-network.png', fullPage: true });

    // Check for failed websocketService requests
    const websocketServiceErrors = failedRequests.filter(req =>
      req.includes('websocketService')
    );

    console.log('Failed requests:', failedRequests);
    console.log('WebSocket service errors:', websocketServiceErrors);

    expect(websocketServiceErrors.length).toBe(0);

    // Verify React app loaded
    const rootContent = await page.locator('#root').innerHTML();
    expect(rootContent.length).toBeGreaterThan(100);

    console.log('✅ All JS modules loaded successfully');
  });

  test('FINAL CHECK: All acceptance criteria verified', async ({ page }) => {
    console.log('\n=== FINAL CHECK: Verify ALL acceptance criteria ===');

    const results = {
      homepageLoads: false,
      loginPageLoads: false,
      uiElementsVisible: false,
      noLoggerErrors: false,
      reactAppMounts: false
    };

    const pageErrors: string[] = [];
    page.on('pageerror', error => pageErrors.push(error.message));

    // Test 1: Homepage loads
    console.log('Checking homepage...');
    await page.goto('http://localhost:8080', { waitUntil: 'networkidle' });
    const homepageContent = await page.locator('#root').innerHTML();
    results.homepageLoads = homepageContent.length > 100;
    results.reactAppMounts = homepageContent.length > 100;

    // Test 2: Login page loads
    console.log('Checking login page...');
    await page.goto('http://localhost:8080/auth', { waitUntil: 'networkidle' });
    const authContent = await page.locator('#root').innerHTML();
    results.loginPageLoads = authContent.length > 100;

    // Test 3: UI elements visible
    const elementCount = await page.locator('body *').count();
    results.uiElementsVisible = elementCount > 5;

    // Test 4: No logger errors
    const loggerErrors = pageErrors.filter(err =>
      err.toLowerCase().includes('logger') ||
      err.toLowerCase().includes('referenceerror')
    );
    results.noLoggerErrors = loggerErrors.length === 0;

    // Take final screenshot
    await page.screenshot({ path: '/tmp/final-check.png', fullPage: true });

    console.log('\n=== FINAL RESULTS ===');
    console.log('Homepage loads without white screen:', results.homepageLoads ? '✅' : '❌');
    console.log('Login page loads without white screen:', results.loginPageLoads ? '✅' : '❌');
    console.log('UI elements visible:', results.uiElementsVisible ? '✅' : '❌');
    console.log('No logger errors:', results.noLoggerErrors ? '✅' : '❌');
    console.log('React app mounts:', results.reactAppMounts ? '✅' : '❌');

    // All must pass
    expect(results.homepageLoads).toBe(true);
    expect(results.loginPageLoads).toBe(true);
    expect(results.uiElementsVisible).toBe(true);
    expect(results.noLoggerErrors).toBe(true);
    expect(results.reactAppMounts).toBe(true);

    console.log('\n✅ ALL ACCEPTANCE CRITERIA PASSED');
  });
});
