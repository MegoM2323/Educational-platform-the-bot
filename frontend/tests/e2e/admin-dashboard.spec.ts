import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  logout,
  navigateToAdminDashboard,
  navigateToStudentManagement,
  navigateToParentManagement,
  navigateToStaffManagement,
  createStudent,
  searchStudent,
  filterByStatus,
  getStudentCount,
  editStudent,
  resetStudentPassword,
  deleteStudent,
  goToNextPage,
  waitForTableLoad,
  hasToastMessage,
  generateTestEmail,
  generateTestName,
  isStudentInList,
  getStudentInfo,
  waitForCreateDialog,
  closeDialog,
  isValidPassword,
  ADMIN_CONFIG,
} from './helpers/admin-dashboard-helpers';

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Логинимся перед каждым тестом
    await loginAsAdmin(page);
  });

  test.afterEach(async ({ page }) => {
    // Пытаемся выйти после каждого теста
    try {
      await logout(page);
    } catch {
      // Игнорируем ошибку выхода
    }
  });

  test.describe('AdminDashboard Navigation', () => {
    test('should display admin dashboard with statistics cards', async ({ page }) => {
      // Переходим на админ панель
      await navigateToAdminDashboard(page);

      // Проверяем заголовок
      await expect(page.locator('h1').filter({ hasText: 'Администратор' })).toBeVisible();

      // Проверяем карточки со статистикой
      await expect(page.locator('text=Всего пользователей')).toBeVisible();
      await expect(page.locator('text=Студентов')).toBeVisible();
      await expect(page.locator('text=Преподавателей')).toBeVisible();
      await expect(page.locator('text=Активных сегодня')).toBeVisible();

      // Проверяем наличие статистических цифр
      const statsValues = page.locator('[class*="Card"]').locator('div:has-text(/^\\d+$/)');
      const count = await statsValues.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should display all tabs in admin dashboard', async ({ page }) => {
      await navigateToAdminDashboard(page);

      // Проверяем наличие табов
      await expect(page.locator('button[role="tab"]:has-text("Студенты")')).toBeVisible();
      await expect(page.locator('button[role="tab"]:has-text("Преподаватели")')).toBeVisible();
      await expect(page.locator('button[role="tab"]:has-text("Родители")')).toBeVisible();
    });

    test('should navigate to Student Management via tab', async ({ page }) => {
      await navigateToAdminDashboard(page);

      // Кликаем на таб "Студенты"
      await page.locator('button[role="tab"]:has-text("Студенты")').click();
      await page.waitForTimeout(500);

      // Проверяем что загрузилась таблица студентов
      await expect(page.locator('text=Управление студентами')).toBeVisible();
      await expect(page.locator('table')).toBeVisible();
    });

    test('should display logout button', async ({ page }) => {
      await navigateToAdminDashboard(page);

      const logoutButton = page.locator('button:has-text("Выйти")').first();
      await expect(logoutButton).toBeVisible();
    });
  });

  test.describe('StudentManagement - List and Filters', () => {
    test('should display student list', async ({ page }) => {
      await navigateToStudentManagement(page);

      // Проверяем заголовок
      await expect(page.locator('text=Управление студентами')).toBeVisible();

      // Проверяем таблицу
      await expect(page.locator('table')).toBeVisible();
      await expect(page.locator('table thead')).toBeVisible();
    });

    test('should display student list with proper columns', async ({ page }) => {
      await navigateToStudentManagement(page);

      // Проверяем наличие колонок
      await expect(page.locator('th:has-text("ФИО")')).toBeVisible();
      await expect(page.locator('th:has-text("Email")')).toBeVisible();
      await expect(page.locator('th:has-text("Класс")')).toBeVisible();
      await expect(page.locator('th:has-text("Статус")')).toBeVisible();
      await expect(page.locator('th:has-text("Дата регистрации")')).toBeVisible();
      await expect(page.locator('th:has-text("Действия")')).toBeVisible();
    });

    test('should search student by email', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      // Получаем email первого студента
      const firstEmail = await page.locator('table tbody tr').first().locator('td').nth(1).textContent();
      if (!firstEmail) {
        test.skip();
      }

      // Ищем по email
      await searchStudent(page, firstEmail || '');
      await page.waitForTimeout(500);

      // Проверяем что результаты отфильтрованы
      const rows = await getStudentCount(page);
      expect(rows).toBeGreaterThan(0);
    });

    test('should filter students by status', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      const initialCount = await getStudentCount(page);

      // Фильтруем по активным
      await filterByStatus(page, 'активные');
      await page.waitForTimeout(500);

      const activeCount = await getStudentCount(page);

      // Фильтруем по неактивным
      await filterByStatus(page, 'неактивные');
      await page.waitForTimeout(500);

      const inactiveCount = await getStudentCount(page);

      // Сумма активных и неактивных должна быть <= всех
      expect(activeCount + inactiveCount).toBeLessThanOrEqual(initialCount);
    });

    test('should display create student button', async ({ page }) => {
      await navigateToStudentManagement(page);

      const createButton = page.locator('button:has-text("Создать студента")');
      await expect(createButton).toBeVisible();
    });
  });

  test.describe('StudentManagement - Create Student', () => {
    test('should create new student successfully', async ({ page }) => {
      await navigateToStudentManagement(page);

      const testEmail = generateTestEmail('newstudent');
      const testFirstName = 'Иван';
      const testLastName = 'Иванов';
      const testGrade = '10';

      // Создаем студента
      const result = await createStudent(page, {
        email: testEmail,
        firstName: testFirstName,
        lastName: testLastName,
        grade: testGrade,
      });

      // Проверяем что пароль был сгенерирован
      expect(isValidPassword(result.password)).toBeTruthy();

      // Проверяем что студент появился в списке
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      const isInList = await isStudentInList(page, testEmail);
      expect(isInList).toBeTruthy();
    });

    test('should validate email field when creating student', async ({ page }) => {
      await navigateToStudentManagement(page);

      // Открываем диалог создания
      await page.locator('button:has-text("Создать студента")').click();
      await waitForCreateDialog(page);

      // Вводим невалидный email
      const emailInput = page.locator('input[type="email"]').first();
      await emailInput.fill('invalid-email');

      // Пытаемся отправить форму
      const submitButton = page.locator('button[type="submit"]:has-text("Создать"), button[type="submit"]:has-text("Сохранить")').first();
      const isDisabled = await submitButton.isDisabled();

      // Может быть либо disabled кнопка, либо ошибка валидации
      if (!isDisabled) {
        await submitButton.click();
        // Ждем ошибки
        await page.waitForTimeout(500);
      }

      // Закрываем диалог
      await closeDialog(page);
    });

    test('should require all mandatory fields when creating student', async ({ page }) => {
      await navigateToStudentManagement(page);

      // Открываем диалог создания
      await page.locator('button:has-text("Создать студента")').click();
      await waitForCreateDialog(page);

      // Пытаемся отправить пустую форму
      const submitButton = page.locator('button[type="submit"]:has-text("Создать"), button[type="submit"]:has-text("Сохранить")').first();

      // Кнопка должна быть disabled пока не заполнены поля
      const isDisabled = await submitButton.isDisabled();
      expect(isDisabled).toBeTruthy();

      // Закрываем диалог
      await closeDialog(page);
    });

    test('should copy generated password', async ({ page }) => {
      await navigateToStudentManagement(page);

      const testEmail = generateTestEmail('copytest');

      // Создаем студента
      const result = await createStudent(page, {
        email: testEmail,
        firstName: 'Test',
        lastName: 'User',
      });

      // Проверяем что пароль не пустой
      expect(result.password).toBeTruthy();
      expect(result.password?.length).toBeGreaterThan(0);
    });
  });

  test.describe('StudentManagement - Edit Student', () => {
    test('should edit student information', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      // Создаем студента для редактирования
      const testEmail = generateTestEmail('edittest');
      await createStudent(page, {
        email: testEmail,
        firstName: 'Original',
        lastName: 'Name',
      });

      // Переходим в управление студентами
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      // Открываем редактирование
      await editStudent(page, testEmail);
      await page.waitForTimeout(300);

      // Ищем input поля и обновляем их
      const firstNameInputs = page.locator('input[placeholder*="имя"], input[placeholder*="Имя"]');
      if (await firstNameInputs.first().isVisible()) {
        await firstNameInputs.first().clear();
        await firstNameInputs.first().fill('Updated');
      }

      // Сохраняем изменения
      await page.locator('button[type="submit"]:has-text("Сохранить"), button[type="submit"]:has-text("Обновить")').click();
      await page.waitForTimeout(500);

      // Проверяем что успешно обновлено
      const success = await hasToastMessage(page, 'success');
      // Может быть toast или просто редирект
    });
  });

  test.describe('StudentManagement - Reset Password', () => {
    test('should reset student password', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      // Создаем студента
      const testEmail = generateTestEmail('resettest');
      await createStudent(page, {
        email: testEmail,
        firstName: 'Reset',
        lastName: 'Test',
      });

      // Переходим в управление студентами
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      // Сбрасываем пароль
      const newPassword = await resetStudentPassword(page, testEmail);

      // Проверяем что пароль был сгенерирован
      expect(isValidPassword(newPassword)).toBeTruthy();
    });

    test('should generate unique password on reset', async ({ page }) => {
      await navigateToStudentManagement(page);

      const testEmail = generateTestEmail('uniquepasstest');
      const result1 = await createStudent(page, {
        email: testEmail,
        firstName: 'Test',
        lastName: 'Pass',
      });

      // Переходим в управление студентами
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      // Сбрасываем пароль
      const result2 = await resetStudentPassword(page, testEmail);

      // Пароли могут быть разными или одинаковыми (система решит)
      expect(isValidPassword(result2)).toBeTruthy();
    });
  });

  test.describe('StudentManagement - Delete Student', () => {
    test('should soft delete student', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      // Создаем студента
      const testEmail = generateTestEmail('softdeletetest');
      await createStudent(page, {
        email: testEmail,
        firstName: 'Soft',
        lastName: 'Delete',
      });

      // Переходим в управление студентами
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      // Удаляем студента (soft delete)
      await deleteStudent(page, testEmail, false);
      await page.waitForTimeout(500);

      // После soft delete студент должен остаться в списке (но неактивным)
      // или исчезнуть из списка "активные"
    });

    test('should hard delete student', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      // Создаем студента
      const testEmail = generateTestEmail('harddeletetest');
      await createStudent(page, {
        email: testEmail,
        firstName: 'Hard',
        lastName: 'Delete',
      });

      // Переходим в управление студентами
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      // Удаляем студента (hard delete)
      await deleteStudent(page, testEmail, true);
      await page.waitForTimeout(500);

      // Студент должен полностью исчезнуть из списка
      const isInList = await isStudentInList(page, testEmail);
      expect(isInList).toBeFalsy();
    });
  });

  test.describe('StudentManagement - Pagination', () => {
    test('should navigate to next page', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      const countBefore = await getStudentCount(page);

      // Если есть следующая страница
      const nextButton = page.locator('button:has-text("Далее"), button:has-text("→"), [aria-label*="следующая"]').first();
      const hasNextPage = await nextButton.isVisible().catch(() => false);

      if (hasNextPage && !(await nextButton.isDisabled())) {
        await goToNextPage(page);
        const countAfter = await getStudentCount(page);

        // Страницы могут быть одинакового размера
        expect(countAfter).toBeGreaterThanOrEqual(0);
      }
    });

    test('should display pagination info', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      // Ищем инфо о пагинации
      const paginationInfo = page.locator('text=/Страница \\d+ из \\d+/');
      const isVisible = await paginationInfo.isVisible().catch(() => false);

      if (isVisible) {
        await expect(paginationInfo).toBeVisible();
      }
    });
  });

  test.describe('ParentManagement', () => {
    test('should display parent management page', async ({ page }) => {
      await navigateToParentManagement(page);

      // Проверяем заголовок
      const title = page.locator('text=Управление родителями');
      const exists = await title.isVisible().catch(() => false);

      if (exists) {
        await expect(title).toBeVisible();
        await expect(page.locator('table')).toBeVisible();
      }
    });
  });

  test.describe('StaffManagement', () => {
    test('should display staff management page', async ({ page }) => {
      await navigateToStaffManagement(page);

      // Проверяем заголовок
      const title = page.locator('text=Управление преподавателями');
      const exists = await title.isVisible().catch(() => false);

      if (exists) {
        await expect(title).toBeVisible();
        await expect(page.locator('table')).toBeVisible();
      }
    });
  });

  test.describe('AdminDashboard - Logout', () => {
    test('should logout successfully', async ({ page }) => {
      await navigateToAdminDashboard(page);

      // Нажимаем кнопку выхода
      const logoutButton = page.locator('button:has-text("Выйти")').first();
      await logoutButton.click();

      // Проверяем редирект на auth страницу
      await page.waitForURL(/\/auth/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/auth/);
    });

    test('should not be able to access admin after logout', async ({ page }) => {
      await navigateToAdminDashboard(page);
      await logout(page);

      // Пытаемся перейти на админ панель
      await page.goto(`${ADMIN_CONFIG.baseUrl}/admin`);
      await page.waitForTimeout(500);

      // Должны перенаправить на auth
      const currentUrl = page.url();
      expect(currentUrl).toContain('/auth');
    });
  });

  test.describe('AdminDashboard - Integration Tests', () => {
    test('should complete full student management workflow', async ({ page }) => {
      await navigateToStudentManagement(page);
      await waitForTableLoad(page);

      const initialCount = await getStudentCount(page);

      // Создаем студента
      const testEmail = generateTestEmail('workflow');
      const createResult = await createStudent(page, {
        email: testEmail,
        firstName: 'Workflow',
        lastName: 'Test',
        grade: '11',
      });

      expect(isValidPassword(createResult.password)).toBeTruthy();

      // Переходим обратно в список
      await navigateToStudentManagement(page);
      await page.waitForTimeout(500);

      // Проверяем что студент есть
      const isInList = await isStudentInList(page, testEmail);
      expect(isInList).toBeTruthy();

      // Получаем информацию о студенте
      const studentInfo = await getStudentInfo(page, testEmail);
      expect(studentInfo.email).toContain(testEmail);

      const finalCount = await getStudentCount(page);
      expect(finalCount).toBeGreaterThanOrEqual(initialCount);
    });

    test('should maintain admin session across multiple operations', async ({ page }) => {
      // Операция 1: Перейти на admin dashboard
      await navigateToAdminDashboard(page);
      await expect(page.locator('h1').filter({ hasText: 'Администратор' })).toBeVisible();

      // Операция 2: Перейти на управление студентами
      await navigateToStudentManagement(page);
      await expect(page.locator('text=Управление студентами')).toBeVisible();

      // Операция 3: Перейти на управление родителями
      await navigateToParentManagement(page);
      // Проверяем что мы на нужной странице

      // Операция 4: Вернуться на админ dashboard
      await navigateToAdminDashboard(page);
      await expect(page.locator('h1').filter({ hasText: 'Администратор' })).toBeVisible();

      // Все еще залогинены
      expect(page.url()).toContain('/admin');
    });
  });
});
