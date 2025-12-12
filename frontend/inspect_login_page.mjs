import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();

try {
  await page.goto('http://127.0.0.1:8080', { waitUntil: 'networkidle', timeout: 30000 });
  console.log('Page loaded');
  console.log('URL:', page.url());
  
  // Get page content
  const content = await page.content();
  
  // Look for input fields
  const inputs = await page.locator('input').all();
  console.log(`\nFound ${inputs.length} input elements:`);
  for (let i = 0; i < inputs.length; i++) {
    const type = await inputs[i].getAttribute('type');
    const name = await inputs[i].getAttribute('name');
    const id = await inputs[i].getAttribute('id');
    const placeholder = await inputs[i].getAttribute('placeholder');
    console.log(`  [${i}] type=${type}, name=${name}, id=${id}, placeholder=${placeholder}`);
  }
  
  // Look for buttons
  const buttons = await page.locator('button').all();
  console.log(`\nFound ${buttons.length} button elements:`);
  for (let i = 0; i < Math.min(buttons.length, 5); i++) {
    const text = await buttons[i].textContent();
    const type = await buttons[i].getAttribute('type');
    console.log(`  [${i}] type=${type}, text="${text?.trim()}"`);
  }
  
  // Check for forms
  const forms = await page.locator('form').all();
  console.log(`\nFound ${forms.length} form elements`);
  
  // Get body HTML
  const body = await page.locator('body').innerHTML();
  console.log('\n=== First 500 chars of page ===');
  console.log(body.substring(0, 500));
  
  await page.waitForTimeout(2000);
} catch (e) {
  console.error('Error:', e.message);
} finally {
  await browser.close();
}
