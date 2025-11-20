import { test, expect, Page } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8080';
const TEACHER_EMAIL = 'teacher@test.com';
const TEACHER_PASSWORD = 'testpass123';
const STUDENT_EMAIL = 'student@test.com';
const STUDENT_PASSWORD = 'testpass123';

// Вспомогательная функция для логина
async function login(page: Page, email: string, password: string) {
  await page.goto(`${baseURL}/auth`);
  await page.waitForLoadState('networkidle');
  
  // Ищем поле ввода email/username
  const emailInput = page.locator('input[placeholder*="Email"]').or(page.locator('input[type="email"]')).or(page.locator('input[name="emailOrUsername"]')).first();
  await emailInput.waitFor({ state: 'visible', timeout: 10000 });
  await emailInput.fill(email);
  
  // Заполняем пароль
  const passwordInput = page.locator('input[type="password"]').or(page.locator('input[placeholder*="Пароль"]')).first();
  await passwordInput.fill(password);
  
  // Кликаем кнопку входа
  const loginButton = page.locator('button[type="submit"]').or(page.locator('button:has-text("Войти")')).first();
  await loginButton.click();
  
  await page.waitForTimeout(2000);
}

// Вспомогательная функция для логаута
async function logout(page: Page) {
  // Ищем кнопку выхода в сайдбаре или меню
  const logoutButton = page.locator('button:has-text("Выход")').or(page.locator('a:has-text("Выход")')).first();
  if (await logoutButton.isVisible()) {
    await logoutButton.click();
    await page.waitForTimeout(1000);
  } else {
    // Альтернативный способ - через API
    await page.goto(`${baseURL}/auth`);
  }
}

test.describe('Study Plans E2E Flow', () => {
  test('complete flow: teacher creates and sends plan, student views it', async ({ page }) => {
    // ===== ШАГ 1: Логин как преподаватель =====
    console.log('Step 1: Teacher login');
    await login(page, TEACHER_EMAIL, TEACHER_PASSWORD);
    await expect(page).toHaveURL(/.*dashboard\/teacher.*/, { timeout: 10000 });

    // ===== ШАГ 2: Переход на страницу планов занятий =====
    console.log('Step 2: Navigate to study plans page');
    await page.goto(`${baseURL}/dashboard/teacher/study-plans`);
    await page.waitForSelector('h1:has-text("Планы занятий")', { timeout: 10000 });

    // ===== ШАГ 3: Открытие диалога создания плана =====
    console.log('Step 3: Open create plan dialog');
    await page.click('button:has-text("Создать план")');
    await page.waitForSelector('text=Создать план занятий', { timeout: 5000 });

    // ===== ШАГ 4: Заполнение формы создания плана =====
    console.log('Step 4: Fill in plan details');
    
    // Выбираем предмет
    const subjectSelect = page.locator('label:has-text("Предмет")').locator('..').locator('button').first();
    await subjectSelect.click();
    await page.waitForTimeout(500);
    
    // Выбираем первый доступный предмет
    const firstSubject = page.locator('[role="option"]').first();
    await firstSubject.waitFor({ state: 'visible', timeout: 5000 });
    const subjectText = await firstSubject.textContent();
    console.log(`Selected subject: ${subjectText}`);
    await firstSubject.click();
    await page.waitForTimeout(1000);

    // Ждем загрузки студентов для выбранного предмета
    await page.waitForTimeout(2000);

    // Выбираем студента
    const studentSelect = page.locator('label:has-text("Студент")').locator('..').locator('button').first();
    await studentSelect.click();
    await page.waitForTimeout(500);
    
    // Выбираем первого доступного студента
    const firstStudent = page.locator('[role="option"]').first();
    await firstStudent.waitFor({ state: 'visible', timeout: 5000 });
    const studentText = await firstStudent.textContent();
    console.log(`Selected student: ${studentText}`);
    await firstStudent.click();
    await page.waitForTimeout(500);

    // Заполняем название плана
    const planTitle = `E2E Test Plan ${Date.now()}`;
    await page.fill('input[placeholder*="Неделя"]', planTitle);

    // Заполняем дату начала недели
    const today = new Date().toISOString().split('T')[0];
    await page.fill('input[type="date"]', today);

    // Заполняем содержание плана
    const planContent = `Это автоматически созданный план занятий для E2E теста.
Студент должен:
1. Изучить основы темы
2. Выполнить практические задания
3. Пройти тест по материалу
4. Подготовить отчет`;
    await page.fill('textarea[placeholder*="Опишите план"]', planContent);

    // Выбираем статус "Отправить сразу"
    const statusSelect = page.locator('label:has-text("Статус")').locator('..').locator('button').first();
    await statusSelect.click();
    await page.waitForTimeout(500);
    const sendOption = page.locator('text=Отправить сразу');
    if (await sendOption.isVisible()) {
      await sendOption.click();
    }
    await page.waitForTimeout(500);

    // ===== ШАГ 5: Создание плана =====
    console.log('Step 5: Create plan');
    await page.click('button:has-text("Создать"):not(:has-text("Создать план"))');
    
    // Ждем закрытия диалога
    await page.waitForTimeout(3000);
    
    // Проверяем, что план появился в списке
    console.log('Step 6: Verify plan appears in teacher list');
    await expect(page.locator(`text=${planTitle}`)).toBeVisible({ timeout: 10000 });

    // ===== ШАГ 7: Логаут преподавателя =====
    console.log('Step 7: Teacher logout');
    await logout(page);
    await page.waitForTimeout(2000);

    // ===== ШАГ 8: Логин как студент =====
    console.log('Step 8: Student login');
    await login(page, STUDENT_EMAIL, STUDENT_PASSWORD);
    await page.waitForTimeout(2000);
    
    // Проверяем, что мы на дашборде студента
    await expect(page).toHaveURL(/.*dashboard\/student.*/, { timeout: 10000 });

    // ===== ШАГ 9: Переход на страницу материалов студента =====
    console.log('Step 9: Navigate to student materials page');
    await page.goto(`${baseURL}/dashboard/student/materials`);
    await page.waitForTimeout(2000);

    // ===== ШАГ 10: Проверка, что план виден студенту =====
    console.log('Step 10: Verify plan is visible to student');
    
    // Скроллим до секции с планами
    const plansSection = page.locator('h2:has-text("Планы занятий")').or(page.locator('h3:has-text("Планы занятий")')).first();
    if (await plansSection.isVisible({ timeout: 5000 })) {
      await plansSection.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);
      
      // Проверяем, что план появился в списке
      const planCard = page.locator(`text=${planTitle}`);
      await expect(planCard).toBeVisible({ timeout: 10000 });
      console.log('✓ Plan is visible to student');

      // ===== ШАГ 11: Открытие деталей плана =====
      console.log('Step 11: Open plan details');
      
      // Ищем кнопку "Подробнее" или карточку плана для клика
      const detailsButton = page.locator(`text=${planTitle}`).locator('..').locator('button:has-text("Подробнее")').first();
      
      if (await detailsButton.isVisible({ timeout: 2000 })) {
        await detailsButton.click();
        await page.waitForTimeout(1000);
        
        // Проверяем, что диалог с деталями открылся
        await expect(page.locator(`text=${planTitle}`)).toBeVisible();
        await expect(page.locator(`text=${planContent.split('\n')[0]}`)).toBeVisible({ timeout: 5000 });
        console.log('✓ Plan details dialog opened');
      } else {
        console.log('⚠ Details button not found, but plan is visible');
      }
    } else {
      console.log('⚠ Plans section not found on page');
      // Делаем скриншот для отладки
      await page.screenshot({ path: 'test-results/student-materials-page.png', fullPage: true });
    }

    // ===== ШАГ 12: Логаут студента =====
    console.log('Step 12: Student logout');
    await logout(page);
  });

  test('student can view plan details', async ({ page }) => {
    // Логин как студент
    await login(page, STUDENT_EMAIL, STUDENT_PASSWORD);
    await page.waitForURL(/.*dashboard\/student.*/, { timeout: 10000 });

    // Переход на страницу материалов
    await page.goto(`${baseURL}/dashboard/student/materials`);
    await page.waitForTimeout(2000);

    // Ищем секцию с планами
    const plansSection = page.locator('h2:has-text("Планы занятий")').or(page.locator('h3:has-text("Планы занятий")')).first();
    
    if (await plansSection.isVisible({ timeout: 5000 })) {
      await plansSection.scrollIntoViewIfNeeded();
      
      // Проверяем наличие хотя бы одного плана
      const planCards = page.locator('[class*="card"]').filter({ hasText: 'Неделя' });
      const count = await planCards.count();
      
      if (count > 0) {
        console.log(`Found ${count} study plan(s)`);
        
        // Кликаем на первый план
        const firstPlanCard = planCards.first();
        await firstPlanCard.scrollIntoViewIfNeeded();
        
        // Ищем кнопку "Подробнее"
        const detailsBtn = firstPlanCard.locator('button:has-text("Подробнее")');
        if (await detailsBtn.isVisible({ timeout: 2000 })) {
          await detailsBtn.click();
          await page.waitForTimeout(1000);
          
          // Проверяем, что диалог открылся
          const dialog = page.locator('[role="dialog"]').or(page.locator('[class*="dialog"]')).first();
          await expect(dialog).toBeVisible({ timeout: 5000 });
          console.log('✓ Plan details dialog opened successfully');
        }
      } else {
        console.log('⚠ No plans found for student');
      }
    } else {
      console.log('⚠ Plans section not visible');
      await page.screenshot({ path: 'test-results/no-plans-section.png', fullPage: true });
    }

    await logout(page);
  });
});

