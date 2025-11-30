const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
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
    console.log('On dashboard:', page.url());
    
    // Get all buttons
    const allButtons = await page.locator('button').all();
    console.log(`\nFound ${allButtons.length} buttons:`);
    
    for (let i = 0; i < allButtons.length; i++) {
      const text = await allButtons[i].textContent();
      const visible = await allButtons[i].isVisible();
      console.log(`  [${i}] "${text}" (visible: ${visible})`);
    }
    
    // Get all links
    const allLinks = await page.locator('a').all();
    console.log(`\nFound ${allLinks.length} links:`);
    
    for (let i = 0; i < Math.min(20, allLinks.length); i++) {
      const text = await allLinks[i].textContent();
      const href = await allLinks[i].getAttribute('href');
      console.log(`  [${i}] "${text}" -> "${href}"`);
    }
    
    // Check for profile-related elements
    const profileElements = await page.locator('text=/profil|edit|редактиров/i').all();
    console.log(`\nProfile-related elements: ${profileElements.length}`);
    
  } finally {
    await browser.close();
  }
})();
