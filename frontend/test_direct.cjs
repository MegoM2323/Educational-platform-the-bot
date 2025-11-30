const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();
  
  try {
    console.log('Opening login page...');
    await page.goto('http://localhost:8080/auth');
    
    console.log('Waiting for page to load...');
    await page.waitForLoadState('domcontentloaded');
    
    console.log('Filling email field...');
    await page.fill('input[type="email"]', 'student@test.com');
    
    console.log('Filling password field...');
    await page.fill('input[type="password"]', 'TestPass123!');
    
    console.log('Clicking submit button...');
    const buttons = await page.locator('button').all();
    for (let i = 0; i < buttons.length; i++) {
      const text = await buttons[i].textContent();
      if (text.includes('Вход') || text.includes('Войти') || text.includes('Login')) {
        console.log(`Found login button: "${text}"`);
        await buttons[i].click();
        break;
      }
    }
    
    console.log('Waiting for navigation...');
    await page.waitForTimeout(3000);
    
    const currentUrl = page.url();
    console.log('Current URL after login:', currentUrl);
    
    // Take screenshot
    await page.screenshot({ path: '/tmp/after_login.png' });
    console.log('Screenshot saved');
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    // Wait before closing to see results
    await page.waitForTimeout(2000);
    await browser.close();
  }
})();
