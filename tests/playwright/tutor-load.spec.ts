import { test, expect, request } from '@playwright/test';

const API = (path: string) => `/api${path}`;

// Параметры нагрузки через env: PLAYWRIGHT_LOAD_STUDENTS=10

test.describe('Tutor Load - Create multiple students', () => {
  test('create N students in parallel', async ({ baseURL }) => {
    const count = Number(process.env.PLAYWRIGHT_LOAD_STUDENTS || 5);
    const ctx = await request.newContext({ baseURL: 'http://localhost:8000' });

    // Получаем токен для tutor
    const loginResp = await ctx.post('http://localhost:8000/api/auth/login/', {
      data: { email: 'test_tutor@example.com', password: 'test123' },
    });
    expect(loginResp.ok()).toBeTruthy();
    const loginData = await loginResp.json();
    const token = loginData.data.token;

    const results = [];
    for (let i = 0; i < count; i++) {
      const res = await ctx.post(API('/tutor/students/'), {
        data: {
          first_name: `Load${i}`,
          last_name: `Test${i}`,
          grade: String(5 + (i % 6)),
          goal: 'Load test creation',
          parent_first_name: `P${i}`,
          parent_last_name: `L${i}`,
          parent_email: `parent${i}@example.com`,
          parent_phone: `+7999000${(1000 + i).toString()}`,
        },
        headers: { Authorization: `Token ${token}` },
      });
      results.push(res);
    }
    for (let i = 0; i < results.length; i++) {
      const res = results[i];
      console.log(`Request ${i}: Status ${res.status()}, OK: ${res.ok()}`);
      if (!res.ok()) {
        const text = await res.text();
        console.log(`Error response: ${text}`);
      }
      expect(res.ok()).toBeTruthy();
    }
  });
});
