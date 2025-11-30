const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 200 });
  const page = await browser.newPage();
  
  // Set up navigation logging
  page.on('load', () => console.log('Page loaded:', page.url()));
  page.on('framenavigated', frame => {
    if (frame === page.mainFrame()) {
      console.log('Main frame navigated to:', page.url());
    }
  });
  
  try {
    // Login
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    
    const buttons = await page.locator('button').all();
    for (let btn of buttons) {
      const text = await btn.textContent();
      if (text.includes('Войти')) {
        await btn.click();
        break;
      }
    }
    
    await page.waitForURL(/\/dashboard/);
    console.log('Dashboard loaded');
    
    // Click edit profile button
    const editButton = await page.locator('button:has-text("Редактировать")').first();
    console.log('Clicking edit button...');
    await editButton.click();
    
    console.log('Waiting for navigation...');
    await page.waitForTimeout(2000);
    
    console.log('Final URL:', page.url());
    
    // Save screenshot
    await page.screenshot({ path: '/tmp/after_edit_click.png' });
    console.log('Screenshot saved');
    
    await page.waitForTimeout(2000);
    
  } finally {
    await browser.close();
  }
})();
