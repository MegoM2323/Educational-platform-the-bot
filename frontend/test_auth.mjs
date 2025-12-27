import { chromium } from 'playwright';

(async () => {
  console.log('Testing /auth page...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') console.log('>> BROWSER ERROR:', msg.text());
  });

  try {
    await page.goto('http://localhost:8081/auth', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // Check page content
    const bodyText = await page.evaluate(() => document.body.innerText);
    console.log('Page content (first 500 chars):');
    console.log(bodyText.substring(0, 500));
    
    // Find all interactive elements
    const elements = await page.evaluate(() => {
      const elems = [];
      document.querySelectorAll('input, button, textarea').forEach(el => {
        elems.push({
          tag: el.tagName,
          type: el.type,
          name: el.name,
          id: el.id,
          placeholder: el.placeholder
        });
      });
      return elems;
    });
    
    console.log('\nInteractive elements found:', elements.length);
    elements.forEach((el, i) => {
      console.log(`  ${i}: ${el.tag}[${el.type}] name="${el.name}" placeholder="${el.placeholder}"`);
    });
    
    await page.screenshot({ path: '/tmp/auth_page.png' });
    console.log('\nScreenshot saved: /tmp/auth_page.png');
    
  } catch (error) {
    console.error('Test error:', error.message);
  }
  
  await browser.close();
})();
