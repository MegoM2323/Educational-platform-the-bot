const { chromium } = require('playwright');

async function testProfile(browser, email, role) {
  const page = await browser.newPage();
  try {
    // Navigate to login
    await page.goto('http://localhost:8081/auth');
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'TestPass123!');
    
    // Click login
    const buttons = await page.locator('button').all();
    for (let btn of buttons) {
      const text = await btn.textContent();
      if (text.includes('Войти')) {
        await btn.click();
        break;
      }
    }
    
    // Wait for dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    
    // Click edit profile
    await page.waitForTimeout(500);
    const editButtons = await page.locator('button').all();
    for (let btn of editButtons) {
      const text = await btn.textContent();
      if (text.includes('Редактировать')) {
        await btn.click();
        break;
      }
    }
    
    // Wait for profile page
    const profileRegex = new RegExp('/profile/' + role);
    await page.waitForURL(profileRegex, { timeout: 10000 });
    const finalUrl = page.url();
    
    if (finalUrl.includes('/profile/' + role)) {
      console.log('OK ' + role + ': Profile page loaded successfully');
      return true;
    } else {
      console.log('FAIL ' + role + ': Expected /profile/' + role + ', got ' + finalUrl);
      return false;
    }
    
  } catch (error) {
    console.log('FAIL ' + role + ': ' + error.message);
    return false;
  } finally {
    await page.close();
  }
}

async function testStudentBookings(browser) {
  const page = await browser.newPage();
  try {
    // Login
    await page.goto('http://localhost:8081/auth');
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
    
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    
    // Navigate to bookings
    await page.goto('http://localhost:8081/dashboard/student/bookings');
    await page.waitForLoadState('networkidle');
    
    const errors = await page.locator('text=/Failed|Error|Ошибка/i').count();
    
    if (errors === 0) {
      console.log('OK BOOKINGS: Student bookings page loaded without errors');
      return true;
    } else {
      console.log('FAIL BOOKINGS: Found ' + errors + ' error messages');
      return false;
    }
    
  } catch (error) {
    console.log('FAIL BOOKINGS: ' + error.message);
    return false;
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  
  console.log('\n========================================');
  console.log('T016 User Acceptance Testing - RERUN');
  console.log('========================================\n');
  
  const results = [];
  
  // Test all profiles
  results.push(await testProfile(browser, 'student@test.com', 'student'));
  results.push(await testProfile(browser, 'teacher@test.com', 'teacher'));
  results.push(await testProfile(browser, 'tutor@test.com', 'tutor'));
  
  // Test student bookings
  results.push(await testStudentBookings(browser));
  
  await browser.close();
  
  const passed = results.filter(r => r).length;
  const total = results.length;
  
  console.log('\n========================================');
  console.log('TEST SUMMARY');
  console.log('========================================');
  console.log('Passed: ' + passed + '/' + total);
  
  if (passed === total) {
    console.log('\nOK ALL TESTS PASSED');
    console.log('T016: User Acceptance Testing COMPLETED\n');
    process.exit(0);
  } else {
    console.log('\nFAIL SOME TESTS FAILED\n');
    process.exit(1);
  }
})();
