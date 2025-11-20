import { expect } from '@playwright/test';
import { test } from './fixtures/auth';

// Предполагается, что пользователь-родитель залогинен

test.describe('Parent UI - Children, Payments, Child Detail', () => {
  test('view children list, initiate payment, open child detail', async ({ page, loginAs }) => {
    await loginAs('parent');
    await page.goto('/dashboard/parent/children');
    
    // Ждем загрузки страницы
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await expect(page.getByRole('heading', { name: 'Мои дети' })).toBeVisible();

    const payBtn = page.getByRole('button', { name: /Оплатить/ }).first();
    if (await payBtn.isVisible()) {
      await payBtn.click();
      await expect(page.getByRole('heading', { name: 'Мои дети' })).toBeVisible();
    }

    const detailsBtn = page.getByRole('button', { name: 'Детали' }).first();
    if (await detailsBtn.isVisible()) {
      await detailsBtn.click();
      await expect(page.getByText('Детали ребенка')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Прогресс' })).toBeVisible();
      await expect(page.getByText('Предметы и оплата')).toBeVisible();
    }
  });
});
