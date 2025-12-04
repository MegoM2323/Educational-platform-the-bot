import { test, expect } from '@playwright/test';

/**
 * T007: Test Student Schedule Fix
 *
 * Verify student schedule page now works after changing hook to use getLessons()
 * instead of getMySchedule() endpoint.
 */

test.describe('T007: Student Schedule Fix Verification', () => {
  const baseURL = 'http://localhost:8080';
  const apiURL = 'http://127.0.0.1:8000/api';

  // Credentials from T003
  const studentCredentials = {
    email: 'test_student_sched@test.com',
    password: 'test123'
  };

  test('Student can view schedule without 404 error', async ({ page }) => {
    console.log('\n=== T007: Testing Student Schedule Fix ===\n');

    // Monitor network requests
    const apiRequests: any[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method()
        });
      }
    });

    const apiResponses: any[] = [];
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiResponses.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    // 1. Navigate to login page
    console.log('1. Navigating to login page...');
    await page.goto(baseURL);
    await page.waitForLoadState('networkidle');

    // 2. Login as student
    console.log('2. Logging in as student...');
    await page.fill('input[type="email"]', studentCredentials.email);
    await page.fill('input[type="password"]', studentCredentials.password);

    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/auth/login/') && response.status() === 200
      ),
      page.click('button[type="submit"]')
    ]);

    console.log('   ✓ Login successful');

    // 3. Navigate to student schedule
    console.log('3. Navigating to /dashboard/student/schedule...');
    await page.goto(`${baseURL}/dashboard/student/schedule`);
    await page.waitForLoadState('networkidle');

    // Wait for schedule page to load (wait for any API call to complete)
    await page.waitForTimeout(2000);

    // 4. Verify NO 404 errors in API calls
    console.log('4. Checking API responses...');
    const errors404 = apiResponses.filter(r => r.status === 404);

    if (errors404.length > 0) {
      console.log('   ❌ Found 404 errors:');
      errors404.forEach(r => console.log(`      - ${r.url}`));
    } else {
      console.log('   ✓ No 404 errors found');
    }

    // 5. Verify correct API endpoint is called
    const schedulingRequests = apiRequests.filter(r =>
      r.url.includes('/scheduling/lessons/')
    );

    console.log('5. Checking scheduling API calls:');
    schedulingRequests.forEach(r => {
      console.log(`   - ${r.method} ${r.url}`);
    });

    // 6. Check for the OLD broken endpoint (should NOT be called)
    const myScheduleCalls = apiRequests.filter(r =>
      r.url.includes('/my-schedule/')
    );

    if (myScheduleCalls.length > 0) {
      console.log('   ❌ OLD /my-schedule/ endpoint still being called!');
      myScheduleCalls.forEach(r => console.log(`      - ${r.url}`));
    } else {
      console.log('   ✓ OLD /my-schedule/ endpoint NOT called (correct)');
    }

    // 7. Check for the NEW correct endpoint
    const lessonsListCalls = apiRequests.filter(r =>
      r.url.match(/\/scheduling\/lessons\/\?/) ||
      r.url.endsWith('/scheduling/lessons/')
    );

    if (lessonsListCalls.length > 0) {
      console.log('   ✓ NEW /lessons/ endpoint called (correct)');
      lessonsListCalls.forEach(r => console.log(`      - ${r.url}`));
    } else {
      console.log('   ❌ NEW /lessons/ endpoint NOT called');
    }

    // 8. Take screenshot
    await page.screenshot({
      path: '/home/mego/Python Projects/THE_BOT_platform/student_schedule_fixed.png',
      fullPage: true
    });
    console.log('8. Screenshot saved: student_schedule_fixed.png');

    // 9. Assertions
    console.log('\n=== Assertions ===');

    // Should have NO 404 errors
    expect(errors404.length).toBe(0);
    console.log('✓ No 404 errors');

    // Should NOT call /my-schedule/ (old broken endpoint)
    expect(myScheduleCalls.length).toBe(0);
    console.log('✓ Old /my-schedule/ endpoint not called');

    // Should call /lessons/ (new working endpoint)
    expect(lessonsListCalls.length).toBeGreaterThan(0);
    console.log('✓ New /lessons/ endpoint called');

    // Page should be at schedule route
    expect(page.url()).toContain('/dashboard/student/schedule');
    console.log('✓ On correct route');

    console.log('\n=== T007 Test PASSED ✓ ===\n');
  });
});
