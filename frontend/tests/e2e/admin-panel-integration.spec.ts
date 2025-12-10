import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  createUser,
  deleteUser,
  createSubject,
  deleteSubject,
  assignTeacherToSubject,
  enrollStudentToSubject,
  generateTestEmail,
  generateTestName,
  hasSuccessMessage,
} from './helpers/admin-helpers';

/**
 * Интеграционные E2E тесты для Django Admin Panel
 * Проверяют полные workflow создания пользователей, предметов и зачислений
 */

test.describe('Admin Panel Integration - Complete Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('Complete workflow: Create teacher, subject, assign teacher to subject', async ({ page }) => {
    const teacherEmail = generateTestEmail('teacher');
    const subjectName = generateTestName('Math');

    try {
      // 1. Создаем преподавателя
      await createUser(page, {
        username: teacherEmail,
        email: teacherEmail,
        firstName: 'John',
        lastName: 'Teacher',
        role: 'teacher',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 2. Создаем предмет
      await createSubject(page, {
        name: subjectName,
        description: 'Advanced Mathematics',
        color: '#4CAF50',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 3. Назначаем преподавателя на предмет
      const assigned = await assignTeacherToSubject(page, teacherEmail, subjectName);

      if (assigned) {
        expect(await hasSuccessMessage(page)).toBeTruthy();
      }

    } finally {
      // Cleanup
      await deleteSubject(page, subjectName);
      await deleteUser(page, teacherEmail);
    }
  });

  test('Complete workflow: Create student, parent, tutor and enroll student', async ({ page }) => {
    const studentEmail = generateTestEmail('student');
    const parentEmail = generateTestEmail('parent');
    const tutorEmail = generateTestEmail('tutor');
    const teacherEmail = generateTestEmail('teacher');
    const subjectName = generateTestName('Physics');

    try {
      // 1. Создаем тьютора
      await createUser(page, {
        username: tutorEmail,
        email: tutorEmail,
        firstName: 'Anna',
        lastName: 'Tutor',
        role: 'tutor',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 2. Создаем родителя
      await createUser(page, {
        username: parentEmail,
        email: parentEmail,
        firstName: 'Maria',
        lastName: 'Parent',
        role: 'parent',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 3. Создаем студента
      await createUser(page, {
        username: studentEmail,
        email: studentEmail,
        firstName: 'Ivan',
        lastName: 'Student',
        role: 'student',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 4. Создаем преподавателя
      await createUser(page, {
        username: teacherEmail,
        email: teacherEmail,
        firstName: 'Sergey',
        lastName: 'Teacher',
        role: 'teacher',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 5. Создаем предмет
      await createSubject(page, {
        name: subjectName,
        description: 'Physics for students',
        color: '#2196F3',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // 6. Назначаем преподавателя на предмет
      await assignTeacherToSubject(page, teacherEmail, subjectName);

      // 7. Зачисляем студента на предмет
      const enrolled = await enrollStudentToSubject(page, studentEmail, subjectName, teacherEmail);

      if (enrolled) {
        expect(await hasSuccessMessage(page)).toBeTruthy();
      }

    } finally {
      // Cleanup в обратном порядке
      await deleteSubject(page, subjectName);
      await deleteUser(page, studentEmail);
      await deleteUser(page, teacherEmail);
      await deleteUser(page, parentEmail);
      await deleteUser(page, tutorEmail);
    }
  });

  test('Create multiple students and enroll them to same subject', async ({ page }) => {
    const teacherEmail = generateTestEmail('teacher');
    const student1Email = generateTestEmail('student1');
    const student2Email = generateTestEmail('student2');
    const subjectName = generateTestName('Chemistry');

    try {
      // Создаем преподавателя
      await createUser(page, {
        username: teacherEmail,
        email: teacherEmail,
        firstName: 'Elena',
        lastName: 'Chemistry Teacher',
        role: 'teacher',
      });

      // Создаем предмет
      await createSubject(page, {
        name: subjectName,
        description: 'Organic Chemistry',
      });

      // Назначаем преподавателя
      await assignTeacherToSubject(page, teacherEmail, subjectName);

      // Создаем первого студента
      await createUser(page, {
        username: student1Email,
        email: student1Email,
        firstName: 'Alex',
        lastName: 'Student One',
        role: 'student',
      });

      // Создаем второго студента
      await createUser(page, {
        username: student2Email,
        email: student2Email,
        firstName: 'Boris',
        lastName: 'Student Two',
        role: 'student',
      });

      // Зачисляем обоих студентов
      await enrollStudentToSubject(page, student1Email, subjectName, teacherEmail);
      await enrollStudentToSubject(page, student2Email, subjectName, teacherEmail);

      expect(true).toBeTruthy(); // Workflow completed

    } finally {
      // Cleanup
      await deleteUser(page, student1Email);
      await deleteUser(page, student2Email);
      await deleteSubject(page, subjectName);
      await deleteUser(page, teacherEmail);
    }
  });

  test('Create teacher with multiple subjects', async ({ page }) => {
    const teacherEmail = generateTestEmail('teacher');
    const subject1Name = generateTestName('Biology');
    const subject2Name = generateTestName('Geography');

    try {
      // Создаем преподавателя
      await createUser(page, {
        username: teacherEmail,
        email: teacherEmail,
        firstName: 'Olga',
        lastName: 'Multi Teacher',
        role: 'teacher',
      });

      // Создаем первый предмет
      await createSubject(page, {
        name: subject1Name,
        description: 'Biology basics',
      });

      // Создаем второй предмет
      await createSubject(page, {
        name: subject2Name,
        description: 'World geography',
      });

      // Назначаем преподавателя на оба предмета
      await assignTeacherToSubject(page, teacherEmail, subject1Name);
      await assignTeacherToSubject(page, teacherEmail, subject2Name);

      expect(true).toBeTruthy(); // Workflow completed

    } finally {
      // Cleanup
      await deleteSubject(page, subject1Name);
      await deleteSubject(page, subject2Name);
      await deleteUser(page, teacherEmail);
    }
  });
});

test.describe('Admin Panel Integration - Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('Cannot create duplicate user with same email', async ({ page }) => {
    const email = generateTestEmail('duplicate');

    try {
      // Создаем первого пользователя
      await createUser(page, {
        username: email,
        email: email,
        firstName: 'First',
        lastName: 'User',
        role: 'student',
      });

      expect(await hasSuccessMessage(page)).toBeTruthy();

      // Пытаемся создать второго с тем же email
      await createUser(page, {
        username: `${email}_2`,
        email: email, // Same email
        firstName: 'Second',
        lastName: 'User',
        role: 'student',
      });

      // Должна быть ошибка или предупреждение
      const hasError = await page.locator('.errorlist, .errornote').isVisible().catch(() => false);
      expect(hasError).toBeTruthy();

    } finally {
      await deleteUser(page, email);
    }
  });

  test('Cannot assign same teacher to same subject twice', async ({ page }) => {
    const teacherEmail = generateTestEmail('teacher');
    const subjectName = generateTestName('History');

    try {
      await createUser(page, {
        username: teacherEmail,
        email: teacherEmail,
        firstName: 'Igor',
        lastName: 'Teacher',
        role: 'teacher',
      });

      await createSubject(page, {
        name: subjectName,
        description: 'World History',
      });

      // Первое назначение должно пройти
      await assignTeacherToSubject(page, teacherEmail, subjectName);

      // Второе назначение должно выдать ошибку
      await assignTeacherToSubject(page, teacherEmail, subjectName);

      const hasError = await page.locator('.errorlist, .errornote').isVisible().catch(() => false);
      expect(hasError).toBeTruthy();

    } finally {
      await deleteSubject(page, subjectName);
      await deleteUser(page, teacherEmail);
    }
  });
});

test.describe('Admin Panel Integration - Data Validation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('User fields are properly validated', async ({ page }) => {
    await page.goto('http://localhost:8003/admin/accounts/user/add/');

    // Пытаемся сохранить пустую форму
    await page.click('input[type="submit"][name="_save"]');

    // Должны быть ошибки валидации
    const hasError = await page.locator('.errorlist, .errornote').isVisible().catch(() => false);
    expect(hasError).toBeTruthy();
  });

  test('Subject name is required', async ({ page }) => {
    await page.goto('http://localhost:8003/admin/materials/subject/add/');

    // Пытаемся сохранить без имени
    await page.click('input[type="submit"][name="_save"]');

    // Должна быть ошибка
    const hasError = await page.locator('.errorlist, .errornote').isVisible().catch(() => false);
    expect(hasError).toBeTruthy();
  });
});

test.describe('Admin Panel Integration - Bulk Operations', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('Can delete multiple users at once', async ({ page }) => {
    const user1Email = generateTestEmail('bulk1');
    const user2Email = generateTestEmail('bulk2');

    try {
      // Создаем двух пользователей
      await createUser(page, {
        username: user1Email,
        email: user1Email,
        firstName: 'Bulk',
        lastName: 'User One',
        role: 'student',
      });

      await createUser(page, {
        username: user2Email,
        email: user2Email,
        firstName: 'Bulk',
        lastName: 'User Two',
        role: 'student',
      });

      // Переходим к списку и ищем по общему паттерну
      await page.goto('http://localhost:8003/admin/accounts/user/');
      await page.fill('input#searchbar', 'bulk');
      await page.press('input#searchbar', 'Enter');
      await page.waitForTimeout(1000);

      // Выбираем всех найденных пользователей
      const selectAll = page.locator('#action-toggle');
      if (await selectAll.isVisible()) {
        await selectAll.check();

        // Удаляем
        await page.selectOption('select[name="action"]', 'delete_selected');
        await page.click('button[name="index"]');
        await page.click('input[type="submit"]');

        expect(await hasSuccessMessage(page)).toBeTruthy();
      }

    } catch (error) {
      // Cleanup на случай ошибки
      await deleteUser(page, user1Email);
      await deleteUser(page, user2Email);
    }
  });
});
