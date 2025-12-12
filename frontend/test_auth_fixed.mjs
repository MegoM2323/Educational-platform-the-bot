import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://127.0.0.1:8080';
const SCREENSHOTS_DIR = '/tmp/auth_tests_screenshots';

// Create screenshots directory
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Test data for 5 roles
const testAccounts = [
  { email: 'student@test.com', password: 'TestPass123!', role: 'Student' },
  { email: 'teacher@test.com', password: 'TestPass123!', role: 'Teacher' },
  { email: 'tutor@test.com', password: 'TestPass123!', role: 'Tutor' },
  { email: 'parent@test.com', password: 'TestPass123!', role: 'Parent' },
  { email: 'admin@test.com', password: 'TestPass123!', role: 'Admin' },
];

const testResults = {
  passed: [],
  failed: [],
  errors: [],
};

// Helper to open login dialog/page
async function openLoginForm(page) {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });

  // Click on "Войти" button to open login
  const loginButton = await page.locator('button:has-text("Войти")').first();
  await loginButton.click();

  // Wait for either a modal or navigation
  await page.waitForTimeout(1000);

  // Check if we navigated to /login or if a modal opened
  const url = page.url();
  if (url.includes('/login') || url.includes('/auth')) {
    // We navigated to login page
    return true;
  }

  // Otherwise, check if form appeared on the page
  const emailInput = await page.locator('input[type="email"], input[name="email"]').first();
  await emailInput.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
  return true;
}

// Test 1: Successful login for each role
async function testSuccessfulLogin(page, account) {
  try {
    console.log(`\n[TEST 1] Testing successful login for ${account.role}...`);

    // Open login form
    await openLoginForm(page);

    // Get input fields
    const emailInput = await page.locator('input[type="email"], input[name="email"], [placeholder*="mail" i], [placeholder*="email" i]').first();
    const passwordInput = await page.locator('input[type="password"], input[name="password"], [placeholder*="password" i]').first();

    // Make sure inputs are visible
    await emailInput.waitFor({ state: 'visible', timeout: 5000 });
    await passwordInput.waitFor({ state: 'visible', timeout: 5000 });

    // Fill login form
    await emailInput.fill(account.email);
    await passwordInput.fill(account.password);

    // Submit form - look for login button
    const submitButton = await page.locator(
      'button:has-text("Login"), button:has-text("Вход"), button:has-text("Sign in"), button:has-text("Войти")'
    ).first();
    await submitButton.click();

    // Wait for navigation or page change
    await page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(() => {
      // If no navigation, just wait
    });

    // Wait for page to settle
    await page.waitForTimeout(2000);

    const finalURL = page.url();
    const pageTitle = await page.title();
    const hasError = await page.locator('[role="alert"], .error, .alert-danger, .text-red-500, [class*="error"]').count() > 0;

    // Take screenshot
    const screenshotPath = path.join(SCREENSHOTS_DIR, `${account.role.toLowerCase()}_login_success.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    // Check if we're on dashboard (not on login page anymore)
    const isOnDashboard = !finalURL.includes('/login') && !finalURL.includes('/auth');

    if (isOnDashboard && !hasError) {
      console.log(`✅ ${account.role}: Successfully logged in`);
      console.log(`   URL: ${finalURL}`);
      console.log(`   Screenshot: ${screenshotPath}`);
      testResults.passed.push(`${account.role}: Successful login`);
      return true;
    } else if (hasError) {
      console.log(`❌ ${account.role}: Login showed error message`);
      const errorMsg = await page.locator('[role="alert"], .error, .alert-danger, .text-red-500, [class*="error"]').first().textContent();
      console.log(`   Error: "${errorMsg?.trim()}"`);
      testResults.failed.push(`${account.role}: ${errorMsg?.trim()}`);
      return false;
    } else {
      console.log(`❌ ${account.role}: Still on login page after submission`);
      console.log(`   URL: ${finalURL}`);
      testResults.failed.push(`${account.role}: Not navigated to dashboard`);
      return false;
    }
  } catch (e) {
    console.error(`❌ ${account.role}: Error during login test:`, e.message);
    testResults.errors.push(`${account.role}: ${e.message}`);
    return false;
  }
}

// Test 2: Invalid password error
async function testInvalidPassword(page) {
  try {
    console.log(`\n[TEST 2] Testing invalid password error for Student...`);

    // Open login form
    await openLoginForm(page);

    // Get input fields
    const emailInput = await page.locator('input[type="email"], input[name="email"], [placeholder*="mail" i], [placeholder*="email" i]').first();
    const passwordInput = await page.locator('input[type="password"], input[name="password"], [placeholder*="password" i]').first();

    // Make sure inputs are visible
    await emailInput.waitFor({ state: 'visible', timeout: 5000 });
    await passwordInput.waitFor({ state: 'visible', timeout: 5000 });

    // Fill with invalid password
    await emailInput.fill('student@test.com');
    await passwordInput.fill('WrongPassword123!');

    // Submit
    const submitButton = await page.locator(
      'button:has-text("Login"), button:has-text("Вход"), button:has-text("Sign in"), button:has-text("Войти")'
    ).first();
    await submitButton.click();

    // Wait for error to appear
    await page.waitForTimeout(2000);

    const finalURL = page.url();
    const isStillOnLogin = finalURL.includes('/login') || finalURL === BASE_URL + '/' || finalURL === BASE_URL;
    const errorElements = await page.locator('[role="alert"], .error, .alert-danger, .text-red-500, [class*="error"]').count();
    const hasError = errorElements > 0;

    // Get error text
    let errorText = '';
    if (hasError) {
      errorText = await page.locator('[role="alert"], .error, .alert-danger, .text-red-500, [class*="error"]').first().textContent();
    }

    // Take screenshot
    const screenshotPath = path.join(SCREENSHOTS_DIR, `student_invalid_password_error.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    if (isStillOnLogin && hasError) {
      console.log(`✅ Invalid password error handled correctly`);
      console.log(`   Error message: "${errorText?.trim()}"`);
      console.log(`   Still on login page: Yes`);
      console.log(`   Screenshot: ${screenshotPath}`);
      testResults.passed.push(`Invalid password error displayed correctly`);
      return true;
    } else {
      console.log(`❌ Invalid password handling failed`);
      console.log(`   Is on login: ${isStillOnLogin}, Has error: ${hasError}`);
      console.log(`   URL: ${finalURL}`);
      testResults.failed.push(`Invalid password error not displayed properly`);
      return false;
    }
  } catch (e) {
    console.error(`❌ Error during invalid password test:`, e.message);
    testResults.errors.push(`Invalid password test: ${e.message}`);
    return false;
  }
}

// Test 3: Non-existent email error
async function testNonExistentEmail(page) {
  try {
    console.log(`\n[TEST 3] Testing non-existent email error...`);

    // Open login form
    await openLoginForm(page);

    // Get input fields
    const emailInput = await page.locator('input[type="email"], input[name="email"], [placeholder*="mail" i], [placeholder*="email" i]').first();
    const passwordInput = await page.locator('input[type="password"], input[name="password"], [placeholder*="password" i]').first();

    // Make sure inputs are visible
    await emailInput.waitFor({ state: 'visible', timeout: 5000 });
    await passwordInput.waitFor({ state: 'visible', timeout: 5000 });

    // Fill with non-existent email
    await emailInput.fill('nonexistent@test.com');
    await passwordInput.fill('TestPass123!');

    // Submit
    const submitButton = await page.locator(
      'button:has-text("Login"), button:has-text("Вход"), button:has-text("Sign in"), button:has-text("Войти")'
    ).first();
    await submitButton.click();

    // Wait for error
    await page.waitForTimeout(2000);

    const finalURL = page.url();
    const isStillOnLogin = finalURL.includes('/login') || finalURL === BASE_URL + '/' || finalURL === BASE_URL;
    const errorElements = await page.locator('[role="alert"], .error, .alert-danger, .text-red-500, [class*="error"]').count();
    const hasError = errorElements > 0;

    // Get error text
    let errorText = '';
    if (hasError) {
      errorText = await page.locator('[role="alert"], .error, .alert-danger, .text-red-500, [class*="error"]').first().textContent();
    }

    // Take screenshot
    const screenshotPath = path.join(SCREENSHOTS_DIR, `nonexistent_email_error.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    if (isStillOnLogin && hasError) {
      console.log(`✅ Non-existent email error handled correctly`);
      console.log(`   Error message: "${errorText?.trim()}"`);
      console.log(`   Still on login page: Yes`);
      console.log(`   Screenshot: ${screenshotPath}`);
      testResults.passed.push(`Non-existent email error displayed correctly`);
      return true;
    } else {
      console.log(`❌ Non-existent email handling failed`);
      console.log(`   Is on login: ${isStillOnLogin}, Has error: ${hasError}`);
      console.log(`   URL: ${finalURL}`);
      testResults.failed.push(`Non-existent email error not displayed properly`);
      return false;
    }
  } catch (e) {
    console.error(`❌ Error during non-existent email test:`, e.message);
    testResults.errors.push(`Non-existent email test: ${e.message}`);
    return false;
  }
}

// Main test runner
async function runAllTests() {
  console.log('='.repeat(80));
  console.log('AUTHENTICATION TESTING FOR ALL 5 ROLES');
  console.log('='.repeat(80));
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Screenshots: ${SCREENSHOTS_DIR}`);
  console.log('='.repeat(80));

  const browser = await chromium.launch({ headless: false, timeout: 60000 });

  try {
    // Test successful login for each role
    for (const account of testAccounts) {
      const page = await browser.newPage();
      page.setDefaultTimeout(15000);

      const success = await testSuccessfulLogin(page, account);

      if (success) {
        // Try to logout
        try {
          const logoutBtn = await page.locator(
            'button:has-text("Logout"), button:has-text("Выход"), button:has-text("Sign out")'
          ).first();

          if (await logoutBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
            await logoutBtn.click();
            await page.waitForNavigation({ timeout: 5000 }).catch(() => {});
          }
        } catch (e) {
          // Could not find logout button, that's ok
        }
      }

      await page.close();
    }

    // Test error cases
    {
      const page = await browser.newPage();
      page.setDefaultTimeout(15000);
      await testInvalidPassword(page);
      await page.close();
    }

    {
      const page = await browser.newPage();
      page.setDefaultTimeout(15000);
      await testNonExistentEmail(page);
      await page.close();
    }

  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n' + '='.repeat(80));
  console.log('TEST SUMMARY');
  console.log('='.repeat(80));
  console.log(`✅ Passed: ${testResults.passed.length}`);
  testResults.passed.forEach(t => console.log(`   - ${t}`));

  if (testResults.failed.length > 0) {
    console.log(`\n❌ Failed: ${testResults.failed.length}`);
    testResults.failed.forEach(t => console.log(`   - ${t}`));
  }

  if (testResults.errors.length > 0) {
    console.log(`\n⚠️  Errors: ${testResults.errors.length}`);
    testResults.errors.forEach(t => console.log(`   - ${t}`));
  }

  console.log('\n' + '='.repeat(80));
  console.log(`Screenshots saved to: ${SCREENSHOTS_DIR}`);
  console.log('='.repeat(80));

  return testResults;
}

// Run tests
try {
  const results = await runAllTests();
  const totalTests = results.passed.length + results.failed.length + results.errors.length;
  const passRate = totalTests > 0 ? Math.round((results.passed.length / totalTests) * 100) : 0;
  console.log(`\nOVERALL PASS RATE: ${passRate}% (${results.passed.length}/${totalTests})`);

  process.exit(results.failed.length > 0 || results.errors.length > 0 ? 1 : 0);
} catch (e) {
  console.error('Fatal error:', e);
  process.exit(1);
}
