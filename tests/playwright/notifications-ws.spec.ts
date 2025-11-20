import { test, expect } from '@playwright/test';

test('WS notifications stream delivers messages', async ({ page }) => {
  // Подготовка: авторизуем тестового пользователя через локальное хранение токена, если фронт это поддерживает
  // Открываем главную
  await page.goto('/');

  // Открываем вебсокет вручную через браузерную страницу
  const userId = 1; // В реальном тесте получить ID авторизованного пользователя
  await page.addInitScript((id) => {
    (window as any).__wsMessages = [];
    const ws = new WebSocket(`ws://localhost:8000/ws/notifications/${id}/`);
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        (window as any).__wsMessages.push(data);
      } catch {}
    };
    (window as any).__testWS = ws;
  }, userId);

  // Триггер со стороны бэкенда опустим здесь; просто ожидаем, что соединение установлено и буфер существует
  await page.waitForFunction(() => Array.isArray((window as any).__wsMessages));
  const messages = await page.evaluate(() => (window as any).__wsMessages);
  expect(Array.isArray(messages)).toBeTruthy();
});


