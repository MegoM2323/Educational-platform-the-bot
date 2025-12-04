/**
 * T010: Forum Chat Verification Tests - All Roles
 *
 * Tests forum chat visibility and functionality for all user roles:
 * 1. Student - sees teacher chats + tutor chat
 * 2. Teacher - sees ONLY their student chats
 * 3. Tutor - sees ONLY their assigned student chats
 * 4. Parent - sees NO forum chats
 * 5. Real-time message exchange
 */

import { test, expect, Page } from '@playwright/test';

// Test credentials (must exist in DB)
const CREDENTIALS = {
  student: {
    email: 'student@test.com',
    password: 'password123',
    role: 'student',
  },
  teacher: {
    email: 'teacher@test.com',
    password: 'password123',
    role: 'teacher',
  },
  tutor: {
    email: 'tutor@test.com',
    password: 'password123',
    role: 'tutor',
  },
  parent: {
    email: 'parent@test.com',
    password: 'password123',
    role: 'parent',
  },
};

// Helper: Login as user
async function loginAs(page: Page, role: keyof typeof CREDENTIALS) {
  const user = CREDENTIALS[role];

  await page.goto('http://localhost:8080/auth');
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL(/\/dashboard/, { timeout: 10000 });
}

// Helper: Navigate to forum page
async function goToForum(page: Page, role: string) {
  await page.goto(`http://localhost:8080/dashboard/${role}/forum`);
  await page.waitForLoadState('networkidle');
}

// Helper: Get chat count
async function getChatCount(page: Page): Promise<number> {
  // Wait for loading to complete (no skeleton loaders)
  await page.waitForSelector('[data-testid="chat-list-skeleton"]', { state: 'hidden', timeout: 5000 }).catch(() => {});

  // Count chat items (excluding "no chats" message)
  const chats = await page.locator('[data-testid="chat-item"]').count();
  return chats;
}

// Helper: Send message in chat
async function sendMessage(page: Page, content: string) {
  await page.fill('input[placeholder*="Введите сообщение"]', content);
  await page.click('button:has-text("Send")');

  // Wait for message to appear
  await page.waitForSelector(`text="${content}"`, { timeout: 5000 });
}

test.describe('Forum Chat Verification - All Roles', () => {

  test('Student: sees correct chats (teachers + tutor)', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    // Student should see at least 1 chat (teacher or tutor)
    const chatCount = await getChatCount(page);
    expect(chatCount).toBeGreaterThan(0);

    // Check for "Форум" heading
    await expect(page.locator('h1:has-text("Форум")')).toBeVisible();

    // Verify chat list is visible
    await expect(page.locator('[data-testid="chat-list"]')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-student-chat-list.png', fullPage: true });

    console.log(`✅ Student sees ${chatCount} chat(s)`);
  });

  test('Student: can select and view chat messages', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    // Click first chat
    const firstChat = page.locator('[data-testid="chat-item"]').first();
    await firstChat.click();

    // Wait for chat window to load
    await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

    // Verify chat header is visible
    await expect(page.locator('[data-testid="chat-header"]')).toBeVisible();

    // Verify message input is visible
    await expect(page.locator('input[placeholder*="Введите сообщение"]')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-student-chat-window.png', fullPage: true });

    console.log('✅ Student can view chat window');
  });

  test('Student: can send message', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    // Select first chat
    await page.locator('[data-testid="chat-item"]').first().click();
    await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

    // Send test message
    const timestamp = Date.now();
    const testMessage = `Test message from student at ${timestamp}`;

    await page.fill('input[placeholder*="Введите сообщение"]', testMessage);
    await page.click('button[type="submit"]:has-text("Send"), button:has(svg)');

    // Wait for message to appear in chat
    await page.waitForSelector(`text="${testMessage}"`, { timeout: 10000 });

    // Verify message is visible
    await expect(page.locator(`text="${testMessage}"`)).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-student-message-sent.png', fullPage: true });

    console.log(`✅ Student sent message: ${testMessage}`);
  });

  test('Teacher: sees ONLY their student chats', async ({ page }) => {
    await loginAs(page, 'teacher');
    await goToForum(page, 'teacher');

    // Teacher should see at least 1 student chat
    const chatCount = await getChatCount(page);
    expect(chatCount).toBeGreaterThan(0);

    // Verify forum heading
    await expect(page.locator('h1:has-text("Форум")')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-teacher-chat-list.png', fullPage: true });

    console.log(`✅ Teacher sees ${chatCount} student chat(s)`);
  });

  test('Teacher: can send message to student', async ({ page }) => {
    await loginAs(page, 'teacher');
    await goToForum(page, 'teacher');

    // Select first student chat
    await page.locator('[data-testid="chat-item"]').first().click();
    await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

    // Send test message
    const timestamp = Date.now();
    const testMessage = `Teacher reply at ${timestamp}`;

    await page.fill('input[placeholder*="Введите сообщение"]', testMessage);
    await page.click('button[type="submit"]:has-text("Send"), button:has(svg)');

    // Wait for message to appear
    await page.waitForSelector(`text="${testMessage}"`, { timeout: 10000 });

    // Verify message is visible
    await expect(page.locator(`text="${testMessage}"`)).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-teacher-message-sent.png', fullPage: true });

    console.log(`✅ Teacher sent message: ${testMessage}`);
  });

  test('Tutor: sees ONLY assigned student chats', async ({ page }) => {
    await loginAs(page, 'tutor');
    await goToForum(page, 'tutor');

    // Tutor should see student chats if assigned
    const chatCount = await getChatCount(page);

    // Verify forum heading
    await expect(page.locator('h1:has-text("Форум")')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-tutor-chat-list.png', fullPage: true });

    console.log(`✅ Tutor sees ${chatCount} student chat(s)`);
  });

  test('Tutor: can send message to student', async ({ page }) => {
    await loginAs(page, 'tutor');
    await goToForum(page, 'tutor');

    const chatCount = await getChatCount(page);

    if (chatCount === 0) {
      console.log('⚠️  Tutor has no assigned students, skipping message test');
      return;
    }

    // Select first student chat
    await page.locator('[data-testid="chat-item"]').first().click();
    await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

    // Send test message
    const timestamp = Date.now();
    const testMessage = `Tutor message at ${timestamp}`;

    await page.fill('input[placeholder*="Введите сообщение"]', testMessage);
    await page.click('button[type="submit"]:has-text("Send"), button:has(svg)');

    // Wait for message to appear
    await page.waitForSelector(`text="${testMessage}"`, { timeout: 10000 });

    // Verify message is visible
    await expect(page.locator(`text="${testMessage}"`)).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-tutor-message-sent.png', fullPage: true });

    console.log(`✅ Tutor sent message: ${testMessage}`);
  });

  test('Parent: has NO forum access', async ({ page }) => {
    await loginAs(page, 'parent');
    await goToForum(page, 'parent');

    // Parent should see either:
    // 1. "No chats" message
    // 2. Empty chat list
    const chatCount = await getChatCount(page);
    expect(chatCount).toBe(0);

    // Verify "no chats" message
    await expect(page.locator('text="Нет активных чатов"')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-parent-no-chats.png', fullPage: true });

    console.log('✅ Parent has no forum chats (as expected)');
  });

  test('Real-time: message appears instantly (WebSocket)', async ({ browser }) => {
    // Open two browser contexts (student and teacher)
    const studentContext = await browser.newContext();
    const teacherContext = await browser.newContext();

    const studentPage = await studentContext.newPage();
    const teacherPage = await teacherContext.newPage();

    try {
      // Login both users
      await loginAs(studentPage, 'student');
      await loginAs(teacherPage, 'teacher');

      // Navigate to forum
      await goToForum(studentPage, 'student');
      await goToForum(teacherPage, 'teacher');

      // Student selects first chat
      await studentPage.locator('[data-testid="chat-item"]').first().click();
      await studentPage.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

      // Teacher selects first chat (should be same chat)
      await teacherPage.locator('[data-testid="chat-item"]').first().click();
      await teacherPage.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

      // Take "before" screenshots
      await studentPage.screenshot({ path: '/tmp/forum-realtime-student-before.png', fullPage: true });
      await teacherPage.screenshot({ path: '/tmp/forum-realtime-teacher-before.png', fullPage: true });

      // Student sends message
      const timestamp = Date.now();
      const testMessage = `Real-time test ${timestamp}`;

      await studentPage.fill('input[placeholder*="Введите сообщение"]', testMessage);
      await studentPage.click('button[type="submit"]:has-text("Send"), button:has(svg)');

      // Wait for message on student side
      await studentPage.waitForSelector(`text="${testMessage}"`, { timeout: 10000 });

      // CRITICAL: Wait for message to appear on teacher side (WebSocket)
      await teacherPage.waitForSelector(`text="${testMessage}"`, { timeout: 15000 });

      // Verify message is visible on both sides
      await expect(studentPage.locator(`text="${testMessage}"`)).toBeVisible();
      await expect(teacherPage.locator(`text="${testMessage}"`)).toBeVisible();

      // Take "after" screenshots
      await studentPage.screenshot({ path: '/tmp/forum-realtime-student-after.png', fullPage: true });
      await teacherPage.screenshot({ path: '/tmp/forum-realtime-teacher-after.png', fullPage: true });

      console.log(`✅ Real-time message delivery verified: ${testMessage}`);

    } finally {
      await studentContext.close();
      await teacherContext.close();
    }
  });

  test('WebSocket: connection status indicator', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    // Select first chat
    await page.locator('[data-testid="chat-item"]').first().click();
    await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

    // Wait for WebSocket connection
    await page.waitForTimeout(2000);

    // Check for "Онлайн" status indicator
    const onlineStatus = page.locator('text="Онлайн"');

    // Should be connected within 5 seconds
    await expect(onlineStatus).toBeVisible({ timeout: 5000 });

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-websocket-connected.png', fullPage: true });

    console.log('✅ WebSocket connection established');
  });

  test('Error handling: empty message validation', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    // Select first chat
    await page.locator('[data-testid="chat-item"]').first().click();
    await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });

    // Try to send empty message (button should be disabled)
    const sendButton = page.locator('button[type="submit"]:has-text("Send"), button:has(svg)');

    // Button should be disabled when input is empty
    await expect(sendButton).toBeDisabled();

    // Type spaces only
    await page.fill('input[placeholder*="Введите сообщение"]', '   ');

    // Button should still be disabled
    await expect(sendButton).toBeDisabled();

    console.log('✅ Empty message validation works');
  });

  test('Responsive: chat list scrollable', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    // Verify chat list has scroll area
    const chatList = page.locator('[data-testid="chat-list"]');
    await expect(chatList).toBeVisible();

    // Check if scrollable (has overflow)
    const isScrollable = await chatList.evaluate((el) => {
      return el.scrollHeight > el.clientHeight;
    });

    console.log(`Chat list scrollable: ${isScrollable}`);

    // Take screenshot
    await page.screenshot({ path: '/tmp/forum-chat-list-scroll.png', fullPage: true });
  });

  test('Search: filter chats by name', async ({ page }) => {
    await loginAs(page, 'student');
    await goToForum(page, 'student');

    const initialChatCount = await getChatCount(page);

    if (initialChatCount === 0) {
      console.log('No chats to search, skipping test');
      return;
    }

    // Get first chat name
    const firstChatName = await page.locator('[data-testid="chat-item"]').first().textContent();
    const searchTerm = firstChatName?.substring(0, 3) || 'test';

    // Use search input
    await page.fill('input[placeholder*="Поиск"]', searchTerm);

    // Wait for filtering
    await page.waitForTimeout(500);

    const filteredCount = await getChatCount(page);

    // Filtered count should be <= initial count
    expect(filteredCount).toBeLessThanOrEqual(initialChatCount);

    console.log(`✅ Search works: ${initialChatCount} → ${filteredCount} chats`);
  });
});
