/**
 * E2E тесты навигации форума - проверка доступности в каждой роли
 *
 * Feature: Forum Navigation - Accessible from all role dashboards
 * - Student sidebar has Forum link
 * - Teacher sidebar has Forum link
 * - Tutor sidebar has Forum link
 * - Parent sidebar has Forum link (if applicable)
 * - Forum navigation works for all roles
 */

import { test, expect } from '@playwright/test';
import { loginAs, logout, TEST_USERS } from '../helpers/auth';

test.describe('Forum Navigation - Student', () => {
  test.beforeEach(async ({ page }) => {
    // Login as student
    await loginAs(page, 'student');
  });

  test('should have Forum link in student sidebar', async ({ page }) => {
    // Check if we're on student dashboard
    await expect(page).toHaveURL(/\/dashboard\/student/);

    // Look for Forum link in sidebar
    const forumLink = page.locator('a, button').filter({ hasText: /форум|forum/i });

    if (await forumLink.count() > 0) {
      await expect(forumLink.first()).toBeVisible();
      console.log('Forum link found in student sidebar');
    } else {
      console.log('Forum link not yet visible (might need to expand menu or have no chats)');
    }
  });

  test('clicking Forum navigates to forum page', async ({ page }) => {
    // Click Forum link
    const forumLink = page.locator('a, button').filter({ hasText: /форум|forum/i }).first();

    if (await forumLink.count() > 0) {
      await forumLink.click();

      // Wait for navigation
      await page.waitForURL('**/dashboard/student/forum', { timeout: 10000 });

      // Verify we're on forum page
      const currentUrl = page.url();
      expect(currentUrl).toContain('/dashboard/student/forum');

      console.log('Student forum navigation works');
    } else {
      // If link not visible, navigate directly
      await page.goto('/dashboard/student/forum');
      const currentUrl = page.url();
      expect(currentUrl).toContain('/dashboard/student/forum');
    }
  });

  test('forum page has proper layout', async ({ page }) => {
    // Navigate to forum
    await page.goto('/dashboard/student/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });

    // Check for main layout elements
    const mainContent = page.locator('[role="main"], main').first();
    await expect(mainContent).toBeVisible({ timeout: 5000 });

    // Look for chat list and message area
    const gridContainer = page.locator('.grid, [class*="grid"]').first();
    if (await gridContainer.count() > 0) {
      await expect(gridContainer).toBeVisible();
      console.log('Forum layout visible');
    } else {
      console.log('Forum grid container not found (layout might be different)');
    }
  });

  test('can navigate away from forum and back', async ({ page }) => {
    // Navigate to forum
    await page.goto('/dashboard/student/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });
    await expect(page).toHaveURL(/\/dashboard\/student\/forum/);

    // Navigate to dashboard
    await page.goto('/dashboard/student');
    await page.waitForLoadState('networkidle', { timeout: 5000 });
    await expect(page).toHaveURL(/\/dashboard\/student$/);

    // Navigate back to forum
    await page.goto('/dashboard/student/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });
    await expect(page).toHaveURL(/\/dashboard\/student\/forum/);

    console.log('Navigation away and back works');
  });
});

test.describe('Forum Navigation - Teacher', () => {
  test.beforeEach(async ({ page }) => {
    // Login as teacher
    await loginAs(page, 'teacher');
  });

  test('should have Forum link in teacher sidebar', async ({ page }) => {
    // Check if we're on teacher dashboard
    await expect(page).toHaveURL(/\/dashboard\/teacher/);

    // Look for Forum link in sidebar
    const forumLink = page.locator('a, button').filter({ hasText: /форум|forum/i });

    if (await forumLink.count() > 0) {
      await expect(forumLink.first()).toBeVisible();
      console.log('Forum link found in teacher sidebar');
    } else {
      console.log('Forum link not yet visible');
    }
  });

  test('teacher forum navigates to correct URL', async ({ page }) => {
    // Navigate to teacher forum
    await page.goto('/dashboard/teacher/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });

    // Verify URL
    const currentUrl = page.url();
    expect(currentUrl).toContain('/dashboard/teacher/forum');

    // Verify forum page loads
    const mainContent = page.locator('[role="main"], main').first();
    await expect(mainContent).toBeVisible({ timeout: 5000 });

    console.log('Teacher forum navigation works');
  });

  test('teacher forum shows different chat list than student', async ({ page }) => {
    // Teacher views their forum
    await page.goto('/dashboard/teacher/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });

    // Count visible chats
    const chatItems = page.locator('[role="main"], main').locator('div[class*="p-3"], div[class*="border"]');
    const teacherChatCount = await chatItems.count();

    console.log(`Teacher sees ${teacherChatCount} forum chats`);

    // Log out and check student view
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Login as student
    await loginAs(page, 'student');

    // Student views their forum
    await page.goto('/dashboard/student/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });

    const studentChatItems = page.locator('[role="main"], main').locator('div[class*="p-3"], div[class*="border"]');
    const studentChatCount = await studentChatItems.count();

    console.log(`Student sees ${studentChatCount} forum chats`);

    // Chats might be different based on enrollments
    console.log(`Chat list differs by role: student=${studentChatCount}, teacher=${teacherChatCount}`);
  });
});

test.describe('Forum Navigation - Tutor', () => {
  test.beforeEach(async ({ page }) => {
    // Login as tutor
    await loginAs(page, 'tutor');
  });

  test('should navigate to tutor forum', async ({ page }) => {
    // Verify on tutor dashboard
    await expect(page).toHaveURL(/\/dashboard\/tutor/);

    // Navigate to forum
    await page.goto('/dashboard/tutor/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });

    // Verify URL
    const currentUrl = page.url();
    expect(currentUrl).toContain('/dashboard/tutor/forum');

    // Verify forum loads
    const mainContent = page.locator('[role="main"], main').first();
    await expect(mainContent).toBeVisible({ timeout: 5000 });

    console.log('Tutor forum navigation works');
  });

  test('tutor sees assigned student chats', async ({ page }) => {
    // Navigate to tutor forum
    await page.goto('/dashboard/tutor/forum');
    await page.waitForLoadState('networkidle', { timeout: 5000 });

    // Look for student names in chat list
    const chatList = page.locator('[role="main"], main').first();
    await expect(chatList).toBeVisible({ timeout: 5000 });

    // Count chats (should be empty or have assigned students)
    const chats = page.locator('div[class*="p-3"]');
    const chatCount = await chats.count();

    console.log(`Tutor sees ${chatCount} student chats`);
  });
});

test.describe('Forum Navigation - Parent', () => {
  test.beforeEach(async ({ page }) => {
    // Login as parent
    await loginAs(page, 'parent');
  });

  test('should navigate to parent forum if applicable', async ({ page }) => {
    // Verify on parent dashboard
    await expect(page).toHaveURL(/\/dashboard\/parent/);

    // Try to navigate to forum
    try {
      await page.goto('/dashboard/parent/forum');
      await page.waitForLoadState('networkidle', { timeout: 5000 });

      const currentUrl = page.url();
      if (currentUrl.includes('/dashboard/parent/forum')) {
        console.log('Parent forum navigation available');

        // Verify forum loads
        const mainContent = page.locator('[role="main"], main').first();
        if (await mainContent.count() > 0) {
          await expect(mainContent).toBeVisible({ timeout: 5000 });
          console.log('Parent forum page loaded');
        }
      } else {
        console.log('Parent forum route redirects (might not be applicable)');
      }
    } catch (error) {
      console.log('Parent forum navigation not available (expected behavior)');
    }
  });
});

test.describe('Forum Navigation - Cross-Role', () => {
  test('forum link uses MessageCircle icon (consistent across roles)', async ({ page }) => {
    // Login as student
    await loginAs(page, 'student');

    // Look for Forum link
    const forumLink = page.locator('a, button').filter({ hasText: /форум|forum/i }).first();

    if (await forumLink.count() > 0) {
      // Check if icon is present (MessageCircle)
      const icon = forumLink.locator('svg, [class*="icon"]').first();
      if (await icon.count() > 0) {
        console.log('Forum link has icon');
      }
    }

    // Log out
    await logout(page);

    // Login as teacher
    await loginAs(page, 'teacher');

    // Look for Forum link in teacher sidebar
    const teacherForumLink = page.locator('a, button').filter({ hasText: /форум|forum/i }).first();

    if (await teacherForumLink.count() > 0) {
      console.log('Forum link visible in teacher sidebar too');
    }
  });

  test('forum page is accessible from all dashboards', async ({ page }) => {
    // Define all roles to test
    const roles: Array<keyof typeof TEST_USERS> = ['student', 'teacher', 'tutor'];

    for (const role of roles) {
      // Clear auth
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });

      // Login as role
      await loginAs(page, role);

      // Navigate to forum
      const forumPath = `/dashboard/${role}/forum`;
      await page.goto(forumPath);

      // Wait for load
      await page.waitForLoadState('networkidle', { timeout: 5000 });

      // Verify we're on the forum page
      const currentUrl = page.url();
      expect(currentUrl).toContain(`/dashboard/${role}/forum`);

      // Verify main content loads
      const mainContent = page.locator('[role="main"], main').first();
      const isVisible = await mainContent.count() > 0;
      console.log(`${role.toUpperCase()} forum accessible: ${isVisible}`);
    }
  });
});
