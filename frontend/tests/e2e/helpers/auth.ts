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
 */
export async function loginAs(page: Page, userKey: keyof typeof TEST_USERS): Promise<void> {
  const user = TEST_USERS[userKey];

  await page.goto('/auth');

  // Заполняем форму
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);

  // Отправляем форму
  await page.click('button[type="submit"]');

  // Ждем редиректа на дашборд
  await page.waitForURL(`**${user.dashboardPath}`, { timeout: 15000 });

  // Проверяем что токен сохранен
  const token = await page.evaluate(() => localStorage.getItem('authToken'));
  if (!token) {
    throw new Error(`Failed to login as ${userKey}: no auth token found`);
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
