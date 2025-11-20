import { test, expect } from '@playwright/test';

test.describe('Landing page interactions', () => {
  test('Hero buttons navigate to application and auth', async ({ page }) => {
    await page.goto('/');

    // Кнопка "Подать заявку" ведет на /application
    await page.getByRole('button', { name: 'Подать заявку' }).first().click();
    await expect(page).toHaveURL(/\/application$/);

    // Возвращаемся на главную
    await page.goto('/');

    // Кнопка "Личный кабинет" ведет на /auth
    await page.getByRole('button', { name: 'Личный кабинет' }).click();
    await expect(page).toHaveURL(/\/auth$/);
  });

  test('Top nav scrolls to sections and login link works', async ({ page }) => {
    await page.goto('/');

    // Ссылка "Возможности" скроллит к секции #features
    await page.locator('header nav a[href="#features"]').click();
    await expect(page.locator('#features')).toBeInViewport();

    // Ссылка "Для кого" скроллит к секции #roles
    await page.locator('header nav a[href="#roles"]').click();
    await expect(page.locator('#roles')).toBeInViewport();

    // Ссылка "Подать заявку" в хедере ведет к секции #apply
    await page.locator('header nav a[href="#apply"]').click();
    await expect(page.locator('#apply')).toBeInViewport();

    // Кнопка "Войти" в хедере ведет на /auth
    await page.getByRole('button', { name: 'Войти' }).click();
    await expect(page).toHaveURL(/\/auth$/);
  });

  test('No broken or dummy links on landing', async ({ page }) => {
    await page.goto('/');

    // Проверяем, что нет <a href=""> или href="#" (кроме валидных якорей #features/#roles/#apply)
    const badLinks = await page.$$eval('a[href]', (links) =>
      links
        .map((a) => (a as HTMLAnchorElement).getAttribute('href') || '')
        .filter((href) => href === '' || href === '#')
    );
    expect(badLinks).toEqual([]);

    // Убеждаемся, что ключевые якорные секции присутствуют
    await expect(page.locator('#features')).toHaveCount(1);
    await expect(page.locator('#roles')).toHaveCount(1);
    await expect(page.locator('#apply')).toHaveCount(1);
  });
});


