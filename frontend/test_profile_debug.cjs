const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 200 });
  const page = await browser.newPage();
  
  // Capture console messages
  const messages = [];
  page.on('console', msg => {
    const msgType = msg.type();
    const msgText = msg.text();
    const text = '[' + msgType.toUpperCase() + '] ' + msgText;
    messages.push(text);
    console.log(text);
  });
  
  try {
    // Login
    console.log('=== STEP 1: Login ===');
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
    console.log('OK Logged in, at dashboard');
    
    // Navigate to profile
    console.log('\n=== STEP 2: Navigate to profile ===');
    await page.goto('http://localhost:8080/profile/student');
    
    // Wait a bit and check where we ended up
    await page.waitForTimeout(3000);
    const finalUrl = page.url();
    console.log('Final URL:', finalUrl);
    
  } finally {
    await page.waitForTimeout(2000);
    await browser.close();
  }
})();
