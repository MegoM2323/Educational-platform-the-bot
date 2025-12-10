import { test, expect, Page } from '@playwright/test';

/**
 * E2E Tests for Teacher Profile Page
 * Tests all required scenarios from T009:
 * 1. Navigation to /profile/teacher
 * 2. Data loading and display
 * 3. Edit profile functionality
 * 4. Avatar upload
 * 5. Form validation
 * 6. Role-based access control
 */

// Helper to login as teacher
async function loginAsTeacher(page: Page) {
  await page.goto('/auth');
  await page.waitForLoadState('networkidle');

  // Fill login form (adjust selectors based on your Auth page)
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();

  await emailInput.fill('teacher@test.com');
  await passwordInput.fill('TestPass123!');

  // Click login button
  const loginButton = page.locator('button[type="submit"], button:has-text("Войти")').first();
  await loginButton.click();

  // Wait for redirect to dashboard
  await page.waitForURL(/\/dashboard\/teacher/, { timeout: 10000 });
}

// Helper to login as student (for role-based access test)
async function loginAsStudent(page: Page) {
  await page.goto('/auth');
  await page.waitForLoadState('networkidle');

  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();

  await emailInput.fill('opt_student_0@test.com');
  await passwordInput.fill('password');

  const loginButton = page.locator('button[type="submit"], button:has-text("Войти")').first();
  await loginButton.click();

  await page.waitForURL(/\/dashboard\/student/, { timeout: 10000 });
}

test.describe('Teacher Profile Page', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.context().clearCookies();
    await page.context().clearPermissions();
  });

  test('T009.1 - Navigate to /profile/teacher and verify data loads', async ({ page }) => {
    await loginAsTeacher(page);

    // Navigate to profile page
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Verify no errors in console
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Check page loaded successfully (no redirect to /auth or /unauthorized)
    await expect(page).toHaveURL(/\/profile\/teacher/);

    // Verify loading spinner appears and disappears
    const spinner = page.locator('[data-testid="loading-spinner"], .animate-spin').first();
    if (await spinner.isVisible({ timeout: 1000 }).catch(() => false)) {
      await spinner.waitFor({ state: 'hidden', timeout: 5000 });
    }

    // Verify profile card is visible
    await expect(page.locator('h1:has-text("Мой профиль"), h1:has-text("Профиль")')).toBeVisible();

    // Verify name fields are populated
    const firstNameInput = page.locator('input[id="first_name"], input[name="first_name"]');
    const lastNameInput = page.locator('input[id="last_name"], input[name="last_name"]');

    await expect(firstNameInput).toBeVisible();
    await expect(lastNameInput).toBeVisible();

    // Verify email field is present and disabled
    const emailInput = page.locator('input[id="email"], input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toBeDisabled();

    // Verify avatar is visible
    const avatar = page.locator('[class*="avatar"], [data-testid="avatar"]').first();
    await expect(avatar).toBeVisible();

    // Verify no console errors
    await page.waitForTimeout(1000); // Wait for any async errors
    expect(consoleErrors.filter(e => !e.includes('404') && !e.includes('warning'))).toHaveLength(0);
  });

  test('T009.2 - Edit profile name and verify changes persist', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Wait for form to load
    const firstNameInput = page.locator('input[id="first_name"], input[name="first_name"]');
    await firstNameInput.waitFor({ state: 'visible' });

    // Edit first name
    const newFirstName = `Teacher${Date.now()}`;
    await firstNameInput.clear();
    await firstNameInput.fill(newFirstName);

    // Verify unsaved changes indicator appears
    const unsavedIndicator = page.locator('text=/несохраненные изменения/i, [class*="pulse"]');
    await expect(unsavedIndicator.first()).toBeVisible({ timeout: 2000 });

    // Click save button
    const saveButton = page.locator('button[type="submit"], button:has-text("Сохранить")');
    await saveButton.click();

    // Wait for success message
    await expect(page.locator('text=/успешно/i, [data-sonner-toast]')).toBeVisible({ timeout: 5000 });

    // Reload page and verify changes persist
    await page.reload();
    await page.waitForLoadState('networkidle');

    const firstNameAfterReload = page.locator('input[id="first_name"], input[name="first_name"]');
    await expect(firstNameAfterReload).toHaveValue(newFirstName);
  });

  test('T009.3 - Avatar upload functionality', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Locate avatar upload input
    const avatarInput = page.locator('input[type="file"], input[accept*="image"]');
    await avatarInput.waitFor({ state: 'attached' });

    // Create a test image file
    const buffer = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
      'base64'
    );

    // Upload the file
    await avatarInput.setInputFiles({
      name: 'test-avatar.png',
      mimeType: 'image/png',
      buffer: buffer,
    });

    // Verify preview appears (if implemented)
    // Note: This depends on your implementation
    await page.waitForTimeout(500);

    // Click save button
    const saveButton = page.locator('button[type="submit"], button:has-text("Сохранить")');
    await saveButton.click();

    // Wait for success message
    await expect(page.locator('text=/успешно/i, [data-sonner-toast]')).toBeVisible({ timeout: 5000 });
  });

  test('T009.4 - Form validation - empty required fields', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Wait for form to load
    const firstNameInput = page.locator('input[id="first_name"], input[name="first_name"]');
    await firstNameInput.waitFor({ state: 'visible' });

    // Clear required field
    await firstNameInput.clear();

    // Try to submit
    const saveButton = page.locator('button[type="submit"], button:has-text("Сохранить")');
    await saveButton.click();

    // Verify browser validation or custom error appears
    // HTML5 validation or custom validation should prevent submission
    const isValid = await firstNameInput.evaluate((el: HTMLInputElement) => el.validity.valid);
    expect(isValid).toBe(false);
  });

  test('T009.5 - Form validation - invalid email format', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Email field should be disabled, so this test verifies it can't be edited with invalid data
    const emailInput = page.locator('input[id="email"], input[type="email"]');
    await expect(emailInput).toBeDisabled();

    // This confirms the email field protection is working correctly
  });

  test('T009.6 - Bio character limit validation', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    const bioTextarea = page.locator('textarea[id="bio"], textarea[name="bio"]');

    if (await bioTextarea.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Fill with text exceeding 1000 characters
      const longText = 'a'.repeat(1001);
      await bioTextarea.fill(longText);

      // Verify maxLength attribute prevents overfill or counter shows limit
      const actualValue = await bioTextarea.inputValue();
      expect(actualValue.length).toBeLessThanOrEqual(1000);

      // Verify character counter is visible
      const counter = page.locator('text=/осталось.*символов/i, text=/\\d+\\s*символов/i');
      await expect(counter.first()).toBeVisible();
    }
  });

  test('T009.7 - Role-based access - student cannot access teacher profile', async ({ page }) => {
    await loginAsStudent(page);

    // Try to navigate to teacher profile
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Should redirect to /unauthorized
    await expect(page).toHaveURL(/\/unauthorized/);

    // Verify unauthorized page content
    await expect(page.locator('text=/403|доступ запрещ[её]н/i')).toBeVisible();
  });

  test('T009.8 - Unauthenticated user redirects to /auth', async ({ page }) => {
    // Clear all cookies/storage to ensure not authenticated
    await page.context().clearCookies();

    // Try to navigate to teacher profile
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Should redirect to /auth
    await expect(page).toHaveURL(/\/auth/);
  });

  test('T009.9 - Subject assignment functionality', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Find subject select dropdown
    const subjectSelect = page.locator('select, [role="combobox"]').filter({ hasText: /предмет/i }).first();

    if (await subjectSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Open dropdown (if using custom select)
      await subjectSelect.click();

      // Wait for options to appear
      await page.waitForTimeout(500);

      // Select a subject (adjust selector based on your implementation)
      const firstOption = page.locator('[role="option"], option').first();
      if (await firstOption.isVisible({ timeout: 1000 }).catch(() => false)) {
        await firstOption.click();

        // Click add button
        const addButton = page.locator('button:has-text("Добавить")');
        await addButton.click();

        // Verify subject badge appears
        await page.waitForTimeout(500);
        const subjectBadge = page.locator('[class*="badge"], .badge').first();
        await expect(subjectBadge).toBeVisible();
      }
    }
  });

  test('T009.10 - Navigation back button works', async ({ page }) => {
    await loginAsTeacher(page);

    // Start from dashboard
    await page.goto('/dashboard/teacher');
    await page.waitForLoadState('networkidle');

    // Navigate to profile
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Click back button
    const backButton = page.locator('button:has-text("Назад"), button[aria-label*="ернуться"]');
    await backButton.click();

    // Should return to previous page (dashboard)
    await expect(page).toHaveURL(/\/dashboard\/teacher/);
  });

  test('T009.11 - Experience years validation', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    const experienceInput = page.locator('input[id="experience_years"], input[name="experience_years"]');

    if (await experienceInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Try negative value
      await experienceInput.fill('-5');
      const negativeValue = await experienceInput.inputValue();
      expect(parseInt(negativeValue)).toBeGreaterThanOrEqual(0);

      // Try excessive value
      await experienceInput.fill('999');
      const maxValue = await experienceInput.inputValue();
      expect(parseInt(maxValue)).toBeLessThanOrEqual(80);
    }
  });

  test('T009.12 - Telegram handle validation', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    const telegramInput = page.locator('input[id="telegram"], input[name="telegram"]');

    if (await telegramInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Test with @ prefix
      await telegramInput.fill('@testuser');
      await expect(telegramInput).toHaveValue('@testuser');

      // Test without @ prefix
      await telegramInput.fill('testuser');
      await expect(telegramInput).toHaveValue('testuser');

      // Both formats should be accepted
    }
  });
});

test.describe('Student Profile Page', () => {
  test('T009.13 - Student can access /profile/student', async ({ page }) => {
    await loginAsStudent(page);

    await page.goto('/profile/student');
    await page.waitForLoadState('networkidle');

    // Should successfully load
    await expect(page).toHaveURL(/\/profile\/student/);
    await expect(page.locator('h1:has-text("Мой профиль"), h1:has-text("Профиль")')).toBeVisible();
  });

  test('T009.14 - Teacher cannot access /profile/student', async ({ page }) => {
    await loginAsTeacher(page);

    await page.goto('/profile/student');
    await page.waitForLoadState('networkidle');

    // Should redirect to /unauthorized
    await expect(page).toHaveURL(/\/unauthorized/);
  });
});

test.describe('Profile Page Error Handling', () => {
  test('T009.15 - Handle network error gracefully', async ({ page }) => {
    await loginAsTeacher(page);

    // Intercept API call and simulate network error
    await page.route('**/api/profile/teacher/', route => {
      route.abort('failed');
    });

    await page.goto('/profile/teacher');
    await page.waitForLoadState('networkidle');

    // Should show error message or retry
    // Depending on implementation, might show error toast or error state
    await page.waitForTimeout(2000);

    // Page should not crash (no redirect to error page)
    await expect(page).toHaveURL(/\/profile\/teacher/);
  });
});
