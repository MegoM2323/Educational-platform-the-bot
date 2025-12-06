import { Page } from '@playwright/test';

export interface TestUser {
  email: string;
  password: string;
  role: 'student' | 'teacher' | 'tutor' | 'parent' | 'admin';
  dashboardPath: string;
}

export const TEST_USERS: Record<string, TestUser> = {
  student: {
    email: 'student@test.com',
    password: 'TestPass123!',
    role: 'student',
    dashboardPath: '/dashboard/student',
  },
  student2: {
    email: 'student2@test.com',
    password: 'TestPass123!',
    role: 'student',
    dashboardPath: '/dashboard/student',
  },
  teacher: {
    email: 'teacher@test.com',
    password: 'TestPass123!',
    role: 'teacher',
    dashboardPath: '/dashboard/teacher',
  },
  teacher2: {
    email: 'teacher2@test.com',
    password: 'TestPass123!',
    role: 'teacher',
    dashboardPath: '/dashboard/teacher',
  },
  tutor: {
    email: 'tutor@test.com',
    password: 'TestPass123!',
    role: 'tutor',
    dashboardPath: '/dashboard/tutor',
  },
  parent: {
    email: 'parent@test.com',
    password: 'TestPass123!',
    role: 'parent',
    dashboardPath: '/dashboard/parent',
  },
  admin: {
    email: 'admin@test.com',
    password: 'TestPass123!',
    role: 'admin',
    dashboardPath: '/admin/staff',
  },
};

/**
 * Вход в систему от имени пользователя
 * Uses UI-based authentication with data-testid selectors for reliability
 */
export async function loginAs(page: Page, userKey: keyof typeof TEST_USERS): Promise<void> {
  const user = TEST_USERS[userKey];

  // UI-based login (fallback approach - works even when API is unavailable)
  try {
    // Navigate to auth page
    await page.goto('/auth');
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Fill email/username field using data-testid
    const emailInput = page.locator('[data-testid="login-email-input"]');
    await emailInput.waitFor({ state: 'visible', timeout: 5000 });
    await emailInput.fill(user.email);

    // Fill password field using data-testid
    const passwordInput = page.locator('[data-testid="login-password-input"]');
    await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
    await passwordInput.fill(user.password);

    // Click submit button using data-testid
    const submitButton = page.locator('[data-testid="login-submit-button"]');
    await submitButton.click();

    // Wait for redirect to dashboard
    await page.waitForURL(`**${user.dashboardPath}`, { timeout: 15000 });

    // Verify token is stored
    const token = await page.evaluate(() => localStorage.getItem('authToken'));
    if (!token) {
      throw new Error(`Failed to login as ${userKey}: no auth token found in localStorage after login`);
    }

    console.log(`✓ Successfully logged in as ${userKey} (${user.role})`);

  } catch (error) {
    console.error(`Failed to login as ${userKey}:`, error);

    // Take screenshot for debugging
    await page.screenshot({ path: `/tmp/login-failed-${userKey}.png`, fullPage: true });

    throw new Error(`Login failed for ${userKey}: ${error}`);
  }
}

/**
 * Выход из системы
 */
export async function logout(page: Page): Promise<void> {
  const logoutButton = page.locator('text=/выход|выйти|logout/i').first();

  if (await logoutButton.count() > 0) {
    await logoutButton.click();
    await page.waitForURL('**/auth', { timeout: 10000 });
  } else {
    // Если нет кнопки выхода, очищаем вручную
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto('/auth');
  }
}

/**
 * Проверка что пользователь залогинен
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  const token = await page.evaluate(() => localStorage.getItem('authToken'));
  return !!token;
}

/**
 * Очистить все данные аутентификации
 */
export async function clearAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}
