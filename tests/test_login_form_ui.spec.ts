import { test, expect } from '@playwright/test';

test.describe('Login Form UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8080');
  });

  test('should show email input by default', async ({ page }) => {
    // Проверяем, что по умолчанию выбран email
    const emailButton = page.getByRole('button', { name: 'Email' });
    const usernameButton = page.getByRole('button', { name: 'Логин' });
    
    await expect(emailButton).toHaveAttribute('data-state', 'on');
    await expect(usernameButton).not.toHaveAttribute('data-state', 'on');
    
    // Проверяем, что input имеет type="email"
    const input = page.getByLabel('Email');
    await expect(input).toHaveAttribute('type', 'email');
  });

  test('should switch to username input when clicking username button', async ({ page }) => {
    // Кликаем на кнопку "Логин"
    const usernameButton = page.getByRole('button', { name: 'Логин' });
    await usernameButton.click();
    
    // Проверяем, что кнопка "Логин" активна
    await expect(usernameButton).toHaveAttribute('data-state', 'on');
    
    // Проверяем, что label изменился на "Имя пользователя"
    const label = page.getByLabel('Имя пользователя');
    await expect(label).toBeVisible();
    
    // Проверяем, что input имеет type="text"
    const input = page.getByLabel('Имя пользователя');
    await expect(input).toHaveAttribute('type', 'text');
    
    // Проверяем placeholder
    await expect(input).toHaveAttribute('placeholder', 'mylogin');
  });

  test('should switch back to email input when clicking email button', async ({ page }) => {
    // Сначала переключаемся на username
    const usernameButton = page.getByRole('button', { name: 'Логин' });
    await usernameButton.click();
    
    // Потом переключаемся обратно на email
    const emailButton = page.getByRole('button', { name: 'Email' });
    await emailButton.click();
    
    // Проверяем, что кнопка "Email" активна
    await expect(emailButton).toHaveAttribute('data-state', 'on');
    
    // Проверяем, что label изменился на "Email"
    const emailLabel = page.getByLabel('Email');
    await expect(emailLabel).toBeVisible();
    
    // Проверяем, что input имеет type="email"
    const input = page.getByLabel('Email');
    await expect(input).toHaveAttribute('type', 'email');
    
    // Проверяем placeholder
    await expect(input).toHaveAttribute('placeholder', 'example@mail.ru');
  });

  test('should validate email format when email mode is active', async ({ page }) => {
    const emailInput = page.getByLabel('Email');
    
    // Вводим невалидный email
    await emailInput.fill('invalid-email');
    
    // Пытаемся отправить форму
    const submitButton = page.getByRole('button', { name: 'Войти' });
    await submitButton.click();
    
    // Проверяем, что появилось сообщение об ошибке
    const errorToast = page.locator('text=Пожалуйста, введите корректный email адрес');
    await expect(errorToast).toBeVisible();
  });

  test('should not validate email format when username mode is active', async ({ page }) => {
    // Переключаемся на username
    const usernameButton = page.getByRole('button', { name: 'Логин' });
    await usernameButton.click();
    
    const usernameInput = page.getByLabel('Имя пользователя');
    
    // Вводим просто имя (не email)
    await usernameInput.fill('testuser');
    await usernameInput.fill('testuser');  // Дважды для уверенности
    
    // Только поле пароля должно быть пустым для ошибки
    const passwordInput = page.getByLabel('Пароль');
    await passwordInput.fill('testpass123');
    
    // Пытаемся отправить форму
    const submitButton = page.getByRole('button', { name: 'Войти' });
    await submitButton.click();
    
    // Ждем небольшую задержку
    await page.waitForTimeout(500);
    
    // Проверяем, что НЕ появилось сообщение об ошибке валидации email
    const errorToast = page.locator('text=Пожалуйста, введите корректный email адрес');
    await expect(errorToast).not.toBeVisible();
  });
});

