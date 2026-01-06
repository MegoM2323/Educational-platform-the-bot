import { test, expect, Page, Browser } from '@playwright/test';
import { v4 as uuidv4 } from 'crypto';

const BASE_URL = 'http://localhost:8080';
const API_URL = 'http://localhost:8000';

interface TestUser {
  username: string;
  password: string;
  role: string;
  displayName: string;
}

const TEST_USERS: Record<string, TestUser> = {
  student_test: {
    username: 'student_test',
    password: 'TestStudent123!',
    role: 'student',
    displayName: 'Student User'
  },
  teacher_test: {
    username: 'teacher_test',
    password: 'TestTeacher123!',
    role: 'teacher',
    displayName: 'Teacher User'
  },
  tutor_test: {
    username: 'tutor_test',
    password: 'TestTutor123!',
    role: 'tutor',
    displayName: 'Tutor User'
  },
  parent_test: {
    username: 'parent_test',
    password: 'TestParent123!',
    role: 'parent',
    displayName: 'Parent User'
  }
};

// Test pairs for Phase 2
const PHASE2_PAIRS = [
  { sender: 'student_test', receiver: 'tutor_test', testName: 'Student ↔ Tutor' },
  { sender: 'teacher_test', receiver: 'student_test', testName: 'Teacher ↔ Student' },
  { sender: 'parent_test', receiver: 'student_test', testName: 'Parent ↔ Student' }
];

/**
 * LOGIN HELPER
 */
async function loginUser(page: Page, userKey: string) {
  const user = TEST_USERS[userKey];

  await page.goto(`${BASE_URL}/auth/signin`);
  await page.waitForLoadState('networkidle');

  // Wait for login form
  const usernameField = page.locator('input[type="text"], input[placeholder*="email"], input[placeholder*="username"]').first();
  const passwordField = page.locator('input[type="password"]').first();

  // Fill credentials
  await usernameField.fill(user.username, { timeout: 5000 });
  await passwordField.fill(user.password, { timeout: 5000 });

  // Submit
  const submitBtn = page.locator('button[type="submit"], button:has-text("Войти"), button:has-text("Sign In")').first();
  await submitBtn.click();

  // Wait for dashboard to load
  await page.waitForURL('/**/dashboard/**', { timeout: 15000 });
  await page.waitForLoadState('networkidle');
}

/**
 * NAVIGATE TO CHAT
 */
async function navigateToChat(page: Page, role: string) {
  const chatUrl = `${BASE_URL}/dashboard/${role}/chat`;
  await page.goto(chatUrl);

  // Wait for ChatList to load
  await page.waitForSelector('[data-testid="chat-list"], .chat-list, [role="list"]', { timeout: 10000 }).catch(() => {});
  await page.waitForLoadState('networkidle');
}

/**
 * FIND AND OPEN CHAT
 */
async function findAndOpenChat(page: Page, contactName: string): Promise<boolean> {
  try {
    // Try to find contact in chat list
    const chatItems = page.locator('[data-testid="chat-item"], .chat-item, [role="listitem"]');
    const count = await chatItems.count();

    if (count === 0) {
      console.log(`No chats found for "${contactName}". Trying to create new chat.`);

      // Try to create new chat
      const newChatBtn = page.locator('button:has-text("Новый"), button:has-text("New"), button[aria-label*="New"]').first();
      if (await newChatBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await newChatBtn.click();
        await page.waitForTimeout(500);

        // Search for contact
        const searchInput = page.locator('input[placeholder*="Поиск"], input[placeholder*="Search"], input[placeholder*="контакт"]').first();
        if (await searchInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await searchInput.fill(contactName);
          await page.waitForTimeout(800);

          // Click on search result
          const resultItem = page.locator(`text=${contactName}`).first();
          if (await resultItem.isVisible({ timeout: 3000 }).catch(() => false)) {
            await resultItem.click();
            await page.waitForTimeout(1000);
            return true;
          }
        }
      }
      return false;
    }

    // Try to find by contact name in list
    for (let i = 0; i < count; i++) {
      const item = chatItems.nth(i);
      const text = await item.textContent();
      if (text && text.includes(contactName)) {
        await item.click();
        await page.waitForTimeout(800);
        return true;
      }
    }

    console.log(`Could not find chat with "${contactName}" in list`);
    return false;
  } catch (error) {
    console.error(`Error finding chat: ${error}`);
    return false;
  }
}

/**
 * SEND MESSAGE
 */
async function sendMessage(page: Page, message: string): Promise<boolean> {
  try {
    // Find message input
    const textareas = page.locator('textarea');
    const textInputs = page.locator('input[placeholder*="Сообщение"], input[placeholder*="Message"]');

    let inputFound = false;

    if (await textareas.count() > 0) {
      const textarea = textareas.first();
      await textarea.fill(message);
      inputFound = true;
    } else if (await textInputs.count() > 0) {
      const input = textInputs.first();
      await input.fill(message);
      inputFound = true;
    }

    if (!inputFound) {
      console.log('No message input found');
      return false;
    }

    // Find and click send button
    const sendBtn = page.locator(
      'button[aria-label*="Send"], button[aria-label*="Отправить"], button:has-text("Отправить"), button:has-text("Send"), button[type="submit"]'
    ).first();

    if (await sendBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await sendBtn.click();
    } else {
      // Try pressing Enter
      const input = textareas.count() > 0 ? textareas.first() : textInputs.first();
      await input.press('Enter');
    }

    await page.waitForTimeout(1500);
    return true;
  } catch (error) {
    console.error(`Error sending message: ${error}`);
    return false;
  }
}

/**
 * VERIFY MESSAGE VISIBLE
 */
async function isMessageVisible(page: Page, message: string): Promise<boolean> {
  try {
    const messageLocator = page.locator(`text=${message}`);
    return await messageLocator.isVisible({ timeout: 5000 }).catch(() => false);
  } catch {
    return false;
  }
}

/**
 * GET CONSOLE ERRORS
 */
async function getConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  return errors;
}

/**
 * TAKE SCREENSHOT WITH LABEL
 */
async function takeScreenshot(page: Page, label: string) {
  const sanitized = label.replace(/[^\w-]/g, '_').toLowerCase();
  const filename = `phase2_${sanitized}.png`;
  await page.screenshot({ path: `./e2e-results/${filename}` }).catch(() => {});
}

/**
 * MAIN TESTS
 */
test.describe('Phase 2: Message Sending & Receiving E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Create output directory for screenshots
    // Note: Using dynamic import for better ES6 compatibility
    const { mkdir } = await import('fs/promises');
    await mkdir('./e2e-results', { recursive: true }).catch(() => {});
  });

  for (const pair of PHASE2_PAIRS) {
    test(`${pair.testName}: Send & Receive Message`, async ({ browser }) => {
      console.log(`\n========== TEST: ${pair.testName} ==========\n`);

      const senderUser = TEST_USERS[pair.sender];
      const receiverUser = TEST_USERS[pair.receiver];

      const senderMsg = `Test message from ${senderUser.role} at ${new Date().toISOString()}`;
      const receiverMsg = `Reply from ${receiverUser.role} at ${new Date().toISOString()}`;

      // ===== STEP 1: SENDER SENDS MESSAGE =====
      console.log(`[STEP 1] ${senderUser.role} sends message to ${receiverUser.role}`);

      const senderPage = await browser.newPage();
      const senderErrors: string[] = [];

      senderPage.on('console', msg => {
        if (msg.type() === 'error') {
          senderErrors.push(msg.text());
          console.log(`[CONSOLE ERROR] ${msg.text()}`);
        }
      });

      // Login
      await loginUser(senderPage, pair.sender);
      console.log(`✓ ${senderUser.role} logged in`);

      // Navigate to chat
      await navigateToChat(senderPage, senderUser.role);
      console.log(`✓ Navigated to chat page`);

      // Find chat
      const chatFound = await findAndOpenChat(senderPage, receiverUser.displayName);
      expect(chatFound).toBeTruthy();
      console.log(`✓ Found chat with ${receiverUser.displayName}`);

      // Take screenshot of empty chat
      await takeScreenshot(senderPage, `${pair.sender}_chat_opened`);

      // Send message
      const sendSuccess = await sendMessage(senderPage, senderMsg);
      expect(sendSuccess).toBeTruthy();
      console.log(`✓ Message sent`);

      // Verify message appears in sender's view
      const msgVisible = await isMessageVisible(senderPage, senderMsg);
      expect(msgVisible).toBeTruthy();
      console.log(`✓ Message visible in sender's chat window`);

      // Take screenshot with message
      await takeScreenshot(senderPage, `${pair.sender}_message_sent`);

      // Check for console errors
      expect(senderErrors).toHaveLength(0);
      console.log(`✓ No console errors`);

      // ===== STEP 2: RECEIVER RECEIVES MESSAGE =====
      console.log(`\n[STEP 2] ${receiverUser.role} receives message`);

      const receiverPage = await browser.newPage();
      const receiverErrors: string[] = [];

      receiverPage.on('console', msg => {
        if (msg.type() === 'error') {
          receiverErrors.push(msg.text());
          console.log(`[CONSOLE ERROR] ${msg.text()}`);
        }
      });

      // Login
      await loginUser(receiverPage, pair.receiver);
      console.log(`✓ ${receiverUser.role} logged in`);

      // Navigate to chat
      await navigateToChat(receiverPage, receiverUser.role);
      console.log(`✓ Navigated to chat page`);

      // Find chat
      const chatFound2 = await findAndOpenChat(receiverPage, senderUser.displayName);
      expect(chatFound2).toBeTruthy();
      console.log(`✓ Found chat with ${senderUser.displayName}`);

      // Wait for message to appear
      const receiverSeesSender = await isMessageVisible(receiverPage, senderMsg);
      expect(receiverSeesSender).toBeTruthy();
      console.log(`✓ Received message visible in receiver's chat window`);

      // Take screenshot of received message
      await takeScreenshot(receiverPage, `${pair.receiver}_message_received`);

      // Check for console errors
      expect(receiverErrors).toHaveLength(0);
      console.log(`✓ No console errors`);

      // ===== STEP 3: RECEIVER REPLIES =====
      console.log(`\n[STEP 3] ${receiverUser.role} sends reply`);

      const replySuccess = await sendMessage(receiverPage, receiverMsg);
      expect(replySuccess).toBeTruthy();
      console.log(`✓ Reply sent`);

      // Verify reply appears in receiver's view
      const replyVisible = await isMessageVisible(receiverPage, receiverMsg);
      expect(replyVisible).toBeTruthy();
      console.log(`✓ Reply visible in receiver's chat window`);

      // Take screenshot with reply
      await takeScreenshot(receiverPage, `${pair.receiver}_reply_sent`);

      // ===== STEP 4: SENDER RECEIVES REPLY =====
      console.log(`\n[STEP 4] ${senderUser.role} receives reply`);

      // Refresh sender's page to see reply
      await senderPage.reload();
      await senderPage.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Check if reply is visible
      const senderSeesReply = await isMessageVisible(senderPage, receiverMsg);
      expect(senderSeesReply).toBeTruthy();
      console.log(`✓ Reply visible in sender's chat window`);

      // Take screenshot with reply visible
      await takeScreenshot(senderPage, `${pair.sender}_reply_received`);

      // ===== VERIFY CHAT HISTORY =====
      console.log(`\n[VERIFICATION] Chat history synchronization`);

      // Both messages should be visible
      const historySenderHasAll = await Promise.all([
        isMessageVisible(senderPage, senderMsg),
        isMessageVisible(senderPage, receiverMsg)
      ]);
      expect(historySenderHasAll[0]).toBeTruthy();
      expect(historySenderHasAll[1]).toBeTruthy();
      console.log(`✓ Sender can see both messages (sent + reply)`);

      const historyReceiverHasAll = await Promise.all([
        isMessageVisible(receiverPage, senderMsg),
        isMessageVisible(receiverPage, receiverMsg)
      ]);
      expect(historyReceiverHasAll[0]).toBeTruthy();
      expect(historyReceiverHasAll[1]).toBeTruthy();
      console.log(`✓ Receiver can see both messages (received + reply)`);

      // ===== CLEANUP =====
      console.log(`\n[CLEANUP]`);
      await senderPage.close();
      await receiverPage.close();
      console.log(`✓ Pages closed`);

      console.log(`\n========== TEST PASSED: ${pair.testName} ==========\n`);
    });
  }

  // ===== CONSOLE & NETWORK VERIFICATION TEST =====
  test('Console & Network Health Check', async ({ page }) => {
    console.log('\n========== CONSOLE & NETWORK HEALTH CHECK ==========\n');

    const consoleMessages: { type: string; text: string }[] = [];
    const networkErrors: string[] = [];

    page.on('console', msg => {
      consoleMessages.push({ type: msg.type(), text: msg.text() });
    });

    page.on('response', response => {
      if (response.status() >= 400) {
        networkErrors.push(`${response.status()} ${response.url()}`);
      }
    });

    // Login as student
    await loginUser(page, 'student_test');

    // Navigate to chat
    await navigateToChat(page, 'student');

    // Filter console errors
    const errors = consoleMessages.filter(m => m.type === 'error');
    const warnings = consoleMessages.filter(m => m.type === 'warning');

    console.log(`Console Summary:`);
    console.log(`  - Errors: ${errors.length}`);
    console.log(`  - Warnings: ${warnings.length}`);
    console.log(`  - Network Errors (4xx/5xx): ${networkErrors.length}`);

    // Should be minimal
    expect(errors.length).toBeLessThanOrEqual(2); // Allow minor React warnings
    expect(networkErrors.filter(e => !e.includes('404'))).toHaveLength(0); // No 500 errors

    console.log(`✓ Console & Network health verified\n`);
  });
});

test.describe('UI Element Visibility Tests', () => {
  test('All chat UI elements are present', async ({ page }) => {
    console.log('\n========== UI ELEMENTS VISIBILITY TEST ==========\n');

    await loginUser(page, 'student_test');
    await navigateToChat(page, 'student');

    // Check for key UI elements
    const chatList = page.locator('[data-testid="chat-list"], .chat-list, [role="list"]').first();
    const chatWindow = page.locator('[data-testid="chat-window"], .chat-window').first();
    const messageInput = page.locator('textarea, input[placeholder*="Сообщение"], input[placeholder*="Message"]').first();

    expect(await chatList.isVisible({ timeout: 5000 }).catch(() => false)).toBeTruthy();
    console.log('✓ Chat list visible');

    expect(await chatWindow.isVisible({ timeout: 5000 }).catch(() => false)).toBeTruthy();
    console.log('✓ Chat window visible');

    expect(await messageInput.isVisible({ timeout: 5000 }).catch(() => false)).toBeTruthy();
    console.log('✓ Message input visible');

    console.log(`✓ All UI elements present\n`);
  });
});
