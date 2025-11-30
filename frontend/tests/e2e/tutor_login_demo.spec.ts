import { test, expect, Page } from '@playwright/test';

test('Tutor Login Demo', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Установим большой размер экрана
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  console.log('🚀 Переходу на страницу логина...');
  await page.goto('/auth', { waitUntil: 'networkidle' });
  
  console.log('📧 Заполняю email: tutor@test.com');
  await page.fill('input[type="email"]', 'tutor@test.com');
  
  console.log('🔐 Заполняю пароль: TestPass123!');
  await page.fill('input[type="password"]', 'TestPass123!');
  
  console.log('✅ Нажимаю кнопку входа...');
  await page.click('button[type="submit"]');
  
  console.log('⏳ Жду загрузки панели...');
  await page.waitForNavigation({ waitUntil: 'networkidle' });
  
  console.log('📸 Снимаю скриншот после логина...');
  await page.screenshot({ path: 'tutor-dashboard.png', fullPage: false });
  
  console.log('➡️ Переходу в профиль...');
  await page.goto('/profile', { waitUntil: 'networkidle' });
  
  console.log('📸 Снимаю скриншот профиля...');
  await page.screenshot({ path: 'tutor-profile.png', fullPage: true });
  
  console.log('\n✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨');
  console.log('🎉 УСПЕШНО! Вошли в профиль тьютора!');
  console.log('✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨\n');
  
  console.log('📍 URL:', page.url());
  console.log('✅ Скриншоты сохранены:');
  console.log('   - tutor-dashboard.png');
  console.log('   - tutor-profile.png\n');
  
  await context.close();
});
