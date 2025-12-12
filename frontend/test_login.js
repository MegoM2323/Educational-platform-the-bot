const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    await page.goto('http://127.0.0.1:8080', { waitUntil: 'networkidle', timeout: 30000 });
    console.log('Navigated to login page');
    console.log('URL:', page.url());
    
    // Wait 3 seconds to see the page
    await page.waitForTimeout(3000);
  } catch (e) {
    console.error('Error:', e.message);
  } finally {
    await browser.close();
  }
})();
