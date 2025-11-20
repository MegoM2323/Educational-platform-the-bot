import { test, expect } from '@playwright/test';

test.describe('Admin creates teacher via UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('authToken', 'dev-token');
      localStorage.setItem('userData', JSON.stringify({
        id: 999,
        email: 'admin@example.com',
        first_name: 'Admin',
        last_name: 'User',
        role: 'teacher',
        role_display: 'Преподаватель',
        phone: '+70000000000',
        is_verified: true,
        is_staff: true,
        date_joined: new Date().toISOString(),
        full_name: 'Admin User',
      }));
    });
    await page.goto('http://localhost:8080/admin/staff');
    await expect(page.getByText('Управление преподавателями и тьюторами')).toBeVisible({ timeout: 15000 });
  });

  test('create teacher and show one-time credentials', async ({ page }) => {
    await page.getByRole('button', { name: 'Создать преподавателя' }).click();

    await page.getByLabel('Email').fill(`ui-teacher-${Date.now()}@example.com`);
    await page.getByLabel('Имя').fill('UI');
    await page.getByLabel('Фамилия').fill('Teacher');
    await page.getByLabel('Предмет').fill('Математика');
    await page.getByRole('button', { name: 'Создать' }).click();

    await expect(page.getByText('Учетные данные (показаны один раз)')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Логин (email):')).toBeVisible();
    await expect(page.getByText('Пароль:')).toBeVisible();
  });
});


