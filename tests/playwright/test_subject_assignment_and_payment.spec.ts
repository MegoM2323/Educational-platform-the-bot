import { test, expect } from '@playwright/test';

test.describe('Subject Assignment and Payment Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Переходим на главную страницу
    await page.goto('http://localhost:5173');
  });

  test('Teacher can assign subject to student', async ({ page }) => {
    // Логин как преподаватель
    await page.goto('http://localhost:5173/auth');
    await page.fill('input[name="email"]', 'teacher@test.com');
    await page.fill('input[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Ждем перехода на дашборд
    await page.waitForURL('**/dashboard/teacher');
    
    // Переходим на страницу назначения предметов
    await page.goto('http://localhost:5173/dashboard/teacher/assign-subject');
    await page.waitForSelector('h1:has-text("Назначение предмета")');
    
    // Выбираем предмет
    await page.click('button:has-text("Выберите предмет")');
    await page.click('text=Математика');
    
    // Выбираем студента
    await page.click('input[type="checkbox"]');
    
    // Нажимаем кнопку назначить
    await page.click('button:has-text("Назначить предмет")');
    
    // Проверяем успешное сообщение
    await expect(page.locator('text=Предмет успешно назначен')).toBeVisible({ timeout: 5000 });
  });

  test('Student can see assigned subjects', async ({ page }) => {
    // Логин как студент
    await page.goto('http://localhost:5173/auth');
    await page.fill('input[name="email"]', 'student@test.com');
    await page.fill('input[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Ждем перехода на дашборд
    await page.waitForURL('**/dashboard/student');
    
    // Переходим на страницу предметов
    await page.goto('http://localhost:5173/dashboard/student/subjects');
    await page.waitForSelector('h1:has-text("Мои предметы")');
    
    // Проверяем, что предметы отображаются
    const subjects = page.locator('[data-testid="subject-card"]');
    await expect(subjects.first()).toBeVisible({ timeout: 5000 });
  });

  test('Parent can see child subjects and pay', async ({ page }) => {
    // Логин как родитель
    await page.goto('http://localhost:5173/auth');
    await page.fill('input[name="email"]', 'parent@test.com');
    await page.fill('input[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Ждем перехода на дашборд
    await page.waitForURL('**/dashboard/parent');
    
    // Проверяем, что карточки детей отображаются
    await page.waitForSelector('text=Профили детей', { timeout: 5000 });
    
    // Проверяем, что предметы отображаются в карточках
    const subjectCards = page.locator('text=Математика');
    await expect(subjectCards.first()).toBeVisible({ timeout: 5000 });
    
    // Проверяем наличие кнопки оплаты
    const payButton = page.locator('button:has-text("Оплатить")').first();
    await expect(payButton).toBeVisible({ timeout: 5000 });
  });

  test('Parent can view payment history', async ({ page }) => {
    // Логин как родитель
    await page.goto('http://localhost:5173/auth');
    await page.fill('input[name="email"]', 'parent@test.com');
    await page.fill('input[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Ждем перехода на дашборд
    await page.waitForURL('**/dashboard/parent');
    
    // Переходим на страницу истории платежей
    await page.goto('http://localhost:5173/dashboard/parent/payment-history');
    await page.waitForSelector('h1:has-text("История платежей")', { timeout: 5000 });
    
    // Проверяем, что страница загрузилась
    await expect(page.locator('h1:has-text("История платежей")')).toBeVisible();
  });
});

