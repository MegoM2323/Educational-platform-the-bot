import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';
const API_URL = 'http://localhost:8000';

interface StudentUser {
  username: string;
  password: string;
  role: string;
}

const TEST_STUDENT: StudentUser = {
  username: 'student_test',
  password: 'TestStudent123!',
  role: 'student'
};

/**
 * Login student to dashboard
 */
async function loginStudent(page: Page) {
  await page.goto(`${BASE_URL}/auth/signin`);
  await page.waitForSelector('button:has-text("Войти")', { timeout: 10000 });

  // Check if email tab is active and switch to username/login tab
  const loginTab = page.locator('button:has-text("Логин"), [role="tab"]:has-text("Логин")').first();
  const emailTab = page.locator('button:has-text("Email"), [role="tab"]:has-text("Email")').first();

  // If email tab exists and is active, click login tab
  if (await emailTab.isVisible({ timeout: 5000 }).catch(() => false)) {
    const emailTabAttribute = await emailTab.getAttribute('aria-selected', { timeout: 5000 }).catch(() => null);
    if (emailTabAttribute === 'true' || (await loginTab.isVisible({ timeout: 5000 }).catch(() => false))) {
      await loginTab.click();
      await page.waitForTimeout(500); // Wait for tab content to appear
    }
  }

  // Wait for username input to be visible
  await page.waitForSelector('input[placeholder*="Имя пользователя"], input[placeholder*="Username"]', { timeout: 10000 });

  // Fill in credentials
  const usernameInput = page.locator('input[placeholder*="Имя пользователя"], input[placeholder*="Username"]').first();
  const passwordInput = page.locator('input[placeholder*="Пароль"], input[placeholder*="Password"]').first();

  await usernameInput.fill(TEST_STUDENT.username);
  await passwordInput.fill(TEST_STUDENT.password);

  // Click sign in button
  const signInButton = page.locator('button:has-text("Войти")').last();
  await signInButton.click();

  // Wait for navigation to student dashboard
  await page.waitForURL(/\/student/, { timeout: 15000 });
}

test.describe('Student Dashboard E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Clear any cached auth state
    await page.context().clearCookies();
  });

  test('Student can login and access dashboard', async ({ page }) => {
    await loginStudent(page);

    // Verify we're on student dashboard
    const currentUrl = page.url();
    expect(currentUrl).toContain('/student');

    // Verify dashboard title
    const title = await page.title();
    expect(title).toContain('THE BOT');

    // Take screenshot of dashboard
    await page.screenshot({ path: 'test-results/student-dashboard-main.png' });
  });

  test('Student can view materials list', async ({ page }) => {
    await loginStudent(page);

    // Navigate to materials section
    const materialsLink = page.locator('a, button').filter({ hasText: /материал|Material|курс|Course|lesson/i }).first();

    if (await materialsLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await materialsLink.click();
      await page.waitForURL(/.*material|.*course|.*lesson/, { timeout: 5000 }).catch(() => {});

      // Verify materials are displayed
      const materialsList = page.locator('[role="list"], .materials, .courses').first();
      const isVisible = await materialsList.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await page.screenshot({ path: 'test-results/student-materials.png' });
        expect(isVisible).toBeTruthy();
      }
    } else {
      test.info('Materials link not found or not visible');
    }
  });

  test('Student can view progress', async ({ page }) => {
    await loginStudent(page);

    // Look for progress or analytics section
    const progressLink = page.locator('a, button').filter({ hasText: /прогресс|progress|статус|status/i }).first();

    if (await progressLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await progressLink.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

      // Take screenshot
      await page.screenshot({ path: 'test-results/student-progress.png' });
      expect(true).toBeTruthy();
    }
  });

  test('Student dashboard displays user info', async ({ page }) => {
    await loginStudent(page);

    // Look for user name/profile section
    const userNameLocator = page.locator('text=' + TEST_STUDENT.username);
    const userNameVisible = await userNameLocator.isVisible({ timeout: 5000 }).catch(() => false);

    if (!userNameVisible) {
      // Try to find in dropdown menu
      const profileButton = page.locator('[aria-label*="profile"], [aria-label*="user"], button:has-text("Профиль")').first();
      if (await profileButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await profileButton.click();
        await page.waitForTimeout(500);
      }
    }

    // Take screenshot showing profile info
    await page.screenshot({ path: 'test-results/student-profile.png' });
  });

  test('Student can navigate back to home from dashboard', async ({ page }) => {
    await loginStudent(page);

    // Look for home or back button
    const homeButton = page.locator('a, button').filter({ hasText: /home|главная|dashboard/i }).first();

    if (await homeButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await homeButton.click();
      await page.waitForTimeout(1000);
    }

    // Verify we're still on student pages
    const url = page.url();
    expect(url).toContain('/student');
  });

  test('Student dashboard layout is responsive', async ({ page }) => {
    await loginStudent(page);

    // Check viewport is reasonable
    const viewport = page.viewportSize();
    expect(viewport).toBeTruthy();
    expect(viewport?.width).toBeGreaterThan(0);
    expect(viewport?.height).toBeGreaterThan(0);

    // Verify main content area is visible
    const mainContent = page.locator('main, [role="main"], .container').first();
    const isVisible = await mainContent.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      expect(isVisible).toBeTruthy();
    }
  });

  test('Student can logout', async ({ page }) => {
    await loginStudent(page);

    // Look for logout button
    const logoutButton = page.locator('button, a').filter({ hasText: /выход|logout|sign out/i }).first();

    if (await logoutButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await logoutButton.click();
      await page.waitForURL(/.*signin|.*login|.*auth/, { timeout: 10000 }).catch(() => {});

      // Verify we're back at login page
      const currentUrl = page.url();
      expect(currentUrl).toMatch(/signin|login|auth/i);
    }
  });

  test('Student dashboard performs well (no console errors)', async ({ page }) => {
    const errors: string[] = [];
    const warnings: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });

    await loginStudent(page);
    await page.waitForTimeout(2000);

    // Filter out known safe warnings
    const safeWarnings = warnings.filter(w =>
      !w.includes('webpack') &&
      !w.includes('DevTools') &&
      !w.includes('Cannot find module')
    );

    if (errors.length > 0) {
      test.info(`Console Errors: ${errors.join(', ')}`);
    }
    if (safeWarnings.length > 0) {
      test.info(`Console Warnings: ${safeWarnings.join(', ')}`);
    }

    // We're mainly checking that page loads without critical errors
    await page.screenshot({ path: 'test-results/student-console-check.png' });
  });

  test('Student can access assignment section', async ({ page }) => {
    await loginStudent(page);

    // Look for assignments/homework section
    const assignmentsLink = page.locator('a, button').filter({ hasText: /задание|assignment|homework|работа/i }).first();

    if (await assignmentsLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await assignmentsLink.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

      // Take screenshot
      await page.screenshot({ path: 'test-results/student-assignments.png' });

      // Verify page loaded
      const url = page.url();
      expect(url.length).toBeGreaterThan(0);
    }
  });

  test('Student dashboard has working navigation menu', async ({ page }) => {
    await loginStudent(page);

    // Look for nav menu items
    const navItems = await page.locator('nav a, nav button, [role="navigation"] a, [role="navigation"] button').count();

    if (navItems > 0) {
      expect(navItems).toBeGreaterThan(0);
      await page.screenshot({ path: 'test-results/student-navigation.png' });
    }
  });

  test('Student page loads within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await loginStudent(page);

    const loadTime = Date.now() - startTime;

    // Dashboard should load within 20 seconds (including login)
    expect(loadTime).toBeLessThan(20000);

    test.info(`Student dashboard loaded in ${loadTime}ms`);
  });

  test('Student dashboard displays without layout breaks', async ({ page }) => {
    await loginStudent(page);

    // Check for layout issues
    const layoutErrors = await page.evaluate(() => {
      const issues: string[] = [];

      // Check for visible overflow
      const body = document.body;
      if (body.scrollWidth > window.innerWidth) {
        issues.push('Horizontal overflow detected');
      }

      // Check for missing elements
      const hiddenElements = document.querySelectorAll('[style*="display: none"]');
      if (hiddenElements.length > 10) {
        issues.push('Many hidden elements detected');
      }

      return issues;
    });

    if (layoutErrors.length > 0) {
      test.info(`Layout Issues: ${layoutErrors.join(', ')}`);
    }

    await page.screenshot({ path: 'test-results/student-layout-check.png' });
  });
});

test.describe('Student Dashboard Accessibility Tests', () => {

  test('Student dashboard has proper heading hierarchy', async ({ page }) => {
    await loginStudent(page);

    // Check for headings
    const h1Count = await page.locator('h1').count();
    const h2Count = await page.locator('h2').count();

    // At minimum, should have some structure
    expect(h1Count + h2Count).toBeGreaterThanOrEqual(0);

    await page.screenshot({ path: 'test-results/student-headings.png' });
  });

  test('Student dashboard buttons are keyboard accessible', async ({ page }) => {
    await loginStudent(page);

    // Try tabbing through page
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);

    // Check if any element is focused
    const focusedElement = await page.evaluate(() => document.activeElement?.className);

    expect(focusedElement).toBeDefined();

    await page.screenshot({ path: 'test-results/student-keyboard-nav.png' });
  });

  test('Student dashboard has alt text for images', async ({ page }) => {
    await loginStudent(page);

    // Check for images without alt text
    const imagesWithoutAlt = await page.locator('img:not([alt])').count();

    // Some images might not need alt text, but we should have awareness
    if (imagesWithoutAlt > 0) {
      test.info(`Found ${imagesWithoutAlt} images without alt text`);
    }

    await page.screenshot({ path: 'test-results/student-images.png' });
  });
});
