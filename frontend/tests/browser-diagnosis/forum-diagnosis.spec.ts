import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';

// Test credentials from T002
const CREDENTIALS = {
  student: { email: 'test_student@test.com', password: 'test123' },
  teacher: { email: 'test_teacher@test.com', password: 'test123' },
  tutor: { email: 'test_tutor@test.com', password: 'test123' },
};

test.describe('Forum Frontend Diagnosis', () => {
  test.beforeEach(async ({ page }) => {
    // Listen for console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.log(`❌ CONSOLE ERROR: ${msg.text()}`);
      }
    });

    // Listen for page errors
    page.on('pageerror', (error) => {
      console.log(`❌ PAGE ERROR: ${error.message}`);
    });
  });

  test('Student - Forum Page Diagnosis', async ({ page }) => {
    console.log('\n===== TESTING STUDENT ROLE =====\n');

    // Navigate to login page
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Login as student
    console.log('1. Logging in as student...');
    await page.fill('input[type="email"]', CREDENTIALS.student.email);
    await page.fill('input[type="password"]', CREDENTIALS.student.password);

    // Intercept API calls
    const apiCalls: any[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
        console.log(`📡 API Call: ${response.request().method()} ${response.url()} - ${response.status()}`);
      }
    });

    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Check current URL
    const currentUrl = page.url();
    console.log(`2. Current URL after login: ${currentUrl}`);

    // Navigate to forum
    console.log('3. Navigating to /dashboard/student/forum...');
    await page.goto(`${BASE_URL}/dashboard/student/forum`);
    await page.waitForLoadState('networkidle');

    // Wait a bit for API calls to complete
    await page.waitForTimeout(2000);

    // Check if we're still on forum page
    const forumUrl = page.url();
    console.log(`4. Current URL after forum navigation: ${forumUrl}`);

    // Take screenshot
    await page.screenshot({ path: '/tmp/student-forum-page.png', fullPage: true });
    console.log('📸 Screenshot saved: /tmp/student-forum-page.png');

    // Check for chat list component
    const chatListVisible = await page.locator('text=Chat').isVisible().catch(() => false);
    console.log(`5. ChatList component visible: ${chatListVisible}`);

    // Check for WebSocket connection
    const wsConnections: any[] = [];
    page.on('websocket', (ws) => {
      console.log(`🔌 WebSocket connection: ${ws.url()}`);
      wsConnections.push(ws.url());

      ws.on('framesent', (event) => console.log(`📤 WS Frame sent: ${event.payload}`));
      ws.on('framereceived', (event) => console.log(`📥 WS Frame received: ${event.payload}`));
      ws.on('close', () => console.log('🔌 WebSocket closed'));
    });

    // Check API calls made
    console.log('\n6. API Calls Summary:');
    apiCalls.forEach((call) => {
      console.log(`   ${call.method} ${call.url} - Status: ${call.status}`);
    });

    console.log('\n7. WebSocket Connections:');
    console.log(wsConnections.length > 0 ? wsConnections : '   None detected');

    // Get page content
    const pageContent = await page.content();
    if (pageContent.includes('error') || pageContent.includes('Error')) {
      console.log('\n⚠️  Page content contains "error" text');
    }

    // Check for specific error messages
    const errorMessages = await page.locator('[role="alert"]').allTextContents();
    if (errorMessages.length > 0) {
      console.log('\n⚠️  Alert messages found:');
      errorMessages.forEach(msg => console.log(`   - ${msg}`));
    }
  });

  test('Teacher - Forum Page Diagnosis', async ({ page }) => {
    console.log('\n===== TESTING TEACHER ROLE =====\n');

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    console.log('1. Logging in as teacher...');
    await page.fill('input[type="email"]', CREDENTIALS.teacher.email);
    await page.fill('input[type="password"]', CREDENTIALS.teacher.password);

    const apiCalls: any[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
        console.log(`📡 API Call: ${response.request().method()} ${response.url()} - ${response.status()}`);
      }
    });

    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    console.log(`2. Current URL after login: ${currentUrl}`);

    console.log('3. Navigating to /dashboard/teacher/forum...');
    await page.goto(`${BASE_URL}/dashboard/teacher/forum`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const forumUrl = page.url();
    console.log(`4. Current URL after forum navigation: ${forumUrl}`);

    await page.screenshot({ path: '/tmp/teacher-forum-page.png', fullPage: true });
    console.log('📸 Screenshot saved: /tmp/teacher-forum-page.png');

    console.log('\n5. API Calls Summary:');
    apiCalls.forEach((call) => {
      console.log(`   ${call.method} ${call.url} - Status: ${call.status}`);
    });

    const errorMessages = await page.locator('[role="alert"]').allTextContents();
    if (errorMessages.length > 0) {
      console.log('\n⚠️  Alert messages found:');
      errorMessages.forEach(msg => console.log(`   - ${msg}`));
    }
  });

  test('Tutor - Forum Page Diagnosis', async ({ page }) => {
    console.log('\n===== TESTING TUTOR ROLE =====\n');

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    console.log('1. Logging in as tutor...');
    await page.fill('input[type="email"]', CREDENTIALS.tutor.email);
    await page.fill('input[type="password"]', CREDENTIALS.tutor.password);

    const apiCalls: any[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
        console.log(`📡 API Call: ${response.request().method()} ${response.url()} - ${response.status()}`);
      }
    });

    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    console.log(`2. Current URL after login: ${currentUrl}`);

    console.log('3. Navigating to /dashboard/tutor/forum...');
    await page.goto(`${BASE_URL}/dashboard/tutor/forum`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const forumUrl = page.url();
    console.log(`4. Current URL after forum navigation: ${forumUrl}`);

    await page.screenshot({ path: '/tmp/tutor-forum-page.png', fullPage: true });
    console.log('📸 Screenshot saved: /tmp/tutor-forum-page.png');

    console.log('\n5. API Calls Summary:');
    apiCalls.forEach((call) => {
      console.log(`   ${call.method} ${call.url} - Status: ${call.status}`);
    });

    const errorMessages = await page.locator('[role="alert"]').allTextContents();
    if (errorMessages.length > 0) {
      console.log('\n⚠️  Alert messages found:');
      errorMessages.forEach(msg => console.log(`   - ${msg}`));
    }
  });
});
