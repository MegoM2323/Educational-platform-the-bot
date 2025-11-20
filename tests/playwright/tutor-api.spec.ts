import { test, expect, request } from '@playwright/test';

const API = (path: string) => `/api/auth${path}`;

test.describe('Tutor API', () => {
  test('create student and assign subject', async ({ baseURL }) => {
    test.skip(!process.env.PLAYWRIGHT_TUTOR_TOKEN, 'No tutor token provided');
    const ctx = await request.newContext({ baseURL });

    // Создание ученика
    const createResp = await ctx.post(API('/tutor/students/'), {
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
      headers: { Authorization: process.env.PLAYWRIGHT_TUTOR_TOKEN || '' },
    });

    expect(createResp.status()).toBeGreaterThanOrEqual(200);
    expect(createResp.status()).toBeLessThan(300);
    const body = await createResp.json();
    expect(body.student).toBeTruthy();

    const profileId = body.student.id as number;

    const subjectId = Number(process.env.PLAYWRIGHT_SUBJECT_ID || 0);
    const teacherId = Number(process.env.PLAYWRIGHT_TEACHER_ID || 0);
    test.skip(subjectId === 0 || teacherId === 0, 'No subject/teacher provided via env');

    const assignResp = await ctx.post(API(`/tutor/students/${profileId}/subjects/`), {
      data: { subject_id: subjectId, teacher_id: teacherId },
      headers: { Authorization: process.env.PLAYWRIGHT_TUTOR_TOKEN || '' },
    });
    expect(assignResp.ok()).toBeTruthy();
  });
});


