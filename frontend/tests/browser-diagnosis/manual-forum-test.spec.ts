import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';

// Test credentials from T002
const CREDENTIALS = {
  student: { email: 'test_student@test.com', password: 'test123' },
  teacher: { email: 'test_teacher@test.com', password: 'test123' },
  tutor: { email: 'test_tutor@test.com', password: 'test123' },
};

test.describe('Forum Frontend Diagnosis - Manual Tests', () => {
  test('Student Forum Diagnosis', async ({ page }) => {
    console.log('\n========== STUDENT FORUM DIAGNOSIS ==========\n');

    // Setup console and error logging
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const apiCalls: any[] = [];
    const wsConnections: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        consoleErrors.push(text);
        console.log(`❌ CONSOLE ERROR: ${text}`);
      }
    });

    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
      console.log(`❌ PAGE ERROR: ${error.message}`);
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/')) {
        const call = {
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        };
        apiCalls.push(call);
        console.log(`📡 API: ${call.method} ${call.url} - ${call.status}`);

        // Log response body for forum endpoints
        if (response.url().includes('/forum/') || response.url().includes('/chat/')) {
          try {
            const body = await response.text();
            console.log(`   Response body: ${body.substring(0, 200)}...`);
          } catch (e) {
            console.log('   (Could not read response body)');
          }
        }
      }
    });

    page.on('websocket', (ws) => {
      wsConnections.push(ws.url());
      console.log(`🔌 WebSocket: ${ws.url()}`);

      ws.on('framesent', (event) => console.log(`📤 WS Sent: ${event.payload}`));
      ws.on('framereceived', (event) => console.log(`📥 WS Received: ${event.payload}`));
      ws.on('close', () => console.log('🔌 WebSocket closed'));
    });

    // Step 1: Navigate to auth page
    console.log('1. Navigating to auth page...');
    await page.goto(`${BASE_URL}/auth`);
    await page.waitForLoadState('networkidle');

    // Step 2: Login
    console.log('2. Logging in as student...');
    await page.getByTestId('login-email-input').fill(CREDENTIALS.student.email);
    await page.getByTestId('login-password-input').fill(CREDENTIALS.student.password);
    await page.getByTestId('login-submit-button').click();

    // Wait for navigation to dashboard
    await page.waitForLoadState('networkidle');
    const dashboardUrl = page.url();
    console.log(`3. Redirected to: ${dashboardUrl}`);

    // Step 3: Navigate to forum
    console.log('4. Navigating to /dashboard/student/forum...');
    await page.goto(`${BASE_URL}/dashboard/student/forum`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000); // Wait for API calls

    const forumUrl = page.url();
    console.log(`5. Current URL: ${forumUrl}`);

    // Check if redirected away
    if (!forumUrl.includes('/forum')) {
      console.log(`⚠️  REDIRECTED AWAY FROM FORUM! Current URL: ${forumUrl}`);
    }

    // Step 4: Take screenshot
    await page.screenshot({ path: '/tmp/student-forum.png', fullPage: true });
    console.log('📸 Screenshot: /tmp/student-forum.png');

    // Step 5: Check page content
    const pageText = await page.textContent('body');
    console.log(`6. Page contains "forum": ${pageText?.toLowerCase().includes('forum')}`);
    console.log(`   Page contains "chat": ${pageText?.toLowerCase().includes('chat')}`);
    console.log(`   Page contains "error": ${pageText?.toLowerCase().includes('error')}`);

    // Step 6: Check for specific elements
    const hasChatList = await page.locator('[data-testid="chat-list"]').isVisible().catch(() => false);
    const hasForumHeader = await page.locator('h1, h2, h3').filter({ hasText: /форум|forum/i }).isVisible().catch(() => false);

    console.log(`7. ChatList component visible: ${hasChatList}`);
    console.log(`   Forum header visible: ${hasForumHeader}`);

    // Step 7: Summary
    console.log('\n========== SUMMARY ==========');
    console.log(`Console Errors: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
    }

    console.log(`\nPage Errors: ${pageErrors.length}`);
    if (pageErrors.length > 0) {
      pageErrors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
    }

    console.log(`\nAPI Calls: ${apiCalls.length}`);
    apiCalls.forEach((call) => {
      console.log(`  ${call.method} ${call.url} - ${call.status}`);
    });

    console.log(`\nWebSocket Connections: ${wsConnections.length}`);
    wsConnections.forEach((url) => console.log(`  ${url}`));

    console.log('\n========================================\n');
  });

  test('Teacher Forum Diagnosis', async ({ page }) => {
    console.log('\n========== TEACHER FORUM DIAGNOSIS ==========\n');

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const apiCalls: any[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log(`❌ CONSOLE ERROR: ${msg.text()}`);
      }
    });

    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
      console.log(`❌ PAGE ERROR: ${error.message}`);
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/')) {
        const call = {
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        };
        apiCalls.push(call);
        console.log(`📡 API: ${call.method} ${call.url} - ${call.status}`);
      }
    });

    await page.goto(`${BASE_URL}/auth`);
    await page.waitForLoadState('networkidle');

    console.log('Logging in as teacher...');
    await page.getByTestId('login-email-input').fill(CREDENTIALS.teacher.email);
    await page.getByTestId('login-password-input').fill(CREDENTIALS.teacher.password);
    await page.getByTestId('login-submit-button').click();

    await page.waitForLoadState('networkidle');
    console.log(`Redirected to: ${page.url()}`);

    console.log('Navigating to /dashboard/teacher/forum...');
    await page.goto(`${BASE_URL}/dashboard/teacher/forum`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const forumUrl = page.url();
    console.log(`Current URL: ${forumUrl}`);

    await page.screenshot({ path: '/tmp/teacher-forum.png', fullPage: true });
    console.log('📸 Screenshot: /tmp/teacher-forum.png');

    console.log('\n========== SUMMARY ==========');
    console.log(`Console Errors: ${consoleErrors.length}`);
    consoleErrors.forEach((err) => console.log(`  ${err}`));
    console.log(`Page Errors: ${pageErrors.length}`);
    pageErrors.forEach((err) => console.log(`  ${err}`));
    console.log(`API Calls: ${apiCalls.length}`);
    apiCalls.forEach((call) => console.log(`  ${call.method} ${call.url} - ${call.status}`));
    console.log('\n========================================\n');
  });

  test('Tutor Forum Diagnosis', async ({ page }) => {
    console.log('\n========== TUTOR FORUM DIAGNOSIS ==========\n');

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const apiCalls: any[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log(`❌ CONSOLE ERROR: ${msg.text()}`);
      }
    });

    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
      console.log(`❌ PAGE ERROR: ${error.message}`);
    });

    page.on('response', async (response) => {
      if (response.url().includes('/api/')) {
        const call = {
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        };
        apiCalls.push(call);
        console.log(`📡 API: ${call.method} ${call.url} - ${call.status}`);
      }
    });

    await page.goto(`${BASE_URL}/auth`);
    await page.waitForLoadState('networkidle');

    console.log('Logging in as tutor...');
    await page.getByTestId('login-email-input').fill(CREDENTIALS.tutor.email);
    await page.getByTestId('login-password-input').fill(CREDENTIALS.tutor.password);
    await page.getByTestId('login-submit-button').click();

    await page.waitForLoadState('networkidle');
    console.log(`Redirected to: ${page.url()}`);

    console.log('Navigating to /dashboard/tutor/forum...');
    await page.goto(`${BASE_URL}/dashboard/tutor/forum`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const forumUrl = page.url();
    console.log(`Current URL: ${forumUrl}`);

    await page.screenshot({ path: '/tmp/tutor-forum.png', fullPage: true });
    console.log('📸 Screenshot: /tmp/tutor-forum.png');

    console.log('\n========== SUMMARY ==========');
    console.log(`Console Errors: ${consoleErrors.length}`);
    consoleErrors.forEach((err) => console.log(`  ${err}`));
    console.log(`Page Errors: ${pageErrors.length}`);
    pageErrors.forEach((err) => console.log(`  ${err}`));
    console.log(`API Calls: ${apiCalls.length}`);
    apiCalls.forEach((call) => console.log(`  ${call.method} ${call.url} - ${call.status}`));
    console.log('\n========================================\n');
  });
});
