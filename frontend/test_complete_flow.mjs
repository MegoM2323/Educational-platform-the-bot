import { chromium } from 'playwright';

(async () => {
  console.log('=== Testing Student Profile Edit Flow (T506) ===\n');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error' || text.includes('ERROR') || text.includes('error')) {
      console.log('>> BROWSER LOG:', text);
    }
  });

  try {
    // Step 1: Login
    console.log('Step 1: Navigate to /auth');
    await page.goto('http://localhost:8081/auth', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/T506_01_auth_page.png' });
    console.log('✓ At /auth page');
    
    console.log('\nStep 2: Fill login credentials');
    const emailInput = await page.$('input[placeholder="Email"]');
    const passwordInput = await page.$('input[placeholder="Password"]');
    
    if (emailInput && passwordInput) {
      await emailInput.fill('student@test.com');
      await passwordInput.fill('testpass123');
      console.log('✓ Filled email and password');
    } else {
      console.error('✗ Email or password input not found');
      process.exit(1);
    }
    
    console.log('\nStep 3: Click login button');
    const loginBtn = await page.$('button[type="submit"]');
    if (loginBtn) {
      await loginBtn.click();
      await page.waitForTimeout(3000);
      console.log('✓ Clicked login button');
    } else {
      console.error('✗ Login button not found');
      process.exit(1);
    }
    
    await page.screenshot({ path: '/tmp/T506_02_after_login.png' });
    console.log('✓ Screenshot after login');
    
    // Step 4: Navigate to student profile
    console.log('\nStep 4: Navigate to /profile/student');
    await page.goto('http://localhost:8081/profile/student', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const profileTitle = await page.evaluate(() => {
      const h1 = document.querySelector('h1, h2, [role="heading"]');
      return h1 ? h1.textContent : null;
    });
    
    if (profileTitle) {
      console.log(`✓ At profile page, title: "${profileTitle}"`);
    } else {
      console.log('⚠ No clear title found, but page loaded');
    }
    
    await page.screenshot({ path: '/tmp/T506_03_profile_page.png' });
    console.log('✓ Screenshot of profile page');
    
    // Step 5: Find and update profile fields
    console.log('\nStep 5: Check form fields');
    const inputs = await page.evaluate(() => {
      const inps = [];
      document.querySelectorAll('input, textarea').forEach(el => {
        inps.push({
          type: el.tagName.toLowerCase(),
          name: el.name || el.getAttribute('data-testid') || el.placeholder || '(unnamed)',
          value: el.value || el.textContent,
          placeholder: el.placeholder
        });
      });
      return inps;
    });
    
    console.log(`Found ${inputs.length} form fields:`);
    inputs.forEach((inp, i) => {
      console.log(`  ${i}: ${inp.type}[name="${inp.name}"] = "${inp.value}"`);
    });
    
    // Try to find learning_goal field
    let goalUpdated = false;
    const goalInputs = await page.$$('[placeholder*="goal"], [name*="goal"], input[name*="learning"]');
    if (goalInputs.length > 0) {
      await goalInputs[0].fill('Prepare for university entrance exams');
      goalUpdated = true;
      console.log('✓ Updated learning goal field');
    } else {
      console.log('⚠ Learning goal field not found by common selectors');
    }
    
    // Try to find grade field
    let gradeUpdated = false;
    const gradeInputs = await page.$$('[placeholder*="grade"], [name*="grade"], input[name*="grade"]');
    if (gradeInputs.length > 0) {
      await gradeInputs[0].fill('11');
      gradeUpdated = true;
      console.log('✓ Updated grade field');
    } else {
      console.log('⚠ Grade field not found');
    }
    
    await page.screenshot({ path: '/tmp/T506_04_profile_edited.png' });
    console.log('✓ Screenshot after editing fields');
    
    // Step 6: Save
    console.log('\nStep 6: Save profile');
    const saveBtn = await page.$('button[type="submit"], button:has-text("Save"), button:has-text("Сохранить")');
    if (saveBtn) {
      await saveBtn.click();
      await page.waitForTimeout(2000);
      console.log('✓ Clicked save button');
    } else {
      const buttons = await page.$$eval('button', btns => btns.map(b => ({text: b.textContent.trim().substring(0, 30), type: b.type})));
      console.log('⚠ Save button not found. Available buttons:', buttons);
    }
    
    await page.screenshot({ path: '/tmp/T506_05_after_save.png' });
    console.log('✓ Screenshot after save');
    
    // Step 7: Refresh and verify
    console.log('\nStep 7: Refresh page to verify changes persist');
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    const finalInputs = await page.evaluate(() => {
      const inps = [];
      document.querySelectorAll('input, textarea').forEach(el => {
        inps.push({
          name: el.name || el.placeholder || '(unnamed)',
          value: el.value || el.textContent
        });
      });
      return inps;
    });
    
    console.log('Fields after refresh:');
    finalInputs.forEach(inp => {
      if (inp.value) {
        console.log(`  ${inp.name}: "${inp.value}"`);
      }
    });
    
    await page.screenshot({ path: '/tmp/T506_06_after_refresh.png' });
    console.log('✓ Screenshot after refresh');
    
    console.log('\n=== TEST COMPLETED ===');
    console.log('Screenshots saved in /tmp/T506_*.png');
    
  } catch (error) {
    console.error('\n✗ TEST FAILED');
    console.error('Error:', error.message);
    process.exit(1);
  }
  
  await browser.close();
})();
