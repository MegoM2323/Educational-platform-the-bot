import { test, expect } from '@playwright/test';

test.describe('Admin Panel Logout', () => {
  test('should logout from StaffManagement page', async ({ page }) => {
    // 1. Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // 2. Login as admin
    await page.getByTestId('login-email-input').fill('admin@test.com');
    await page.getByTestId('login-password-input').fill('TestPass123!');
    await page.getByTestId('login-submit-button').click();

    // 3. Wait for redirect to admin panel
    await page.waitForURL('**/admin/staff', { timeout: 15000 });
    await expect(page).toHaveURL(/\/admin\/staff/);

    // 4. Verify page title
    await expect(page.locator('text=Управление преподавателями')).toBeVisible();

    // 5. Find and click logout button
    const logoutButton = page.locator('button:has-text("Выйти")').first();
    await expect(logoutButton).toBeVisible();
    await logoutButton.click();

    // 6. Verify redirect to auth page
    await page.waitForURL('**/auth', { timeout: 5000 });
    await expect(page).toHaveURL(/\/auth/);

    // 7. Verify success message
    await expect(page.locator('text=Вы вышли из системы')).toBeVisible();
  });

  test('should logout from ParentManagement page', async ({ page }) => {
    // 1. Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // 2. Login as admin
    await page.getByTestId('login-email-input').fill('admin@test.com');
    await page.getByTestId('login-password-input').fill('TestPass123!');
    await page.getByTestId('login-submit-button').click();

    // 3. Wait for redirect to admin panel
    await page.waitForURL('**/admin/staff', { timeout: 15000 });

    // 4. Navigate to parent management (if route exists)
    await page.goto('/admin/parents');
    await page.waitForLoadState('networkidle');

    // 5. Verify page title
    await expect(page.locator('text=Управление родителями')).toBeVisible();

    // 6. Find and click logout button
    const logoutButton = page.locator('button:has-text("Выйти")').first();
    await expect(logoutButton).toBeVisible();
    await logoutButton.click();

    // 7. Verify redirect to auth page
    await page.waitForURL('**/auth', { timeout: 5000 });
    await expect(page).toHaveURL(/\/auth/);
  });

  test('should display ProfileCard in StudentDashboard', async ({ page }) => {
    // 1. Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // 2. Login as student
    await page.getByTestId('login-email-input').fill('student@test.com');
    await page.getByTestId('login-password-input').fill('TestPass123!');
    await page.getByTestId('login-submit-button').click();

    // 3. Wait for redirect to student dashboard
    await page.waitForURL('**/dashboard/student', { timeout: 15000 });
    await expect(page).toHaveURL(/\/dashboard\/student/);

    // 4. Verify ProfileCard is visible
    await expect(page.locator('text=Мой профиль').first()).toBeVisible({ timeout: 5000 });

    // 5. Verify profile information is displayed
    await expect(page.locator('text=student@test.com')).toBeVisible();
  });

  test('should display ProfileCard in TeacherDashboard', async ({ page }) => {
    // 1. Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // 2. Login as teacher
    await page.getByTestId('login-email-input').fill('teacher@test.com');
    await page.getByTestId('login-password-input').fill('TestPass123!');
    await page.getByTestId('login-submit-button').click();

    // 3. Wait for redirect to teacher dashboard
    await page.waitForURL('**/dashboard/teacher', { timeout: 15000 });
    await expect(page).toHaveURL(/\/dashboard\/teacher/);

    // 4. Verify ProfileCard is visible
    await expect(page.locator('text=Мой профиль').first()).toBeVisible({ timeout: 5000 });

    // 5. Verify role badge
    await expect(page.locator('span:has-text("teacher")')).toBeVisible();
  });

  test('should display ProfileCard in TutorDashboard', async ({ page }) => {
    // 1. Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // 2. Login as tutor
    await page.getByTestId('login-email-input').fill('tutor@test.com');
    await page.getByTestId('login-password-input').fill('TestPass123!');
    await page.getByTestId('login-submit-button').click();

    // 3. Wait for redirect to tutor dashboard
    await page.waitForURL('**/dashboard/tutor', { timeout: 15000 });
    await expect(page).toHaveURL(/\/dashboard\/tutor/);

    // 4. Verify ProfileCard is visible
    await expect(page.locator('text=Мой профиль').first()).toBeVisible({ timeout: 5000 });
  });

  test('should display ProfileCard in ParentDashboard', async ({ page }) => {
    // 1. Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // 2. Login as parent
    await page.getByTestId('login-email-input').fill('parent@test.com');
    await page.getByTestId('login-password-input').fill('TestPass123!');
    await page.getByTestId('login-submit-button').click();

    // 3. Wait for redirect to parent dashboard
    await page.waitForURL('**/dashboard/parent', { timeout: 15000 });
    await expect(page).toHaveURL(/\/dashboard\/parent/);

    // 4. Verify ProfileCard is visible
    await expect(page.locator('text=Мой профиль').first()).toBeVisible({ timeout: 5000 });

    // 5. Verify email
    await expect(page.locator('text=parent@test.com')).toBeVisible();
  });
});
