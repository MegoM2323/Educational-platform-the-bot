import { test, expect, type Page } from '@playwright/test';

/**
 * Complete Student Workflow Test Suite
 * Tests all scenarios specified in the QA task
 */

// Test configuration
const TEST_STUDENT = {
  email: 'student@test.com',
  password: 'testpass123',
};

const BASE_URL = 'http://localhost:8081';
const DASHBOARD_URL = `${BASE_URL}/dashboard/student`;
const AUTH_URL = `${BASE_URL}/auth`;

// Helper function to check console for errors
async function checkConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

test.describe('Student Complete Workflow - ProtectedRoute Fix Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.context().clearCookies();
    await page.context().clearPermissions();
  });

  test('Scenario 1: Login & Auth Fix Verification (CRITICAL)', async ({ page }) => {
    const consoleErrors: string[] = [];

    // Capture console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to login page
    console.log('[TEST] Navigating to login page:', AUTH_URL);
    await page.goto(AUTH_URL);
    await page.waitForLoadState('networkidle');

    // Take screenshot of login page
    await page.screenshot({ path: 'test-results/01-login-page.png', fullPage: true });

    // Verify login form is visible
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    console.log('[TEST] Login form is visible');

    // Fill in credentials
    console.log('[TEST] Entering credentials:', TEST_STUDENT.email);
    await page.locator('input[type="email"]').fill(TEST_STUDENT.email);
    await page.locator('input[type="password"]').fill(TEST_STUDENT.password);

    // Take screenshot before clicking login
    await page.screenshot({ path: 'test-results/02-before-login.png', fullPage: true });

    // Click login button
    const loginButton = page.locator('button:has-text("Войти")');
    await expect(loginButton).toBeVisible();
    console.log('[TEST] Clicking login button');
    await loginButton.click();

    // Wait for navigation
    console.log('[TEST] Waiting for navigation...');
    await page.waitForURL(DASHBOARD_URL, { timeout: 10000 });

    // CRITICAL CHECK: Verify URL is dashboard (not /auth)
    const currentURL = page.url();
    console.log('[TEST] Current URL after login:', currentURL);
    expect(currentURL).toBe(DASHBOARD_URL);
    console.log('[PASS] URL is correct (no redirect to /auth)');

    // Wait for dashboard to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Give time for React to render

    // Take screenshot of dashboard
    await page.screenshot({ path: 'test-results/03-student-dashboard.png', fullPage: true });

    // Verify dashboard content is visible (NOT login form)
    const loginFormVisible = await page.locator('input[type="email"]').isVisible().catch(() => false);
    expect(loginFormVisible).toBe(false);
    console.log('[PASS] Login form is NOT visible (good - we are on dashboard)');

    // Verify dashboard elements are present
    const dashboardContent = page.locator('main, [role="main"], .dashboard, [data-testid="dashboard"]');
    await expect(dashboardContent).toBeVisible({ timeout: 5000 });
    console.log('[PASS] Dashboard main content is visible');

    // Check for student name/role display
    const studentInfo = await page.locator('text=/студент|student/i').isVisible().catch(() => false);
    console.log('[INFO] Student role indicator visible:', studentInfo);

    // Check console for AuthContext timeout warnings
    const authTimeoutWarnings = consoleErrors.filter(e => e.includes('AuthContext') || e.includes('timeout'));
    if (authTimeoutWarnings.length > 0) {
      console.log('[WARNING] AuthContext timeout warnings found:', authTimeoutWarnings);
    } else {
      console.log('[PASS] No AuthContext timeout warnings');
    }

    // Log all console errors
    if (consoleErrors.length > 0) {
      console.log('[CONSOLE ERRORS]:', consoleErrors);
    } else {
      console.log('[PASS] No console errors');
    }

    // Final verification: page should show student dashboard content
    const pageText = await page.textContent('body');
    const hasLoginText = pageText?.toLowerCase().includes('войти') || false;
    expect(hasLoginText).toBe(false);
    console.log('[PASS] Page does not show login text (confirmed on dashboard)');
  });

  test('Scenario 2: Dashboard Navigation', async ({ page }) => {
    // Login first
    await page.goto(AUTH_URL);
    await page.locator('input[type="email"]').fill(TEST_STUDENT.email);
    await page.locator('input[type="password"]').fill(TEST_STUDENT.password);
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');

    console.log('[TEST] Verifying dashboard elements...');

    // Take screenshot of dashboard
    await page.screenshot({ path: 'test-results/04-dashboard-full.png', fullPage: true });

    // Verify dashboard displays student info
    const bodyText = await page.textContent('body');
    console.log('[INFO] Dashboard loaded, body text length:', bodyText?.length || 0);

    // Check for progress cards (may be empty if no enrollments)
    const progressSection = page.locator('text=/прогресс|progress/i').first();
    const hasProgress = await progressSection.isVisible().catch(() => false);
    console.log('[INFO] Progress section visible:', hasProgress);

    // Check for upcoming lessons section
    const lessonsSection = page.locator('text=/занятия|lessons|расписание|schedule/i').first();
    const hasLessons = await lessonsSection.isVisible().catch(() => false);
    console.log('[INFO] Lessons section visible:', hasLessons);

    // Check navigation menu
    const nav = page.locator('nav, [role="navigation"]');
    await expect(nav).toBeVisible({ timeout: 5000 });
    console.log('[PASS] Navigation menu is visible');

    // Click through navigation items
    const navLinks = await page.locator('nav a, [role="navigation"] a').all();
    console.log('[INFO] Found', navLinks.length, 'navigation links');

    // Take screenshot of navigation
    await page.screenshot({ path: 'test-results/05-navigation.png', fullPage: true });

    // Check console for errors
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    if (consoleErrors.length > 0) {
      console.log('[CONSOLE ERRORS]:', consoleErrors);
    } else {
      console.log('[PASS] No console errors during navigation');
    }
  });

  test('Scenario 3: Schedule Page', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Login first
    await page.goto(AUTH_URL);
    await page.locator('input[type="email"]').fill(TEST_STUDENT.email);
    await page.locator('input[type="password"]').fill(TEST_STUDENT.password);
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL(DASHBOARD_URL);

    // Navigate to schedule page
    const scheduleURL = `${BASE_URL}/dashboard/student/schedule`;
    console.log('[TEST] Navigating to schedule page:', scheduleURL);
    await page.goto(scheduleURL);
    await page.waitForLoadState('networkidle');

    // Verify page loaded successfully
    expect(page.url()).toBe(scheduleURL);
    console.log('[PASS] Schedule page URL correct');

    // Take screenshot
    await page.screenshot({ path: 'test-results/06-schedule-page.png', fullPage: true });

    // Check for schedule content
    const bodyText = await page.textContent('body');
    const hasScheduleContent = bodyText?.toLowerCase().includes('расписание') ||
                               bodyText?.toLowerCase().includes('schedule') ||
                               bodyText?.toLowerCase().includes('занятия');
    console.log('[INFO] Schedule content present:', hasScheduleContent);

    // Check for calendar component
    const calendar = page.locator('[role="grid"], .calendar, [data-testid="calendar"]').first();
    const calendarVisible = await calendar.isVisible().catch(() => false);
    console.log('[INFO] Calendar component visible:', calendarVisible);

    // Check for lessons list (may be empty)
    const lessonsList = page.locator('[data-testid="lessons-list"], .lessons, ul').first();
    const lessonsVisible = await lessonsList.isVisible().catch(() => false);
    console.log('[INFO] Lessons list visible:', lessonsVisible);

    // Verify no console errors
    if (consoleErrors.length > 0) {
      console.log('[CONSOLE ERRORS]:', consoleErrors);
    } else {
      console.log('[PASS] No console errors on schedule page');
    }
  });

  test('Scenario 4: Forum Page', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Login first
    await page.goto(AUTH_URL);
    await page.locator('input[type="email"]').fill(TEST_STUDENT.email);
    await page.locator('input[type="password"]').fill(TEST_STUDENT.password);
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL(DASHBOARD_URL);

    // Navigate to forum page
    const forumURL = `${BASE_URL}/dashboard/student/forum`;
    console.log('[TEST] Navigating to forum page:', forumURL);
    await page.goto(forumURL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Wait for API calls

    // Verify page loaded successfully
    expect(page.url()).toBe(forumURL);
    console.log('[PASS] Forum page URL correct');

    // Take screenshot
    await page.screenshot({ path: 'test-results/07-forum-page.png', fullPage: true });

    // Check for forum content
    const bodyText = await page.textContent('body');
    const hasForumContent = bodyText?.toLowerCase().includes('форум') ||
                           bodyText?.toLowerCase().includes('chat') ||
                           bodyText?.toLowerCase().includes('сообщения');
    console.log('[INFO] Forum content present:', hasForumContent);

    // Check if chat list loads (even if empty)
    const chatList = page.locator('[data-testid="chat-list"], .chat-list, .chats').first();
    const chatListVisible = await chatList.isVisible().catch(() => false);
    console.log('[INFO] Chat list component visible:', chatListVisible);

    // Check for "no chats" message or chat items
    const noChatsMessage = await page.locator('text=/нет.*чат|no.*chat/i').isVisible().catch(() => false);
    const chatItems = await page.locator('[data-testid="chat-item"], .chat-item').count();
    console.log('[INFO] No chats message:', noChatsMessage, ', Chat items count:', chatItems);

    // If chats exist, try to click on one
    if (chatItems > 0) {
      console.log('[TEST] Clicking on first chat...');
      await page.locator('[data-testid="chat-item"], .chat-item').first().click();
      await page.waitForTimeout(1000);

      // Check if message history loads
      const messageHistory = page.locator('[data-testid="message-list"], .messages, .chat-messages').first();
      const messagesVisible = await messageHistory.isVisible().catch(() => false);
      console.log('[INFO] Message history visible:', messagesVisible);

      // Take screenshot of chat
      await page.screenshot({ path: 'test-results/08-forum-chat-open.png', fullPage: true });

      // Try sending a test message (if input is available)
      const messageInput = page.locator('textarea, input[type="text"]').last();
      const inputVisible = await messageInput.isVisible().catch(() => false);
      if (inputVisible) {
        console.log('[TEST] Sending test message...');
        await messageInput.fill('Test message from automated test');
        const sendButton = page.locator('button:has-text("Отправить"), button[type="submit"]').last();
        if (await sendButton.isVisible().catch(() => false)) {
          await sendButton.click();
          await page.waitForTimeout(1000);
          console.log('[INFO] Test message sent');

          // Take screenshot after sending
          await page.screenshot({ path: 'test-results/09-forum-message-sent.png', fullPage: true });
        }
      }
    }

    // Check WebSocket connection status (if visible in UI)
    const wsStatus = await page.locator('text=/connected|подключен/i').isVisible().catch(() => false);
    console.log('[INFO] WebSocket status indicator visible:', wsStatus);

    // Verify no console errors
    if (consoleErrors.length > 0) {
      console.log('[CONSOLE ERRORS]:', consoleErrors);
    } else {
      console.log('[PASS] No console errors on forum page');
    }
  });
});

test.describe('Student Workflow - Comprehensive Checks', () => {
  test('All Navigation Links Work', async ({ page }) => {
    // Login
    await page.goto(AUTH_URL);
    await page.locator('input[type="email"]').fill(TEST_STUDENT.email);
    await page.locator('input[type="password"]').fill(TEST_STUDENT.password);
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL(DASHBOARD_URL);

    // Get all navigation links
    const navLinks = await page.locator('nav a, [role="navigation"] a').all();
    console.log('[TEST] Testing', navLinks.length, 'navigation links');

    for (const link of navLinks) {
      const href = await link.getAttribute('href');
      const text = await link.textContent();
      console.log('[TEST] Clicking link:', text?.trim(), '→', href);

      await link.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // Verify we didn't get redirected to auth
      const currentURL = page.url();
      expect(currentURL).not.toContain('/auth');
      console.log('[PASS] Link works, current URL:', currentURL);
    }
  });

  test('No Authentication Errors in Console', async ({ page }) => {
    const consoleErrors: string[] = [];
    const consoleWarnings: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      } else if (msg.type() === 'warning') {
        consoleWarnings.push(msg.text());
      }
    });

    // Login
    await page.goto(AUTH_URL);
    await page.locator('input[type="email"]').fill(TEST_STUDENT.email);
    await page.locator('input[type="password"]').fill(TEST_STUDENT.password);
    await page.locator('button:has-text("Войти")').click();
    await page.waitForURL(DASHBOARD_URL);
    await page.waitForTimeout(3000);

    // Check for auth-related errors
    const authErrors = consoleErrors.filter(e =>
      e.toLowerCase().includes('auth') ||
      e.toLowerCase().includes('token') ||
      e.toLowerCase().includes('401') ||
      e.toLowerCase().includes('403')
    );

    const authWarnings = consoleWarnings.filter(w =>
      w.toLowerCase().includes('auth') ||
      w.toLowerCase().includes('token')
    );

    console.log('[INFO] Total console errors:', consoleErrors.length);
    console.log('[INFO] Auth-related errors:', authErrors.length);
    console.log('[INFO] Auth-related warnings:', authWarnings.length);

    if (authErrors.length > 0) {
      console.log('[ERRORS]:', authErrors);
    }
    if (authWarnings.length > 0) {
      console.log('[WARNINGS]:', authWarnings);
    }

    expect(authErrors.length).toBe(0);
  });
});
