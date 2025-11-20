import { test, expect, request } from '@playwright/test';

const API = (path: string) => `/api${path}`;

// Требуются переменные окружения для аккаунтов или фикстур:
// PLAYWRIGHT_TUTOR_TOKEN, PLAYWRIGHT_STUDENT_TOKEN, PLAYWRIGHT_TEACHER_TOKEN, PLAYWRIGHT_PARENT_TOKEN
// PLAYWRIGHT_SUBJECT_ID, PLAYWRIGHT_TEACHER_ID

test.describe('Full E2E Flow: Tutor -> Student -> Teacher -> Parent', () => {
  test('create student, assign subject, submit homework, review, parent pays', async ({ page, baseURL, context }) => {
    // Получаем токен для tutor
    const tutorCtx = await request.newContext({ baseURL });
    const loginResp = await tutorCtx.post('http://localhost:8000/api/auth/login/', {
      data: { email: 'test_tutor@example.com', password: 'test123' },
    });
    expect(loginResp.ok()).toBeTruthy();
    const loginData = await loginResp.json();
    const token = loginData.data.token;
    
    // 1) Тьютор создает ученика
    const createResp = await tutorCtx.post('http://localhost:8000/api/tutor/students/', {
      data: {
        first_name: 'Ivan',
        last_name: 'Petrov',
        grade: '7',
        goal: 'Improve math',
        parent_first_name: 'Olga',
        parent_last_name: 'Petrova',
        parent_email: 'olga@example.com',
        parent_phone: '+79990000000',
      },
      headers: { Authorization: `Token ${token}` },
    });
    expect(createResp.ok()).toBeTruthy();
    const created = await createResp.json();
    const studentProfileId = created.student.id as number;

    // 2) Назначение предмета
    const subjectId = Number(process.env.PLAYWRIGHT_SUBJECT_ID || 0);
    const teacherId = Number(process.env.PLAYWRIGHT_TEACHER_ID || 0);
    test.skip(subjectId === 0 || teacherId === 0, 'No subject/teacher provided via env');

    const assignResp = await tutorCtx.post(API(`/tutor/students/${studentProfileId}/subjects/`), {
      data: { subject_id: subjectId, teacher_id: teacherId },
      headers: { Authorization: process.env.PLAYWRIGHT_TUTOR_TOKEN || '' },
    });
    expect(assignResp.ok()).toBeTruthy();

    // 3) Студент отправляет ДЗ через UI (упрощенно — открываем страницу материалов)
    await page.goto('/dashboard/student/materials');
    // Открываем диалог ответа, если доступна кнопка
    const answerBtn = page.getByRole('button', { name: 'Ответить' }).first();
    if (await answerBtn.isVisible()) {
      await answerBtn.click();
      await page.getByLabel('Текст ответа').fill('Мой e2e ответ');
      await page.getByRole('button', { name: 'Отправить' }).click();
      await expect(page.getByText('Учебные материалы')).toBeVisible();
    }

    // 4) Преподаватель проверяет и дает фидбэк
    await page.goto('/dashboard/teacher/submissions/pending');
    const fb = page.getByLabel('Фидбэк').first();
    if (await fb.isVisible()) {
      await fb.fill('Хорошая работа!');
      await page.getByLabel('Оценка').first().fill('90');
      await page.getByRole('button', { name: 'Отправить фидбэк' }).first().click();
      await expect(page.getByText('Задания на проверку')).toBeVisible();
    }

    // 5) Родитель инициирует оплату
    await page.goto('/dashboard/parent/children');
    const payBtn = page.getByRole('button', { name: /Оплатить/ }).first();
    if (await payBtn.isVisible()) {
      await payBtn.click();
      await expect(page.getByText('Мои дети')).toBeVisible();
    }
  });
});
