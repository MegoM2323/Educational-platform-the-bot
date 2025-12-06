/**
 * Manual Student Role E2E Test
 * This is a simplified version that can be run manually
 * without Playwright's webServer configuration
 */

import { chromium, Browser, Page } from 'playwright';

const BASE_URL = 'http://127.0.0.1:8080';
const TEST_CREDENTIALS = {
  email: 'student@test.com',
  password: 'testpass123'
};

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTests() {
  let browser: Browser | null = null;
  let page: Page | null = null;

  try {
    console.log('🚀 Starting Student Role E2E Tests...\n');

    // Launch browser
    browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    page = await context.newPage();

    // Enable console logging
    page.on('console', msg => {
      const type = msg.type();
      if (type === 'error') {
        console.log(`❌ CONSOLE ERROR: ${msg.text()}`);
      } else if (type === 'warning') {
        console.log(`⚠️  CONSOLE WARNING: ${msg.text()}`);
      }
    });

    console.log('='.repeat(70));
    console.log('T003: Student Login & Dashboard');
    console.log('='.repeat(70));

    // Scenario 1: Navigate to login
    console.log('\n📍 Scenario 1: Navigate to /auth');
    await page.goto(`${BASE_URL}/auth`);
    await sleep(2000);

    await page.screenshot({
      path: '.playwright-mcp/T003_01_auth_page.png',
      fullPage: true
    });
    console.log('✅ Screenshot saved: T003_01_auth_page.png');

    // Scenario 2: Fill login form
    console.log('\n📍 Scenario 2: Fill login form');
    await page.fill('input[type="email"]', TEST_CREDENTIALS.email);
    await page.fill('input[type="password"]', TEST_CREDENTIALS.password);

    await page.screenshot({
      path: '.playwright-mcp/T003_02_form_filled.png',
      fullPage: true
    });
    console.log('✅ Screenshot saved: T003_02_form_filled.png');

    // Scenario 3: Click Login button
    console.log('\n📍 Scenario 3: Click Войти button');
    await page.click('button:has-text("Войти")');

    // Wait for navigation
    await page.waitForURL(`${BASE_URL}/dashboard/student`, { timeout: 10000 });
    await sleep(2000);

    await page.screenshot({
      path: '.playwright-mcp/T003_03_dashboard.png',
      fullPage: true
    });
    console.log('✅ Redirected to /dashboard/student');
    console.log('✅ Screenshot saved: T003_03_dashboard.png');

    // Scenario 4: Verify dashboard UI
    console.log('\n📍 Scenario 4: Verify dashboard UI');
    const dashboardText = await page.textContent('body');
    if (dashboardText?.includes('прогресс') || dashboardText?.includes('Расписание')) {
      console.log('✅ Dashboard shows student-specific UI');
    } else {
      console.log('❌ Dashboard UI verification failed');
    }

    // Scenario 5: Navigate to pages
    console.log('\n📍 Scenario 5: Test navigation');

    const navLinks = [
      { text: 'Расписание', url: '/dashboard/student/schedule' },
      { text: 'Форум', url: '/dashboard/student/forum' }
    ];

    for (const link of navLinks) {
      console.log(`\n  → Navigating to ${link.text}...`);
      await page.click(`a:has-text("${link.text}")`);
      await sleep(1500);

      const currentURL = page.url();
      if (currentURL.includes(link.url)) {
        console.log(`  ✅ Successfully navigated to ${link.url}`);
        await page.screenshot({
          path: `.playwright-mcp/T003_04_${link.text.toLowerCase().replace(/\s/g, '_')}.png`,
          fullPage: true
        });
      } else {
        console.log(`  ❌ Navigation failed. Expected ${link.url}, got ${currentURL}`);
      }
    }

    console.log('\n' + '='.repeat(70));
    console.log('T004: Student Schedule');
    console.log('='.repeat(70));

    // Navigate to schedule
    console.log('\n📍 Navigating to /dashboard/student/schedule');
    await page.goto(`${BASE_URL}/dashboard/student/schedule`);
    await sleep(2000);

    await page.screenshot({
      path: '.playwright-mcp/T004_01_schedule.png',
      fullPage: true
    });
    console.log('✅ Screenshot saved: T004_01_schedule.png');

    // Check if calendar exists
    const bodyHTML = await page.content();
    if (bodyHTML.includes('calendar') || bodyHTML.includes('schedule') || bodyHTML.includes('Расписание')) {
      console.log('✅ Schedule page loaded with calendar component');
    } else {
      console.log('⚠️  Schedule page loaded but calendar not detected');
    }

    console.log('\n' + '='.repeat(70));
    console.log('T005: Student Forum (Chat)');
    console.log('='.repeat(70));

    // Navigate to forum
    console.log('\n📍 Navigating to /dashboard/student/forum');
    await page.goto(`${BASE_URL}/dashboard/student/forum`);
    await sleep(3000); // Wait for TanStack Query to load data

    await page.screenshot({
      path: '.playwright-mcp/T005_01_forum_initial.png',
      fullPage: true
    });
    console.log('✅ Screenshot saved: T005_01_forum_initial.png');

    // Check if chat list loaded
    const forumText = await page.textContent('body');
    if (forumText?.includes('Нет активных чатов')) {
      console.log('❌ FAILURE: Forum shows "Нет активных чатов" - chat list not loading');
      await page.screenshot({
        path: '.playwright-mcp/T005_FAIL_no_chats.png',
        fullPage: true
      });
    } else {
      console.log('✅ Forum chat list appears to be loading');

      // Try to find and click first chat
      try {
        const chatItems = await page.locator('[class*="chat"]').count();
        console.log(`  → Found ${chatItems} chat-related elements`);

        if (chatItems > 0) {
          console.log('  → Clicking first chat...');
          await page.locator('[class*="chat"]').first().click();
          await sleep(2000);

          await page.screenshot({
            path: '.playwright-mcp/T005_02_chat_opened.png',
            fullPage: true
          });
          console.log('  ✅ Chat opened');

          // Try to send message
          console.log('  → Attempting to send test message...');
          const messageInput = page.locator('textarea, input[type="text"]').last();
          await messageInput.fill('Test from student');

          const sendButton = page.locator('button:has-text("Отправить"), button[type="submit"]').last();
          await sendButton.click();
          await sleep(1500);

          await page.screenshot({
            path: '.playwright-mcp/T005_03_message_sent.png',
            fullPage: true
          });
          console.log('  ✅ Message sent');
        }
      } catch (error) {
        console.log(`  ⚠️  Error interacting with chat: ${error}`);
      }
    }

    console.log('\n' + '='.repeat(70));
    console.log('✅ ALL TESTS COMPLETED');
    console.log('='.repeat(70));
    console.log('\n📸 Screenshots saved in .playwright-mcp/');
    console.log('🔍 Review the screenshots to verify test results');

  } catch (error) {
    console.error('\n❌ TEST FAILED WITH ERROR:');
    console.error(error);

    if (page) {
      await page.screenshot({
        path: '.playwright-mcp/ERROR_screenshot.png',
        fullPage: true
      });
      console.log('\n📸 Error screenshot saved: ERROR_screenshot.png');
    }
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Run the tests
runTests().then(() => {
  console.log('\n✅ Test runner completed');
  process.exit(0);
}).catch(error => {
  console.error('\n❌ Test runner failed:', error);
  process.exit(1);
});
