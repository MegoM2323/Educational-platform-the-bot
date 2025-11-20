import { test, expect, Page } from '@playwright/test';

/**
 * Тест для проверки доступа к защищенным файлам study plans
 */

const FRONTEND_URL = process.env.VITE_FRONTEND_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_DJANGO_API_URL || 'http://localhost:8000/api';

// Тестовые данные
const TEST_TEACHER = {
  email: 'teacher@test.com',
  password: 'Test123!@#'
};

const TEST_STUDENT = {
  email: 'student@test.com', 
  password: 'Test123!@#'
};

/**
 * Логин пользователя
 */
async function login(page: Page, email: string, password: string) {
  await page.goto(`${FRONTEND_URL}/login`);
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  
  // Ждем редиректа на dashboard
  await page.waitForURL(/\/dashboard/, { timeout: 10000 });
}

test.describe('Защищенные файлы Study Plans', () => {
  test.beforeEach(async ({ page }) => {
    // Очищаем localStorage перед каждым тестом
    await page.goto(FRONTEND_URL);
    await page.evaluate(() => localStorage.clear());
  });

  test('Преподаватель может открыть файл study plan', async ({ page, context }) => {
    // Логинимся как преподаватель
    await login(page, TEST_TEACHER.email, TEST_TEACHER.password);
    
    // Переходим на страницу study plans
    await page.goto(`${FRONTEND_URL}/dashboard/teacher/study-plans`);
    
    // Ждем загрузки планов
    await page.waitForSelector('text=Планы занятий', { timeout: 10000 });
    
    // Проверяем, есть ли планы с файлами
    const fileLinks = await page.locator('a[href*="/media/study_plans/"]').count();
    
    if (fileLinks > 0) {
      console.log(`Найдено ${fileLinks} файлов study plans`);
      
      // Слушаем открытие новой вкладки
      const newPagePromise = context.waitForEvent('page');
      
      // Кликаем на первую ссылку файла
      await page.locator('a[href*="/media/study_plans/"]').first().click();
      
      // Ждем открытия новой вкладки
      const newPage = await newPagePromise;
      await newPage.waitForLoadState('load', { timeout: 10000 });
      
      // Проверяем, что файл открылся (не 404)
      const url = newPage.url();
      console.log('Opened file URL:', url);
      
      // Проверяем, что это blob URL (файл был загружен через нашу утилиту)
      expect(url).toMatch(/^blob:/);
      
      await newPage.close();
    } else {
      console.log('Нет файлов study plans для тестирования');
      test.skip();
    }
  });

  test('Студент может открыть файл study plan', async ({ page, context }) => {
    // Логинимся как студент
    await login(page, TEST_STUDENT.email, TEST_STUDENT.password);
    
    // Переходим на страницу материалов
    await page.goto(`${FRONTEND_URL}/dashboard/student/materials`);
    
    // Ждем загрузки
    await page.waitForSelector('text=Материалы', { timeout: 10000 });
    
    // Проверяем, есть ли планы с файлами
    const studyPlansTab = page.locator('text=Планы занятий');
    if (await studyPlansTab.isVisible()) {
      await studyPlansTab.click();
      
      // Ждем загрузки планов
      await page.waitForTimeout(1000);
      
      const fileLinks = await page.locator('a[href*="/media/study_plans/"]').count();
      
      if (fileLinks > 0) {
        console.log(`Найдено ${fileLinks} файлов study plans`);
        
        // Слушаем открытие новой вкладки
        const newPagePromise = context.waitForEvent('page');
        
        // Кликаем на первую ссылку файла
        await page.locator('a[href*="/media/study_plans/"]').first().click();
        
        // Ждем открытия новой вкладки
        const newPage = await newPagePromise;
        await newPage.waitForLoadState('load', { timeout: 10000 });
        
        // Проверяем, что файл открылся (не 404)
        const url = newPage.url();
        console.log('Opened file URL:', url);
        
        // Проверяем, что это blob URL
        expect(url).toMatch(/^blob:/);
        
        await newPage.close();
      } else {
        console.log('Нет файлов study plans для тестирования');
        test.skip();
      }
    } else {
      console.log('У студента нет планов занятий');
      test.skip();
    }
  });

  test('Неавторизованный пользователь не может получить доступ к файлу напрямую', async ({ page }) => {
    // Пробуем открыть файл напрямую без авторизации
    const response = await page.goto(`${API_URL.replace('/api', '')}/media/study_plans/files/test.pdf`);
    
    // Должны получить 401 или редирект на логин
    if (response) {
      expect([401, 403, 302]).toContain(response.status());
      console.log(`Неавторизованный доступ заблокирован: ${response.status()}`);
    }
  });

  test('Утилита downloadProtectedFile корректно обрабатывает ошибки', async ({ page }) => {
    // Логинимся
    await login(page, TEST_STUDENT.email, TEST_STUDENT.password);
    
    // Инжектируем тест утилиты
    await page.evaluate(async () => {
      const { downloadProtectedFile } = await import('/src/utils/fileDownload.ts');
      
      try {
        // Пробуем скачать несуществующий файл
        await downloadProtectedFile('/media/nonexistent.pdf', 'test.pdf', false);
        return { success: false, error: 'No error thrown' };
      } catch (error: any) {
        // Ожидаем ошибку
        return { success: true, error: error.message };
      }
    });
  });
});

test.describe('Защищенные submission файлы', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate(() => localStorage.clear());
  });

  test('Преподаватель может открыть submission файл', async ({ page, context }) => {
    // Логинимся как преподаватель
    await login(page, TEST_TEACHER.email, TEST_TEACHER.password);
    
    // Переходим на страницу submissions
    await page.goto(`${FRONTEND_URL}/dashboard/teacher/submissions`);
    
    // Ждем загрузки
    await page.waitForSelector('text=Задания на проверку', { timeout: 10000 });
    
    // Проверяем, есть ли кнопки "Открыть файл"
    const openFileButtons = page.locator('button:has-text("Открыть файл")');
    const buttonCount = await openFileButtons.count();
    
    if (buttonCount > 0) {
      console.log(`Найдено ${buttonCount} submission файлов`);
      
      // Слушаем открытие новой вкладки
      const newPagePromise = context.waitForEvent('page');
      
      // Кликаем на первую кнопку
      await openFileButtons.first().click();
      
      // Ждем открытия новой вкладки
      const newPage = await newPagePromise;
      await newPage.waitForLoadState('load', { timeout: 10000 });
      
      // Проверяем, что файл открылся
      const url = newPage.url();
      console.log('Opened submission file URL:', url);
      
      // Проверяем, что это blob URL
      expect(url).toMatch(/^blob:/);
      
      await newPage.close();
    } else {
      console.log('Нет submission файлов для тестирования');
      test.skip();
    }
  });
});

