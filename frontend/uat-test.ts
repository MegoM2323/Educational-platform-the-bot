import { chromium, Browser, Page } from 'playwright';
import * as fs from 'fs';

const BASE_URL = 'http://127.0.0.1:8080';
const SCREENSHOTS_DIR = '/tmp/uat-screenshots';

// Create screenshots directory
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

interface TestResult {
  scenario: string;
  status: 'PASS' | 'FAIL' | 'BLOCK';
  details: string;
  errors?: string[];
  screenshot?: string;
}

const results: TestResult[] = [];

async function takeScreenshot(page: Page, name: string) {
  const filename = `${SCREENSHOTS_DIR}/${name}.png`;
  await page.screenshot({ path: filename });
  return filename;
}

async function checkConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

async function testScenario(
  browser: Browser,
  scenario: string,
  testFn: (page: Page) => Promise<void>
): Promise<TestResult> {
  console.log(`\n▶ Testing: ${scenario}`);
  const page = await browser.newPage();
  const consoleErrors: string[] = [];

  try {
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await testFn(page);

    const result: TestResult = {
      scenario,
      status: 'PASS',
      details: 'Test passed successfully',
      errors: consoleErrors.length > 0 ? consoleErrors : undefined,
    };

    console.log(`✓ PASS: ${scenario}`);
    return result;
  } catch (error) {
    const screenshot = await takeScreenshot(page, scenario.replace(/\s+/g, '_'));
    console.error(`✗ FAIL: ${scenario}`, error);
    return {
      scenario,
      status: 'FAIL',
      details: error instanceof Error ? error.message : String(error),
      errors: [...consoleErrors, String(error)],
      screenshot,
    };
  } finally {
    await page.close();
  }
}

async function main() {
  console.log('🚀 Starting UAT for THE BOT Platform');
  console.log(`📍 Base URL: ${BASE_URL}`);
  console.log('');

  let browser: Browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (error) {
    console.error('Failed to launch browser:', error);
    process.exit(1);
  }

  // Test 1: Environment Switching (Dev Mode)
  await testScenario(browser, 'Environment Detection - API URL', async (page) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Check that API URLs are correct for development
    const apiUrl = await page.evaluate(() => {
      const env = localStorage.getItem('VITE_DJANGO_API_URL');
      return env || (window as any).__CONFIG__?.apiUrl || 'unknown';
    });

    if (!apiUrl.includes('localhost') && !apiUrl.includes('127.0.0.1')) {
      throw new Error(`API URL should be localhost for dev, got: ${apiUrl}`);
    }
  });

  // Test 2: Student Dashboard Navigation
  await testScenario(browser, 'Student Dashboard - Load and Navigate', async (page) => {
    await page.goto(BASE_URL);

    // Login as student
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Sign In")');
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Check dashboard loaded
    const dashboardText = await page.textContent('body');
    if (!dashboardText?.includes('Dashboard') && !dashboardText?.includes('Dashboard')) {
      throw new Error('Student dashboard did not load');
    }
  });

  // Test 3: Student Edit Profile Navigation
  await testScenario(browser, 'Student - Edit Profile Navigation', async (page) => {
    await page.goto(`${BASE_URL}/dashboard/student`);
    await page.waitForLoadState('networkidle');

    // Find and click Edit Profile button
    const editButton = page.locator('button:has-text("Edit"), button:has-text("edit")').first();
    if (await editButton.count() === 0) {
      throw new Error('Edit Profile button not found');
    }

    await editButton.click();
    await page.waitForURL('**/profile/student', { timeout: 5000 });

    // Verify we're on student profile page
    const url = page.url();
    if (!url.includes('/profile/student')) {
      throw new Error(`Expected /profile/student, got: ${url}`);
    }
  });

  // Test 4: Student Profile Form Submission
  await testScenario(browser, 'Student Profile - Form Submission', async (page) => {
    await page.goto(`${BASE_URL}/profile/student`);
    await page.waitForLoadState('networkidle');

    // Check that form is displayed
    const form = await page.$('form');
    if (!form) {
      throw new Error('Profile form not found on page');
    }

    // Try to fill a field and submit (just validation test)
    const phoneInput = page.locator('input[placeholder*="phone"], input[type="tel"]').first();
    if (await phoneInput.count() > 0) {
      await phoneInput.fill('+79999999999');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(1000);
    }
  });

  // Test 5: Teacher Dashboard Navigation
  await testScenario(browser, 'Teacher Dashboard - Load and Navigate', async (page) => {
    await page.goto(BASE_URL);

    // Login as teacher
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Sign In")');
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Verify dashboard loaded
    const dashboardText = await page.textContent('body');
    if (!dashboardText?.includes('Dashboard')) {
      throw new Error('Teacher dashboard did not load');
    }
  });

  // Test 6: Teacher Edit Profile Navigation
  await testScenario(browser, 'Teacher - Edit Profile Navigation', async (page) => {
    await page.goto(`${BASE_URL}/dashboard/teacher`);
    await page.waitForLoadState('networkidle');

    // Find and click Edit Profile button
    const editButton = page.locator('button:has-text("Edit"), button:has-text("edit")').first();
    if (await editButton.count() === 0) {
      throw new Error('Edit Profile button not found');
    }

    await editButton.click();
    await page.waitForURL('**/profile/teacher', { timeout: 5000 });

    // Verify we're on teacher profile page
    const url = page.url();
    if (!url.includes('/profile/teacher')) {
      throw new Error(`Expected /profile/teacher, got: ${url}`);
    }
  });

  // Test 7: Tutor Dashboard Navigation
  await testScenario(browser, 'Tutor Dashboard - Load and Navigate', async (page) => {
    await page.goto(BASE_URL);

    // Login as tutor
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Sign In")');
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Verify dashboard loaded
    const dashboardText = await page.textContent('body');
    if (!dashboardText?.includes('Dashboard')) {
      throw new Error('Tutor dashboard did not load');
    }
  });

  // Test 8: Tutor Edit Profile Navigation
  await testScenario(browser, 'Tutor - Edit Profile Navigation', async (page) => {
    await page.goto(`${BASE_URL}/dashboard/tutor`);
    await page.waitForLoadState('networkidle');

    // Find and click Edit Profile button
    const editButton = page.locator('button:has-text("Edit"), button:has-text("edit")').first();
    if (await editButton.count() === 0) {
      throw new Error('Edit Profile button not found');
    }

    await editButton.click();
    await page.waitForURL('**/profile/tutor', { timeout: 5000 });

    // Verify we're on tutor profile page
    const url = page.url();
    if (!url.includes('/profile/tutor')) {
      throw new Error(`Expected /profile/tutor, got: ${url}`);
    }
  });

  // Test 9: Admin Dashboard - Create Student
  await testScenario(browser, 'Admin Dashboard - Create Student', async (page) => {
    await page.goto(BASE_URL);

    // Login as admin
    await page.fill('input[type="email"]', 'admin@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Sign In")');
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Navigate to admin panel
    await page.goto(`${BASE_URL}/admin/students`);
    await page.waitForLoadState('networkidle');

    // Check for Create Student button
    const createButton = page.locator('button:has-text("Create"), button:has-text("Add")').first();
    if (await createButton.count() > 0) {
      console.log('✓ Create Student button found');
    }
  });

  // Test 10: No Console Errors
  await testScenario(browser, 'Console Errors Check - Navigation', async (page) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Navigate through pages
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Login and check
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Sign In")');
    await page.waitForLoadState('networkidle');

    // Verify no errors
    if (errors.length > 0) {
      throw new Error(`Console errors found: ${errors.join(', ')}`);
    }
  });

  await browser.close();

  // Generate Report
  console.log('\n\n' + '='.repeat(80));
  console.log('📊 TEST RESULTS SUMMARY');
  console.log('='.repeat(80));

  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  const blocked = results.filter(r => r.status === 'BLOCK').length;

  console.log(`\n✓ Passed: ${passed}/${results.length}`);
  console.log(`✗ Failed: ${failed}/${results.length}`);
  console.log(`⏸ Blocked: ${blocked}/${results.length}`);

  if (failed > 0) {
    console.log('\n❌ FAILED TESTS:');
    results.filter(r => r.status === 'FAIL').forEach(r => {
      console.log(`  - ${r.scenario}`);
      console.log(`    Error: ${r.details}`);
      if (r.screenshot) {
        console.log(`    Screenshot: ${r.screenshot}`);
      }
    });
  }

  // Save full report to file
  const report = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    summary: {
      total: results.length,
      passed,
      failed,
      blocked,
    },
    results,
  };

  fs.writeFileSync(
    '/home/mego/Python Projects/THE_BOT_platform/USER_ACCEPTANCE_TEST_FINAL.json',
    JSON.stringify(report, null, 2)
  );

  console.log('\n📄 Full report saved to: USER_ACCEPTANCE_TEST_FINAL.json');
  console.log('🖼️  Screenshots saved to: ' + SCREENSHOTS_DIR);

  process.exit(failed > 0 ? 1 : 0);
}

main().catch(console.error);
