const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    await page.goto('http://localhost:8080/auth');
    console.log('Page loaded');
    
    // Get all buttons on the page
    const buttons = await page.locator('button').all();
    console.log(`Found ${buttons.length} buttons`);
    
    for (let i = 0; i < buttons.length; i++) {
      const text = await buttons[i].textContent();
      console.log(`Button ${i}: "${text}"`);
    }
    
    // Get all inputs
    const inputs = await page.locator('input').all();
    console.log(`\nFound ${inputs.length} inputs`);
    
    for (let i = 0; i < inputs.length; i++) {
      const type = await inputs[i].getAttribute('type');
      const placeholder = await inputs[i].getAttribute('placeholder');
      console.log(`Input ${i}: type=${type}, placeholder=${placeholder}`);
    }
    
    // Try to find inputs by other selectors
    const emailInput = page.locator('input[type="email"]');
    const emailCount = await emailInput.count();
    console.log(`\nEmail inputs found: ${emailCount}`);
    
    const passwordInput = page.locator('input[type="password"]');
    const passCount = await passwordInput.count();
    console.log(`Password inputs found: ${passCount}`);
    
    // Take screenshot
    await page.screenshot({ path: '/tmp/auth_page.png' });
    console.log('\nScreenshot saved to /tmp/auth_page.png');
    
  } finally {
    await browser.close();
  }
})();
