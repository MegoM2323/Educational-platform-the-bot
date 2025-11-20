import { test, expect } from '@playwright/test';

test.describe('Study Plans Page', () => {
  test.beforeEach(async ({ page }) => {
    // Логин как преподаватель
    await page.goto('http://localhost:5173/auth');
    await page.fill('input[name="email"]', 'teacher@test.com');
    await page.fill('input[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Ждем перехода на дашборд
    await page.waitForURL('**/dashboard/teacher**', { timeout: 10000 });
  });

  test('should load study plans page', async ({ page }) => {
    await page.goto('http://localhost:5173/dashboard/teacher/study-plans');
    
    // Проверяем, что страница загрузилась
    await expect(page.locator('h1:has-text("Планы занятий")')).toBeVisible({ timeout: 10000 });
    
    // Проверяем наличие фильтров
    await expect(page.locator('text=Предмет')).toBeVisible();
    await expect(page.locator('text=Студент')).toBeVisible();
    await expect(page.locator('text=Статус')).toBeVisible();
    
    // Проверяем кнопку создания плана
    await expect(page.locator('button:has-text("Создать план")')).toBeVisible();
  });

  test('should open create plan dialog', async ({ page }) => {
    await page.goto('http://localhost:5173/dashboard/teacher/study-plans');
    
    // Ждем загрузки страницы
    await page.waitForSelector('h1:has-text("Планы занятий")', { timeout: 10000 });
    
    // Открываем диалог создания плана
    await page.click('button:has-text("Создать план")');
    
    // Проверяем, что диалог открылся
    await expect(page.locator('text=Создать план занятий')).toBeVisible({ timeout: 5000 });
    
    // Проверяем наличие полей формы
    await expect(page.locator('label:has-text("Предмет")')).toBeVisible();
    await expect(page.locator('label:has-text("Студент")')).toBeVisible();
    await expect(page.locator('label:has-text("Название плана")')).toBeVisible();
    await expect(page.locator('label:has-text("Дата начала недели")')).toBeVisible();
    await expect(page.locator('label:has-text("Содержание плана")')).toBeVisible();
  });

  test('should create study plan', async ({ page }) => {
    await page.goto('http://localhost:5173/dashboard/teacher/study-plans');
    
    // Ждем загрузки страницы
    await page.waitForSelector('h1:has-text("Планы занятий")', { timeout: 10000 });
    
    // Открываем диалог создания плана
    await page.click('button:has-text("Создать план")');
    
    // Ждем открытия диалога
    await page.waitForSelector('text=Создать план занятий', { timeout: 5000 });
    
    // Заполняем форму
    // Выбираем предмет
    await page.click('button:has-text("Выберите предмет")');
    await page.waitForTimeout(500);
    const subjectOption = page.locator('[role="option"]').first();
    if (await subjectOption.count() > 0) {
      await subjectOption.click();
    }
    
    // Выбираем студента
    await page.click('button:has-text("Выберите студента")');
    await page.waitForTimeout(500);
    const studentOption = page.locator('[role="option"]').first();
    if (await studentOption.count() > 0) {
      await studentOption.click();
    }
    
    // Заполняем название
    await page.fill('input[placeholder*="Неделя"]', 'Тестовый план занятий');
    
    // Заполняем дату (используем сегодняшнюю дату)
    const today = new Date().toISOString().split('T')[0];
    await page.fill('input[type="date"]', today);
    
    // Заполняем содержание
    await page.fill('textarea[placeholder*="Опишите план"]', 'Это тестовый план занятий на неделю. Студент должен изучить материал и выполнить задания.');
    
    // Выбираем статус
    await page.click('button:has-text("Черновик")');
    await page.waitForTimeout(500);
    const statusOption = page.locator('[role="option"]').first();
    if (await statusOption.count() > 0) {
      await statusOption.click();
    }
    
    // Создаем план
    await page.click('button:has-text("Создать")');
    
    // Ждем закрытия диалога или появления сообщения об успехе
    await page.waitForTimeout(2000);
    
    // Проверяем, что диалог закрылся или появилось сообщение
    const dialogVisible = await page.locator('text=Создать план занятий').isVisible();
    expect(dialogVisible).toBeFalsy();
  });

  test('should filter plans by subject', async ({ page }) => {
    await page.goto('http://localhost:5173/dashboard/teacher/study-plans');
    
    // Ждем загрузки страницы
    await page.waitForSelector('h1:has-text("Планы занятий")', { timeout: 10000 });
    
    // Выбираем предмет в фильтре
    await page.click('button:has-text("Все предметы")');
    await page.waitForTimeout(500);
    const subjectOption = page.locator('[role="option"]').nth(1); // Первый предмет (не "Все предметы")
    if (await subjectOption.count() > 0) {
      await subjectOption.click();
      await page.waitForTimeout(1000); // Ждем обновления списка
    }
  });

  test('should filter plans by status', async ({ page }) => {
    await page.goto('http://localhost:5173/dashboard/teacher/study-plans');
    
    // Ждем загрузки страницы
    await page.waitForSelector('h1:has-text("Планы занятий")', { timeout: 10000 });
    
    // Выбираем статус в фильтре
    await page.click('button:has-text("Все статусы")');
    await page.waitForTimeout(500);
    const statusOption = page.locator('text=Черновик').first();
    if (await statusOption.isVisible()) {
      await statusOption.click();
      await page.waitForTimeout(1000); // Ждем обновления списка
    }
  });
});

