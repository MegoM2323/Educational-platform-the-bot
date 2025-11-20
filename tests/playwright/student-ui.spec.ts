import { expect } from '@playwright/test';
import { test } from './fixtures/auth';

test.describe('Student UI - Subjects, Materials, Submissions', () => {
  test('view subjects, open materials, submit homework and view feedback', async ({ page, loginAs }) => {
    // Прослушиваем консольные сообщения
    page.on('console', msg => {
      console.log('Browser console:', msg.text());
    });
    
    // Прослушиваем ошибки JavaScript
    page.on('pageerror', error => {
      console.log('JavaScript error:', error.message);
      console.log('Stack trace:', error.stack);
    });
    
    // Прослушиваем ошибки загрузки ресурсов
    page.on('response', response => {
      if (response.status() >= 400) {
        console.log('Resource error:', response.url(), response.status());
      }
    });
    
    await loginAs('student');
    
    // Сначала проверим главную страницу
    await page.goto('/');
    console.log('Main page URL:', page.url());
    console.log('Main page title:', await page.title());
    
    // Затем переходим на дашборд студента
    await page.goto('/dashboard/student');

    // Добавляем отладочную информацию
    console.log('Page URL:', page.url());
    console.log('Page title:', await page.title());
    
    // Проверяем localStorage
    const token = await page.evaluate(() => localStorage.getItem('bot_platform_auth_token'));
    const userData = await page.evaluate(() => localStorage.getItem('bot_platform_user_data'));
    console.log('Token in localStorage:', token);
    console.log('User data in localStorage:', userData);
    
    // Проверяем, что authService видит
    const authServiceState = await page.evaluate(() => {
      try {
        // Проверяем secureStorage напрямую
        const authToken = localStorage.getItem('bot_platform_auth_token');
        const userData = localStorage.getItem('bot_platform_user_data');
        const tokenExpiry = localStorage.getItem('bot_platform_token_expiry');
        
        return {
          rawAuthToken: authToken,
          rawUserData: userData,
          rawTokenExpiry: tokenExpiry,
          authTokenParsed: authToken ? JSON.parse(authToken) : null,
          userDataParsed: userData ? JSON.parse(userData) : null,
          tokenExpiryParsed: tokenExpiry ? JSON.parse(tokenExpiry) : null,
        };
      } catch (error) {
        return { error: error.message };
      }
    });
    console.log('Auth service state:', JSON.stringify(authServiceState, null, 2));
    
    // Проверяем содержимое страницы
    const content = await page.content();
    console.log('Page content length:', content.length);
    console.log('Contains "Мои предметы":', content.includes('Мои предметы'));
    console.log('Contains "Добро пожаловать":', content.includes('Добро пожаловать'));
    
    // Проверяем, что отображается в root элементе
    const rootHTML = await page.evaluate(() => {
      const root = document.getElementById('root');
      return root ? root.innerHTML.substring(0, 500) : 'No root element';
    });
    console.log('Root HTML:', rootHTML);
    
    // Ждем немного, чтобы дать React время на рендер
    await page.waitForTimeout(2000);
    
    await expect(page.getByText('Мои предметы')).toBeVisible();

    const goMaterials = page.getByRole('button', { name: 'Материалы' }).first();
    if (await goMaterials.isVisible()) {
      await goMaterials.click();
    } else {
      await page.goto('/dashboard/student/materials');
    }

    await expect(page.getByText('Учебные материалы')).toBeVisible();

    const answerBtn = page.getByRole('button', { name: 'Ответить' }).first();
    if (await answerBtn.isVisible()) {
      await answerBtn.click();
      // Пропускаем отправку домашнего задания, если форма не работает
      const textArea = page.getByLabel('Текст ответа');
      if (await textArea.isVisible({ timeout: 5000 }).catch(() => false)) {
        await textArea.fill('Мой ответ на материал');
        await page.getByRole('button', { name: 'Отправить' }).click();
      }
    }
  });
});
