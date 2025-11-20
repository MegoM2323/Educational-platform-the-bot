import { expect } from '@playwright/test';
import { test } from './fixtures/auth';

// Предполагается, что пользователь-преподаватель залогинен

test.describe('Teacher UI - Review submissions', () => {
  test('open pending submissions and provide feedback', async ({ page, loginAs }) => {
    await loginAs('teacher');
    await page.goto('/dashboard/teacher/submissions/pending');

    // Отладка: проверим, что показывается на странице
    await page.waitForTimeout(2000);
    console.log('Page URL:', page.url());
    console.log('Page title:', await page.title());
    const bodyText = await page.locator('body').innerText();
    console.log('Body contains "Задания":', bodyText.includes('Задания'));
    console.log('Body contains "проверку":', bodyText.includes('проверку'));
    console.log('Body contains "Добро пожаловать":', bodyText.includes('Добро пожаловать'));

    await expect(page.getByText('Задания на проверку')).toBeVisible();

    const provideBtn = page.getByRole('button', { name: 'Отправить фидбэк' }).first();
    if (await provideBtn.isVisible()) {
      const feedbackArea = page.getByLabel('Фидбэк').first();
      await feedbackArea.fill('Отличная работа!');
      const gradeInput = page.getByLabel('Оценка').first();
      await gradeInput.fill('95');
      await provideBtn.click();
      await expect(page.getByText('Задания на проверку')).toBeVisible();
    }
  });
});
