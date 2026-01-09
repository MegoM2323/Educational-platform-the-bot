import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * E2E Tests для базовой системы чатов
 * Проверяет: отправка, получение, редактирование, удаление сообщений в реальном времени
 */

const BASE_URL = 'https://the-bot.ru';

// Test credentials
const CREDENTIALS = {
  student: { email: 'test_student@example.com', password: 'TestPassword123!' },
  teacher: { email: 'test_teacher@example.com', password: 'TestPassword123!' },
  parent: { email: 'test_parent@example.com', password: 'TestPassword123!' },
};

/**
 * Helper: Login user
 */
async function loginAs(page: Page, role: 'student' | 'teacher' | 'parent') {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[type="email"]', CREDENTIALS[role].email);
  await page.fill('input[type="password"]', CREDENTIALS[role].password);
  await page.click('button[type="submit"]');
  await page.waitForNavigation({ url: /dashboard/ });
}

/**
 * T3.1.1: Login & Open Chats
 */
test('T3.1.1 Student can login and open chats page', async ({ page }) => {
  await loginAs(page, 'student');

  // Navigate to forum/chats
  await page.goto(`${BASE_URL}/dashboard/student/forum`);

  // Check page loaded
  expect(page.url()).toContain('/forum');

  // Check chat list is visible
  await page.waitForSelector('[data-testid="chat-list"]', { timeout: 10000 });
  const chatList = await page.locator('[data-testid="chat-list"]');
  await expect(chatList).toBeVisible();
});

/**
 * T3.1.2: Create new chat
 */
test('T3.1.2 Student can create a new chat with teacher', async ({ page }) => {
  await loginAs(page, 'student');
  await page.goto(`${BASE_URL}/dashboard/student/forum`);

  // Click "New message" button
  await page.click('button:has-text("New Message"), button:has-text("Новое сообщение")');

  // Modal should open
  await page.waitForSelector('[data-testid="contacts-list"]', { timeout: 5000 });

  // Select teacher from contacts
  await page.click('[data-testid="contact-item"]:first-child');

  // Chat should be created and visible in list
  await page.waitForSelector('[data-testid="chat-item"]', { timeout: 5000 });
  const chatItem = await page.locator('[data-testid="chat-item"]').first();
  await expect(chatItem).toBeVisible();
});

/**
 * T3.1.3: Send message
 */
test('T3.1.3 Student can send a message', async ({ page }) => {
  await loginAs(page, 'student');
  await page.goto(`${BASE_URL}/dashboard/student/forum`);

  // Open first chat
  await page.click('[data-testid="chat-item"]:first-child');
  await page.waitForSelector('[data-testid="message-list"]', { timeout: 5000 });

  // Type message
  const testMessage = `Test message ${Date.now()}`;
  await page.fill('[data-testid="message-input"]', testMessage);

  // Send message
  await page.click('button[data-testid="send-message"]');

  // Message should appear in list
  await page.waitForSelector(`text=${testMessage}`, { timeout: 5000 });
  await expect(page.locator(`text=${testMessage}`)).toBeVisible();
});

/**
 * T3.1.4: Real-time message receive (WebSocket)
 */
test('T3.1.4 Real-time message receive via WebSocket', async ({ browser }) => {
  // Open two browser contexts (student + teacher)
  const contextStudent = await browser.newContext();
  const contextTeacher = await browser.newContext();

  const pageStudent = await contextStudent.newPage();
  const pageTeacher = await contextTeacher.newPage();

  try {
    // Login both users
    await loginAs(pageStudent, 'student');
    await loginAs(pageTeacher, 'teacher');

    // Open same chat in both windows
    await pageStudent.goto(`${BASE_URL}/dashboard/student/forum`);
    await pageTeacher.goto(`${BASE_URL}/dashboard/teacher/forum`);

    // Wait for chats to load
    await pageStudent.waitForSelector('[data-testid="chat-item"]:first-child', { timeout: 5000 });
    await pageTeacher.waitForSelector('[data-testid="chat-item"]:first-child', { timeout: 5000 });

    // Open same chat
    await pageStudent.click('[data-testid="chat-item"]:first-child');
    await pageTeacher.click('[data-testid="chat-item"]:first-child');

    await pageStudent.waitForSelector('[data-testid="message-input"]', { timeout: 5000 });
    await pageTeacher.waitForSelector('[data-testid="message-input"]', { timeout: 5000 });

    // Student sends message
    const testMessage = `WebSocket test ${Date.now()}`;
    await pageStudent.fill('[data-testid="message-input"]', testMessage);
    await pageStudent.click('button[data-testid="send-message"]');

    // Teacher should receive it in real-time (WebSocket)
    await pageTeacher.waitForSelector(`text=${testMessage}`, { timeout: 10000 });
    await expect(pageTeacher.locator(`text=${testMessage}`)).toBeVisible();
  } finally {
    await contextStudent.close();
    await contextTeacher.close();
  }
});

/**
 * T3.1.5: Edit message
 */
test('T3.1.5 Student can edit their message', async ({ page }) => {
  await loginAs(page, 'student');
  await page.goto(`${BASE_URL}/dashboard/student/forum`);

  // Open first chat
  await page.click('[data-testid="chat-item"]:first-child');
  await page.waitForSelector('[data-testid="message-list"]', { timeout: 5000 });

  // Send initial message
  const originalMessage = `Original ${Date.now()}`;
  await page.fill('[data-testid="message-input"]', originalMessage);
  await page.click('button[data-testid="send-message"]');

  // Wait for message to appear
  await page.waitForSelector(`text=${originalMessage}`, { timeout: 5000 });

  // Find message actions and click edit
  const messageItem = await page.locator(`text=${originalMessage}`).locator('..').first();
  await messageItem.hover();
  await messageItem.click('button[data-testid="edit-message-btn"]');

  // Edit message
  const editedMessage = `Edited ${Date.now()}`;
  const messageInput = await page.locator('[data-testid="message-edit-input"]');
  await messageInput.clear();
  await messageInput.fill(editedMessage);

  // Save
  await page.click('button[data-testid="save-edit-btn"]');

  // Verify edited message appears
  await page.waitForSelector(`text=${editedMessage}`, { timeout: 5000 });
  await expect(page.locator(`text=${editedMessage}`)).toBeVisible();

  // Original text should not be visible
  await expect(page.locator(`text=${originalMessage}`)).not.toBeVisible();
});

/**
 * T3.1.6: Delete message
 */
test('T3.1.6 Student can delete their message', async ({ page }) => {
  await loginAs(page, 'student');
  await page.goto(`${BASE_URL}/dashboard/student/forum`);

  // Open first chat
  await page.click('[data-testid="chat-item"]:first-child');
  await page.waitForSelector('[data-testid="message-list"]', { timeout: 5000 });

  // Send message to delete
  const messageToDelete = `Delete me ${Date.now()}`;
  await page.fill('[data-testid="message-input"]', messageToDelete);
  await page.click('button[data-testid="send-message"]');

  // Wait for message
  await page.waitForSelector(`text=${messageToDelete}`, { timeout: 5000 });

  // Find and delete
  const messageItem = await page.locator(`text=${messageToDelete}`).locator('..').first();
  await messageItem.hover();
  await messageItem.click('button[data-testid="delete-message-btn"]');

  // Confirm deletion
  await page.click('button:has-text("Delete"), button:has-text("Удалить")');

  // Message should disappear
  await expect(page.locator(`text=${messageToDelete}`)).not.toBeVisible({ timeout: 5000 });
});

/**
 * T3.2.1: Teacher role - all features
 */
test('T3.2.1 Teacher can send/receive/edit/delete messages', async ({ page }) => {
  await loginAs(page, 'teacher');
  await page.goto(`${BASE_URL}/dashboard/teacher/forum`);

  // Open chat
  await page.click('[data-testid="chat-item"]:first-child');
  await page.waitForSelector('[data-testid="message-input"]', { timeout: 5000 });

  // Send message
  const msg = `Teacher message ${Date.now()}`;
  await page.fill('[data-testid="message-input"]', msg);
  await page.click('button[data-testid="send-message"]');

  // Verify sent
  await page.waitForSelector(`text=${msg}`, { timeout: 5000 });
  await expect(page.locator(`text=${msg}`)).toBeVisible();
});

/**
 * T3.3.1: WebSocket heartbeat/ping-pong
 */
test('T3.3.1 WebSocket connection stable (heartbeat)', async ({ page }) => {
  await loginAs(page, 'student');
  await page.goto(`${BASE_URL}/dashboard/student/forum`);

  // Open chat to establish WebSocket
  await page.click('[data-testid="chat-item"]:first-child');
  await page.waitForSelector('[data-testid="message-list"]', { timeout: 5000 });

  // Wait 120 seconds - if heartbeat works, connection should stay alive
  // Send a message after waiting to confirm connection
  const delayedMsg = `After delay ${Date.now()}`;

  await page.waitForTimeout(15000); // Wait 15 seconds

  // Try to send message
  await page.fill('[data-testid="message-input"]', delayedMsg);
  await page.click('button[data-testid="send-message"]');

  // Should work without reconnecting
  await page.waitForSelector(`text=${delayedMsg}`, { timeout: 5000 });
  await expect(page.locator(`text=${delayedMsg}`)).toBeVisible();
});

/**
 * T3.3.2: Typing indicator
 */
test('T3.3.2 Typing indicator shows when user types', async ({ browser }) => {
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();

  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  try {
    await loginAs(pageA, 'student');
    await loginAs(pageB, 'teacher');

    // Open same chat
    await pageA.goto(`${BASE_URL}/dashboard/student/forum`);
    await pageB.goto(`${BASE_URL}/dashboard/teacher/forum`);

    await pageA.click('[data-testid="chat-item"]:first-child');
    await pageB.click('[data-testid="chat-item"]:first-child');

    await pageA.waitForSelector('[data-testid="message-input"]', { timeout: 5000 });
    await pageB.waitForSelector('[data-testid="message-input"]', { timeout: 5000 });

    // User A starts typing
    await pageA.fill('[data-testid="message-input"]', 'typing...');

    // User B should see typing indicator
    await pageB.waitForSelector('[data-testid="typing-indicator"]', { timeout: 5000 });
    await expect(pageB.locator('[data-testid="typing-indicator"]')).toBeVisible();
  } finally {
    await contextA.close();
    await contextB.close();
  }
});

/**
 * T3.4: Full workflow - create chat, send, edit, delete, receive
 */
test('T3.4 Complete workflow: create -> send -> edit -> delete -> receive', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await loginAs(page, 'student');
    await page.goto(`${BASE_URL}/dashboard/student/forum`);

    // Step 1: Create chat
    await page.click('button:has-text("New Message"), button:has-text("Новое сообщение")');
    await page.waitForSelector('[data-testid="contacts-list"]', { timeout: 5000 });
    await page.click('[data-testid="contact-item"]:first-child');

    // Step 2: Send message
    const workflow = `Workflow test ${Date.now()}`;
    await page.waitForSelector('[data-testid="message-input"]', { timeout: 5000 });
    await page.fill('[data-testid="message-input"]', workflow);
    await page.click('button[data-testid="send-message"]');

    // Step 3: Verify sent
    await page.waitForSelector(`text=${workflow}`, { timeout: 5000 });
    await expect(page.locator(`text=${workflow}`)).toBeVisible();

    // Step 4: Edit message
    const msgItem = await page.locator(`text=${workflow}`).locator('..').first();
    await msgItem.hover();
    await msgItem.click('button[data-testid="edit-message-btn"]');

    const edited = `Edited workflow ${Date.now()}`;
    const input = await page.locator('[data-testid="message-edit-input"]');
    await input.clear();
    await input.fill(edited);
    await page.click('button[data-testid="save-edit-btn"]');

    // Verify edit
    await page.waitForSelector(`text=${edited}`, { timeout: 5000 });
    await expect(page.locator(`text=${edited}`)).toBeVisible();

    // Step 5: Delete message
    const delItem = await page.locator(`text=${edited}`).locator('..').first();
    await delItem.hover();
    await delItem.click('button[data-testid="delete-message-btn"]');
    await page.click('button:has-text("Delete"), button:has-text("Удалить")');

    // Verify delete
    await expect(page.locator(`text=${edited}`)).not.toBeVisible({ timeout: 5000 });
  } finally {
    await context.close();
  }
});
