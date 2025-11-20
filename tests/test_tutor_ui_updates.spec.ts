import { test, expect } from '@playwright/test';

/**
 * Тест проверяет обновление UI в личном кабинете тьютора:
 * 1. Создание нового ученика должно отображаться в списке
 * 2. Назначение предмета должно обновлять список назначенных предметов
 */

test.describe('Tutor Dashboard - UI Updates', () => {
  
  test.beforeEach(async ({ page }) => {
    // Логин как тьютор
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="text"]', 'tutor1');
    await page.fill('input[type="password"]', 'tutor123');
    await page.click('button[type="submit"]');
    
    // Ждем перенаправления на dashboard тьютора
    await page.waitForURL('**/tutor/students', { timeout: 10000 });
    await expect(page.locator('text=Мои ученики')).toBeVisible({ timeout: 5000 });
  });

  test('should display newly created student in the list', async ({ page }) => {
    console.log('[Test] Starting student creation test');
    
    // Получаем текущее количество студентов
    const studentCards = page.locator('[class*="Card"]:has-text("Класс:")');
    const initialCount = await studentCards.count();
    console.log(`[Test] Initial students count: ${initialCount}`);
    
    // Нажимаем кнопку создания ученика
    await page.click('button:has-text("Создать ученика")');
    
    // Ждем открытия диалога
    await expect(page.locator('text=Создание ученика')).toBeVisible({ timeout: 3000 });
    
    // Заполняем форму
    const timestamp = Date.now();
    await page.fill('#first_name', `Тестовый${timestamp}`);
    await page.fill('#last_name', `Ученик${timestamp}`);
    await page.fill('#grade', '7А');
    await page.fill('#goal', 'Тестовая цель');
    await page.fill('#parent_first_name', `Родитель${timestamp}`);
    await page.fill('#parent_last_name', `Фамилия${timestamp}`);
    await page.fill('#parent_email', `parent${timestamp}@test.com`);
    await page.fill('#parent_phone', '+79991234567');
    
    // Отправляем форму
    await page.click('button:has-text("Создать")');
    
    // Ждем закрытия первого диалога и открытия диалога с учетными данными
    await expect(page.locator('text=Сгенерированные учетные данные')).toBeVisible({ timeout: 5000 });
    
    // Закрываем диалог с учетными данными
    await page.click('button:has-text("Закрыть")');
    
    // Ждем закрытия диалога
    await expect(page.locator('text=Сгенерированные учетные данные')).not.toBeVisible({ timeout: 3000 });
    
    // Ждем обновления списка студентов
    await page.waitForTimeout(1000);
    
    // Проверяем, что количество студентов увеличилось
    const updatedCount = await studentCards.count();
    console.log(`[Test] Updated students count: ${updatedCount}`);
    expect(updatedCount).toBe(initialCount + 1);
    
    // Проверяем, что новый студент отображается
    const newStudentName = `Тестовый${timestamp} Ученик${timestamp}`;
    await expect(page.locator(`text=${newStudentName}`)).toBeVisible({ timeout: 3000 });
    
    console.log('[Test] ✓ New student is displayed in the list');
  });

  test('should update subjects list after assigning a subject', async ({ page }) => {
    console.log('[Test] Starting subject assignment test');
    
    // Находим первую карточку студента
    const studentCard = page.locator('[class*="Card"]:has-text("Класс:")').first();
    await expect(studentCard).toBeVisible({ timeout: 5000 });
    
    // Проверяем текущее состояние предметов
    const hasSubjects = await studentCard.locator('text=/Назначенные предметы/').count() > 0;
    let initialSubjectsCount = 0;
    
    if (hasSubjects) {
      const subjectsText = await studentCard.locator('text=/Назначенные предметы \\((\\d+)\\)/').textContent();
      const match = subjectsText?.match(/\((\d+)\)/);
      if (match) {
        initialSubjectsCount = parseInt(match[1]);
      }
    }
    
    console.log(`[Test] Initial subjects count: ${initialSubjectsCount}`);
    
    // Нажимаем кнопку "Назначить предмет"
    await studentCard.locator('button:has-text("Назначить предмет")').click();
    
    // Ждем открытия диалога
    await expect(page.locator('text=Назначить предмет').first()).toBeVisible({ timeout: 3000 });
    
    // Выбираем существующий предмет
    const subjectSelect = page.locator('[aria-label="subject-select"]');
    await subjectSelect.click();
    await page.waitForTimeout(500);
    
    // Выбираем первый предмет
    const firstSubjectOption = page.locator('div[role="option"]').first();
    await expect(firstSubjectOption).toBeVisible({ timeout: 3000 });
    const subjectName = await firstSubjectOption.textContent();
    console.log(`[Test] Selected subject: ${subjectName}`);
    await firstSubjectOption.click();
    
    // Выбираем преподавателя
    const teacherSelect = page.locator('[aria-label="teacher-select"]');
    await teacherSelect.click();
    await page.waitForTimeout(500);
    
    // Выбираем первого преподавателя
    const firstTeacherOption = page.locator('div[role="option"]').first();
    await expect(firstTeacherOption).toBeVisible({ timeout: 3000 });
    const teacherName = await firstTeacherOption.textContent();
    console.log(`[Test] Selected teacher: ${teacherName}`);
    await firstTeacherOption.click();
    
    // Нажимаем кнопку "Назначить"
    await page.locator('button:has-text("Назначить")').click();
    
    // Ждем закрытия диалога
    await expect(page.locator('text=Назначить предмет').first()).not.toBeVisible({ timeout: 5000 });
    
    // Ждем toast с успешным сообщением
    await expect(page.locator('text=/Предмет успешно назначен/i')).toBeVisible({ timeout: 5000 });
    
    // Ждем обновления данных
    await page.waitForTimeout(1000);
    
    // Проверяем, что список предметов обновился
    const updatedStudentCard = page.locator('[class*="Card"]:has-text("Класс:")').first();
    await expect(updatedStudentCard).toBeVisible({ timeout: 5000 });
    
    // Проверяем, что есть секция с назначенными предметами
    const subjectsSection = updatedStudentCard.locator('text=/Назначенные предметы \\((\\d+)\\)/');
    await expect(subjectsSection).toBeVisible({ timeout: 5000 });
    
    // Получаем новое количество предметов
    const updatedSubjectsText = await subjectsSection.textContent();
    const updatedMatch = updatedSubjectsText?.match(/\((\d+)\)/);
    let updatedSubjectsCount = 0;
    if (updatedMatch) {
      updatedSubjectsCount = parseInt(updatedMatch[1]);
    }
    
    console.log(`[Test] Updated subjects count: ${updatedSubjectsCount}`);
    
    // Проверяем, что количество предметов увеличилось
    expect(updatedSubjectsCount).toBeGreaterThan(initialSubjectsCount);
    
    // Проверяем, что назначенный предмет отображается в списке
    if (subjectName) {
      await expect(updatedStudentCard.locator(`text=${subjectName.trim()}`)).toBeVisible({ timeout: 3000 });
    }
    
    console.log('[Test] ✓ Subject assignment and list update successful');
  });
});

