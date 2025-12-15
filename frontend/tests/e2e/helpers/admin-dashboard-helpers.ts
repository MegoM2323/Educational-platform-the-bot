import { Page, expect } from '@playwright/test';

/**
 * Helper функции для E2E тестов React Admin Dashboard
 */

export const ADMIN_CONFIG = {
  baseUrl: process.env.BASE_URL || '',
  adminEmail: 'admin@test.com',
  adminPassword: 'TestPass123!',
};

/**
 * Логин как администратор
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.baseUrl}/auth`);
  await page.waitForLoadState('networkidle');

  // Fill email field - try different selectors
  const emailInputs = await page.locator('input[type="email"], input[placeholder*="email" i], input[aria-label*="email" i]').count();
  if (emailInputs > 0) {
    await page.locator('input[type="email"], input[placeholder*="email" i], input[aria-label*="email" i]').first().fill(ADMIN_CONFIG.adminEmail);
  } else {
    // Try textbox selector
    await page.locator('textbox[name*="email" i]').first().fill(ADMIN_CONFIG.adminEmail);
  }

  // Fill password field
  const passwordInputs = await page.locator('input[type="password"], input[placeholder*="password" i], input[aria-label*="password" i]').count();
  if (passwordInputs > 0) {
    await page.locator('input[type="password"], input[placeholder*="password" i], input[aria-label*="password" i]').first().fill(ADMIN_CONFIG.adminPassword);
  } else {
    // Try textbox selector
    await page.locator('textbox[name*="password" i]').first().fill(ADMIN_CONFIG.adminPassword);
  }

  // Click submit button
  const submitButtons = await page.locator('button[type="submit"], button:has-text("Войти")').count();
  if (submitButtons > 0) {
    await page.locator('button[type="submit"], button:has-text("Войти")').first().click();
  }

  // Ждем успешного логина или загрузки страницы (может быть редирект на dashboard или текущая страница)
  try {
    // Проверяем если есть ошибка входа
    await page.waitForSelector('text=/неверный|error|unauthorized/i', { timeout: 3000 }).catch(() => null);

    // Если ошибка - бросаем исключение
    const errorMsg = await page.locator('text=/неверный|error|unauthorized/i').count();
    if (errorMsg > 0) {
      throw new Error('Login failed - invalid credentials or access denied');
    }
  } catch {
    // Ignore timeout, continue
  }

  // Ждём редиректа на главную или админ панель, но с более мягким подходом
  try {
    await page.waitForURL(/\/(dashboard|admin|)/, { timeout: 15000 });
  } catch {
    // Если редирект не произошел, просто ждём загрузки страницы
    await page.waitForLoadState('networkidle');
  }

  await page.waitForLoadState('networkidle');
}

/**
 * Выход из системы
 */
export async function logout(page: Page): Promise<void> {
  try {
    // Найти кнопку выхода (может быть в меню или прямо на странице)
    const logoutButton = page.locator('button', { has: page.locator('text=/выйти|logout|sign out/i') }).first();
    if (await logoutButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await logoutButton.click();
    }

    // Ждем редиректа на страницу логина
    await page.waitForURL(/\/login/, { timeout: 10000 }).catch(() => {});
  } catch (error) {
    console.log('Logout may have already occurred or button not found');
  }
}

/**
 * Навигация к Admin Dashboard
 */
export async function navigateToAdminDashboard(page: Page): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.baseUrl}/admin`);
  await page.waitForLoadState('networkidle');
}

/**
 * Навигация к Student Management
 */
export async function navigateToStudentManagement(page: Page): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/accounts`);
  await page.waitForLoadState('networkidle');
  // Wait for StudentSection to be visible
  await page.waitForSelector('text=Студенты', { timeout: 10000 });
  // Scroll to StudentSection if needed
  await page.locator('text=Студенты').first().scrollIntoViewIfNeeded();
}

/**
 * Навигация к Parent Management
 */
export async function navigateToParentManagement(page: Page): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/accounts`);
  await page.waitForLoadState('networkidle');
  // Wait for ParentSection to be visible
  await page.waitForSelector('text=Родители', { timeout: 10000 });
  await page.locator('text=Родители').first().scrollIntoViewIfNeeded();
}

/**
 * Навигация к Teacher Management
 */
export async function navigateToTeacherManagement(page: Page): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/accounts`);
  await page.waitForLoadState('networkidle');
  // Wait for TeacherSection to be visible
  await page.waitForSelector('text=Преподаватели', { timeout: 10000 });
  await page.locator('text=Преподаватели').first().scrollIntoViewIfNeeded();
}

/**
 * Навигация к Staff Management (alias for Teacher Management)
 */
export async function navigateToStaffManagement(page: Page): Promise<void> {
  await navigateToTeacherManagement(page);
}

/**
 * Навигация к Tutor Management
 */
export async function navigateToTutorManagement(page: Page): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.baseUrl}/admin/accounts`);
  await page.waitForLoadState('networkidle');
  // Wait for TutorSection to be visible
  await page.waitForSelector('text=Тьютеры', { timeout: 10000 });
  await page.locator('text=Тьютеры').first().scrollIntoViewIfNeeded();
}

/**
 * Ждем загрузку таблицы
 */
export async function waitForTableLoad(page: Page, timeout: number = 10000): Promise<void> {
  // Ждем пока spinner исчезнет или таблица появится
  await page.locator('table').first().waitFor({ state: 'visible', timeout });
}

/**
 * Создание студента через диалог
 */
export async function createStudent(
  page: Page,
  data: {
    email: string;
    firstName: string;
    lastName: string;
    grade?: string;
  }
): Promise<{ email: string; password?: string }> {
  // Нажимаем "Создать студента"
  await page.locator('button:has-text("Создать студента")').click();
  await page.waitForTimeout(500);

  // Заполняем форму
  await page.fill('input[type="email"]', data.email);
  await page.fill('input[placeholder*="имя"], input[placeholder*="Имя"]', data.firstName);
  await page.fill('input[placeholder*="фамилия"], input[placeholder*="Фамилия"]', data.lastName);

  if (data.grade) {
    const gradeInput = page.locator('input[placeholder*="класс"], input[placeholder*="Класс"]');
    if (await gradeInput.isVisible()) {
      await gradeInput.fill(data.grade);
    }
  }

  // Сохраняем
  await page.locator('button[type="submit"]:has-text("Создать"), button[type="submit"]:has-text("Сохранить")').click();

  // Ждем появления success диалога с паролем
  await page.waitForTimeout(500);

  // Ищем пароль в readonly поле
  let generatedPassword: string | undefined;
  const passwordField = page.locator('input[readonly]').first();
  if (await passwordField.isVisible()) {
    generatedPassword = await passwordField.inputValue();
  }

  // Закрываем диалог
  await page.locator('button:has-text("Закрыть"), button:has-text("OK"), button:has-text("Готово")').click();
  await page.waitForTimeout(500);

  return { email: data.email, password: generatedPassword };
}

/**
 * Поиск студента по email
 */
export async function searchStudent(page: Page, email: string): Promise<void> {
  const searchInput = page.locator('input[placeholder*="ФИО"], input[placeholder*="email"], input[placeholder*="поиск"]');
  await searchInput.fill(email);
  await page.waitForTimeout(300);
  // Автоматический поиск при вводе
}

/**
 * Фильтрация по статусу
 */
export async function filterByStatus(page: Page, status: 'все' | 'активные' | 'неактивные'): Promise<void> {
  const statusSelect = page.locator('select').last();
  if (await statusSelect.isVisible()) {
    const statusMap = {
      'все': 'all',
      'активные': 'true',
      'неактивные': 'false',
    };
    await statusSelect.selectOption(statusMap[status] || status);
    await page.waitForTimeout(300);
  }
}

/**
 * Получить количество студентов в таблице
 */
export async function getStudentCount(page: Page): Promise<number> {
  const rows = page.locator('table tbody tr').filter({ has: page.locator('td') });
  return await rows.count();
}

/**
 * Нажать на кнопку редактирования студента
 */
export async function editStudent(page: Page, studentEmail: string): Promise<void> {
  // Находим строку студента
  const row = page.locator('table tbody tr').filter({ hasText: studentEmail }).first();
  const editButton = row.locator('button[title*="Редактировать"], button:has-text("✎")').first();
  await editButton.click();
  await page.waitForTimeout(500);
}

/**
 * Сброс пароля студента
 */
export async function resetStudentPassword(page: Page, studentEmail: string): Promise<string | undefined> {
  // Находим строку студента
  const row = page.locator('table tbody tr').filter({ hasText: studentEmail }).first();
  const resetButton = row.locator('button[title*="Сбросить"], button[title*="пароль"], button:has-text("🔑")').first();
  await resetButton.click();
  await page.waitForTimeout(500);

  // Ждем диалога с новым паролем
  const passwordField = page.locator('input[readonly]').first();
  let newPassword: string | undefined;
  if (await passwordField.isVisible()) {
    newPassword = await passwordField.inputValue();
  }

  // Закрываем диалог
  await page.locator('button:has-text("Закрыть"), button:has-text("OK")').click();
  await page.waitForTimeout(500);

  return newPassword;
}

/**
 * Удаление студента
 */
export async function deleteStudent(page: Page, studentEmail: string, hardDelete: boolean = false): Promise<void> {
  // Находим строку студента
  const row = page.locator('table tbody tr').filter({ hasText: studentEmail }).first();
  const deleteButton = row.locator('button[title*="Удалить"], button:has-text("🗑")').first();
  await deleteButton.click();
  await page.waitForTimeout(500);

  // Если есть выбор между soft и hard delete
  if (hardDelete) {
    const hardDeleteOption = page.locator('text=Полное удаление, Hard delete').first();
    if (await hardDeleteOption.isVisible()) {
      await hardDeleteOption.click();
      await page.waitForTimeout(300);
    }
  }

  // Подтверждаем удаление
  await page.locator('button:has-text("Удалить"), button:has-text("Да"), button[type="submit"]:has-text("Подтвердить")').click();
  await page.waitForTimeout(500);
}

/**
 * Переключение на следующую страницу
 */
export async function goToNextPage(page: Page): Promise<void> {
  const nextButton = page.locator('button:has-text("Далее"), button:has-text("→"), [aria-label*="следующая"]').first();
  if (await nextButton.isVisible() && !(await nextButton.isDisabled())) {
    await nextButton.click();
    await waitForTableLoad(page);
  }
}

/**
 * Переключение на предыдущую страницу
 */
export async function goToPreviousPage(page: Page): Promise<void> {
  const prevButton = page.locator('button:has-text("Назад"), button:has-text("←"), [aria-label*="предыдущая"]').first();
  if (await prevButton.isVisible() && !(await prevButton.isDisabled())) {
    await prevButton.click();
    await waitForTableLoad(page);
  }
}

/**
 * Проверить наличие toast уведомления
 */
export async function hasToastMessage(page: Page, type: 'success' | 'error' = 'success'): Promise<boolean> {
  const toastLocator = type === 'success'
    ? page.locator('[class*="toast"], [role="status"]').filter({ hasText: /успешно|сохранено|создано/i })
    : page.locator('[class*="toast"], [role="alert"]').filter({ hasText: /ошибк/i });

  return await toastLocator.isVisible().catch(() => false);
}

/**
 * Генерация уникального email
 */
export function generateTestEmail(prefix: string = 'test'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}@test.com`;
}

/**
 * Генерация уникального имени
 */
export function generateTestName(prefix: string = 'Test'): string {
  return `${prefix}_${Date.now()}`;
}

/**
 * Проверить что элемент видим (с автоматическим скроллом)
 */
export async function scrollToAndCheck(page: Page, selector: string): Promise<boolean> {
  try {
    const element = page.locator(selector).first();
    await element.scrollIntoViewIfNeeded();
    return await element.isVisible();
  } catch {
    return false;
  }
}

/**
 * Получить текст из ячейки таблицы
 */
export async function getCellText(page: Page, email: string, columnIndex: number): Promise<string> {
  const row = page.locator('table tbody tr').filter({ hasText: email }).first();
  const cell = row.locator('td').nth(columnIndex);
  return await cell.textContent() || '';
}

/**
 * Ждем пока элемент исчезнет
 */
export async function waitForElementToDisappear(page: Page, selector: string, timeout: number = 5000): Promise<void> {
  await page.locator(selector).first().waitFor({ state: 'hidden', timeout });
}

/**
 * Проверить что студент находится в списке
 */
export async function isStudentInList(page: Page, email: string): Promise<boolean> {
  try {
    await page.locator('table tbody tr').filter({ hasText: email }).first().waitFor({ state: 'visible', timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Получить информацию о студенте из строки таблицы
 */
export async function getStudentInfo(page: Page, email: string): Promise<{
  email: string;
  firstName: string;
  grade?: string;
  status: string;
}> {
  const row = page.locator('table tbody tr').filter({ hasText: email }).first();

  const cells = await row.locator('td').evaluateAll(cells =>
    cells.map(cell => cell.textContent?.trim() || '')
  );

  return {
    email,
    firstName: cells[0] || '',
    grade: cells[2] || '',
    status: cells[3] || '',
  };
}

/**
 * Ждем появления диалога создания
 */
export async function waitForCreateDialog(page: Page, timeout: number = 5000): Promise<void> {
  // Ждем появления элементов формы создания
  await page.locator('input[type="email"]').first().waitFor({ state: 'visible', timeout });
}

/**
 * Закрыть открытый диалог
 */
export async function closeDialog(page: Page): Promise<void> {
  const closeButton = page.locator('button[aria-label*="Close"], button:has-text("✕"), button:has-text("Закрыть")').first();
  if (await closeButton.isVisible()) {
    await closeButton.click();
    await page.waitForTimeout(300);
  }
}

/**
 * Проверить что пароль был сгенерирован (валидный формат)
 */
export function isValidPassword(password?: string): boolean {
  if (!password) return false;
  // Проверяем что пароль имеет минимальную длину
  return password.length >= 8;
}

/**
 * Ждем редиректа на страницу
 */
export async function waitForNavigation(page: Page, pattern: string | RegExp, timeout: number = 10000): Promise<void> {
  await page.waitForURL(pattern, { timeout });
  await page.waitForLoadState('networkidle');
}

/**
 * Получить значение из input поля
 */
export async function getInputValue(page: Page, selector: string): Promise<string> {
  return await page.locator(selector).first().inputValue();
}
