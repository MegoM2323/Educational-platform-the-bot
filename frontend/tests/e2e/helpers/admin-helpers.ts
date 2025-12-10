import { Page } from '@playwright/test';

/**
 * Helper функции для E2E тестов Django Admin Panel
 */

export const ADMIN_CONFIG = {
  url: 'http://localhost:8003/admin/',
  credentials: {
    username: 'admin@test.com',
    password: 'TestPass123!',
  },
};

/**
 * Вход в админ панель
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto(ADMIN_CONFIG.url);

  // Проверяем, не залогинены ли мы уже
  const isLoggedIn = await page.locator('#site-name').isVisible().catch(() => false);

  if (!isLoggedIn) {
    await page.fill('input[name="username"]', ADMIN_CONFIG.credentials.username);
    await page.fill('input[name="password"]', ADMIN_CONFIG.credentials.password);
    await page.click('input[type="submit"]');

    // Ждем загрузки главной страницы админки
    await page.waitForSelector('#site-name', { timeout: 10000 });
  }
}

/**
 * Выход из админ панели
 */
export async function logoutFromAdmin(page: Page): Promise<void> {
  const logoutLink = page.locator('text=/Log out|Выход/i').first();
  if (await logoutLink.isVisible()) {
    await logoutLink.click();
    await page.waitForTimeout(1000);
  }
}

/**
 * Создание пользователя через админ панель
 */
export async function createUser(
  page: Page,
  userData: {
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    role: 'student' | 'teacher' | 'tutor' | 'parent';
    password?: string;
  }
): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.url}accounts/user/`);
  await page.click('text=/Add user|Добавить/i');

  await page.fill('input[name="username"]', userData.username);
  await page.fill('input[name="email"]', userData.email);
  await page.fill('input[name="first_name"]', userData.firstName);
  await page.fill('input[name="last_name"]', userData.lastName);
  await page.selectOption('select[name="role"]', userData.role);

  // Пароль опционален
  const password = userData.password || 'TestPassword123!';
  const passwordField = page.locator('input[name="password1"]');
  if (await passwordField.isVisible()) {
    await passwordField.fill(password);
    await page.fill('input[name="password2"]', password);
  }

  await page.click('input[type="submit"][name="_save"]');
  await page.waitForTimeout(1000);
}

/**
 * Удаление пользователя через поиск и bulk action
 */
export async function deleteUser(page: Page, username: string): Promise<void> {
  try {
    await page.goto(`${ADMIN_CONFIG.url}accounts/user/`);

    // Поиск пользователя
    const searchInput = page.locator('input#searchbar');
    await searchInput.fill(username);
    await searchInput.press('Enter');
    await page.waitForTimeout(1000);

    // Проверяем, есть ли результаты
    const noResults = await page.locator('text=/0 пользователей|0 users/i').isVisible().catch(() => false);

    if (!noResults) {
      // Выбираем чекбокс
      const checkbox = page.locator('input[name="_selected_action"]').first();
      if (await checkbox.isVisible()) {
        await checkbox.check();

        // Выбираем действие "Удалить"
        await page.selectOption('select[name="action"]', 'delete_selected');
        await page.click('button[name="index"]');

        // Подтверждаем удаление
        const confirmButton = page.locator('input[type="submit"]');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(500);
        }
      }
    }
  } catch (error) {
    console.log(`Failed to delete user ${username}:`, error);
  }
}

/**
 * Редактирование пользователя
 */
export async function editUser(
  page: Page,
  username: string,
  updates: {
    firstName?: string;
    lastName?: string;
    email?: string;
    role?: 'student' | 'teacher' | 'tutor' | 'parent';
  }
): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.url}accounts/user/`);

  // Поиск пользователя
  await page.fill('input#searchbar', username);
  await page.press('input#searchbar', 'Enter');
  await page.waitForTimeout(1000);

  // Кликаем на пользователя
  await page.click(`text=${username}`);

  // Применяем изменения
  if (updates.firstName) {
    await page.fill('input[name="first_name"]', updates.firstName);
  }
  if (updates.lastName) {
    await page.fill('input[name="last_name"]', updates.lastName);
  }
  if (updates.email) {
    await page.fill('input[name="email"]', updates.email);
  }
  if (updates.role) {
    await page.selectOption('select[name="role"]', updates.role);
  }

  await page.click('input[type="submit"][name="_save"]');
  await page.waitForTimeout(1000);
}

/**
 * Создание предмета
 */
export async function createSubject(
  page: Page,
  subjectData: {
    name: string;
    description?: string;
    color?: string;
  }
): Promise<void> {
  await page.goto(`${ADMIN_CONFIG.url}materials/subject/`);
  await page.click('text=/Add subject|Добавить/i');

  await page.fill('input[name="name"]', subjectData.name);

  if (subjectData.description) {
    await page.fill('textarea[name="description"]', subjectData.description);
  }

  if (subjectData.color) {
    const colorField = page.locator('input[name="color"]');
    if (await colorField.isVisible()) {
      await colorField.fill(subjectData.color);
    }
  }

  await page.click('input[type="submit"][name="_save"]');
  await page.waitForTimeout(1000);
}

/**
 * Удаление предмета
 */
export async function deleteSubject(page: Page, subjectName: string): Promise<void> {
  try {
    await page.goto(`${ADMIN_CONFIG.url}materials/subject/`);

    const subjectLink = page.locator(`text=${subjectName}`);
    if (await subjectLink.isVisible()) {
      await subjectLink.click();
      await page.click('text=/Delete|Удалить/i');
      await page.click('input[type="submit"]');
      await page.waitForTimeout(500);
    }
  } catch (error) {
    console.log(`Failed to delete subject ${subjectName}:`, error);
  }
}

/**
 * Создание назначения преподавателя на предмет
 */
export async function assignTeacherToSubject(
  page: Page,
  teacherEmail: string,
  subjectName: string
): Promise<boolean> {
  try {
    await page.goto(`${ADMIN_CONFIG.url}materials/teachersubject/`);
    await page.click('text=/Add teacher subject|Добавить/i');

    // Выбираем преподавателя
    const teacherSelect = page.locator('select[name="teacher"]');
    const teacherOption = await teacherSelect.locator(`option:has-text("${teacherEmail}")`).first();
    if (await teacherOption.isVisible()) {
      await teacherOption.click();
    } else {
      return false;
    }

    // Выбираем предмет
    const subjectSelect = page.locator('select[name="subject"]');
    const subjectOption = await subjectSelect.locator(`option:has-text("${subjectName}")`).first();
    if (await subjectOption.isVisible()) {
      await subjectOption.click();
    } else {
      return false;
    }

    await page.click('input[type="submit"][name="_save"]');
    await page.waitForTimeout(1000);

    return true;
  } catch (error) {
    console.log('Failed to assign teacher to subject:', error);
    return false;
  }
}

/**
 * Зачисление студента на предмет
 */
export async function enrollStudentToSubject(
  page: Page,
  studentEmail: string,
  subjectName: string,
  teacherEmail: string
): Promise<boolean> {
  try {
    await page.goto(`${ADMIN_CONFIG.url}materials/subjectenrollment/`);
    await page.click('text=/Add subject enrollment|Добавить/i');

    // Выбираем студента
    const studentSelect = page.locator('select[name="student"]');
    const studentOption = await studentSelect.locator(`option:has-text("${studentEmail}")`).first();
    if (await studentOption.isVisible()) {
      await studentOption.click();
    } else {
      return false;
    }

    // Выбираем предмет
    const subjectSelect = page.locator('select[name="subject"]');
    const subjectOption = await subjectSelect.locator(`option:has-text("${subjectName}")`).first();
    if (await subjectOption.isVisible()) {
      await subjectOption.click();
    } else {
      return false;
    }

    // Выбираем преподавателя
    const teacherSelect = page.locator('select[name="teacher"]');
    const teacherOption = await teacherSelect.locator(`option:has-text("${teacherEmail}")`).first();
    if (await teacherOption.isVisible()) {
      await teacherOption.click();
    } else {
      return false;
    }

    await page.click('input[type="submit"][name="_save"]');
    await page.waitForTimeout(1000);

    return true;
  } catch (error) {
    console.log('Failed to enroll student:', error);
    return false;
  }
}

/**
 * Проверка наличия сообщения об успехе
 */
export async function hasSuccessMessage(page: Page): Promise<boolean> {
  return await page.locator('.success, .messagelist .success').isVisible().catch(() => false);
}

/**
 * Проверка наличия сообщения об ошибке
 */
export async function hasErrorMessage(page: Page): Promise<boolean> {
  return await page.locator('.errorlist, .errornote').isVisible().catch(() => false);
}

/**
 * Поиск в админ панели
 */
export async function searchInAdmin(page: Page, query: string): Promise<void> {
  const searchInput = page.locator('input#searchbar');
  await searchInput.fill(query);
  await searchInput.press('Enter');
  await page.waitForTimeout(1000);
}

/**
 * Применение фильтра
 */
export async function applyFilter(page: Page, filterName: string, filterValue: string): Promise<void> {
  const filterSidebar = page.locator('#changelist-filter');
  if (await filterSidebar.isVisible()) {
    const filterLink = filterSidebar.locator(`text=${filterValue}`);
    if (await filterLink.isVisible()) {
      await filterLink.click();
      await page.waitForTimeout(1000);
    }
  }
}

/**
 * Получение количества записей в списке
 */
export async function getRecordCount(page: Page): Promise<number> {
  const rows = page.locator('#result_list tbody tr');
  return await rows.count();
}

/**
 * Выбор всех записей через "Select all"
 */
export async function selectAllRecords(page: Page): Promise<void> {
  const selectAllCheckbox = page.locator('#action-toggle');
  if (await selectAllCheckbox.isVisible()) {
    await selectAllCheckbox.check();
    await page.waitForTimeout(500);
  }
}

/**
 * Применение bulk action
 */
export async function applyBulkAction(page: Page, action: string): Promise<void> {
  await page.selectOption('select[name="action"]', action);
  await page.click('button[name="index"]');
  await page.waitForTimeout(1000);
}

/**
 * Генерация уникального email для тестов
 */
export function generateTestEmail(prefix: string = 'test'): string {
  return `${prefix}_${Date.now()}@test.com`;
}

/**
 * Генерация уникального имени для тестов
 */
export function generateTestName(prefix: string = 'Test'): string {
  return `${prefix} ${Date.now()}`;
}
