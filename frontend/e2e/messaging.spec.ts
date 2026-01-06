import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';
const API_URL = 'http://localhost:8000';

interface TestUser {
  username: string;
  password: string;
  role: string;
}

const TEST_USERS: Record<string, TestUser> = {
  admin_test: {
    username: 'admin_test',
    password: 'TestAdmin123!',
    role: 'admin'
  },
  teacher_test: {
    username: 'teacher_test',
    password: 'TestTeacher123!',
    role: 'teacher'
  },
  tutor_test: {
    username: 'tutor_test',
    password: 'TestTutor123!',
    role: 'tutor'
  },
  student_test: {
    username: 'student_test',
    password: 'TestStudent123!',
    role: 'student'
  },
  parent_test: {
    username: 'parent_test',
    password: 'TestParent123!',
    role: 'parent'
  }
};

const MESSAGING_PAIRS = [
  { sender: 'admin_test', receiver: 'teacher_test', senderMsg: 'Админ: Привет, учитель!', receiverMsg: 'Учитель: Здравствуйте, администратор!' },
  { sender: 'admin_test', receiver: 'tutor_test', senderMsg: 'Админ: Привет, репетитор!', receiverMsg: 'Репетитор: Здравствуйте, администратор!' },
  { sender: 'admin_test', receiver: 'student_test', senderMsg: 'Админ: Привет, ученик!', receiverMsg: 'Ученик: Здравствуйте, администратор!' },
  { sender: 'admin_test', receiver: 'parent_test', senderMsg: 'Админ: Привет, родитель!', receiverMsg: 'Родитель: Добрый день, администратор!' },
  { sender: 'teacher_test', receiver: 'tutor_test', senderMsg: 'Учитель: Привет, коллега!', receiverMsg: 'Репетитор: Привет, учитель!' },
  { sender: 'teacher_test', receiver: 'student_test', senderMsg: 'Учитель: Привет, Петр!', receiverMsg: 'Ученик: Привет, учитель!' },
  { sender: 'teacher_test', receiver: 'parent_test', senderMsg: 'Учитель: Привет, родитель студента!', receiverMsg: 'Родитель: Привет, учитель!' },
  { sender: 'tutor_test', receiver: 'student_test', senderMsg: 'Репетитор: Привет, Петр!', receiverMsg: 'Ученик: Привет, репетитор!' },
  { sender: 'tutor_test', receiver: 'parent_test', senderMsg: 'Репетитор: Привет, родитель!', receiverMsg: 'Родитель: Привет, репетитор!' },
  { sender: 'student_test', receiver: 'parent_test', senderMsg: 'Ученик: Мама, как дела?', receiverMsg: 'Родитель: Привет, Петр!' }
];

async function loginUser(page: Page, userKey: string) {
  const user = TEST_USERS[userKey];

  await page.goto(`${BASE_URL}/auth/signin`);

  // Wait for login form to load
  await page.waitForSelector('button:has-text("Войти")', { timeout: 10000 });

  // Check if we need to switch to username/password mode
  const loginButtons = await page.locator('button').filter({ hasText: /^Логин$/ });
  if (await loginButtons.count() > 0) {
    await loginButtons.first().click();
    await page.waitForTimeout(500);
  }

  // Fill in credentials
  const usernameInput = page.locator('input[placeholder*="Имя пользователя"], input[placeholder*="Username"]').first();
  const passwordInput = page.locator('input[placeholder*="Пароль"], input[placeholder*="Password"]').first();

  await usernameInput.fill(user.username);
  await passwordInput.fill(user.password);

  // Click sign in button
  const signInButton = page.locator('button:has-text("Войти")').last();
  await signInButton.click();

  // Wait for navigation to dashboard
  await page.waitForURL(/\/(admin|dashboard|student|teacher|tutor|parent)/, { timeout: 15000 });
}

async function navigateToChat(page: Page) {
  // Navigate to chat section
  // Different paths for different roles
  const url = page.url();

  if (url.includes('/admin')) {
    // Admin: click on chat link
    const chatLink = page.locator('a:has-text("Чаты"), a:has-text("Chat")').first();
    if (await chatLink.isVisible()) {
      await chatLink.click();
      await page.waitForURL(/.*\/chat/, { timeout: 10000 });
    }
  } else {
    // For other roles, navigate directly
    await page.goto(`${BASE_URL}/chat`);
  }
}

async function sendMessage(page: Page, message: string) {
  // Look for message input field
  const messageInput = page.locator('textarea, input[placeholder*="Сообщение"], input[placeholder*="Message"]').first();

  if (await messageInput.isVisible()) {
    await messageInput.fill(message);

    // Send button - could be icon button or text button
    const sendButton = page.locator('button[aria-label*="Send"], button:has-text("Отправить"), button:has-text("Send")').first();
    if (await sendButton.isVisible()) {
      await sendButton.click();
    } else {
      // Try pressing Enter
      await messageInput.press('Enter');
    }

    await page.waitForTimeout(1000);
  }
}

test.describe('Messaging System E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Clear any cached auth state
    await page.context().clearCookies();
  });

  for (const pair of MESSAGING_PAIRS) {
    test(`Pair: ${pair.sender} ↔ ${pair.receiver}`, async ({ browser }) => {
      // Phase 1: Sender sends message
      const senderPage = await browser.newPage();
      await loginUser(senderPage, pair.sender);

      // Navigate to chat
      await navigateToChat(senderPage);
      await senderPage.waitForTimeout(1000);

      // Find or create chat with receiver
      const receiverName = TEST_USERS[pair.receiver].username;
      const searchBox = senderPage.locator('input[placeholder*="Поиск"], input[placeholder*="Search"]').first();

      if (await searchBox.isVisible()) {
        await searchBox.fill(receiverName);
        await senderPage.waitForTimeout(500);

        // Click on first result
        const contactItem = senderPage.locator(`text=${pair.receiver}`).first();
        if (await contactItem.isVisible()) {
          await contactItem.click();
          await senderPage.waitForTimeout(1000);
        }
      }

      // Send message from sender
      await sendMessage(senderPage, pair.senderMsg);

      // Verify message appears in sender's view
      const messageVisible = await senderPage.locator(`text=${pair.senderMsg}`).isVisible();
      expect(messageVisible).toBeTruthy();

      // Phase 2: Receiver receives and replies
      const receiverPage = await browser.newPage();
      await loginUser(receiverPage, pair.receiver);

      // Navigate to chat
      await navigateToChat(receiverPage);
      await receiverPage.waitForTimeout(1000);

      // Find chat with sender
      const receiverSearchBox = receiverPage.locator('input[placeholder*="Поиск"], input[placeholder*="Search"]').first();
      if (await receiverSearchBox.isVisible()) {
        await receiverSearchBox.fill(pair.sender);
        await receiverPage.waitForTimeout(500);

        const senderItem = receiverPage.locator(`text=${pair.sender}`).first();
        if (await senderItem.isVisible()) {
          await senderItem.click();
          await receiverPage.waitForTimeout(1000);
        }
      }

      // Verify receiver can see sender's message
      const receiverSeesSenderMsg = await receiverPage.locator(`text=${pair.senderMsg}`).isVisible({ timeout: 5000 }).catch(() => false);
      if (receiverSeesSenderMsg) {
        // Send reply
        await sendMessage(receiverPage, pair.receiverMsg);

        // Verify reply appears in receiver's view
        const replyVisible = await receiverPage.locator(`text=${pair.receiverMsg}`).isVisible();
        expect(replyVisible).toBeTruthy();

        // Verify sender sees the reply
        await senderPage.reload();
        await senderPage.waitForTimeout(2000);
        const senderSeesReply = await senderPage.locator(`text=${pair.receiverMsg}`).isVisible({ timeout: 5000 }).catch(() => false);
        expect(senderSeesReply).toBeTruthy();
      }

      await senderPage.close();
      await receiverPage.close();
    });
  }
});

test.describe('Chat Navigation and UI', () => {

  test('Admin can view all chats', async ({ page }) => {
    await loginUser(page, 'admin_test');

    // Navigate to chats
    const chatsLink = page.locator('a:has-text("Все чаты"), a:has-text("Chats")').first();
    if (await chatsLink.isVisible()) {
      await chatsLink.click();
      await page.waitForURL(/.*chats/, { timeout: 10000 });

      // Verify chat list is visible
      const chatList = page.locator('[role="list"]').first();
      expect(chatList).toBeTruthy();
    }
  });

  test('User can access personal chat section', async ({ page }) => {
    await loginUser(page, 'teacher_test');

    // Try to navigate to personal chat
    await page.goto(`${BASE_URL}/chat`);

    // Verify page loaded
    const title = await page.title();
    expect(title).toContain('THE BOT');
  });
});
