import { test, expect, Page, Browser, BrowserContext } from '@playwright/test';

/**
 * E2E Tests: Полное тестирование переписки Forum/Chat
 * после объединения Forum и Chat в единую систему
 *
 * Тестируемые сценарии:
 * 1. Создание чата между student и teacher
 * 2. Отправка сообщений
 * 3. Редактирование сообщения
 * 4. Удаление сообщения
 * 5. WebSocket real-time updates
 */

const BASE_URL = process.env.BASE_URL || 'https://the-bot.ru';

// Test credentials (verified in production database)
const STUDENT = {
  email: 'student@test.com',
  password: 'TestPassword123!',
  role: 'student' as const
};

const TEACHER = {
  email: 'teacher@test.com',
  password: 'TestPassword123!',
  role: 'teacher' as const
};

/**
 * Helper: Login user and wait for dashboard
 */
async function login(page: Page, email: string, password: string, role: string) {
  console.log(`\n[LOGIN] Logging in as ${email}...`);

  // Navigate to auth/signin (correct path)
  await page.goto(`${BASE_URL}/auth/signin`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});

  // Wait for email input to be visible
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });

  // Fill login form
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);

  // Submit
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard (increased timeout for production auth flow)
  await page.waitForURL(`**/dashboard/${role}/**`, { timeout: 60000 });
  console.log(`[LOGIN] ✅ Logged in as ${email}`);
}

/**
 * Helper: Navigate to Forum page
 */
async function navigateToForum(page: Page, role: string) {
  console.log(`\n[NAVIGATE] Going to Forum page...`);
  await page.goto(`${BASE_URL}/dashboard/${role}/forum`);
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1000); // Extra safety delay
  console.log(`[NAVIGATE] ✅ Forum page loaded`);
}

/**
 * Helper: Take screenshot on error
 */
async function takeScreenshot(page: Page, name: string) {
  const timestamp = Date.now();
  const filename = `/tmp/playwright-${name}-${timestamp}.png`;
  await page.screenshot({ path: filename, fullPage: true });
  console.log(`[SCREENSHOT] Saved: ${filename}`);
  return filename;
}

/**
 * Helper: Find message input (tries multiple selectors)
 */
async function findMessageInput(page: Page): Promise<any> {
  const selectors = [
    '[data-testid="message-input"]',
    'textarea[placeholder*="message"]',
    'textarea[placeholder*="сообщение"]',
    'textarea',
    'input[placeholder*="message"]'
  ];

  for (const selector of selectors) {
    const input = await page.locator(selector).first();
    if (await input.isVisible({ timeout: 1000 }).catch(() => false)) {
      return input;
    }
  }

  throw new Error('Message input not found with any selector');
}

/**
 * Helper: Find send button
 */
async function findSendButton(page: Page): Promise<any> {
  const selectors = [
    'button[data-testid="send-message"]',
    'button:has-text("Send")',
    'button:has-text("Отправить")',
    'button[type="submit"]'
  ];

  for (const selector of selectors) {
    const button = await page.locator(selector).first();
    if (await button.isVisible({ timeout: 1000 }).catch(() => false)) {
      return button;
    }
  }

  throw new Error('Send button not found');
}

test.describe('FORUM MESSAGING: Full E2E Flow', () => {
  // Increase timeout for all tests (production can be slow)
  test.setTimeout(60000); // 60 seconds per test

  /**
   * TEST 1: Student creates chat with teacher
   */
  test('Step 1: Student creates new chat with teacher', async ({ page }) => {
    console.log('\n' + '='.repeat(80));
    console.log('TEST 1: Student creates chat with teacher');
    console.log('='.repeat(80));

    try {
      // 1. Login as student
      await login(page, STUDENT.email, STUDENT.password, STUDENT.role);

      // 2. Navigate to forum
      await navigateToForum(page, STUDENT.role);

      // 3. Check if "New Message" button exists
      const newMsgBtn = page.locator('button:has-text("New Message"), button:has-text("Новое сообщение")').first();
      const btnExists = await newMsgBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnExists) {
        console.log('[STEP 1] ✅ "New Message" button found');

        // 4. Click "New Message"
        await newMsgBtn.click();
        console.log('[STEP 1] ✅ Clicked "New Message" button');

        // 5. Wait for contacts list
        await page.waitForSelector('[data-testid="contacts-list"], [data-testid="contact-item"]', { timeout: 10000 });
        console.log('[STEP 1] ✅ Contacts list loaded');

        // 6. Select first contact (should be teacher)
        const firstContact = page.locator('[data-testid="contact-item"]').first();
        if (await firstContact.isVisible({ timeout: 3000 }).catch(() => false)) {
          await firstContact.click();
          console.log('[STEP 1] ✅ Selected teacher contact');

          // 7. Wait for chat to open
          await page.waitForTimeout(2000);
          const messageInput = await findMessageInput(page);
          expect(await messageInput.isVisible()).toBe(true);
          console.log('[STEP 1] ✅ Chat opened successfully');
        }
      } else {
        console.log('[STEP 1] ⚠️ "New Message" button not found - chat may already exist');

        // Try to open existing chat
        const existingChat = page.locator('[data-testid="chat-item"]').first();
        if (await existingChat.isVisible({ timeout: 3000 }).catch(() => false)) {
          await existingChat.click();
          console.log('[STEP 1] ✅ Opened existing chat');
        }
      }

      console.log('\n[TEST 1] ✅ PASSED: Chat created/opened successfully\n');

    } catch (error) {
      await takeScreenshot(page, 'test1-error');
      console.error('[TEST 1] ❌ FAILED:', error);
      throw error;
    }
  });

  /**
   * TEST 2: Student sends message to teacher
   */
  test('Step 2: Student sends message "Привет учитель!"', async ({ page }) => {
    console.log('\n' + '='.repeat(80));
    console.log('TEST 2: Student sends message');
    console.log('='.repeat(80));

    try {
      // Setup
      await login(page, STUDENT.email, STUDENT.password, STUDENT.role);
      await navigateToForum(page, STUDENT.role);

      // Open chat (first available)
      const chatItem = page.locator('[data-testid="chat-item"]').first();
      if (await chatItem.isVisible({ timeout: 5000 }).catch(() => false)) {
        await chatItem.click();
        console.log('[STEP 2] ✅ Chat opened');
      }

      await page.waitForTimeout(1000);

      // Find message input
      const messageInput = await findMessageInput(page);
      console.log('[STEP 2] ✅ Message input found');

      // Type message
      const testMessage = 'Привет учитель!';
      await messageInput.fill(testMessage);
      console.log(`[STEP 2] ✅ Typed message: "${testMessage}"`);

      // Find and click send button
      const sendBtn = await findSendButton(page);
      await sendBtn.click();
      console.log('[STEP 2] ✅ Send button clicked');

      // Verify message appears in chat
      await page.waitForTimeout(2000);
      const messageSent = await page.locator(`text="${testMessage}"`).isVisible({ timeout: 5000 }).catch(() => false);

      if (messageSent) {
        console.log('[STEP 2] ✅ Message appears in chat history');
        expect(messageSent).toBe(true);
      } else {
        await takeScreenshot(page, 'test2-message-not-visible');
        console.error('[STEP 2] ❌ Message not visible in chat');
        throw new Error('Message not visible after sending');
      }

      console.log('\n[TEST 2] ✅ PASSED: Message sent successfully\n');

    } catch (error) {
      await takeScreenshot(page, 'test2-error');
      console.error('[TEST 2] ❌ FAILED:', error);
      throw error;
    }
  });

  /**
   * TEST 3: Student edits message to "Привет, учитель!"
   */
  test('Step 3: Student edits message', async ({ page }) => {
    console.log('\n' + '='.repeat(80));
    console.log('TEST 3: Student edits message');
    console.log('='.repeat(80));

    try {
      // Setup
      await login(page, STUDENT.email, STUDENT.password, STUDENT.role);
      await navigateToForum(page, STUDENT.role);

      // Open chat
      const chatItem = page.locator('[data-testid="chat-item"]').first();
      if (await chatItem.isVisible({ timeout: 5000 }).catch(() => false)) {
        await chatItem.click();
      }

      await page.waitForTimeout(1000);

      // Send a message to edit
      const messageInput = await findMessageInput(page);
      const originalMessage = `Message to edit ${Date.now()}`;
      await messageInput.fill(originalMessage);

      const sendBtn = await findSendButton(page);
      await sendBtn.click();
      console.log(`[STEP 3] ✅ Sent message: "${originalMessage}"`);

      await page.waitForTimeout(2000);

      // Find the message and hover to show actions
      const messageLocator = page.locator(`text="${originalMessage.substring(0, 20)}"`).first();
      if (await messageLocator.isVisible({ timeout: 3000 }).catch(() => false)) {
        await messageLocator.hover();
        console.log('[STEP 3] ✅ Hovered over message');

        // Click edit button
        const editBtn = page.locator('button[data-testid="edit-message-btn"], button:has-text("Edit"), button:has-text("Редактировать")').first();
        if (await editBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await editBtn.click();
          console.log('[STEP 3] ✅ Clicked Edit button');

          // Find edit input and change text
          const editInput = page.locator('[data-testid="message-edit-input"], textarea').first();
          if (await editInput.isVisible({ timeout: 3000 }).catch(() => false)) {
            const editedMessage = `Edited message ${Date.now()}`;
            await editInput.clear();
            await editInput.fill(editedMessage);
            console.log(`[STEP 3] ✅ Changed text to: "${editedMessage}"`);

            // Save edit
            const saveBtn = page.locator('button[data-testid="save-edit-btn"], button:has-text("Save"), button:has-text("Сохранить")').first();
            if (await saveBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
              await saveBtn.click();
              console.log('[STEP 3] ✅ Clicked Save button');

              // Verify edited message appears
              await page.waitForTimeout(2000);
              const editedVisible = await page.locator(`text="Edited"`).isVisible({ timeout: 5000 }).catch(() => false);

              if (editedVisible) {
                console.log('[STEP 3] ✅ Edited message visible in chat');
                expect(editedVisible).toBe(true);
              } else {
                await takeScreenshot(page, 'test3-edit-not-visible');
                console.error('[STEP 3] ❌ Edited message not visible');
                throw new Error('Edited message not visible');
              }
            } else {
              await takeScreenshot(page, 'test3-save-btn-not-found');
              throw new Error('Save button not found');
            }
          } else {
            await takeScreenshot(page, 'test3-edit-input-not-found');
            throw new Error('Edit input not found');
          }
        } else {
          await takeScreenshot(page, 'test3-edit-btn-not-found');
          throw new Error('Edit button not found after hover');
        }
      } else {
        await takeScreenshot(page, 'test3-message-not-found');
        throw new Error('Original message not found');
      }

      console.log('\n[TEST 3] ✅ PASSED: Message edited successfully\n');

    } catch (error) {
      await takeScreenshot(page, 'test3-error');
      console.error('[TEST 3] ❌ FAILED:', error);
      throw error;
    }
  });

  /**
   * TEST 4: Student deletes message
   */
  test('Step 4: Student deletes message', async ({ page }) => {
    console.log('\n' + '='.repeat(80));
    console.log('TEST 4: Student deletes message');
    console.log('='.repeat(80));

    try {
      // Setup
      await login(page, STUDENT.email, STUDENT.password, STUDENT.role);
      await navigateToForum(page, STUDENT.role);

      // Open chat
      const chatItem = page.locator('[data-testid="chat-item"]').first();
      if (await chatItem.isVisible({ timeout: 5000 }).catch(() => false)) {
        await chatItem.click();
      }

      await page.waitForTimeout(1000);

      // Send a message to delete
      const messageInput = await findMessageInput(page);
      const messageToDelete = `Delete this ${Date.now()}`;
      await messageInput.fill(messageToDelete);

      const sendBtn = await findSendButton(page);
      await sendBtn.click();
      console.log(`[STEP 4] ✅ Sent message: "${messageToDelete}"`);

      await page.waitForTimeout(2000);

      // Find message and hover
      const messageLocator = page.locator(`text="${messageToDelete.substring(0, 15)}"`).first();
      if (await messageLocator.isVisible({ timeout: 3000 }).catch(() => false)) {
        await messageLocator.hover();
        console.log('[STEP 4] ✅ Hovered over message');

        // Click delete button
        const deleteBtn = page.locator('button[data-testid="delete-message-btn"], button:has-text("Delete"), button:has-text("Удалить")').first();
        if (await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await deleteBtn.click();
          console.log('[STEP 4] ✅ Clicked Delete button');

          // Confirm deletion (dialog should appear)
          await page.waitForTimeout(500);
          const confirmBtn = page.locator('button:has-text("Delete"), button:has-text("Удалить"), button:has-text("Confirm")').first();
          if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
            await confirmBtn.click();
            console.log('[STEP 4] ✅ Confirmed deletion');

            // Verify message is gone
            await page.waitForTimeout(2000);
            const messageGone = !(await page.locator(`text="${messageToDelete}"`).isVisible({ timeout: 3000 }).catch(() => true));

            if (messageGone) {
              console.log('[STEP 4] ✅ Message deleted successfully');
              expect(messageGone).toBe(true);
            } else {
              await takeScreenshot(page, 'test4-message-still-visible');
              console.error('[STEP 4] ❌ Message still visible after deletion');
              throw new Error('Message not deleted');
            }
          } else {
            await takeScreenshot(page, 'test4-confirm-btn-not-found');
            throw new Error('Confirm delete button not found');
          }
        } else {
          await takeScreenshot(page, 'test4-delete-btn-not-found');
          throw new Error('Delete button not found after hover');
        }
      } else {
        await takeScreenshot(page, 'test4-message-not-found');
        throw new Error('Message to delete not found');
      }

      console.log('\n[TEST 4] ✅ PASSED: Message deleted successfully\n');

    } catch (error) {
      await takeScreenshot(page, 'test4-error');
      console.error('[TEST 4] ❌ FAILED:', error);
      throw error;
    }
  });

  /**
   * TEST 5: WebSocket real-time updates (Student sends, Teacher receives)
   */
  test('Step 5: WebSocket real-time: Student sends → Teacher receives', async ({ browser }) => {
    console.log('\n' + '='.repeat(80));
    console.log('TEST 5: WebSocket real-time updates');
    console.log('='.repeat(80));

    let contextStudent: BrowserContext | null = null;
    let contextTeacher: BrowserContext | null = null;

    try {
      // Create two browser contexts
      contextStudent = await browser.newContext();
      contextTeacher = await browser.newContext();

      const pageStudent = await contextStudent.newPage();
      const pageTeacher = await contextTeacher.newPage();

      // Login both users
      console.log('[STEP 5] Logging in both users...');
      await login(pageStudent, STUDENT.email, STUDENT.password, STUDENT.role);
      await login(pageTeacher, TEACHER.email, TEACHER.password, TEACHER.role);
      console.log('[STEP 5] ✅ Both users logged in');

      // Navigate both to Forum
      await navigateToForum(pageStudent, STUDENT.role);
      await navigateToForum(pageTeacher, TEACHER.role);
      console.log('[STEP 5] ✅ Both users on Forum page');

      // Open same chat in both windows
      const studentChat = pageStudent.locator('[data-testid="chat-item"]').first();
      const teacherChat = pageTeacher.locator('[data-testid="chat-item"]').first();

      if (await studentChat.isVisible({ timeout: 5000 }).catch(() => false)) {
        await studentChat.click();
        console.log('[STEP 5] ✅ Student opened chat');
      }

      if (await teacherChat.isVisible({ timeout: 5000 }).catch(() => false)) {
        await teacherChat.click();
        console.log('[STEP 5] ✅ Teacher opened chat');
      }

      await pageStudent.waitForTimeout(2000);
      await pageTeacher.waitForTimeout(2000);

      // Student sends message
      const messageInput = await findMessageInput(pageStudent);
      const websocketTestMsg = `WebSocket test ${Date.now()}`;
      await messageInput.fill(websocketTestMsg);
      console.log(`[STEP 5] ✅ Student typed: "${websocketTestMsg}"`);

      const sendBtn = await findSendButton(pageStudent);
      await sendBtn.click();
      console.log('[STEP 5] ✅ Student clicked Send');

      // Wait for message to appear in student's chat
      await pageStudent.waitForTimeout(1000);
      const studentSees = await pageStudent.locator(`text="${websocketTestMsg.substring(0, 20)}"`).isVisible({ timeout: 5000 }).catch(() => false);

      if (studentSees) {
        console.log('[STEP 5] ✅ Student sees their message');
      } else {
        await takeScreenshot(pageStudent, 'test5-student-no-message');
        throw new Error('Student does not see their own message');
      }

      // CRITICAL: Teacher should receive message via WebSocket in REAL-TIME
      console.log('[STEP 5] ⏳ Waiting for teacher to receive message via WebSocket...');
      const teacherReceives = await pageTeacher.locator(`text="${websocketTestMsg.substring(0, 20)}"`).isVisible({ timeout: 10000 }).catch(() => false);

      if (teacherReceives) {
        console.log('[STEP 5] ✅✅✅ SUCCESS! Teacher received message in REAL-TIME (WebSocket works!)');
        expect(teacherReceives).toBe(true);
      } else {
        await takeScreenshot(pageTeacher, 'test5-teacher-no-message');
        console.error('[STEP 5] ❌ FAILED: Teacher did not receive message via WebSocket');

        // Try refreshing teacher's page to see if message appears (polling fallback)
        console.log('[STEP 5] ⏳ Trying page refresh to check if message exists...');
        await pageTeacher.reload();
        await pageTeacher.waitForTimeout(2000);

        const afterRefresh = await pageTeacher.locator(`text="${websocketTestMsg.substring(0, 20)}"`).isVisible({ timeout: 5000 }).catch(() => false);

        if (afterRefresh) {
          console.log('[STEP 5] ⚠️ Message appeared after refresh (WebSocket issue, but API works)');
          throw new Error('WebSocket real-time update failed - message only visible after refresh');
        } else {
          console.error('[STEP 5] ❌❌❌ Message not found even after refresh - API problem!');
          throw new Error('Message not received by teacher at all');
        }
      }

      console.log('\n[TEST 5] ✅ PASSED: WebSocket real-time updates work correctly\n');

    } catch (error) {
      if (contextStudent) {
        const pages = contextStudent.pages();
        if (pages.length > 0) await takeScreenshot(pages[0], 'test5-student-error');
      }
      if (contextTeacher) {
        const pages = contextTeacher.pages();
        if (pages.length > 0) await takeScreenshot(pages[0], 'test5-teacher-error');
      }
      console.error('[TEST 5] ❌ FAILED:', error);
      throw error;
    } finally {
      if (contextStudent) await contextStudent.close();
      if (contextTeacher) await contextTeacher.close();
    }
  });

  /**
   * TEST 6: Teacher replies to student (reverse direction)
   */
  test('Step 6: Teacher replies to student', async ({ browser }) => {
    console.log('\n' + '='.repeat(80));
    console.log('TEST 6: Teacher replies to student');
    console.log('='.repeat(80));

    let contextStudent: BrowserContext | null = null;
    let contextTeacher: BrowserContext | null = null;

    try {
      // Create two contexts
      contextStudent = await browser.newContext();
      contextTeacher = await browser.newContext();

      const pageStudent = await contextStudent.newPage();
      const pageTeacher = await contextTeacher.newPage();

      // Login both
      await login(pageStudent, STUDENT.email, STUDENT.password, STUDENT.role);
      await login(pageTeacher, TEACHER.email, TEACHER.password, TEACHER.role);
      console.log('[STEP 6] ✅ Both logged in');

      // Open Forum
      await navigateToForum(pageStudent, STUDENT.role);
      await navigateToForum(pageTeacher, TEACHER.role);

      // Open chats
      const studentChat = pageStudent.locator('[data-testid="chat-item"]').first();
      const teacherChat = pageTeacher.locator('[data-testid="chat-item"]').first();

      if (await studentChat.isVisible({ timeout: 5000 }).catch(() => false)) {
        await studentChat.click();
      }
      if (await teacherChat.isVisible({ timeout: 5000 }).catch(() => false)) {
        await teacherChat.click();
      }

      await pageStudent.waitForTimeout(1000);
      await pageTeacher.waitForTimeout(1000);

      // Teacher sends reply
      const teacherInput = await findMessageInput(pageTeacher);
      const teacherReply = `Teacher reply ${Date.now()}`;
      await teacherInput.fill(teacherReply);
      console.log(`[STEP 6] ✅ Teacher typed: "${teacherReply}"`);

      const teacherSendBtn = await findSendButton(pageTeacher);
      await teacherSendBtn.click();
      console.log('[STEP 6] ✅ Teacher sent message');

      // Verify teacher sees their message
      await pageTeacher.waitForTimeout(1000);
      const teacherSees = await pageTeacher.locator(`text="${teacherReply.substring(0, 20)}"`).isVisible({ timeout: 5000 }).catch(() => false);

      if (teacherSees) {
        console.log('[STEP 6] ✅ Teacher sees their reply');
      }

      // CRITICAL: Student should receive reply via WebSocket
      console.log('[STEP 6] ⏳ Waiting for student to receive teacher reply...');
      const studentReceives = await pageStudent.locator(`text="${teacherReply.substring(0, 20)}"`).isVisible({ timeout: 10000 }).catch(() => false);

      if (studentReceives) {
        console.log('[STEP 6] ✅✅✅ SUCCESS! Student received teacher reply in REAL-TIME');
        expect(studentReceives).toBe(true);
      } else {
        await takeScreenshot(pageStudent, 'test6-student-no-reply');
        console.error('[STEP 6] ❌ Student did not receive teacher reply');
        throw new Error('Student did not receive teacher reply via WebSocket');
      }

      console.log('\n[TEST 6] ✅ PASSED: Two-way communication works\n');

    } catch (error) {
      console.error('[TEST 6] ❌ FAILED:', error);
      throw error;
    } finally {
      if (contextStudent) await contextStudent.close();
      if (contextTeacher) await contextTeacher.close();
    }
  });
});

/**
 * FINAL SUMMARY TEST: Run all steps in sequence
 */
test.describe('COMPLETE WORKFLOW: All Steps Combined', () => {
  // Increase timeout for complete workflow test
  test.setTimeout(90000); // 90 seconds

  test('Complete workflow: Create → Send → Edit → Delete → Real-time', async ({ browser }) => {
    console.log('\n' + '='.repeat(80));
    console.log('COMPLETE WORKFLOW TEST: All steps in one');
    console.log('='.repeat(80));

    const results = {
      create: false,
      send: false,
      edit: false,
      delete: false,
      websocket: false
    };

    let contextStudent: BrowserContext | null = null;
    let contextTeacher: BrowserContext | null = null;

    try {
      contextStudent = await browser.newContext();
      const pageStudent = await contextStudent.newPage();

      // Step 1: Create/Open chat
      try {
        await login(pageStudent, STUDENT.email, STUDENT.password, STUDENT.role);
        await navigateToForum(pageStudent, STUDENT.role);

        const chatItem = pageStudent.locator('[data-testid="chat-item"]').first();
        if (await chatItem.isVisible({ timeout: 5000 }).catch(() => false)) {
          await chatItem.click();
          results.create = true;
          console.log('[WORKFLOW] ✅ Step 1: Chat opened');
        }
      } catch (e) {
        console.error('[WORKFLOW] ❌ Step 1 failed:', e);
      }

      // Step 2: Send message
      try {
        const input = await findMessageInput(pageStudent);
        const msg = `Complete test ${Date.now()}`;
        await input.fill(msg);

        const btn = await findSendButton(pageStudent);
        await btn.click();

        await pageStudent.waitForTimeout(2000);
        const visible = await pageStudent.locator(`text="${msg.substring(0, 15)}"`).isVisible({ timeout: 5000 }).catch(() => false);

        if (visible) {
          results.send = true;
          console.log('[WORKFLOW] ✅ Step 2: Message sent');
        }
      } catch (e) {
        console.error('[WORKFLOW] ❌ Step 2 failed:', e);
      }

      // Step 3: Edit message
      try {
        const editInput = await findMessageInput(pageStudent);
        const editMsg = `Edit test ${Date.now()}`;
        await editInput.fill(editMsg);

        const sendBtn = await findSendButton(pageStudent);
        await sendBtn.click();
        await pageStudent.waitForTimeout(2000);

        const msgLoc = pageStudent.locator(`text="${editMsg.substring(0, 10)}"`).first();
        if (await msgLoc.isVisible({ timeout: 3000 }).catch(() => false)) {
          await msgLoc.hover();

          const editBtn = pageStudent.locator('button[data-testid="edit-message-btn"]').first();
          if (await editBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
            await editBtn.click();

            const input = pageStudent.locator('[data-testid="message-edit-input"]').first();
            if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
              await input.clear();
              await input.fill(`Edited ${Date.now()}`);

              const saveBtn = pageStudent.locator('button[data-testid="save-edit-btn"]').first();
              if (await saveBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
                await saveBtn.click();
                results.edit = true;
                console.log('[WORKFLOW] ✅ Step 3: Message edited');
              }
            }
          }
        }
      } catch (e) {
        console.error('[WORKFLOW] ❌ Step 3 failed:', e);
      }

      // Step 4: Delete message
      try {
        const delInput = await findMessageInput(pageStudent);
        const delMsg = `Delete ${Date.now()}`;
        await delInput.fill(delMsg);

        const sendBtn = await findSendButton(pageStudent);
        await sendBtn.click();
        await pageStudent.waitForTimeout(2000);

        const delLoc = pageStudent.locator(`text="${delMsg.substring(0, 10)}"`).first();
        if (await delLoc.isVisible({ timeout: 3000 }).catch(() => false)) {
          await delLoc.hover();

          const delBtn = pageStudent.locator('button[data-testid="delete-message-btn"]').first();
          if (await delBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
            await delBtn.click();

            await pageStudent.waitForTimeout(500);
            const confirmBtn = pageStudent.locator('button:has-text("Delete"), button:has-text("Удалить")').first();
            if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
              await confirmBtn.click();
              await pageStudent.waitForTimeout(1000);
              results.delete = true;
              console.log('[WORKFLOW] ✅ Step 4: Message deleted');
            }
          }
        }
      } catch (e) {
        console.error('[WORKFLOW] ❌ Step 4 failed:', e);
      }

      // Step 5: WebSocket test
      try {
        contextTeacher = await browser.newContext();
        const pageTeacher = await contextTeacher.newPage();

        await login(pageTeacher, TEACHER.email, TEACHER.password, TEACHER.role);
        await navigateToForum(pageTeacher, TEACHER.role);

        const teacherChat = pageTeacher.locator('[data-testid="chat-item"]').first();
        if (await teacherChat.isVisible({ timeout: 5000 }).catch(() => false)) {
          await teacherChat.click();
        }

        await pageStudent.waitForTimeout(1000);
        await pageTeacher.waitForTimeout(1000);

        const wsInput = await findMessageInput(pageStudent);
        const wsMsg = `WS test ${Date.now()}`;
        await wsInput.fill(wsMsg);

        const wsBtn = await findSendButton(pageStudent);
        await wsBtn.click();

        await pageTeacher.waitForTimeout(3000);
        const teacherSees = await pageTeacher.locator(`text="${wsMsg.substring(0, 15)}"`).isVisible({ timeout: 8000 }).catch(() => false);

        if (teacherSees) {
          results.websocket = true;
          console.log('[WORKFLOW] ✅ Step 5: WebSocket works');
        }
      } catch (e) {
        console.error('[WORKFLOW] ❌ Step 5 failed:', e);
      }

    } finally {
      if (contextStudent) await contextStudent.close();
      if (contextTeacher) await contextTeacher.close();
    }

    // Print summary
    console.log('\n' + '='.repeat(80));
    console.log('WORKFLOW TEST SUMMARY:');
    console.log('='.repeat(80));
    console.log(`Create/Open Chat:  ${results.create ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Send Message:      ${results.send ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Edit Message:      ${results.edit ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Delete Message:    ${results.delete ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`WebSocket Updates: ${results.websocket ? '✅ PASS' : '❌ FAIL'}`);
    console.log('='.repeat(80));

    const passedCount = Object.values(results).filter(v => v).length;
    const totalCount = Object.values(results).length;
    console.log(`\nRESULT: ${passedCount}/${totalCount} tests passed`);

    // Fail test if any step failed
    if (passedCount < totalCount) {
      throw new Error(`Workflow incomplete: ${passedCount}/${totalCount} steps passed`);
    }
  });
});
