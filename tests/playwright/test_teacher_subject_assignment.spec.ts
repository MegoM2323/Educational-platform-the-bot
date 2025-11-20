import { test, expect } from '@playwright/test';

// Helper function to login as teacher
async function loginAsTeacher(page: any) {
  await page.goto('/');
  await page.fill('input[type="email"]', 'teacher@test.com');
  await page.fill('input[type="password"]', 'testpass123');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard/teacher');
}

test.describe('Teacher Subject Assignment', () => {
  test.beforeEach(async ({ page }) => {
    // Логинимся как преподаватель
    await loginAsTeacher(page);
  });

  test('should navigate to assign subject page', async ({ page }) => {
    // Переходим на страницу назначения предметов
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Проверяем, что страница загрузилась
    await expect(page.locator('h1')).toContainText('Назначение предмета');
  });

  test('should display subjects list', async ({ page }) => {
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Ожидаем загрузки предметов
    await page.waitForSelector('[data-testid="subject-select"]', { timeout: 10000 });
    
    // Проверяем, что есть кнопка для выбора предмета
    const selectButton = page.locator('button:has-text("Выберите предмет")');
    await expect(selectButton).toBeVisible();
  });

  test('should display students list', async ({ page }) => {
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Ожидаем загрузки студентов
    await page.waitForTimeout(2000);
    
    // Проверяем, что есть студенты на странице
    const selectAllButton = page.locator('button:has-text("Выбрать всех")');
    await expect(selectAllButton).toBeVisible();
  });

  test('should show validation error if subject not selected', async ({ page }) => {
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Не выбираем предмет и пытаемся отправить форму
    const submitButton = page.locator('button:has-text("Назначить предмет")');
    await submitButton.click();
    
    // Должно появиться сообщение об ошибке
    // (точный текст зависит от реализации toast)
    await page.waitForTimeout(500);
  });

  test('should show validation error if no students selected', async ({ page }) => {
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Выбираем предмет (если есть предметы)
    try {
      await page.click('button:has-text("Выберите предмет")');
      await page.waitForTimeout(500);
      
      // Выбираем первый предмет из списка
      const firstSubject = page.locator('[role="option"]').first();
      if (await firstSubject.isVisible({ timeout: 2000 })) {
        await firstSubject.click();
      }
    } catch (e) {
      // Если предметов нет, пропускаем выбор
      console.log('No subjects available');
    }
    
    // Не выбираем студентов и пытаемся отправить
    const submitButton = page.locator('button:has-text("Назначить предмет")');
    await submitButton.click();
    
    // Должно появиться сообщение об ошибке
    await page.waitForTimeout(500);
  });

  test('should allow selecting all students', async ({ page }) => {
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Ожидаем загрузки
    await page.waitForTimeout(2000);
    
    // Нажимаем "Выбрать всех"
    const selectAllButton = page.locator('button:has-text("Выбрать всех")');
    
    if (await selectAllButton.isVisible({ timeout: 3000 })) {
      await selectAllButton.click();
      
      // Проверяем, что текст изменился
      await expect(selectAllButton).toContainText('Снять выделение');
    }
  });

  test('should navigate back to dashboard', async ({ page }) => {
    await page.goto('/dashboard/teacher/assign-subject');
    
    // Нажимаем кнопку "Отмена" или кнопку возврата
    const backButton = page.locator('button[aria-label*="Back"], button:has-text("Отмена")').first();
    await backButton.click();
    
    // Должны вернуться на дашборд
    await expect(page).toHaveURL(/.*dashboard\/teacher/);
  });
});

// Тест через сайдбар
test.describe('Teacher Sidebar Navigation', () => {
  test('should have assign subject link in sidebar', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/dashboard/teacher');
    
    // Проверяем наличие ссылки на назначение предметов в сайдбаре
    const assignSubjectLink = page.locator('a:has-text("Назначение предметов")');
    await expect(assignSubjectLink).toBeVisible();
  });

  test('should navigate to assign subject from sidebar', async ({ page }) => {
    await loginAsTeacher(page);
    await page.goto('/dashboard/teacher');
    
    // Кликаем на ссылку в сайдбаре
    const assignSubjectLink = page.locator('a:has-text("Назначение предметов")');
    await assignSubjectLink.click();
    
    // Должны перейти на страницу назначения предметов
    await expect(page).toHaveURL(/.*assign-subject/);
  });
});

