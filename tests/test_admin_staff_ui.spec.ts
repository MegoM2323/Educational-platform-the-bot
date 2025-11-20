import { test, expect } from '@playwright/test';

test.describe('Admin Staff Management Page', () => {
  test.beforeEach(async ({ page }) => {
    // Имитация авторизованного admin пользователя в localStorage
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
  });

  test('opens page and shows tabs and create buttons', async ({ page }) => {
    await page.goto('/admin/staff');

    await expect(page.getByText('Управление преподавателями и тьюторами')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Создать преподавателя' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Создать тьютора' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Преподаватели' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Тьюторы' })).toBeVisible();
  });

  test('open create teacher dialog and validate fields', async ({ page }) => {
    await page.goto('/admin/staff');
    await page.getByRole('button', { name: 'Создать преподавателя' }).click();

    await expect(page.getByText('Создание преподавателя')).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Имя')).toBeVisible();
    await expect(page.getByLabel('Фамилия')).toBeVisible();
    await expect(page.getByLabel('Предмет')).toBeVisible();
  });

  test('open create tutor dialog and validate fields', async ({ page }) => {
    await page.goto('/admin/staff');
    await page.getByRole('button', { name: 'Создать тьютора' }).click();

    await expect(page.getByText('Создание тьютора')).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Имя')).toBeVisible();
    await expect(page.getByLabel('Фамилия')).toBeVisible();
    await expect(page.getByLabel('Специализация')).toBeVisible();
  });
});


