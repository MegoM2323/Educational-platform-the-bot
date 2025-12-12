import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();

try {
  await page.goto('http://127.0.0.1:8080', { waitUntil: 'networkidle', timeout: 30000 });
  console.log('Navigated to login page');
  console.log('URL:', page.url());
  
  await page.waitForTimeout(3000);
} catch (e) {
  console.error('Error:', e.message);
} finally {
  await browser.close();
}
