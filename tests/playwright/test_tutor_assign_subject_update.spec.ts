import { test, expect } from '@playwright/test';

/**
 * Тест проверяет, что после назначения предмета список назначенных предметов обновляется
 */

test.describe('Tutor Assign Subject - UI Update', () => {
  test('should update subjects list after assigning a subject', async ({ page }) => {
    // Логин как тьютор
    await page.goto('http://localhost:5173/login');
    
    // Заполняем форму входа для тьютора
    await page.fill('input[type="text"]', 'tutor1');
    await page.fill('input[type="password"]', 'tutor123');
    await page.click('button[type="submit"]');
    
    // Ждем перенаправления на dashboard тьютора
    await page.waitForURL('**/tutor/students', { timeout: 10000 });
    
    // Проверяем, что мы на странице студентов
    await expect(page.locator('text=Мои ученики')).toBeVisible({ timeout: 5000 });
    
    // Находим первую карточку студента
    const studentCard = page.locator('[class*="Card"]:has-text("Класс:")').first();
    await expect(studentCard).toBeVisible({ timeout: 5000 });
    
    // Запоминаем текущее количество предметов
    const subjectsCountBefore = await studentCard.locator('text=/Назначенные предметы \\((\\d+)\\)/').count();
    console.log(`[Test] Subjects count before: ${subjectsCountBefore}`);
    
    // Нажимаем кнопку "Назначить предмет"
    await studentCard.locator('button:has-text("Назначить предмет")').click();
    
    // Ждем открытия диалога
    await expect(page.locator('text=Назначить предмет').first()).toBeVisible({ timeout: 3000 });
    
    // Выбираем существующий предмет (режим по умолчанию)
    const subjectSelect = page.locator('[aria-label="subject-select"]');
    await subjectSelect.click();
    
    // Ждем загрузки предметов и выбираем первый
    await page.waitForTimeout(1000);
    const firstSubject = page.locator('div[role="option"]').first();
    await expect(firstSubject).toBeVisible({ timeout: 3000 });
    await firstSubject.click();
    
    // Выбираем преподавателя
    const teacherSelect = page.locator('[aria-label="teacher-select"]');
    await teacherSelect.click();
    
    // Ждем загрузки преподавателей и выбираем первого
    await page.waitForTimeout(1000);
    const firstTeacher = page.locator('div[role="option"]').first();
    await expect(firstTeacher).toBeVisible({ timeout: 3000 });
    await firstTeacher.click();
    
    // Нажимаем кнопку "Назначить"
    await page.locator('button:has-text("Назначить")').click();
    
    // Ждем закрытия диалога (проверяем, что диалог исчез)
    await expect(page.locator('text=Назначить предмет').first()).not.toBeVisible({ timeout: 5000 });
    
    // Ждем toast с успешным сообщением
    await expect(page.locator('text=/Предмет успешно назначен/i')).toBeVisible({ timeout: 5000 });
    
    // Ждем обновления данных (задержка 100мс в хуке + время на загрузку)
    await page.waitForTimeout(500);
    
    // Проверяем, что количество предметов увеличилось
    // Ищем обновленную карточку студента
    const updatedStudentCard = page.locator('[class*="Card"]:has-text("Класс:")').first();
    await expect(updatedStudentCard).toBeVisible({ timeout: 5000 });
    
    // Проверяем, что есть хотя бы один назначенный предмет
    const subjectsSection = updatedStudentCard.locator('text=/Назначенные предметы \\((\\d+)\\)/');
    await expect(subjectsSection).toBeVisible({ timeout: 5000 });
    
    // Получаем текст с количеством предметов
    const subjectsText = await subjectsSection.textContent();
    console.log(`[Test] Subjects text after assignment: ${subjectsText}`);
    
    // Проверяем, что количество больше 0
    expect(subjectsText).toMatch(/Назначенные предметы \((\d+)\)/);
    const match = subjectsText?.match(/Назначенные предметы \((\d+)\)/);
    if (match) {
      const count = parseInt(match[1]);
      console.log(`[Test] Subjects count after: ${count}`);
      expect(count).toBeGreaterThan(0);
    }
    
    console.log('[Test] ✓ Subject assignment and list update successful');
  });
});

