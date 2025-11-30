const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage();
  
  try {
    console.log('Opening login page...');
    await page.goto('http://localhost:8081/auth', { waitUntil: 'domcontentloaded' });
    console.log('Auth page loaded');
    
    console.log('Filling credentials...');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    console.log('Credentials filled');
    
    console.log('Looking for login button...');
    const buttons = await page.locator('button').all();
    let found = false;
    for (let btn of buttons) {
      const text = await btn.textContent();
      console.log('Button:', text);
      if (text.includes('Войти')) {
        console.log('Clicking login button...');
        await btn.click();
        found = true;
        break;
      }
    }
    
    if (!found) {
      console.log('ERROR: Login button not found');
    }
    
    console.log('Waiting for navigation...');
    await page.waitForTimeout(5000);
    
    console.log('Final URL:', page.url());
    
  } finally {
    await browser.close();
  }
})();
