import { chromium } from 'playwright';

(async () => {
  console.log('=== Testing Student Profile Edit (T506) - Fixed ===\n');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Step 1: Go to auth page
    console.log('Step 1: Navigate to /auth');
    await page.goto('http://localhost:8081/auth', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(1500);
    console.log('SUCCESS: At /auth page');

    // Step 2: Login
    console.log('\nStep 2: Login as student@test.com');
    const emailInput = await page.$('input[placeholder="Email"]');
    const passwordInput = await page.$('input[placeholder="Password"]');

    await emailInput.fill('student@test.com');
    await passwordInput.fill('testpass123');

    const loginBtn = await page.$('button');
    const buttons = await page.$$('button');
    for (const btn of buttons) {
      const text = await btn.textContent();
      if (text.includes('Войти')) {
        await btn.click();
        break;
      }
    }

    // Wait for login response
    await page.waitForTimeout(3000);
    console.log('Current URL after login: ' + page.url());

    // Check if token was stored
    const token = await page.evaluate(() => localStorage.getItem('token'));
    if (token) {
      console.log('SUCCESS: Token saved in localStorage');
    } else {
      console.log('WARNING: No token in localStorage');
    }

    // Step 3: Navigate to profile
    console.log('\nStep 3: Navigate to /profile/student');
    await page.goto('http://localhost:8081/profile/student', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);

    const currentUrl = page.url();
    console.log('Current URL: ' + currentUrl);

    if (currentUrl.includes('/auth')) {
      console.log('WARNING: Still at auth page');
      process.exit(1);
    }

    // Find form fields
    const fieldDetails = await page.evaluate(() => {
      const fields = [];
      document.querySelectorAll('input, textarea, select').forEach(el => {
        fields.push({
          tag: el.tagName,
          name: el.name,
          id: el.id,
          placeholder: el.placeholder,
          value: el.value
        });
      });
      return fields;
    });

    console.log('Form fields found: ' + fieldDetails.length);
    fieldDetails.forEach((f, i) => {
      console.log('  Field ' + i + ': ' + f.tag + '[name=' + f.name + '] placeholder=' + f.placeholder);
    });

    // Take screenshot
    await page.screenshot({ path: '/tmp/T506_profile_form.png' });
    console.log('SUCCESS: Screenshot saved');

  } catch (error) {
    console.error('ERROR: ' + error.message);
    await page.screenshot({ path: '/tmp/T506_error.png' });
    process.exit(1);
  }

  await browser.close();
})();
