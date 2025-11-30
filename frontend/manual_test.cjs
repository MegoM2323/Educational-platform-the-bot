const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // Test 1: Student Profile Navigation
    console.log('\n========================================');
    console.log('TEST 1: Student Profile Navigation');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    console.log('✓ Auth page opened');
    
    // Fill login
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Вход")');
    console.log('✓ Login submitted');
    
    // Wait for dashboard
    try {
      await page.waitForURL(/\/dashboard/, { timeout: 15000 });
      console.log('✓ Redirected to dashboard');
    } catch (e) {
      console.log('✗ Did not redirect to dashboard:', page.url());
      throw e;
    }
    
    // Find and click Edit Profile button
    try {
      await page.click('button:has-text("Редактировать")', { timeout: 5000 });
      console.log('✓ Edit button clicked');
    } catch (e) {
      console.log('✗ Could not find Edit button');
      throw e;
    }
    
    // Wait for profile page
    try {
      await page.waitForURL(/\/profile\/student/, { timeout: 10000 });
      console.log('✓ Navigated to /profile/student');
    } catch (e) {
      console.log('✗ Did not navigate to profile:', page.url());
      throw e;
    }
    
    // Check if profile form is visible
    const formExists = await page.locator('form').count();
    if (formExists > 0) {
      console.log('✓ Profile form found');
    }
    
    console.log('\n✓✓✓ TEST 1 PASSED ✓✓✓\n');
    
    // Test 2: Teacher Profile
    console.log('========================================');
    console.log('TEST 2: Teacher Profile Navigation');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Вход")');
    console.log('✓ Teacher login submitted');
    
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    console.log('✓ Redirected to dashboard');
    
    await page.click('button:has-text("Редактировать")', { timeout: 5000 });
    console.log('✓ Edit button clicked');
    
    await page.waitForURL(/\/profile\/teacher/, { timeout: 10000 });
    console.log('✓ Navigated to /profile/teacher');
    
    console.log('\n✓✓✓ TEST 2 PASSED ✓✓✓\n');
    
    // Test 3: Tutor Profile
    console.log('========================================');
    console.log('TEST 3: Tutor Profile Navigation');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Вход")');
    console.log('✓ Tutor login submitted');
    
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    console.log('✓ Redirected to dashboard');
    
    await page.click('button:has-text("Редактировать")', { timeout: 5000 });
    console.log('✓ Edit button clicked');
    
    await page.waitForURL(/\/profile\/tutor/, { timeout: 10000 });
    console.log('✓ Navigated to /profile/tutor');
    
    console.log('\n✓✓✓ TEST 3 PASSED ✓✓✓\n');
    
    console.log('\n========================================');
    console.log('✓✓✓ ALL PROFILE TESTS PASSED ✓✓✓');
    console.log('========================================\n');
    
  } catch (error) {
    console.error('\n✗✗✗ TEST FAILED ✗✗✗');
    console.error('Error:', error.message);
    await page.screenshot({ path: '/tmp/test_failure.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
