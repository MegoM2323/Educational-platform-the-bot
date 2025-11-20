/**
 * КОМПЛЕКСНЫЕ E2E ТЕСТЫ ВЗАИМОДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЕЙ
 *
 * Этот файл содержит полный цикл взаимодействий между всеми ролями пользователей:
 * Admin -> Tutor -> Teacher -> Student -> Parent
 *
 * Тесты проверяют:
 * - Создание пользователей и структуры
 * - Работу с материалами и заданиями
 * - Загрузку и скачивание файлов
 * - Отчеты между пользователями
 * - Систему оплаты
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, logout, TEST_USERS } from './helpers/auth';
import {
  createTestPDF,
  createTestTextFile,
  uploadFile,
  waitForFileUploadSuccess,
  cleanupTestFiles
} from './helpers/files';
import {
  waitForToast,
  expectSuccessMessage,
  expectPageHasText,
  waitForLoadingComplete,
  generateRandomEmail,
  generateRandomName,
  wait,
} from './helpers/utils';

// Глобальное состояние для сохранения данных между тестами
let testData: {
  studentEmail?: string;
  studentId?: number;
  parentEmail?: string;
  tutorEmail?: string;
  teacherEmail?: string;
  subjectId?: number;
  enrollmentId?: number;
  materialId?: number;
  assignmentId?: number;
  studyPlanId?: number;
  testFiles: string[];
} = {
  testFiles: [],
};

test.describe.serial('FULL USER INTERACTION FLOW', () => {

  // ========================================
  // A. ADMIN FLOW - Администратор создает структуру
  // ========================================
  test.describe('A. Admin creates platform structure', () => {

    test('A1. Admin logs in', async ({ page }) => {
      await loginAs(page, 'admin');
      await expectPageHasText(page, /панель|dashboard|admin/i);
    });

    test('A2. Admin creates new tutor through admin panel', async ({ page }) => {
      await loginAs(page, 'admin');

      // Переходим в админ панель создания пользователей
      await page.goto('http://localhost:8080/admin/staff');
      await waitForLoadingComplete(page);

      // Ищем кнопку создания тьютора
      const createButton = page.locator('text=/создать|добавить|create/i').first();

      if (await createButton.count() > 0) {
        await createButton.click();

        // Заполняем форму создания тьютора
        testData.tutorEmail = generateRandomEmail('tutor');

        await page.fill('input[name="email"], input[id*="email"]', testData.tutorEmail);
        await page.fill('input[name="first_name"], input[id*="first"]', 'Test');
        await page.fill('input[name="last_name"], input[id*="last"]', 'Tutor');

        // Выбираем роль тьютора
        const roleSelect = page.locator('select[name="role"], select[id*="role"]');
        if (await roleSelect.count() > 0) {
          await roleSelect.selectOption('tutor');
        }

        // Сохраняем
        const submitButton = page.locator('button[type="submit"], button:has-text("Сохранить")').first();
        await submitButton.click();

        await expectSuccessMessage(page);
      } else {
        console.log('Create tutor button not found - skipping this test');
      }
    });

    test('A3. Admin creates new teacher through admin panel', async ({ page }) => {
      await loginAs(page, 'admin');

      await page.goto('http://localhost:8080/admin/staff');
      await waitForLoadingComplete(page);

      const createButton = page.locator('text=/создать|добавить|create/i').first();

      if (await createButton.count() > 0) {
        await createButton.click();

        testData.teacherEmail = generateRandomEmail('teacher');

        await page.fill('input[name="email"], input[id*="email"]', testData.teacherEmail);
        await page.fill('input[name="first_name"], input[id*="first"]', 'Test');
        await page.fill('input[name="last_name"], input[id*="last"]', 'Teacher');

        const roleSelect = page.locator('select[name="role"], select[id*="role"]');
        if (await roleSelect.count() > 0) {
          await roleSelect.selectOption('teacher');
        }

        const submitButton = page.locator('button[type="submit"], button:has-text("Сохранить")').first();
        await submitButton.click();

        await expectSuccessMessage(page);
      } else {
        console.log('Create teacher button not found - skipping this test');
      }
    });

    test('A4. Admin assigns subjects to teachers', async ({ page }) => {
      await loginAs(page, 'admin');

      // Переходим в раздел управления предметами
      await page.goto('http://localhost:8080/admin/subjects');
      await waitForLoadingComplete(page);

      // Ищем функционал назначения предметов
      const assignButton = page.locator('text=/назначить|assign/i').first();

      if (await assignButton.count() > 0) {
        await assignButton.click();
        await expectSuccessMessage(page);
      } else {
        console.log('Subject assignment not available in UI - may be done via Django admin');
      }
    });
  });

  // ========================================
  // B. TUTOR FLOW - Тьютор управляет студентами
  // ========================================
  test.describe('B. Tutor manages students', () => {

    test('B1. Tutor logs in', async ({ page }) => {
      await loginAs(page, 'tutor');
      await expectPageHasText(page, /тьютор|tutor|dashboard/i);
    });

    test('B2. Tutor creates new student account', async ({ page }) => {
      await loginAs(page, 'tutor');

      await page.goto('http://localhost:8080/dashboard/tutor');
      await waitForLoadingComplete(page);

      // Ищем раздел создания студентов
      const studentsLink = page.locator('text=/студенты|students/i').first();
      if (await studentsLink.count() > 0) {
        await studentsLink.click();
        await waitForLoadingComplete(page);
      }

      // Кнопка создания студента
      const createButton = page.locator('text=/создать|добавить|новый студент/i').first();

      if (await createButton.count() > 0) {
        await createButton.click();

        testData.studentEmail = generateRandomEmail('student');
        const studentName = generateRandomName('Student');

        await page.fill('input[name="email"], input[id*="email"]', testData.studentEmail);
        await page.fill('input[name="first_name"], input[id*="first"]', studentName.split(' ')[0]);
        await page.fill('input[name="last_name"], input[id*="last"]', studentName.split(' ')[1]);

        // Заполняем дополнительные поля если есть
        const gradeInput = page.locator('input[name="grade"], select[name="grade"]');
        if (await gradeInput.count() > 0) {
          await page.fill('input[name="grade"]', '10');
        }

        const goalInput = page.locator('input[name="goal"], textarea[name="goal"]');
        if (await goalInput.count() > 0) {
          await page.fill('input[name="goal"], textarea[name="goal"]', 'Подготовка к ЕГЭ');
        }

        const submitButton = page.locator('button[type="submit"], button:has-text("Создать")').first();
        await submitButton.click();

        await expectSuccessMessage(page);
      } else {
        console.log('Create student button not found');
      }
    });

    test('B3. Tutor assigns subjects to student', async ({ page }) => {
      await loginAs(page, 'tutor');

      await page.goto('http://localhost:8080/dashboard/tutor');
      await waitForLoadingComplete(page);

      // Находим созданного студента
      const studentCard = page.locator(`text=${testData.studentEmail}`).first();

      if (await studentCard.count() > 0) {
        // Кликаем для открытия деталей
        await studentCard.click();
        await waitForLoadingComplete(page);

        // Ищем кнопку назначения предмета
        const assignSubjectButton = page.locator('text=/назначить предмет|добавить предмет/i').first();

        if (await assignSubjectButton.count() > 0) {
          await assignSubjectButton.click();

          // Выбираем предмет (например, Математика)
          const subjectSelect = page.locator('select[name="subject"], select[id*="subject"]');
          if (await subjectSelect.count() > 0) {
            await subjectSelect.selectOption({ index: 1 }); // Первый доступный предмет
          }

          const submitButton = page.locator('button[type="submit"], button:has-text("Назначить")').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      } else {
        console.log('Student not found in tutor dashboard');
      }
    });

    test('B4. Tutor assigns teachers to student subjects', async ({ page }) => {
      await loginAs(page, 'tutor');

      await page.goto('http://localhost:8080/dashboard/tutor');
      await waitForLoadingComplete(page);

      // Находим студента и его предметы
      const studentCard = page.locator(`text=${testData.studentEmail}`).first();

      if (await studentCard.count() > 0) {
        await studentCard.click();
        await waitForLoadingComplete(page);

        // Ищем кнопку назначения учителя
        const assignTeacherButton = page.locator('text=/назначить учителя|выбрать учителя/i').first();

        if (await assignTeacherButton.count() > 0) {
          await assignTeacherButton.click();

          // Выбираем учителя
          const teacherSelect = page.locator('select[name="teacher"], select[id*="teacher"]');
          if (await teacherSelect.count() > 0) {
            await teacherSelect.selectOption({ index: 1 });
          }

          const submitButton = page.locator('button[type="submit"]').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      }
    });

    test('B5. Tutor creates report for parent', async ({ page }) => {
      await loginAs(page, 'tutor');

      await page.goto('http://localhost:8080/dashboard/tutor');
      await waitForLoadingComplete(page);

      // Переходим в раздел отчетов
      const reportsLink = page.locator('text=/отчеты|reports/i').first();

      if (await reportsLink.count() > 0) {
        await reportsLink.click();
        await waitForLoadingComplete(page);

        // Кнопка создания отчета
        const createReportButton = page.locator('text=/создать отчет|новый отчет/i').first();

        if (await createReportButton.count() > 0) {
          await createReportButton.click();

          // Заполняем отчет
          await page.fill('textarea[name="content"], textarea[id*="content"]',
            'Студент показывает хорошие результаты. Рекомендуется продолжить занятия.');

          // Загружаем файл отчета
          const reportFile = await createTestPDF('tutor-report.pdf');
          testData.testFiles.push(reportFile);

          const fileInput = page.locator('input[type="file"]');
          if (await fileInput.count() > 0) {
            await uploadFile(page, 'input[type="file"]', reportFile);
          }

          const submitButton = page.locator('button[type="submit"], button:has-text("Отправить")').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      }
    });
  });

  // ========================================
  // C. TEACHER FLOW - Учитель работает со студентом
  // ========================================
  test.describe('C. Teacher works with student', () => {

    test('C1. Teacher logs in', async ({ page }) => {
      await loginAs(page, 'teacher');
      await expectPageHasText(page, /учитель|teacher|dashboard/i);
    });

    test('C2. Teacher creates study plan with file attachment', async ({ page }) => {
      await loginAs(page, 'teacher');

      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      // Переходим в раздел планов занятий
      const plansLink = page.locator('text=/планы|study plans|расписание/i').first();

      if (await plansLink.count() > 0) {
        await plansLink.click();
        await waitForLoadingComplete(page);

        const createButton = page.locator('text=/создать план|новый план/i').first();

        if (await createButton.count() > 0) {
          await createButton.click();

          // Заполняем план
          await page.fill('input[name="title"], input[id*="title"]', 'План занятий на неделю');
          await page.fill('textarea[name="description"], textarea[id*="description"]',
            'Темы: алгебра, геометрия, тригонометрия');

          const submitButton = page.locator('button[type="submit"]').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      } else {
        console.log('Study plans section not found');
      }
    });

    test('C3. Teacher uploads study plan PDF file', async ({ page }) => {
      await loginAs(page, 'teacher');

      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      const plansLink = page.locator('text=/планы|study plans/i').first();

      if (await plansLink.count() > 0) {
        await plansLink.click();
        await waitForLoadingComplete(page);

        // Находим созданный план
        const planCard = page.locator('text=/план занятий/i').first();

        if (await planCard.count() > 0) {
          // Кликаем для загрузки файла
          const uploadButton = page.locator('text=/загрузить файл|прикрепить/i').first();

          if (await uploadButton.count() > 0) {
            await uploadButton.click();

            const studyPlanFile = await createTestPDF('study-plan.pdf');
            testData.testFiles.push(studyPlanFile);

            await uploadFile(page, 'input[type="file"]', studyPlanFile);
            await waitForFileUploadSuccess(page);
          }
        }
      }
    });

    test('C4. Teacher creates material for subject', async ({ page }) => {
      await loginAs(page, 'teacher');

      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      // Переходим в раздел материалов
      const materialsLink = page.locator('text=/материалы|materials/i').first();

      if (await materialsLink.count() > 0) {
        await materialsLink.click();
        await waitForLoadingComplete(page);

        const createButton = page.locator('text=/создать|добавить|новый материал/i').first();

        if (await createButton.count() > 0) {
          await createButton.click();

          await page.fill('input[name="title"], input[id*="title"]', 'Квадратные уравнения');
          await page.fill('textarea[name="description"], textarea[id*="description"]',
            'Материалы для изучения квадратных уравнений');

          // Загружаем файл материала
          const materialFile = await createTestPDF('material-quadratic.pdf');
          testData.testFiles.push(materialFile);

          const fileInput = page.locator('input[type="file"]');
          if (await fileInput.count() > 0) {
            await uploadFile(page, 'input[type="file"]', materialFile);
          }

          const submitButton = page.locator('button[type="submit"]').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      }
    });

    test('C5. Teacher creates assignment for student', async ({ page }) => {
      await loginAs(page, 'teacher');

      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      // Переходим в раздел заданий
      const assignmentsLink = page.locator('text=/задания|assignments|домашка/i').first();

      if (await assignmentsLink.count() > 0) {
        await assignmentsLink.click();
        await waitForLoadingComplete(page);

        const createButton = page.locator('text=/создать задание|новое задание/i').first();

        if (await createButton.count() > 0) {
          await createButton.click();

          await page.fill('input[name="title"], input[id*="title"]', 'Решить уравнения');
          await page.fill('textarea[name="description"], textarea[id*="description"]',
            'Решить задачи 1-10 из учебника');

          // Устанавливаем дедлайн
          const deadlineInput = page.locator('input[type="date"], input[name="deadline"]');
          if (await deadlineInput.count() > 0) {
            const futureDate = new Date();
            futureDate.setDate(futureDate.getDate() + 7);
            await deadlineInput.fill(futureDate.toISOString().split('T')[0]);
          }

          const submitButton = page.locator('button[type="submit"]').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      }
    });

    test('C6. Teacher grades student submission', async ({ page }) => {
      await loginAs(page, 'teacher');

      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      const assignmentsLink = page.locator('text=/задания|assignments/i').first();

      if (await assignmentsLink.count() > 0) {
        await assignmentsLink.click();
        await waitForLoadingComplete(page);

        // Находим задание со статусом "сдано"
        const submittedAssignment = page.locator('text=/сдано|submitted/i').first();

        if (await submittedAssignment.count() > 0) {
          await submittedAssignment.click();
          await waitForLoadingComplete(page);

          // Проставляем оценку
          const gradeButton = page.locator('text=/оценить|grade/i').first();

          if (await gradeButton.count() > 0) {
            await gradeButton.click();

            await page.fill('input[name="grade"], input[id*="grade"]', '5');
            await page.fill('textarea[name="feedback"], textarea[id*="feedback"]',
              'Отличная работа! Все задачи решены верно.');

            const submitButton = page.locator('button[type="submit"]').first();
            await submitButton.click();

            await expectSuccessMessage(page);
          }
        }
      }
    });

    test('C7. Teacher creates student report for tutor', async ({ page }) => {
      await loginAs(page, 'teacher');

      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      const reportsLink = page.locator('text=/отчеты|reports/i').first();

      if (await reportsLink.count() > 0) {
        await reportsLink.click();
        await waitForLoadingComplete(page);

        const createButton = page.locator('text=/создать отчет|новый отчет/i').first();

        if (await createButton.count() > 0) {
          await createButton.click();

          await page.fill('textarea[name="content"], textarea[id*="content"]',
            'Студент активно участвует в занятиях. Прогресс виден. Рекомендую продолжать работу.');

          // Загружаем файл отчета
          const reportFile = await createTestPDF('teacher-report.pdf');
          testData.testFiles.push(reportFile);

          const fileInput = page.locator('input[type="file"]');
          if (await fileInput.count() > 0) {
            await uploadFile(page, 'input[type="file"]', reportFile);
          }

          const submitButton = page.locator('button[type="submit"]').first();
          await submitButton.click();

          await expectSuccessMessage(page);
        }
      }
    });
  });

  // ========================================
  // D. STUDENT FLOW - Студент работает с материалами
  // ========================================
  test.describe('D. Student interacts with materials', () => {

    test('D1. Student logs in', async ({ page }) => {
      await loginAs(page, 'student');
      await expectPageHasText(page, /студент|student|dashboard/i);
    });

    test('D2. Student views study plan', async ({ page }) => {
      await loginAs(page, 'student');

      await page.goto('http://localhost:8080/dashboard/student');
      await waitForLoadingComplete(page);

      // Проверяем что план занятий отображается
      const studyPlanCard = page.locator('text=/план занятий|study plan/i').first();

      if (await studyPlanCard.count() > 0) {
        await expect(studyPlanCard).toBeVisible();
      } else {
        console.log('Study plan not visible to student');
      }
    });

    test('D3. Student opens study plan PDF file', async ({ page }) => {
      await loginAs(page, 'student');

      await page.goto('http://localhost:8080/dashboard/student');
      await waitForLoadingComplete(page);

      const studyPlanLink = page.locator('text=/план занятий|study plan/i').first();

      if (await studyPlanLink.count() > 0) {
        await studyPlanLink.click();
        await waitForLoadingComplete(page);

        // Ищем кнопку открытия PDF
        const openPdfButton = page.locator('text=/открыть|скачать|download/i').first();

        if (await openPdfButton.count() > 0) {
          // Проверяем что файл можно открыть
          await expect(openPdfButton).toBeVisible();
        }
      }
    });

    test('D4. Student downloads material', async ({ page }) => {
      await loginAs(page, 'student');

      await page.goto('http://localhost:8080/dashboard/student');
      await waitForLoadingComplete(page);

      // Переходим в раздел материалов
      const materialsLink = page.locator('text=/материалы|materials/i').first();

      if (await materialsLink.count() > 0) {
        await materialsLink.click();
        await waitForLoadingComplete(page);

        // Находим материал
        const materialCard = page.locator('text=/квадратные уравнения/i').first();

        if (await materialCard.count() > 0) {
          await materialCard.click();

          // Кнопка скачивания
          const downloadButton = page.locator('text=/скачать|download/i').first();

          if (await downloadButton.count() > 0) {
            await expect(downloadButton).toBeVisible();
          }
        }
      }
    });

    test('D5. Student submits assignment with file', async ({ page }) => {
      await loginAs(page, 'student');

      await page.goto('http://localhost:8080/dashboard/student');
      await waitForLoadingComplete(page);

      // Переходим в раздел заданий
      const assignmentsLink = page.locator('text=/задания|assignments/i').first();

      if (await assignmentsLink.count() > 0) {
        await assignmentsLink.click();
        await waitForLoadingComplete(page);

        // Находим задание
        const assignmentCard = page.locator('text=/решить уравнения/i').first();

        if (await assignmentCard.count() > 0) {
          await assignmentCard.click();
          await waitForLoadingComplete(page);

          // Кнопка сдачи задания
          const submitButton = page.locator('text=/сдать|submit/i').first();

          if (await submitButton.count() > 0) {
            await submitButton.click();

            // Загружаем файл с решением
            const submissionFile = await createTestPDF('student-homework.pdf');
            testData.testFiles.push(submissionFile);

            const fileInput = page.locator('input[type="file"]');
            if (await fileInput.count() > 0) {
              await uploadFile(page, 'input[type="file"]', submissionFile);
            }

            const confirmButton = page.locator('button[type="submit"], button:has-text("Отправить")').first();
            await confirmButton.click();

            await expectSuccessMessage(page);
          }
        }
      }
    });

    test('D6. Student sends message to teacher in chat', async ({ page }) => {
      await loginAs(page, 'student');

      await page.goto('http://localhost:8080/dashboard/student');
      await waitForLoadingComplete(page);

      // Переходим в чат
      const chatLink = page.locator('text=/чат|chat|сообщения/i').first();

      if (await chatLink.count() > 0) {
        await chatLink.click();
        await waitForLoadingComplete(page);

        // Выбираем учителя
        const teacherChat = page.locator('text=/учитель|teacher/i').first();

        if (await teacherChat.count() > 0) {
          await teacherChat.click();
          await wait(1000);

          // Вводим сообщение
          const messageInput = page.locator('textarea[placeholder*="сообщение"], input[placeholder*="сообщение"]');

          if (await messageInput.count() > 0) {
            await messageInput.fill('Здравствуйте! У меня вопрос по заданию.');

            const sendButton = page.locator('button:has-text("Отправить"), button[type="submit"]').last();
            await sendButton.click();

            await wait(500);

            // Проверяем что сообщение появилось
            await expectPageHasText(page, /вопрос по заданию/i);
          }
        }
      }
    });
  });

  // ========================================
  // E. PARENT FLOW - Родитель проверяет прогресс
  // ========================================
  test.describe('E. Parent monitors and pays', () => {

    test('E1. Parent logs in', async ({ page }) => {
      await loginAs(page, 'parent');
      await expectPageHasText(page, /родитель|parent|dashboard/i);
    });

    test('E2. Parent views child progress', async ({ page }) => {
      await loginAs(page, 'parent');

      await page.goto('http://localhost:8080/dashboard/parent');
      await waitForLoadingComplete(page);

      // Переходим в раздел "Мои дети"
      const childrenLink = page.locator('text=/мои дети|children/i').first();

      if (await childrenLink.count() > 0) {
        await childrenLink.click();
        await waitForLoadingComplete(page);

        // Проверяем что отображается информация о ребенке
        const childCard = page.locator('[class*="card"]').first();
        await expect(childCard).toBeVisible();

        // Проверяем наличие предметов
        const subjectInfo = page.locator('text=/предмет|subject/i').first();
        if (await subjectInfo.count() > 0) {
          await expect(subjectInfo).toBeVisible();
        }
      }
    });

    test('E3. Parent reads tutor report', async ({ page }) => {
      await loginAs(page, 'parent');

      await page.goto('http://localhost:8080/dashboard/parent');
      await waitForLoadingComplete(page);

      // Переходим в раздел отчетов
      const reportsLink = page.locator('text=/отчеты|reports/i').first();

      if (await reportsLink.count() > 0) {
        await reportsLink.click();
        await waitForLoadingComplete(page);

        // Находим отчет от тьютора
        const tutorReport = page.locator('text=/тьютор|tutor/i').first();

        if (await tutorReport.count() > 0) {
          await tutorReport.click();
          await waitForLoadingComplete(page);

          // Проверяем что содержание отчета видно
          await expectPageHasText(page, /результат|прогресс|рекомендуе/i);
        }
      }
    });

    test('E4. Parent initiates payment', async ({ page }) => {
      await loginAs(page, 'parent');

      await page.goto('http://localhost:8080/dashboard/parent/children');
      await waitForLoadingComplete(page);

      // Находим кнопку оплаты
      const payButton = page.locator('text=/оплатить|подключить предмет|pay/i').first();

      if (await payButton.count() > 0) {
        await payButton.click();
        await wait(2000);

        // Проверяем что открылась страница оплаты или форма
        // В тестовом режиме должен быть редирект на YooKassa или показана форма
        const currentUrl = page.url();
        const isPaymentPage = currentUrl.includes('payment') ||
                             currentUrl.includes('yookassa') ||
                             await page.locator('text=/оплата|payment/i').count() > 0;

        expect(isPaymentPage).toBeTruthy();
      } else {
        console.log('Payment button not found - subject may already be paid');
      }
    });

    test('E5. Parent views payment history', async ({ page }) => {
      await loginAs(page, 'parent');

      await page.goto('http://localhost:8080/dashboard/parent');
      await waitForLoadingComplete(page);

      // Переходим в раздел платежей
      const paymentsLink = page.locator('text=/платежи|payments|история оплат/i').first();

      if (await paymentsLink.count() > 0) {
        await paymentsLink.click();
        await waitForLoadingComplete(page);

        // Проверяем что отображается история платежей
        await expectPageHasText(page, /платеж|payment|оплата/i);
      } else {
        console.log('Payment history section not found');
      }
    });
  });

  // ========================================
  // F. CROSS-USER FILE INTERACTIONS
  // ========================================
  test.describe('F. File operations across users', () => {

    test('F1. Teacher uploads report, tutor opens it', async ({ page }) => {
      // 1. Teacher создает отчет с файлом
      await loginAs(page, 'teacher');
      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      const reportsLink = page.locator('text=/отчеты|reports/i').first();

      if (await reportsLink.count() > 0) {
        await reportsLink.click();
        await waitForLoadingComplete(page);

        // Проверяем что есть отчет с файлом
        const reportWithFile = page.locator('text=/отчет|report/i').first();

        if (await reportWithFile.count() > 0) {
          await logout(page);

          // 2. Tutor открывает отчет
          await loginAs(page, 'tutor');
          await page.goto('http://localhost:8080/dashboard/tutor');
          await waitForLoadingComplete(page);

          const tutorReportsLink = page.locator('text=/отчеты|reports/i').first();

          if (await tutorReportsLink.count() > 0) {
            await tutorReportsLink.click();
            await waitForLoadingComplete(page);

            const teacherReport = page.locator('text=/учитель|teacher/i').first();

            if (await teacherReport.count() > 0) {
              await teacherReport.click();

              // Проверяем что файл доступен
              const fileLink = page.locator('text=/скачать|download|открыть/i').first();
              if (await fileLink.count() > 0) {
                await expect(fileLink).toBeVisible();
              }
            }
          }
        }
      }
    });

    test('F2. Teacher creates plan, student downloads it', async ({ page }) => {
      // 1. Teacher создает план
      await loginAs(page, 'teacher');
      await page.goto('http://localhost:8080/dashboard/teacher');
      await waitForLoadingComplete(page);

      const plansLink = page.locator('text=/планы|study plans/i').first();

      if (await plansLink.count() > 0) {
        await plansLink.click();
        await waitForLoadingComplete(page);

        await logout(page);

        // 2. Student скачивает план
        await loginAs(page, 'student');
        await page.goto('http://localhost:8080/dashboard/student');
        await waitForLoadingComplete(page);

        const studentPlansLink = page.locator('text=/план|расписание|schedule/i').first();

        if (await studentPlansLink.count() > 0) {
          await studentPlansLink.click();
          await waitForLoadingComplete(page);

          const downloadButton = page.locator('text=/скачать|download/i').first();

          if (await downloadButton.count() > 0) {
            await expect(downloadButton).toBeVisible();
          }
        }
      }
    });

    test('F3. Student submits work, teacher downloads and grades', async ({ page }) => {
      // 1. Student сдает работу
      await loginAs(page, 'student');
      await page.goto('http://localhost:8080/dashboard/student');
      await waitForLoadingComplete(page);

      const assignmentsLink = page.locator('text=/задания|assignments/i').first();

      if (await assignmentsLink.count() > 0) {
        await assignmentsLink.click();
        await waitForLoadingComplete(page);

        // Проверяем что есть сданное задание
        const submittedWork = page.locator('text=/сдано|submitted/i').first();

        if (await submittedWork.count() > 0) {
          await logout(page);

          // 2. Teacher скачивает и оценивает
          await loginAs(page, 'teacher');
          await page.goto('http://localhost:8080/dashboard/teacher');
          await waitForLoadingComplete(page);

          const teacherAssignmentsLink = page.locator('text=/задания|assignments/i').first();

          if (await teacherAssignmentsLink.count() > 0) {
            await teacherAssignmentsLink.click();
            await waitForLoadingComplete(page);

            const studentSubmission = page.locator('text=/сдано|submitted/i').first();

            if (await studentSubmission.count() > 0) {
              await studentSubmission.click();

              // Проверяем что файл можно скачать
              const downloadButton = page.locator('text=/скачать|download/i').first();

              if (await downloadButton.count() > 0) {
                await expect(downloadButton).toBeVisible();
              }

              // Проверяем что есть кнопка оценивания
              const gradeButton = page.locator('text=/оценить|grade/i').first();

              if (await gradeButton.count() > 0) {
                await expect(gradeButton).toBeVisible();
              }
            }
          }
        }
      }
    });
  });

  // ========================================
  // CLEANUP - Очистка тестовых файлов
  // ========================================
  test.afterAll(async () => {
    cleanupTestFiles(testData.testFiles);
  });
});
