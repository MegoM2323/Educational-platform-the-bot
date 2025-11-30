const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Capture console errors
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
      console.log('[ERROR]', msg.text());
    }
  });
  
  try {
    await page.goto('http://localhost:8081/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    
    // Get the form
    const form = await page.locator('form').first();
    console.log('Form found:', !!form);
    
    const buttons = await page.locator('button').all();
    for (let btn of buttons) {
      const text = await btn.textContent();
      if (text.includes('Войти')) {
        await btn.click();
        break;
      }
    }
    
    // Wait and check what happened
    await page.waitForTimeout(2000);
    
    console.log('URL after click:', page.url());
    console.log('Errors:', errors);
    
    // Check form values
    const email = await page.inputValue('input[type="email"]');
    const password = await page.inputValue('input[type="password"]');
    console.log('Form still has email:', !!email);
    console.log('Form still has password:', !!password);
    
  } finally {
    await browser.close();
  }
})();
