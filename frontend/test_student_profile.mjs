import { chromium } from 'playwright';

(async () => {
  console.log('Starting student profile test...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Log console messages
  page.on('console', msg => console.log('>> BROWSER:', msg.text()));
  page.on('pageerror', error => console.log('>> ERROR:', error));

  try {
    // Navigate to frontend
    console.log('Navigating to http://localhost:8080');
    await page.goto('http://localhost:8080', { waitUntil: 'domcontentloaded', timeout: 15000 });
    
    await page.screenshot({ path: '/tmp/01_homepage.png' });
    console.log('Screenshot: 01_homepage.png');
    
    // Wait for page
    await page.waitForTimeout(2000);
    
    // Check current URL
    console.log('Current URL:', page.url());
    
    // List all inputs
    const inputs = await page.$$eval('input, textarea', els => 
      els.map(e => ({
        type: e.tagName.toLowerCase(),
        name: e.getAttribute('name'),
        placeholder: e.getAttribute('placeholder'),
        value: e.value || e.textContent
      }))
    );
    console.log('Inputs found:', inputs.length);
    inputs.forEach((inp, i) => console.log(`  ${i}: ${inp.type}[name="${inp.name}"]`));
    
    // Try to find and fill email input
    const emailInput = await page.$('input[type="email"]');
    if (emailInput) {
      console.log('Found email input');
      await emailInput.fill('student@test.com');
      
      const passwordInput = await page.$('input[type="password"]');
      if (passwordInput) {
        await passwordInput.fill('testpass123');
        console.log('Filled credentials');
      }
      
      // Find login button
      const loginBtn = await page.$('button[type="submit"]');
      if (loginBtn) {
        await loginBtn.click();
        console.log('Clicked login button');
        await page.waitForTimeout(3000);
      }
    } else {
      console.log('Email input not found on this page');
    }
    
    await page.screenshot({ path: '/tmp/02_after_login.png' });
    console.log('Screenshot: 02_after_login.png');
    
    // Navigate to profile
    console.log('Navigating to profile page');
    await page.goto('http://localhost:8080/profile/student', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ path: '/tmp/03_profile_page.png' });
    console.log('Screenshot: 03_profile_page.png');
    
    // Get page HTML to understand structure
    const html = await page.content();
    const hasForm = html.includes('form') || html.includes('input');
    console.log('Page has form elements:', hasForm);
    
  } catch (error) {
    console.error('Test error:', error.message);
  }
  
  await browser.close();
  console.log('Test completed');
})();
