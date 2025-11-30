import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('http://localhost:8081/auth/login', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);

  const html = await page.content();

  // Print relevant parts
  if (html.includes('form')) {
    console.log('Page contains: form');
  }
  if (html.includes('email')) {
    console.log('Page contains: email');
  }
  if (html.includes('password')) {
    console.log('Page contains: password');
  }
  if (html.includes('input')) {
    console.log('Page contains: input');
  }

  // Get all text content
  const bodyText = await page.evaluate(() => document.body.innerText);
  console.log('\n=== Page text content (first 1000 chars) ===');
  console.log(bodyText.substring(0, 1000));

  // Find all interactive elements
  const elements = await page.evaluate(() => {
    const elems = [];
    document.querySelectorAll('input, button, textarea, [role="textbox"]').forEach(el => {
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

  console.log('\n=== Interactive elements ===');
  elements.forEach(el => {
    console.log(`${el.tag}[name="${el.name}" id="${el.id}" type="${el.type}"] placeholder="${el.placeholder}"`);
  });

  await browser.close();
})();
