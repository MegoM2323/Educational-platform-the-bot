import { test, expect } from '@playwright/test';

// Helper function to generate unique email
function generateTestEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}@test.com`;
}

test.describe('Application Form E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/application');
    await expect(page.locator('text=Личная информация')).toBeVisible({ timeout: 10000 });
  });

  test('Test 1: Empty form cannot proceed', async ({ page }) => {
    // Check that button is disabled when form is empty
    const nextButton = page.locator('button:has-text("Далее")');

    // Wait a bit for form to fully load
    await page.waitForTimeout(500);

    // Button might be disabled or click will show error
    const isDisabled = await nextButton.isDisabled();
    expect(isDisabled).toBe(true);

    console.log('Test 3 PASSED: Empty form cannot proceed');
  });

  test('Test 3: Auto-save and localStorage recovery', async ({ page }) => {
    const testData = {
      firstName: 'Петр',
      lastName: 'Сидоров',
      email: generateTestEmail('test-autosave'),
      phone: '+79991234567'
    };

    // Fill form
    await page.fill('input[id="firstName"]', testData.firstName);
    await page.fill('input[id="lastName"]', testData.lastName);
    await page.fill('input[id="email"]', testData.email);
    await page.fill('input[id="phone"]', testData.phone);

    await page.waitForTimeout(500);

    // Reload page
    await page.reload();
    await expect(page.locator('text=Личная информация')).toBeVisible({ timeout: 10000 });

    // Verify data restored from localStorage
    expect(await page.inputValue('input[id="firstName"]')).toBe(testData.firstName);
    expect(await page.inputValue('input[id="lastName"]')).toBe(testData.lastName);
    expect(await page.inputValue('input[id="email"]')).toBe(testData.email);

    const phoneValue = await page.inputValue('input[id="phone"]');
    expect(phoneValue).toContain('7999');

    console.log('Test 5 PASSED: Auto-save and localStorage recovery working');
  });

  test('Test 6: Clear saved data button functionality', async ({ page }) => {
    // Fill some data
    await page.fill('input[id="firstName"]', 'Тест');
    await page.fill('input[id="lastName"]', 'Тестов');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="phone"]', '+79999999999');

    await page.waitForTimeout(500);

    // Click clear button if visible
    const clearButton = page.locator('button:has-text("Очистить сохраненные данные")');

    if (await clearButton.isVisible()) {
      await clearButton.click();

      // Verify success message
      await expect(page.locator('text=удалены')).toBeVisible({ timeout: 5000 });

      // Verify fields cleared
      expect(await page.inputValue('input[id="firstName"]')).toBe('');
      expect(await page.inputValue('input[id="lastName"]')).toBe('');

      console.log('Test 6 PASSED: Clear saved data button works');
    } else {
      console.log('Test 6 SKIPPED: Clear button not visible');
    }
  });

  test('Test 7: Back button navigation between steps', async ({ page }) => {
    // Fill Step 1
    await page.fill('input[id="firstName"]', 'Иван');
    await page.fill('input[id="lastName"]', 'Петров');
    await page.fill('input[id="email"]', generateTestEmail('test'));
    await page.fill('input[id="phone"]', '+79999999999');

    // Go to Step 2
    await page.click('button:has-text("Далее")');
    await expect(page.locator('text=Тип заявки')).toBeVisible();

    // Go back to Step 1
    await page.click('button:has-text("Назад")');
    await expect(page.locator('text=Личная информация')).toBeVisible();

    // Data should be preserved
    expect(await page.inputValue('input[id="firstName"]')).toBe('Иван');

    console.log('Test 7 PASSED: Back button navigation works correctly');
  });

  test('Test 8: Mobile viewport responsiveness', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Form should be visible
    await expect(page.locator('text=Личная информация')).toBeVisible();

    // Fill form
    await page.fill('input[id="firstName"]', 'Иван');
    await page.fill('input[id="lastName"]', 'Петров');
    await page.fill('input[id="email"]', generateTestEmail('test-mobile'));
    await page.fill('input[id="phone"]', '+79999999999');

    // Navigation should work
    await page.click('button:has-text("Далее")');
    await expect(page.locator('text=Тип заявки')).toBeVisible({ timeout: 5000 });

    console.log('Test 8 PASSED: Mobile viewport works correctly');
  });

  test('Test 9: Telegram ID field is optional', async ({ page }) => {
    const testEmail = generateTestEmail('test-telegram');

    // Fill required fields only
    await page.fill('input[id="firstName"]', 'Иван');
    await page.fill('input[id="lastName"]', 'Петров');
    await page.fill('input[id="email"]', testEmail);
    await page.fill('input[id="phone"]', '+79999999999');

    // Leave Telegram empty
    const telegramInput = page.locator('input[id="telegramId"]');
    expect(await telegramInput.inputValue()).toBe('');

    // Should still be able to proceed
    await page.click('button:has-text("Далее")');
    await expect(page.locator('text=Тип заявки')).toBeVisible({ timeout: 5000 });

    console.log('Test 9 PASSED: Telegram ID field is optional');
  });

  test('Test 10: Back button is disabled on Step 1', async ({ page }) => {
    const backButton = page.locator('button:has-text("Назад")');

    // Check if disabled on initial load
    const isDisabled = await backButton.isDisabled();
    expect(isDisabled).toBe(true);

    console.log('Test 10 PASSED: Back button correctly disabled on Step 1');
  });

  test('Test 11: Special characters in names are handled', async ({ page }) => {
    const email = generateTestEmail('test-special');

    // Test with special characters
    await page.fill('input[id="firstName"]', 'Иван-Петр');
    await page.fill('input[id="lastName"]', "О'Коннор");
    await page.fill('input[id="email"]', email);
    await page.fill('input[id="phone"]', '+79999999999');

    // Values should be preserved
    expect(await page.inputValue('input[id="firstName"]')).toBe('Иван-Петр');
    expect(await page.inputValue('input[id="lastName"]')).toBe("О'Коннор");

    console.log('Test 11 PASSED: Special characters handled correctly');
  });

  test('Test 12: Whitespace handling in form fields', async ({ page }) => {
    const email = generateTestEmail('test-whitespace');

    // Fill with leading/trailing spaces
    await page.fill('input[id="firstName"]', '  Иван  ');
    await page.fill('input[id="lastName"]', '  Петров  ');
    await page.fill('input[id="email"]', email);
    await page.fill('input[id="phone"]', '  +79999999999  ');

    // Values should be captured
    expect(await page.inputValue('input[id="firstName"]')).toBeTruthy();
    expect(await page.inputValue('input[id="lastName"]')).toBeTruthy();

    console.log('Test 12 PASSED: Whitespace handled correctly');
  });

  test('Test 13: Grade dropdown opens and has options', async ({ page }) => {
    const email = generateTestEmail('test-grades');

    // Fill Step 1
    await page.fill('input[id="firstName"]', 'Иван');
    await page.fill('input[id="lastName"]', 'Петров');
    await page.fill('input[id="email"]', email);
    await page.fill('input[id="phone"]', '+79999999999');

    await page.click('button:has-text("Далее")');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Space');
    await page.click('button:has-text("Далее")');

    // Open grade dropdown
    const gradeButton = page.locator('button:has-text("Выберите класс")');
    await gradeButton.click();

    // Check that dropdown opened (has options)
    const options = page.locator('[role="option"]');
    const count = await options.count();
    expect(count).toBeGreaterThan(0);

    console.log('Test 13 PASSED: Grade dropdown has options');
  });
});
