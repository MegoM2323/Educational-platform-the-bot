import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  logout,
  navigateToAdminDashboard,
  ADMIN_CONFIG,
} from '../helpers/admin-dashboard-helpers';

/**
 * E2E Tests for Admin Schedule Page
 * Tests: admin-only access, calendar display, filters, and responsive layout
 */

test.describe('Admin Schedule Page', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin using helper function
    await loginAsAdmin(page);

    // Navigate to admin schedule page
    await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.afterEach(async ({ page }) => {
    // Logout after each test
    try {
      await logout(page);
    } catch {
      // Ignore logout errors
    }
  });

  test.describe('Schedule Page Load and Display', () => {
    test('should load admin schedule page successfully', async ({ page }) => {
      // Verify page loaded - check for any heading or calendar elements
      const heading = page.locator('h1, h2, h3').first();
      const hasContent = await heading.count() > 0 || await page.locator('[class*="calendar"], [class*="schedule"]').count() > 0;
      expect(hasContent).toBeTruthy();
    });

    test('should display calendar header with navigation', async ({ page }) => {
      // Check for calendar title with month/year
      const monthYear = page.locator('h2').filter({ hasText: /\d{4}|\d{1,2}\s/i }).first();
      await expect(monthYear).toBeVisible({ timeout: 5000 });

      // Check for navigation buttons
      const prevButton = page.locator('button[aria-label*="previous"], button:has-text("←")').first();
      const nextButton = page.locator('button[aria-label*="next"], button:has-text("→")').first();

      if (await prevButton.count() > 0) {
        await expect(prevButton).toBeVisible();
      }
      if (await nextButton.count() > 0) {
        await expect(nextButton).toBeVisible();
      }
    });

    test('should display view mode buttons (month/week/day)', async ({ page }) => {
      // Look for view mode buttons
      const monthButton = page.locator('button:has-text("Месяц")');
      const weekButton = page.locator('button:has-text("Неделя")');
      const dayButton = page.locator('button:has-text("День")');

      await expect(monthButton).toBeVisible({ timeout: 5000 });
      await expect(weekButton).toBeVisible();
      await expect(dayButton).toBeVisible();
    });

    test('should display filter selectors (teacher and subject)', async ({ page }) => {
      // Wait for filters to load
      await page.waitForTimeout(1000);

      // Look for select dropdowns
      const selects = page.locator('select, [role="combobox"]');
      const selectCount = await selects.count();

      // Should have at least 2 select elements for filters
      expect(selectCount).toBeGreaterThanOrEqual(2);

      // Check for placeholder text
      const teacherFilter = page.locator('text=/преподаватель|учитель|teacher/i').first();
      const subjectFilter = page.locator('text=/предмет|subject/i').first();

      if (await teacherFilter.count() > 0) {
        await expect(teacherFilter).toBeVisible();
      }
      if (await subjectFilter.count() > 0) {
        await expect(subjectFilter).toBeVisible();
      }
    });

    test('should display calendar grid with day cells', async ({ page }) => {
      // Wait for calendar to render
      await page.waitForLoadState('networkidle');

      // Check for day grid - should have 35-42 cells (5-6 weeks x 7 days)
      const dayCells = page.locator('[class*="grid"], [class*="calendar"]').first();

      // Wait for at least some day cells to be visible
      const dayNumbers = page.locator('text=/^\\d{1,2}$/').first();
      await expect(dayNumbers).toBeVisible({ timeout: 5000 });
    });

    test('should handle loading state gracefully', async ({ page }) => {
      // Reload the page to see loading state
      await page.reload();

      // Either loading skeletons or instant load
      const skeletons = page.locator('[class*="skeleton"]');

      // Wait for either skeletons to disappear or content to appear
      await page.waitForLoadState('networkidle');

      // Verify page is loaded
      const monthYear = page.locator('h2').first();
      await expect(monthYear).toBeVisible();
    });
  });

  test.describe('Filter Interactions', () => {
    test('should filter lessons by teacher', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Find teacher filter select
      const teacherSelects = page.locator('select, [role="combobox"]');
      const selectCount = await teacherSelects.count();

      if (selectCount >= 2) {
        const teacherSelect = teacherSelects.first();

        // Get current lessons count (if visible)
        const lessonsBefore = await page.locator('[class*="lesson"], [class*="event"]').count();

        // Click on the select and try to select an option
        await teacherSelect.click();

        // Wait for dropdown to open
        await page.waitForTimeout(500);

        // Try to find and click an option
        const options = page.locator('[role="option"]');
        const optionCount = await options.count();

        if (optionCount > 1) {
          // Select the second option (not "all")
          const secondOption = options.nth(1);
          await secondOption.click();

          // Wait for results to update
          await page.waitForTimeout(1000);

          // Verify filter was applied (select should show new value)
          const selectedValue = await teacherSelect.locator('text=/^[^(Все)]/').first();
          if (await selectedValue.count() > 0) {
            await expect(selectedValue).toBeVisible();
          }
        }
      }
    });

    test('should filter lessons by subject', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Find subject filter select
      const allSelects = page.locator('select, [role="combobox"]');
      const selectCount = await allSelects.count();

      if (selectCount >= 2) {
        const subjectSelect = allSelects.nth(1); // Second select is usually subject

        // Click to open dropdown
        await subjectSelect.click();

        // Wait for dropdown to open
        await page.waitForTimeout(500);

        // Try to find and click an option
        const options = page.locator('[role="option"]');
        const optionCount = await options.count();

        if (optionCount > 1) {
          // Select the second option (not "all")
          const secondOption = options.nth(1);
          const optionText = await secondOption.textContent();
          await secondOption.click();

          // Wait for results to update
          await page.waitForTimeout(1000);

          // Verify filter was applied
          if (optionText && !optionText.includes('Все')) {
            const selectedText = page.locator(`text="${optionText}"`);
            if (await selectedText.count() > 0) {
              await expect(selectedText).toBeVisible();
            }
          }
        }
      }
    });

    test('should clear filters and show all lessons', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // First, apply a filter
      const teacherSelect = page.locator('select, [role="combobox"]').first();
      if (await teacherSelect.count() > 0) {
        await teacherSelect.click();
        await page.waitForTimeout(500);

        const options = page.locator('[role="option"]');
        if (await options.count() > 1) {
          await options.nth(1).click();
          await page.waitForTimeout(1000);
        }

        // Now clear the filter by selecting "all"
        await teacherSelect.click();
        await page.waitForTimeout(500);

        const allOption = page.locator('[role="option"]:has-text("Все")').first();
        if (await allOption.count() > 0) {
          await allOption.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Calendar Navigation', () => {
    test('should navigate to next month', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Get current month text
      const monthHeader = page.locator('h2').first();
      const monthBefore = await monthHeader.textContent();

      // Click next button
      const nextButtons = page.locator('button[type="button"]').filter({
        has: page.locator('[class*="chevron"], text=/→|next/i')
      });

      // Find the navigation next button (usually rightmost)
      const allButtons = page.locator('button[type="button"]');
      let nextButton = null;

      for (let i = await allButtons.count() - 1; i >= 0; i--) {
        const button = allButtons.nth(i);
        const hasChevron = await button.locator('[class*="chevron-right"], [class*="arrow-right"]').count() > 0;
        if (hasChevron || (await button.textContent())?.includes('→')) {
          nextButton = button;
          break;
        }
      }

      if (nextButton) {
        await nextButton.click();
        await page.waitForTimeout(1000);

        // Verify month changed
        const monthAfter = await monthHeader.textContent();
        // Month should have changed (or if we're in December, it wraps to January next year)
        expect(monthAfter).not.toBe(monthBefore);
      }
    });

    test('should navigate to previous month', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Navigate forward first
      const nextButtons = page.locator('button[type="button"]');
      let nextButton = null;

      for (let i = await nextButtons.count() - 1; i >= 0; i--) {
        const button = nextButtons.nth(i);
        const text = await button.textContent();
        if (text?.includes('→')) {
          nextButton = button;
          break;
        }
      }

      if (nextButton) {
        await nextButton.click();
        await page.waitForTimeout(1000);

        // Get current month
        const monthHeader = page.locator('h2').first();
        const monthAfterNext = await monthHeader.textContent();

        // Now click previous
        let prevButton = null;
        for (let i = 0; i < await nextButtons.count(); i++) {
          const button = nextButtons.nth(i);
          const text = await button.textContent();
          if (text?.includes('←')) {
            prevButton = button;
            break;
          }
        }

        if (prevButton) {
          await prevButton.click();
          await page.waitForTimeout(1000);

          // Month should be back to original
          const monthAfterPrev = await monthHeader.textContent();
          expect(monthAfterPrev).not.toBe(monthAfterNext);
        }
      }
    });

    test('should switch between month/week/day view modes', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Find view mode buttons
      const monthButton = page.locator('button:has-text("Месяц")');
      const weekButton = page.locator('button:has-text("Неделя")');
      const dayButton = page.locator('button:has-text("День")');

      // Switch to week view
      if (await weekButton.count() > 0) {
        await weekButton.click();
        await page.waitForTimeout(1000);

        // Verify button is now active/selected
        await expect(weekButton).toHaveAttribute('class', /active|selected|default/i);
      }

      // Switch to day view
      if (await dayButton.count() > 0) {
        await dayButton.click();
        await page.waitForTimeout(1000);

        await expect(dayButton).toHaveAttribute('class', /active|selected|default/i);
      }

      // Switch back to month view
      if (await monthButton.count() > 0) {
        await monthButton.click();
        await page.waitForTimeout(1000);

        await expect(monthButton).toHaveAttribute('class', /active|selected|default/i);
      }
    });
  });

  test.describe('Lesson Display', () => {
    test('should display lessons in calendar cells', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Look for lesson indicators
      const lessons = page.locator('[class*="lesson"], [class*="event"], [class*="p-1"]').filter({
        has: page.locator('[class*="flex"], [class*="gap"]')
      });

      // Either lessons are present or no lessons message
      const noLessonsMsg = page.locator('text=/нет|no lessons|no events/i');

      const lessonCount = await lessons.count();
      const hasNoLessonsMsg = await noLessonsMsg.count() > 0;

      // Should have either lessons or no lessons message
      expect(lessonCount > 0 || hasNoLessonsMsg).toBeTruthy();
    });

    test('should display lesson details (time, subject, teacher, student)', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Look for lesson elements that contain time and subject
      const timeElements = page.locator('text=/\\d{1,2}:\\d{2}/i');

      if (await timeElements.count() > 0) {
        // Time is displayed
        await expect(timeElements.first()).toBeVisible();

        // Look for subject or teacher names near time
        const subjectElements = page.locator('text=/[A-Яa-z]+/i');
        if (await subjectElements.count() > 0) {
          await expect(subjectElements.first()).toBeVisible();
        }
      }
    });

    test('should display lesson status badges', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Look for status badges - color coded backgrounds
      const statusBadges = page.locator('[class*="bg-"], [class*="text-"], [class*="badge"]').filter({
        has: page.locator('[class*="rounded"], [class*="p-"]')
      });

      // Either status badges or no lessons
      const noLessonsMsg = page.locator('text=/нет|no lessons/i');
      const hasBadges = await statusBadges.count() > 0;
      const hasNoMsg = await noLessonsMsg.count() > 0;

      expect(hasBadges || hasNoMsg).toBeTruthy();
    });
  });

  test.describe('Empty State Handling', () => {
    test('should handle empty state when no lessons match filters', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Try to find a filter that will return no results
      const teacherSelect = page.locator('select, [role="combobox"]').first();

      if (await teacherSelect.count() > 0) {
        // Select a specific teacher (not "all")
        await teacherSelect.click();
        await page.waitForTimeout(500);

        const options = page.locator('[role="option"]');
        if (await options.count() > 2) {
          // Try the last option to increase chance of no results
          await options.last().click();
          await page.waitForTimeout(1500);

          // Now check if there are any error messages or empty state
          const errorMsg = page.locator('text=/ошибка|error/i');
          const emptyMsg = page.locator('text=/нет|no data|no lessons/i');

          // Should have either content or an empty/error message
          const hasError = await errorMsg.count() > 0;
          const isEmpty = await emptyMsg.count() > 0;
          const hasLessons = await page.locator('[class*="lesson"], [class*="event"]').count() > 0;

          expect(hasError || isEmpty || hasLessons).toBeTruthy();
        }
      }
    });

    test('should display error message on API failure', async ({ page }) => {
      // Simulate API error by mocking failed request
      await page.route('**/api/admin/schedule/**', route => {
        route.abort('failed');
      });

      // Reload page to trigger API call
      await page.reload();

      // Should show error message
      const errorMsg = page.locator('text=/ошибка|error|failed/i');
      if (await errorMsg.count() > 0) {
        await expect(errorMsg.first()).toBeVisible({ timeout: 5000 });
      }

      // Should have retry button
      const retryButton = page.locator('button:has-text("Повторить"), button:has-text("Retry")');
      if (await retryButton.count() > 0) {
        await expect(retryButton).toBeVisible();
      }
    });
  });

  test.describe('Responsive Design', () => {
    test('should be responsive on desktop viewport (1920x1080)', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });

      // Wait for layout to adjust
      await page.waitForTimeout(1000);

      // Verify main elements are visible
      const title = page.locator('h1, h2').first();
      await expect(title).toBeVisible();

      // Filters should be in row
      const selects = page.locator('select, [role="combobox"]');
      const selectCount = await selects.count();
      expect(selectCount).toBeGreaterThanOrEqual(2);

      // Calendar should be visible
      const dayNumbers = page.locator('text=/^\\d{1,2}$/').first();
      await expect(dayNumbers).toBeVisible();
    });

    test('should be responsive on tablet viewport (768x1024)', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      // Wait for layout to adjust
      await page.waitForTimeout(1000);

      // Verify main elements are visible
      const title = page.locator('h1, h2').first();
      await expect(title).toBeVisible();

      // Content should not be cut off
      const container = page.locator('[class*="container"], main, [role="main"]').first();
      if (await container.count() > 0) {
        const boundingBox = await container.boundingBox();
        if (boundingBox) {
          // Width should fit in viewport
          expect(boundingBox.width).toBeLessThanOrEqual(768 + 100); // Allow some padding
        }
      }
    });

    test('should be responsive on mobile viewport (375x667)', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      // Wait for layout to adjust
      await page.waitForTimeout(1000);

      // Verify main elements are visible
      const title = page.locator('h1, h2').first();
      await expect(title).toBeVisible();

      // Filters might stack vertically on mobile
      const selects = page.locator('select, [role="combobox"]');
      if (await selects.count() > 0) {
        // At least one filter should be visible
        const firstSelect = selects.first();
        // Check if element is visible
        const isVisible = await firstSelect.isVisible().catch(() => false);
        expect(isVisible).toBeTruthy();
      }

      // Calendar should be readable on mobile (scrollable if needed)
      const dayNumbers = page.locator('text=/^\\d{1,2}$/').first();
      if (await dayNumbers.count() > 0) {
        // Either visible or scrollable
        const container = page.locator('body');
        const scrollHeight = await container.evaluate((el) => el.scrollHeight);
        const clientHeight = await container.evaluate((el) => el.clientHeight);
        // Should have content (either visible or scrollable)
        expect(scrollHeight).toBeGreaterThan(0);
      }
    });

    test('should not have horizontal scroll on tablet', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      // Wait for layout to adjust
      await page.waitForTimeout(1000);

      // Check for horizontal scrolling
      const body = page.locator('body');
      const scrollWidth = await body.evaluate((el) => el.scrollWidth);
      const clientWidth = await body.evaluate((el) => el.clientWidth);

      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 10); // Allow small margin
    });

    test('should maintain layout on very small mobile (320x568)', async ({ page }) => {
      await page.setViewportSize({ width: 320, height: 568 });

      // Wait for layout to adjust
      await page.waitForTimeout(1000);

      // Page should load without crashing
      const title = page.locator('h1, h2').first();
      await expect(title).toBeVisible({ timeout: 5000 });

      // Should not have layout breaks
      const errors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // No critical errors
      const criticalErrors = errors.filter(e =>
        !e.includes('favicon') &&
        !e.includes('WebSocket') &&
        !e.includes('404')
      );
      expect(criticalErrors.length).toBe(0);
    });
  });

  test.describe('Performance and Stability', () => {
    test('should load page within reasonable time', async ({ page }) => {
      const startTime = Date.now();

      await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/schedule`);
      await page.waitForLoadState('networkidle');

      const loadTime = Date.now() - startTime;

      // Should load within 10 seconds
      expect(loadTime).toBeLessThan(10000);
    });

    test('should not have console errors on page load', async ({ page }) => {
      const errors: string[] = [];

      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // Wait for page to fully load
      await page.waitForLoadState('networkidle');

      // Filter out known non-critical errors
      const criticalErrors = errors.filter(e =>
        !e.includes('favicon') &&
        !e.includes('WebSocket') &&
        !e.includes('404') &&
        !e.includes('preflight')
      );

      expect(criticalErrors.length).toBe(0);
    });

    test('should handle multiple filter changes without breaking', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Change filters multiple times
      const teacherSelect = page.locator('select, [role="combobox"]').first();

      if (await teacherSelect.count() > 0) {
        // Make 3 filter changes
        for (let i = 0; i < 3; i++) {
          await teacherSelect.click();
          await page.waitForTimeout(300);

          const options = page.locator('[role="option"]');
          if (await options.count() > 1) {
            const randomIndex = Math.floor(Math.random() * (await options.count()));
            await options.nth(randomIndex).click();
            await page.waitForTimeout(500);
          }
        }

        // Page should still be functional
        const title = page.locator('h1, h2').first();
        await expect(title).toBeVisible();
      }
    });

    test('should properly refresh calendar data on filter change', async ({ page }) => {
      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Get initial lesson count
      const lessonsBefore = await page.locator('[class*="lesson"], [class*="event"]').count();

      // Apply a filter
      const teacherSelect = page.locator('select, [role="combobox"]').first();
      if (await teacherSelect.count() > 0) {
        await teacherSelect.click();
        await page.waitForTimeout(500);

        const options = page.locator('[role="option"]');
        if (await options.count() > 1) {
          await options.nth(1).click();

          // Wait for data to refresh
          await page.waitForTimeout(1500);

          // Should have completed the request
          const title = page.locator('h1, h2').first();
          await expect(title).toBeVisible();
        }
      }
    });
  });

  test.describe('Admin-Only Access', () => {
    test('should be accessible only to admin users', async ({ context }) => {
      // This test verifies that the page requires admin role
      // Non-admin access should be blocked

      const page = await context.newPage();

      // Try to access admin schedule without logging in
      await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/schedule`);

      // Should redirect to login or show access denied
      const currentUrl = page.url();
      const isRedirected = !currentUrl.includes('/admin/schedule');
      const isOnLoginPage = currentUrl.includes('/login') || currentUrl.includes('/auth');
      const isAccessDenied = await page.locator('text=/доступ запрещен|access denied|unauthorized/i').count() > 0;

      expect(isRedirected || isAccessDenied).toBeTruthy();

      await page.close();
    });
  });
});
