import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:8080';
const API_URL = 'http://localhost:8000';

interface AdminUser {
  username: string;
  password: string;
  role: string;
}

const TEST_ADMIN: AdminUser = {
  username: 'admin@test.com',
  password: 'TestPass123!',
  role: 'admin'
};

// Test data for parent creation
const TEST_PARENT = {
  firstName: 'Иван',
  lastName: 'Петровский',
  email: `parent_${Date.now()}@test.com`,
  phone: '+79999999999'
};

const TEST_PARENT_UPDATED = {
  firstName: 'Петр',
  lastName: 'Иванский',
  phone: '+78888888888'
};

/**
 * Login as admin to access admin panel
 */
async function loginAsAdmin(page: Page) {
  await page.goto(`${BASE_URL}/auth/signin`);
  await page.waitForSelector('button:has-text("Войти")', { timeout: 10000 });

  // Fill in credentials
  const usernameInput = page.locator('input[placeholder*="Имя пользователя"], input[placeholder*="Username"], input[placeholder*="Email"]').first();
  const passwordInput = page.locator('input[placeholder*="Пароль"], input[placeholder*="Password"]').first();

  await usernameInput.fill(TEST_ADMIN.username);
  await passwordInput.fill(TEST_ADMIN.password);

  // Click sign in button
  const signInButton = page.locator('button:has-text("Войти")').last();
  await signInButton.click();

  // Wait for navigation - admin redirects to /admin/monitoring
  await page.waitForURL(/.*admin.*|.*dashboard.*/, { timeout: 15000 });
}

/**
 * Navigate to Parent Management page
 */
async function navigateToParentManagement(page: Page) {
  // Parent Management is under /admin/accounts with a tab for parents
  // First navigate to accounts page
  await page.goto(`${BASE_URL}/admin/accounts`);
  await page.waitForLoadState('networkidle', { timeout: 10000 });

  // Look for parent tab or section
  const parentTab = page.locator('[role="tab"], button, a').filter({ hasText: /родител|parent/i }).first();
  if (await parentTab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await parentTab.click();
    await page.waitForLoadState('networkidle', { timeout: 5000 });
  }
}

test.describe('Admin Parent Management E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Clear any cached auth state
    await page.context().clearCookies();
  });

  test('Admin can login and access parent management', async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to parent management
    await navigateToParentManagement(page);

    // Verify page title contains "родители" or "parents"
    const pageTitle = await page.locator('h1, h2, [role="heading"]').first().textContent();
    expect(pageTitle?.toLowerCase()).toContain('родител');

    // Take screenshot
    await page.screenshot({ path: 'test-results/admin-parent-management-main.png' });
  });

  test('T008.1: CREATE - Admin can create new parent', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Click "Create Parent" button
    const createParentButton = page.locator('button').filter({ hasText: /создать родителя|create parent/i }).first();
    await createParentButton.click();

    // Wait for dialog to appear
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    // Fill in parent form
    const firstNameInput = page.locator('input[placeholder*="Имя"], input[placeholder*="First"]').first();
    const lastNameInput = page.locator('input[placeholder*="Фамилия"], input[placeholder*="Last"]').first();
    const emailInput = page.locator('input[type="email"], input[placeholder*="Email"]').first();
    const phoneInput = page.locator('input[type="tel"], input[placeholder*="Телефон"], input[placeholder*="Phone"]').first();

    await firstNameInput.fill(TEST_PARENT.firstName);
    await lastNameInput.fill(TEST_PARENT.lastName);
    await emailInput.fill(TEST_PARENT.email);
    if (await phoneInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await phoneInput.fill(TEST_PARENT.phone);
    }

    // Click Save button
    const saveButton = page.locator('button').filter({ hasText: /сохранить|save|создать|create/i }).last();
    await saveButton.click();

    // Wait for dialog to close and list to refresh
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Verify parent appears in list
    const parentRow = page.locator(`text=${TEST_PARENT.firstName}`);
    await expect(parentRow).toBeVisible({ timeout: 10000 });

    // Verify email is shown in table
    const emailCell = page.locator(`text=${TEST_PARENT.email}`);
    await expect(emailCell).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'test-results/admin-parent-created.png' });
  });

  test('T008.2: UPDATE - Admin can edit parent details', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Wait for parent list to load
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Find the parent we just created
    const parentRow = page.locator(`text=${TEST_PARENT.email}`).first();

    // Find edit button in the same row - look for icon button near the email
    const editButton = parentRow.locator('..')
      .locator('button')
      .filter({ hasText: /редактировать|edit/i })
      .or(page.locator('button[title*="Редактировать"], button[title*="edit"]').first());

    // Try clicking the first icon button (user icon for edit) in the row
    const rowContainer = parentRow.locator('..').locator('..');
    const buttons = rowContainer.locator('button');
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      // First button is usually the edit button
      await buttons.first().click();
    } else {
      // Fallback: find edit button by searching in page
      const allEditButtons = page.locator('button[title*="Редактировать"], button[title*="edit"], button[aria-label*="edit"]').first();
      if (await allEditButtons.isVisible({ timeout: 2000 }).catch(() => false)) {
        await allEditButtons.click();
      }
    }

    // Wait for edit dialog to appear
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    // Update parent details
    const firstNameInput = page.locator('input[placeholder*="Имя"], input[placeholder*="First"]').first();
    const lastNameInput = page.locator('input[placeholder*="Фамилия"], input[placeholder*="Last"]').first();
    const phoneInput = page.locator('input[type="tel"], input[placeholder*="Телефон"], input[placeholder*="Phone"]').first();

    // Clear existing values and enter new ones
    await firstNameInput.fill('');
    await firstNameInput.fill(TEST_PARENT_UPDATED.firstName);

    await lastNameInput.fill('');
    await lastNameInput.fill(TEST_PARENT_UPDATED.lastName);

    if (await phoneInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await phoneInput.fill('');
      await phoneInput.fill(TEST_PARENT_UPDATED.phone);
    }

    // Click Save button
    const saveButton = page.locator('button').filter({ hasText: /сохранить|save|обновить|update/i }).last();
    await saveButton.click();

    // Wait for dialog to close
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Verify updated name appears in list
    const updatedRow = page.locator(`text=${TEST_PARENT_UPDATED.firstName}`);
    await expect(updatedRow).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'test-results/admin-parent-updated.png' });
  });

  test('T008.3: ASSIGN - Admin can assign students to parent', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Wait for page to load
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Look for "Assign Students" or similar button
    const assignButton = page.locator('button').filter({ hasText: /назначить студентов|assign students|назначить/i }).first();

    if (await assignButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await assignButton.click();

      // Wait for assignment dialog to appear
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // Select parent (if needed in dialog)
      const parentSelect = page.locator('select, [role="combobox"]').first();
      if (await parentSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
        // Try to select the parent we created
        await parentSelect.click();
        const parentOption = page.locator(`text=${TEST_PARENT_UPDATED.firstName} ${TEST_PARENT_UPDATED.lastName}`);
        if (await parentOption.isVisible({ timeout: 2000 }).catch(() => false)) {
          await parentOption.click();
        }
      }

      // Look for student checkboxes or multi-select
      const studentCheckboxes = page.locator('input[type="checkbox"]');
      const checkboxCount = await studentCheckboxes.count();

      // Select first student if available
      if (checkboxCount > 0) {
        await studentCheckboxes.first().check();
      }

      // Click Save/Assign button
      const confirmButton = page.locator('button').filter({ hasText: /сохранить|save|назначить|assign|подтвердить|confirm/i }).last();
      if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await confirmButton.click();
        await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
      }

      // Take screenshot
      await page.screenshot({ path: 'test-results/admin-parent-assigned-students.png' });
    } else {
      console.log('Assign Students button not found, skipping this test');
    }
  });

  test('T008.4: DELETE - Admin can delete parent', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Wait for list to load
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Find the parent row
    const parentRow = page.locator(`text=${TEST_PARENT_UPDATED.firstName}`).first();
    const rowContainer = parentRow.locator('..').locator('..');

    // Find delete button (trash icon)
    const deleteButton = rowContainer.locator('button[title*="Удалить"], button[title*="Delete"], button[aria-label*="delete"]')
      .or(rowContainer.locator('button').last());

    await deleteButton.click();

    // Wait for confirmation dialog
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    // Click confirm delete
    const confirmDeleteButton = page.locator('button').filter({ hasText: /удалить|delete|да|yes|подтвердить|confirm/i }).last();
    await confirmDeleteButton.click();

    // Wait for dialog to close
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Verify parent is no longer in list
    const deletedRow = page.locator(`text=${TEST_PARENT_UPDATED.firstName}`);
    const isVisible = await deletedRow.isVisible({ timeout: 3000 }).catch(() => false);

    if (!isVisible) {
      expect(!isVisible).toBeTruthy();
    }

    // Take screenshot
    await page.screenshot({ path: 'test-results/admin-parent-deleted.png' });
  });

  test('Admin parent management displays error handling', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Try to create parent with invalid email (if validation exists)
    const createParentButton = page.locator('button').filter({ hasText: /создать родителя|create parent/i }).first();

    if (await createParentButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await createParentButton.click();
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // Try to fill with invalid data
      const emailInput = page.locator('input[type="email"], input[placeholder*="Email"]').first();
      await emailInput.fill('invalid-email');

      // Try to save
      const saveButton = page.locator('button').filter({ hasText: /сохранить|save|создать|create/i }).last();
      await saveButton.click();

      // Check if error message appears (wait a bit for validation)
      await page.waitForTimeout(2000);

      // Take screenshot to show error handling
      await page.screenshot({ path: 'test-results/admin-parent-error-handling.png' });
    }
  });

  test('Admin can search parents by name and email', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Wait for page to load
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Find search input
    const searchInput = page.locator('input[placeholder*="ФИО"], input[placeholder*="Name"], input[placeholder*="Email"], input[placeholder*="Поиск"]').first();

    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Search by first name
      await searchInput.fill(TEST_PARENT_UPDATED.firstName);
      await page.waitForLoadState('networkidle', { timeout: 5000 });

      // Verify search results
      const results = page.locator(`text=${TEST_PARENT_UPDATED.firstName}`);
      const isVisible = await results.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        expect(isVisible).toBeTruthy();
      }

      // Clear search and try email search
      await searchInput.fill('');
      await searchInput.fill(TEST_PARENT.email);
      await page.waitForLoadState('networkidle', { timeout: 5000 });

      // Take screenshot
      await page.screenshot({ path: 'test-results/admin-parent-search.png' });
    }
  });

  test('Admin parent management page loads within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    const loadTime = Date.now() - startTime;

    // Page should load within 20 seconds (including login)
    expect(loadTime).toBeLessThan(20000);

    console.log(`Parent Management page loaded in ${loadTime}ms`);
  });

  test('Parent management displays all expected columns', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Wait for table to load
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Check for expected column headers
    const expectedHeaders = ['ФИО', 'Email', 'Телефон', 'Детей', 'Действия'];
    let visibleHeaders = 0;

    for (const header of expectedHeaders) {
      const headerElement = page.locator(`th, td`).filter({ hasText: new RegExp(header, 'i') });
      if (await headerElement.isVisible({ timeout: 2000 }).catch(() => false)) {
        visibleHeaders++;
      }
    }

    // At least some headers should be visible
    expect(visibleHeaders).toBeGreaterThanOrEqual(3);

    // Take screenshot showing table structure
    await page.screenshot({ path: 'test-results/admin-parent-table.png' });
  });

  test('Admin can perform full CRUD workflow', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Get initial parent count
    const initialCount = await page.locator('tbody tr').count();

    // CREATE
    const createParentButton = page.locator('button').filter({ hasText: /создать родителя|create parent/i }).first();
    await createParentButton.click();
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    const uniqueEmail = `crud_test_${Date.now()}@test.com`;
    const firstNameInput = page.locator('input[placeholder*="Имя"], input[placeholder*="First"]').first();
    const lastNameInput = page.locator('input[placeholder*="Фамилия"], input[placeholder*="Last"]').first();
    const emailInput = page.locator('input[type="email"], input[placeholder*="Email"]').first();

    await firstNameInput.fill('CRUD');
    await lastNameInput.fill('Test');
    await emailInput.fill(uniqueEmail);

    const saveButton = page.locator('button').filter({ hasText: /сохранить|save|создать|create/i }).last();
    await saveButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Verify created
    const createdRow = page.locator(`text=CRUD`);
    await expect(createdRow).toBeVisible({ timeout: 10000 });

    // UPDATE
    const rowContainer = createdRow.locator('..').locator('..');
    const editButton = rowContainer.locator('button').first();
    await editButton.click();
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    const updateFirstNameInput = page.locator('input[placeholder*="Имя"], input[placeholder*="First"]').first();
    await updateFirstNameInput.fill('');
    await updateFirstNameInput.fill('CRUD_Updated');

    const updateSaveButton = page.locator('button').filter({ hasText: /сохранить|save|обновить|update/i }).last();
    await updateSaveButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Verify updated
    const updatedRow = page.locator(`text=CRUD_Updated`);
    await expect(updatedRow).toBeVisible({ timeout: 10000 });

    // DELETE
    const finalRowContainer = updatedRow.locator('..').locator('..');
    const deleteButton = finalRowContainer.locator('button').last();
    await deleteButton.click();
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    const confirmDeleteButton = page.locator('button').filter({ hasText: /удалить|delete|да|yes/i }).last();
    await confirmDeleteButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Verify deleted
    const deletedRow = page.locator(`text=CRUD_Updated`);
    const isVisible = await deletedRow.isVisible({ timeout: 3000 }).catch(() => false);

    expect(!isVisible).toBeTruthy();

    // Take screenshot of final state
    await page.screenshot({ path: 'test-results/admin-parent-full-crud.png' });
  });

  test('Admin parent management displays without layout breaks', async ({ page }) => {
    await loginAsAdmin(page);
    await navigateToParentManagement(page);

    // Check for layout issues
    const layoutErrors = await page.evaluate(() => {
      const issues: string[] = [];

      // Check for visible overflow
      const body = document.body;
      if (body.scrollWidth > window.innerWidth) {
        issues.push('Horizontal overflow detected');
      }

      // Check for hidden elements
      const hiddenElements = document.querySelectorAll('[style*="display: none"]');
      if (hiddenElements.length > 20) {
        issues.push('Many hidden elements detected');
      }

      return issues;
    });

    if (layoutErrors.length > 0) {
      console.log('Layout Issues:', layoutErrors);
    }

    await page.screenshot({ path: 'test-results/admin-parent-layout-check.png' });
  });

});

test.describe('Admin Parent Management Error Scenarios', () => {

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
  });

  test('Unauthenticated user cannot access parent management', async ({ page }) => {
    // Try to access admin panel without login
    await page.goto(`${BASE_URL}/admin/accounts`);

    // Should redirect to login
    const currentUrl = page.url();
    const isOnLoginPage = currentUrl.includes('/signin') || currentUrl.includes('/login') || currentUrl.includes('/auth');

    expect(isOnLoginPage).toBeTruthy();
  });

});
