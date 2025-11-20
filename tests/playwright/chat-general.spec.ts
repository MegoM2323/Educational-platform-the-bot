import { expect } from '@playwright/test';
import { test } from './fixtures/auth';

test.describe('General Chat - Realtime messaging', () => {
  test('student can open general chat and send a message', async ({ page, loginAs }) => {
    await loginAs('student');

    await page.goto('/dashboard/student/general-chat');

    await expect(page.getByText('Общий чат')).toBeVisible();

    const message = `Авто-тест сообщение ${Date.now()}`;

    const textarea = page.getByPlaceholder('Введите сообщение...');
    await textarea.fill(message);
    await page.getByRole('button', { name: 'Send' }).click();

    await expect(page.getByText(message).first()).toBeVisible();
  });
});


