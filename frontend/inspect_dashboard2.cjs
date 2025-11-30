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
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    console.log('On dashboard:', page.url());
    
    // Get all buttons
    const allButtons = await page.locator('button').all();
    console.log(`Found ${allButtons.length} buttons:`);
    
    for (let i = 0; i < allButtons.length; i++) {
      const text = await allButtons[i].textContent();
      console.log(`  [${i}] "${text}"`);
    }
    
    // Get all clickable elements with text
    const htmlContent = await page.evaluate(() => document.body.innerHTML);
    
    if (htmlContent.includes('Редактировать')) {
      console.log('\n✓ Found "Редактировать" in HTML');
    } else {
      console.log('\n✗ "Редактировать" NOT in HTML');
    }
    
    if (htmlContent.includes('профиль')) {
      console.log('✓ Found "профиль" in HTML');
    }
    
    if (htmlContent.includes('profile')) {
      console.log('✓ Found "profile" in HTML');
    }
    
    // Try to find any clickable element that might be edit profile
    const elements = await page.evaluate(() => {
      const all = document.querySelectorAll('button, a, [role="button"]');
      return Array.from(all).map(el => ({
        tag: el.tagName,
        text: el.textContent.substring(0, 50),
        href: el.getAttribute('href'),
        onclick: el.getAttribute('onclick') ? 'yes' : 'no'
      }));
    });
    
    console.log('\nAll clickable elements:');
    elements.forEach((el, i) => {
      if (el.text.trim()) {
        console.log(`  ${el.tag}: "${el.text}" (href: ${el.href}, onclick: ${el.onclick})`);
      }
    });
    
  } finally {
    await browser.close();
  }
})();
