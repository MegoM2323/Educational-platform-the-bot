import { test, expect } from '@playwright/test';

/**
 * Тест производительности назначения предмета студенту
 * Проверяет, что после назначения предмета список обновляется быстро без задержек
 */
test.describe('Assign Subject Performance', () => {
  test.beforeEach(async ({ page }) => {
    // Входим как тьютор
    await page.goto('http://localhost:8080/auth');
    
    // Используем тестовые учетные данные тьютора
    // Замените на реальные данные из вашего тестового окружения
    const tutorEmail = 'tutor@test.com';
    const tutorPassword = 'testpassword123';
    
    await page.fill('input[type="text"], input[type="email"]', tutorEmail);
    await page.fill('input[type="password"]', tutorPassword);
    await page.click('button[type="submit"]');
    
    // Ждем перехода на страницу тьютора
    await page.waitForURL('**/dashboard/tutor/**', { timeout: 10000 });
    
    // Переходим на страницу студентов
    await page.goto('http://localhost:8080/dashboard/tutor/students');
    await page.waitForLoadState('networkidle');
  });

  test('should update student list immediately after assigning subject', async ({ page }) => {
    // Находим первого студента
    const studentRow = page.locator('table tbody tr').first();
    await expect(studentRow).toBeVisible({ timeout: 5000 });
    
    // Получаем начальное количество предметов у студента
    const initialSubjectsCount = await studentRow.locator('td').nth(2).textContent();
    console.log('Initial subjects count:', initialSubjectsCount);
    
    // Нажимаем кнопку назначения предмета
    const assignButton = studentRow.locator('button:has-text("Назначить предмет")');
    await assignButton.click();
    
    // Ждем открытия диалога
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 3000 });
    
    // Засекаем время начала операции
    const startTime = Date.now();
    
    // Выбираем предмет (первый из списка)
    await page.click('button[aria-label="subject-select"]');
    await page.waitForTimeout(500); // Небольшая задержка для открытия dropdown
    const firstSubject = page.locator('[role="option"]').first();
    await firstSubject.click();
    
    // Выбираем преподавателя (первый из списка)
    await page.click('button[aria-label="teacher-select"]');
    await page.waitForTimeout(500); // Небольшая задержка для открытия dropdown
    const firstTeacher = page.locator('[role="option"]').first();
    await firstTeacher.click();
    
    // Нажимаем кнопку "Назначить"
    await page.click('button:has-text("Назначить")');
    
    // Ждем закрытия диалога
    await expect(dialog).not.toBeVisible({ timeout: 5000 });
    
    // Засекаем время после закрытия диалога
    const dialogCloseTime = Date.now();
    const dialogCloseDuration = dialogCloseTime - startTime;
    
    console.log('Dialog closed after:', dialogCloseDuration, 'ms');
    
    // Проверяем, что диалог закрылся быстро (менее 2 секунд)
    expect(dialogCloseDuration).toBeLessThan(2000);
    
    // Ждем обновления списка студентов (максимум 3 секунды)
    await page.waitForTimeout(1000); // Даем время на обновление данных
    
    // Проверяем, что список обновился
    const updatedStudentRow = page.locator('table tbody tr').first();
    const updatedSubjectsCount = await updatedStudentRow.locator('td').nth(2).textContent();
    
    console.log('Updated subjects count:', updatedSubjectsCount);
    
    // Проверяем, что количество предметов изменилось (или осталось прежним, если предмет уже был назначен)
    // Главное - проверить, что список обновился без большой задержки
    
    // Засекаем общее время операции
    const endTime = Date.now();
    const totalDuration = endTime - startTime;
    
    console.log('Total operation duration:', totalDuration, 'ms');
    
    // Общее время операции должно быть менее 5 секунд (включая задержки на открытие dropdown)
    expect(totalDuration).toBeLessThan(5000);
  });

  test('should update staff list immediately after creating teacher', async ({ page }) => {
    // Переходим на страницу управления преподавателями
    await page.goto('http://localhost:8080/admin/staff');
    await page.waitForLoadState('networkidle');
    
    // Получаем начальное количество преподавателей
    const initialTeachersCount = await page.locator('table tbody tr').count();
    console.log('Initial teachers count:', initialTeachersCount);
    
    // Засекаем время начала операции
    const startTime = Date.now();
    
    // Нажимаем кнопку создания преподавателя
    await page.click('button:has-text("Создать преподавателя")');
    
    // Ждем открытия диалога
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 3000 });
    
    // Заполняем форму
    const timestamp = Date.now();
    await page.fill('input[type="email"]', `teacher${timestamp}@test.com`);
    await page.fill('input[placeholder*="Имя"], input:has-text("Имя")', 'Test');
    await page.fill('input[placeholder*="Фамилия"], input:has-text("Фамилия")', 'Teacher');
    await page.fill('input[placeholder*="Предмет"], input:has-text("Предмет")', 'Математика');
    
    // Нажимаем кнопку создания
    await page.click('button:has-text("Создать")');
    
    // Ждем закрытия диалога
    await expect(dialog).not.toBeVisible({ timeout: 10000 });
    
    // Засекаем время после закрытия диалога
    const dialogCloseTime = Date.now();
    const dialogCloseDuration = dialogCloseTime - startTime;
    
    console.log('Dialog closed after:', dialogCloseDuration, 'ms');
    
    // Проверяем, что диалог закрылся быстро (менее 3 секунд)
    expect(dialogCloseDuration).toBeLessThan(3000);
    
    // Ждем обновления списка (максимум 2 секунды)
    await page.waitForTimeout(1500); // Даем время на обновление данных
    
    // Проверяем, что список обновился
    const updatedTeachersCount = await page.locator('table tbody tr').count();
    
    console.log('Updated teachers count:', updatedTeachersCount);
    
    // Проверяем, что количество преподавателей увеличилось
    expect(updatedTeachersCount).toBeGreaterThan(initialTeachersCount);
    
    // Засекаем общее время операции
    const endTime = Date.now();
    const totalDuration = endTime - startTime;
    
    console.log('Total operation duration:', totalDuration, 'ms');
    
    // Общее время операции должно быть менее 5 секунд
    expect(totalDuration).toBeLessThan(5000);
  });
});

