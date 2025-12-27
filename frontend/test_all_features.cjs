const { chromium } = require('playwright');

async function testStudentProfile(browser) {
  const page = await browser.newPage();
  try {
    console.log('\n=== TEST 1: Student Profile Navigation ===');
    
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
    
    console.log('✓ Login submitted');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    console.log('✓ Dashboard loaded:', page.url());
    
    // Find edit profile button
    const editButtons = await page.locator('button').all();
    for (let btn of editButtons) {
      const text = await btn.textContent();
      if (text.includes('Редактировать') || text.includes('профиль')) {
        await btn.click();
        console.log('✓ Edit profile button clicked');
        break;
      }
    }
    
    await page.waitForURL(/\/profile/, { timeout: 10000 });
    console.log('✓ Profile page loaded:', page.url());
    
    if (page.url().includes('/profile/student')) {
      console.log('✓✓✓ Student Profile Navigation PASSED');
      return true;
    } else {
      console.log('✗ Wrong profile URL:', page.url());
      return false;
    }
    
  } catch (error) {
    console.error('✗ Student Profile Test FAILED:', error.message);
    return false;
  } finally {
    await page.close();
  }
}

async function testTeacherProfile(browser) {
  const page = await browser.newPage();
  try {
    console.log('\n=== TEST 2: Teacher Profile Navigation ===');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    
    const buttons = await page.locator('button').all();
    for (let btn of buttons) {
      const text = await btn.textContent();
      if (text.includes('Войти')) {
        await btn.click();
        break;
      }
    }
    
    console.log('✓ Login submitted');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    console.log('✓ Dashboard loaded');
    
    const editButtons = await page.locator('button').all();
    for (let btn of editButtons) {
      const text = await btn.textContent();
      if (text.includes('Редактировать')) {
        await btn.click();
        console.log('✓ Edit profile button clicked');
        break;
      }
    }
    
    await page.waitForURL(/\/profile/, { timeout: 10000 });
    console.log('✓ Profile page loaded:', page.url());
    
    if (page.url().includes('/profile/teacher')) {
      console.log('✓✓✓ Teacher Profile Navigation PASSED');
      return true;
    } else {
      console.log('✗ Wrong profile URL:', page.url());
      return false;
    }
    
  } catch (error) {
    console.error('✗ Teacher Profile Test FAILED:', error.message);
    return false;
  } finally {
    await page.close();
  }
}

async function testTutorProfile(browser) {
  const page = await browser.newPage();
  try {
    console.log('\n=== TEST 3: Tutor Profile Navigation ===');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    
    const buttons = await page.locator('button').all();
    for (let btn of buttons) {
      const text = await btn.textContent();
      if (text.includes('Войти')) {
        await btn.click();
        break;
      }
    }
    
    console.log('✓ Login submitted');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    console.log('✓ Dashboard loaded');
    
    const editButtons = await page.locator('button').all();
    for (let btn of editButtons) {
      const text = await btn.textContent();
      if (text.includes('Редактировать')) {
        await btn.click();
        console.log('✓ Edit profile button clicked');
        break;
      }
    }
    
    await page.waitForURL(/\/profile/, { timeout: 10000 });
    console.log('✓ Profile page loaded:', page.url());
    
    if (page.url().includes('/profile/tutor')) {
      console.log('✓✓✓ Tutor Profile Navigation PASSED');
      return true;
    } else {
      console.log('✗ Wrong profile URL:', page.url());
      return false;
    }
    
  } catch (error) {
    console.error('✗ Tutor Profile Test FAILED:', error.message);
    return false;
  } finally {
    await page.close();
  }
}

async function testStudentBookings(browser) {
  const page = await browser.newPage();
  try {
    console.log('\n=== TEST 4: Student Bookings Page ===');
    
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
    
    console.log('✓ Login submitted');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    console.log('✓ Dashboard loaded');
    
    // Navigate to bookings page
    await page.goto('http://localhost:8080/dashboard/student/bookings');
    await page.waitForLoadState('networkidle');
    console.log('✓ Bookings page loaded');
    
    // Check for errors
    const errorMessages = await page.locator('text=/Failed|Error|Ошибка/i').count();
    if (errorMessages === 0) {
      console.log('✓ No error messages found');
      console.log('✓✓✓ Student Bookings Page PASSED');
      return true;
    } else {
      console.log(`✗ Found ${errorMessages} error messages`);
      return false;
    }
    
  } catch (error) {
    console.error('✗ Bookings Test FAILED:', error.message);
    return false;
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  
  const results = [];
  results.push(await testStudentProfile(browser));
  results.push(await testTeacherProfile(browser));
  results.push(await testTutorProfile(browser));
  results.push(await testStudentBookings(browser));
  
  await browser.close();
  
  const passed = results.filter(r => r).length;
  const total = results.length;
  
  console.log('\n========================================');
  console.log('TEST SUMMARY');
  console.log('========================================');
  console.log(`Passed: ${passed}/${total}`);
  
  if (passed === total) {
    console.log('\n✓✓✓ ALL TESTS PASSED ✓✓✓\n');
    process.exit(0);
  } else {
    console.log('\n✗✗✗ SOME TESTS FAILED ✗✗✗\n');
    process.exit(1);
  }
})();
