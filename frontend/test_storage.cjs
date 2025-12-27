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
    
    // Get localStorage data
    const storage = await page.evaluate(() => {
      return {
        userData: localStorage.getItem('userData'),
        token: localStorage.getItem('token') ? 'YES' : 'NO',
        allKeys: Object.keys(localStorage).map(k => ({ key: k, valueLength: localStorage.getItem(k).length }))
      };
    });
    
    console.log('localStorage after login:');
    console.log('userData:', storage.userData);
    console.log('token:', storage.token);
    console.log('All keys:', storage.allKeys);
    
    // Now navigate to profile
    console.log('\nNavigating to /profile/student...');
    await page.goto('http://localhost:8080/profile/student');
    await page.waitForTimeout(1000);
    
    console.log('URL after navigation:', page.url());
    
    // Check console errors
    const logs = await page.evaluate(() => {
      return {
        url: window.location.href,
        title: document.title
      };
    });
    
    console.log('Page info:', logs);
    
  } finally {
    await browser.close();
  }
})();
