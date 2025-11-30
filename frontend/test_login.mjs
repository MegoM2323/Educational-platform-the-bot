import { chromium } from 'playwright';

(async () => {
  console.log('Testing login flow...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') console.log('>> ERROR:', msg.text());
  });

  try {
    // Navigate to login page explicitly
    console.log('Navigating to /auth/login');
    await page.goto('http://localhost:8080/auth/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
    
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/login_page.png' });
    console.log('Screenshot: login_page.png');
    
    // Check for form inputs
    const inputs = await page.$$eval('input', els => 
      els.map(e => ({
        type: e.type,
        name: e.name || e.id,
        placeholder: e.placeholder,
        value: e.value
      }))
    );
    console.log('Found inputs:', inputs.length);
    inputs.forEach((inp, i) => {
      console.log(`  ${i}: type="${inp.type}" name="${inp.name}" placeholder="${inp.placeholder}"`);
    });
    
    // Fill login form
    const emailInputs = await page.$$('input[type="email"]');
    const passwordInputs = await page.$$('input[type="password"]');
    
    console.log('Email inputs:', emailInputs.length);
    console.log('Password inputs:', passwordInputs.length);
    
    if (emailInputs.length > 0) {
      await emailInputs[0].fill('student@test.com');
      console.log('Filled email');
    }
    
    if (passwordInputs.length > 0) {
      await passwordInputs[0].fill('testpass123');
      console.log('Filled password');
    }
    
    // Look for submit button
    const buttons = await page.$$eval('button', els =>
      els.map(e => ({
        text: e.textContent.trim(),
        type: e.type
      }))
    );
    console.log('\nButtons found:', buttons.length);
    buttons.slice(0, 10).forEach((btn, i) => {
      console.log(`  ${i}: "${btn.text}" type="${btn.type}"`);
    });
    
    // Click first submit button or button with login text
    const submitBtn = await page.$('button[type="submit"]');
    if (submitBtn) {
      console.log('Clicking submit button');
      await submitBtn.click();
      await page.waitForTimeout(3000);
      
      await page.screenshot({ path: '/tmp/after_login.png' });
      console.log('Screenshot: after_login.png');
      console.log('Current URL:', page.url());
    }
    
  } catch (error) {
    console.error('Test error:', error.message);
    console.error('Stack:', error.stack);
  }
  
  await browser.close();
})();
