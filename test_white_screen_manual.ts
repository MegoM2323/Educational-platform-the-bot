/**
 * Manual White Screen Bug Fix Verification
 * Task T002 RETRY
 *
 * This script manually tests if the white screen bug is fixed
 * by opening the browser and checking each scenario.
 */

import { chromium } from 'playwright';

async function main() {
  console.log('\n=== Starting White Screen Bug Fix Verification ===\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });
  const page = await context.newPage();

  // Track console messages and errors
  const consoleMessages: string[] = [];
  const pageErrors: string[] = [];

  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push(`[${msg.type()}] ${text}`);
    console.log(`  [BROWSER ${msg.type()}] ${text}`);
  });

  page.on('pageerror', error => {
    pageErrors.push(error.message);
    console.error(`  [BROWSER ERROR] ${error.message}`);
  });

  const results = {
    scenario1: false,
    scenario2: false,
    scenario3: false,
    scenario4: false,
    scenario5: false,
  };

  try {
    // SCENARIO 1: Open homepage
    console.log('\n--- SCENARIO 1: Homepage loads without white screen ---');
    const response = await page.goto('http://localhost:8080', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    console.log(`  Response status: ${response?.status()}`);

    // Check if page loaded
    const rootContent = await page.locator('#root').innerHTML();
    console.log(`  Root content length: ${rootContent.length} characters`);

    const bodyText = await page.locator('body').textContent();
    console.log(`  Body text length: ${bodyText?.length || 0} characters`);

    results.scenario1 = rootContent.length > 100 && response?.status()! < 400;
    console.log(`  Result: ${results.scenario1 ? '✅ PASS' : '❌ FAIL'}`);

    // Take screenshot
    await page.screenshot({ path: '/tmp/scenario1-homepage.png', fullPage: true });
    console.log('  Screenshot saved: /tmp/scenario1-homepage.png');

    // SCENARIO 2: Check for logger errors
    console.log('\n--- SCENARIO 2: Browser console has NO logger errors ---');
    const loggerErrors = [...consoleMessages, ...pageErrors].filter(msg =>
      msg.toLowerCase().includes('logger') ||
      msg.toLowerCase().includes('referenceerror')
    );

    console.log(`  Total console messages: ${consoleMessages.length}`);
    console.log(`  Total page errors: ${pageErrors.length}`);
    console.log(`  Logger-related errors: ${loggerErrors.length}`);

    if (loggerErrors.length > 0) {
      console.log('  Logger errors found:');
      loggerErrors.forEach(err => console.log(`    - ${err}`));
    }

    results.scenario2 = loggerErrors.length === 0;
    console.log(`  Result: ${results.scenario2 ? '✅ PASS' : '❌ FAIL'}`);

    await page.screenshot({ path: '/tmp/scenario2-console.png', fullPage: true });
    console.log('  Screenshot saved: /tmp/scenario2-console.png');

    // SCENARIO 3: Wait for stability
    console.log('\n--- SCENARIO 3: Page remains stable after 10 seconds ---');
    console.log('  Waiting 10 seconds...');
    await page.waitForTimeout(10000);

    const afterContent = await page.locator('#root').innerHTML();
    console.log(`  Content after wait: ${afterContent.length} characters`);

    const bodyVisible = await page.locator('body').isVisible();
    console.log(`  Body still visible: ${bodyVisible}`);

    results.scenario3 = afterContent.length > 100 && bodyVisible;
    console.log(`  Result: ${results.scenario3 ? '✅ PASS' : '❌ FAIL'}`);

    await page.screenshot({ path: '/tmp/scenario3-stable.png', fullPage: true });
    console.log('  Screenshot saved: /tmp/scenario3-stable.png');

    // SCENARIO 4: Navigate to /auth
    console.log('\n--- SCENARIO 4: Navigate to /auth shows login form ---');
    await page.goto('http://localhost:8080/auth', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    const authContent = await page.locator('#root').innerHTML();
    console.log(`  Auth page content length: ${authContent.length} characters`);

    const authBodyText = await page.locator('body').textContent();
    console.log(`  Auth page body text: ${authBodyText?.substring(0, 100)}...`);

    const elementCount = await page.locator('body *').count();
    console.log(`  Number of elements on page: ${elementCount}`);

    results.scenario4 = authContent.length > 100 && elementCount > 5;
    console.log(`  Result: ${results.scenario4 ? '✅ PASS' : '❌ FAIL'}`);

    await page.screenshot({ path: '/tmp/scenario4-auth.png', fullPage: true });
    console.log('  Screenshot saved: /tmp/scenario4-auth.png');

    // SCENARIO 5: Check network requests
    console.log('\n--- SCENARIO 5: Network tab shows successful module loading ---');
    const failedRequests: string[] = [];

    page.on('response', response => {
      if (response.status() >= 400) {
        failedRequests.push(`${response.status()} - ${response.url()}`);
      }
    });

    // Reload to check network
    await page.reload({ waitUntil: 'networkidle' });

    console.log(`  Failed requests: ${failedRequests.length}`);
    if (failedRequests.length > 0) {
      console.log('  Failed requests:');
      failedRequests.forEach(req => console.log(`    - ${req}`));
    }

    const websocketServiceErrors = failedRequests.filter(req =>
      req.includes('websocketService')
    );

    results.scenario5 = websocketServiceErrors.length === 0;
    console.log(`  Result: ${results.scenario5 ? '✅ PASS' : '❌ FAIL'}`);

    await page.screenshot({ path: '/tmp/scenario5-network.png', fullPage: true });
    console.log('  Screenshot saved: /tmp/scenario5-network.png');

    // FINAL RESULTS
    console.log('\n\n=== FINAL TEST RESULTS ===\n');
    console.log(`Scenario 1 - Homepage loads: ${results.scenario1 ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Scenario 2 - No logger errors: ${results.scenario2 ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Scenario 3 - Page stability: ${results.scenario3 ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Scenario 4 - Auth page loads: ${results.scenario4 ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Scenario 5 - Network requests: ${results.scenario5 ? '✅ PASS' : '❌ FAIL'}`);

    const allPassed = Object.values(results).every(r => r === true);
    console.log(`\n${allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}\n`);

    // Keep browser open for manual inspection
    console.log('Browser will remain open for 30 seconds for manual inspection...');
    await page.waitForTimeout(30000);

  } catch (error) {
    console.error('\n❌ ERROR during test execution:', error);
  } finally {
    await browser.close();
    console.log('\nBrowser closed. Test complete.');
  }
}

main().catch(console.error);
