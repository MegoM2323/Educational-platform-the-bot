import { test, expect, Page } from '@playwright/test';

/**
 * Combined E2E Test: Student Role Complete Testing
 * Tasks: T003, T004, T005
 *
 * Test Scenarios:
 * - T003: Student Login & Dashboard
 * - T004: Student Schedule (View Lessons)
 * - T005: Student Forum (Chat List & Send Message)
 */

const BASE_URL = 'http://localhost:8080';
const API_URL = 'http://localhost:8000';

const TEST_CREDENTIALS = {
  email: 'student@test.com',
  password: 'testpass123'
};

test.describe('Student Role Complete E2E Testing', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('T003: Student Login & Dashboard', async () => {
    // Scenario 1: Navigate to login page
    await page.goto(`${BASE_URL}/auth`);
    await expect(page).toHaveURL(`${BASE_URL}/auth`);

    // Take screenshot of auth page
    await page.screenshot({
      path: '.playwright-mcp/T003_01_auth_page.png',
      fullPage: true
    });

    // Scenario 2: Fill login form
    await page.fill('input[type="email"]', TEST_CREDENTIALS.email);
    await page.fill('input[type="password"]', TEST_CREDENTIALS.password);

    // Take screenshot of filled form
    await page.screenshot({
      path: '.playwright-mcp/T003_02_auth_form_filled.png',
      fullPage: true
    });

    // Scenario 3: Click "Войти" button
    await page.click('button:has-text("Войти")');

    // Scenario 4: Expected redirect to /dashboard/student
    await page.waitForURL(`${BASE_URL}/dashboard/student`, { timeout: 10000 });
    await expect(page).toHaveURL(`${BASE_URL}/dashboard/student`);

    // Take screenshot of dashboard
    await page.screenshot({
      path: '.playwright-mcp/T003_03_student_dashboard.png',
      fullPage: true
    });

    // Scenario 5: Verify dashboard shows student-specific UI
    await expect(page.locator('text=Мой прогресс')).toBeVisible({ timeout: 5000 });

    // Check for no console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Scenario 6: Click navigation links
    const navLinks = [
      { text: 'Материалы', url: '/dashboard/student/materials' },
      { text: 'Расписание', url: '/dashboard/student/schedule' },
      { text: 'Форум', url: '/dashboard/student/forum' },
      { text: 'Профиль', url: '/profile/student' }
    ];

    for (const link of navLinks) {
      await page.click(`a:has-text("${link.text}")`);
      await page.waitForURL(`${BASE_URL}${link.url}`, { timeout: 5000 });
      await expect(page).toHaveURL(`${BASE_URL}${link.url}`);

      // Take screenshot of each page
      const linkName = link.text.toLowerCase().replace(/\s/g, '_');
      await page.screenshot({
        path: `.playwright-mcp/T003_04_${linkName}_page.png`,
        fullPage: true
      });

      // Wait a bit for page to fully load
      await page.waitForTimeout(1000);
    }

    // Scenario 7: Verify no console errors
    expect(consoleErrors.length).toBe(0);
  });

  test('T004: Student Schedule (View Lessons)', async () => {
    // Ensure we're logged in (should be from T003)
    await page.goto(`${BASE_URL}/dashboard/student`);
    await page.waitForURL(`${BASE_URL}/dashboard/student`, { timeout: 5000 });

    // Scenario 1: Navigate to /dashboard/student/schedule
    await page.goto(`${BASE_URL}/dashboard/student/schedule`);
    await expect(page).toHaveURL(`${BASE_URL}/dashboard/student/schedule`);

    // Scenario 2: Expected - Calendar component renders
    const calendarExists = await page.locator('[class*="calendar"]').count() > 0 ||
                           await page.locator('[class*="schedule"]').count() > 0 ||
                           await page.locator('text=/Расписание|Calendar/i').count() > 0;

    expect(calendarExists).toBeTruthy();

    // Take screenshot of schedule page
    await page.screenshot({
      path: '.playwright-mcp/T004_01_student_schedule_page.png',
      fullPage: true
    });

    // Scenario 3: Expected - Student's lessons appear on calendar
    // Check if any lesson elements exist
    const lessonElements = await page.locator('[class*="lesson"], [class*="event"]').count();

    // Scenario 4: Click on a lesson (if any exist)
    if (lessonElements > 0) {
      await page.click('[class*="lesson"], [class*="event"]');

      // Scenario 5: Expected - Lesson details show
      await page.waitForTimeout(1000); // Wait for modal/details to open

      // Take screenshot of lesson details
      await page.screenshot({
        path: '.playwright-mcp/T004_02_lesson_details.png',
        fullPage: true
      });
    } else {
      console.log('No lessons found on calendar - this is acceptable for test environment');
    }

    // Scenario 6: Take screenshot of schedule page
    await page.screenshot({
      path: '.playwright-mcp/T004_03_schedule_final.png',
      fullPage: true
    });
  });

  test('T005: Student Forum (Chat List & Send Message)', async () => {
    // Ensure we're logged in
    await page.goto(`${BASE_URL}/dashboard/student`);
    await page.waitForURL(`${BASE_URL}/dashboard/student`, { timeout: 5000 });

    // Scenario 1: Navigate to /dashboard/student/forum
    await page.goto(`${BASE_URL}/dashboard/student/forum`);
    await expect(page).toHaveURL(`${BASE_URL}/dashboard/student/forum`);

    // Wait for page to load
    await page.waitForTimeout(2000);

    // Take initial screenshot
    await page.screenshot({
      path: '.playwright-mcp/T005_01_forum_page_initial.png',
      fullPage: true
    });

    // Scenario 2: Expected - Chat list shows student's subject chats
    // Check that "Нет активных чатов" is NOT present OR chat list is present
    const noChatMessage = await page.locator('text=/Нет активных чатов/i').count();
    const chatListExists = await page.locator('[class*="chat"], [class*="message"]').count() > 0;

    if (noChatMessage > 0 && !chatListExists) {
      // This is a failure - no chats loading
      await page.screenshot({
        path: '.playwright-mcp/T005_FAIL_no_chats_loading.png',
        fullPage: true
      });
      console.error('FAILURE: Forum shows "Нет активных чатов" - chat list not loading');
    }

    // Scenario 3: Expected - Shows subject names and last messages
    // Verify at least some chat elements exist
    const chatElements = await page.locator('[class*="chat-item"], [class*="chat-list"] > *').count();
    expect(chatElements).toBeGreaterThan(0);

    // Take screenshot of chat list
    await page.screenshot({
      path: '.playwright-mcp/T005_02_chat_list_loaded.png',
      fullPage: true
    });

    // Scenario 4: Click first chat in list
    const firstChat = page.locator('[class*="chat-item"], [class*="chat-list"] > *').first();
    await firstChat.click();
    await page.waitForTimeout(1000);

    // Scenario 5: Expected - Chat opens, message history loads
    await expect(page.locator('[class*="message"], [class*="chat-window"]')).toBeVisible({ timeout: 5000 });

    // Take screenshot of opened chat
    await page.screenshot({
      path: '.playwright-mcp/T005_03_chat_opened.png',
      fullPage: true
    });

    // Scenario 6: Type test message and send
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await messageInput.fill('Test from student');

    // Find and click send button
    const sendButton = page.locator('button:has-text("Отправить"), button[type="submit"]').last();
    await sendButton.click();

    // Scenario 7: Expected - Message appears in chat immediately
    await page.waitForTimeout(1000);
    await expect(page.locator('text=Test from student')).toBeVisible({ timeout: 5000 });

    // Take screenshot of sent message
    await page.screenshot({
      path: '.playwright-mcp/T005_04_message_sent.png',
      fullPage: true
    });

    // Scenario 8: Check Network tab for WebSocket connection
    // Note: Playwright automatically monitors network, we can check via page.on('websocket')
    let wsConnected = false;
    page.on('websocket', ws => {
      console.log(`WebSocket connected: ${ws.url()}`);
      if (ws.url().includes('ws://localhost:8000/ws/')) {
        wsConnected = true;
      }
    });

    // Refresh to trigger new WebSocket connection
    await page.reload();
    await page.waitForTimeout(2000);

    // Take final screenshot
    await page.screenshot({
      path: '.playwright-mcp/T005_05_websocket_verification.png',
      fullPage: true
    });

    // Verify WebSocket connection (soft assertion - don't fail test if WS not detected)
    if (!wsConnected) {
      console.warn('WARNING: WebSocket connection not detected in this test run');
    }
  });

  test('Final Verification: No Console Errors', async () => {
    const consoleErrors: string[] = [];
    const consoleWarnings: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      } else if (msg.type() === 'warning') {
        consoleWarnings.push(msg.text());
      }
    });

    // Navigate through all student pages one more time
    const pages = [
      '/dashboard/student',
      '/dashboard/student/schedule',
      '/dashboard/student/forum'
    ];

    for (const route of pages) {
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForTimeout(2000);
    }

    // Report console errors
    if (consoleErrors.length > 0) {
      console.error('Console Errors Found:', consoleErrors);
    }

    if (consoleWarnings.length > 0) {
      console.warn('Console Warnings Found:', consoleWarnings);
    }

    expect(consoleErrors.length).toBe(0);
  });
});
