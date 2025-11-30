const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = [];
  
  try {
    // ========== TEST 1: Student Profile Navigation ==========
    console.log('\n========================================');
    console.log('TEST 1: Student Profile Navigation');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    
    try {
      await page.waitForURL(/\/dashboard/, { timeout: 15000 });
      console.log('✓ Redirected to dashboard');
    } catch (e) {
      console.log('✗ Dashboard redirect failed. Current URL:', page.url());
      results.push({ test: 'Student Profile', passed: false, error: 'Dashboard redirect timeout' });
      throw e;
    }
    
    // Click edit profile
    try {
      await page.click('button:has-text("Редактировать")', { timeout: 5000 });
    } catch (e) {
      console.log('✗ Edit button not found');
      results.push({ test: 'Student Profile', passed: false, error: 'Edit button not found' });
      throw e;
    }
    
    try {
      await page.waitForURL(/\/profile\/student/, { timeout: 10000 });
      console.log('✓ Navigated to /profile/student');
      results.push({ test: 'Student Profile Navigation', passed: true });
    } catch (e) {
      console.log('✗ Profile navigation failed. Current URL:', page.url());
      results.push({ test: 'Student Profile Navigation', passed: false, error: 'Profile URL mismatch' });
      throw e;
    }
    
    // ========== TEST 2: Teacher Profile Navigation ==========
    console.log('\n========================================');
    console.log('TEST 2: Teacher Profile Navigation');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'teacher@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    
    try {
      await page.waitForURL(/\/dashboard/, { timeout: 15000 });
      console.log('✓ Teacher dashboard loaded');
    } catch (e) {
      console.log('✗ Teacher dashboard timeout');
      results.push({ test: 'Teacher Profile', passed: false, error: 'Dashboard timeout' });
      throw e;
    }
    
    await page.click('button:has-text("Редактировать")', { timeout: 5000 });
    
    try {
      await page.waitForURL(/\/profile\/teacher/, { timeout: 10000 });
      console.log('✓ Navigated to /profile/teacher');
      results.push({ test: 'Teacher Profile Navigation', passed: true });
    } catch (e) {
      console.log('✗ Teacher profile URL mismatch. Current:', page.url());
      results.push({ test: 'Teacher Profile Navigation', passed: false, error: 'Profile URL mismatch' });
      throw e;
    }
    
    // ========== TEST 3: Tutor Profile Navigation ==========
    console.log('\n========================================');
    console.log('TEST 3: Tutor Profile Navigation');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'tutor@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    
    try {
      await page.waitForURL(/\/dashboard/, { timeout: 15000 });
      console.log('✓ Tutor dashboard loaded');
    } catch (e) {
      console.log('✗ Tutor dashboard timeout');
      results.push({ test: 'Tutor Profile', passed: false, error: 'Dashboard timeout' });
      throw e;
    }
    
    await page.click('button:has-text("Редактировать")', { timeout: 5000 });
    
    try {
      await page.waitForURL(/\/profile\/tutor/, { timeout: 10000 });
      console.log('✓ Navigated to /profile/tutor');
      results.push({ test: 'Tutor Profile Navigation', passed: true });
    } catch (e) {
      console.log('✗ Tutor profile URL mismatch. Current:', page.url());
      results.push({ test: 'Tutor Profile Navigation', passed: false, error: 'Profile URL mismatch' });
      throw e;
    }
    
    // ========== TEST 4: Student Bookings Page ==========
    console.log('\n========================================');
    console.log('TEST 4: Student Bookings Page');
    console.log('========================================');
    
    await page.goto('http://localhost:8080/auth');
    await page.fill('input[type="email"]', 'student@test.com');
    await page.fill('input[type="password"]', 'TestPass123!');
    await page.click('button:has-text("Войти")');
    
    try {
      await page.waitForURL(/\/dashboard/, { timeout: 15000 });
      console.log('✓ Student dashboard loaded');
    } catch (e) {
      results.push({ test: 'Student Bookings Page', passed: false, error: 'Dashboard timeout' });
      throw e;
    }
    
    // Navigate to bookings page
    try {
      await page.goto('http://localhost:8080/dashboard/student/bookings');
      await page.waitForLoadState('networkidle');
      console.log('✓ Bookings page loaded');
      
      // Check for error messages
      const errorElement = await page.locator(':text("Failed to load")').count();
      if (errorElement === 0) {
        console.log('✓ No "Failed to load" error');
        results.push({ test: 'Student Bookings Page', passed: true });
      } else {
        console.log('✗ "Failed to load" error found');
        results.push({ test: 'Student Bookings Page', passed: false, error: 'Failed to load error' });
      }
    } catch (e) {
      console.log('✗ Bookings page error:', e.message);
      results.push({ test: 'Student Bookings Page', passed: false, error: e.message });
    }
    
    // ========== SUMMARY ==========
    console.log('\n========================================');
    console.log('TEST SUMMARY');
    console.log('========================================');
    
    const passed = results.filter(r => r.passed).length;
    const total = results.length;
    
    results.forEach(r => {
      const status = r.passed ? '✓ PASS' : '✗ FAIL';
      const msg = r.error ? ` (${r.error})` : '';
      console.log(`${status}: ${r.test}${msg}`);
    });
    
    console.log(`\nTotal: ${passed}/${total} passed`);
    
    if (passed === total) {
      console.log('\n✓✓✓ ALL TESTS PASSED ✓✓✓\n');
      process.exit(0);
    } else {
      console.log('\n✗✗✗ SOME TESTS FAILED ✗✗✗\n');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('\nCritical error:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
