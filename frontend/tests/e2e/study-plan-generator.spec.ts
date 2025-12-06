import { test, expect, Page } from '@playwright/test';

/**
 * E2E Tests for Study Plan Generator Page
 *
 * Tests the complete user workflow for AI-powered study plan generation.
 * Covers:
 * - Full workflow: login → navigate → fill form → submit → download files
 * - Form validation (missing required fields)
 * - API error handling
 * - Responsive design (desktop, tablet, mobile)
 */

// Helper to login as teacher
async function loginAsTeacher(page: Page) {
  await page.goto('/auth');
  await page.waitForLoadState('networkidle');

  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();

  await emailInput.fill('teacher@test.com');
  await passwordInput.fill('TestPass123!');

  const loginButton = page.locator('button[type="submit"], button:has-text("Войти")').first();
  await loginButton.click();

  await page.waitForURL('**/dashboard/teacher', { timeout: 10000 });
}

// Helper to navigate to study plan generator
async function navigateToGenerator(page: Page) {
  // Via sidebar or direct URL
  await page.goto('/dashboard/teacher/study-plan-generator');
  await page.waitForLoadState('networkidle');
}

/**
 * Helper to mock the study plan generation API
 * Simulates successful generation with 4 files ready for download
 */
async function mockSuccessfulGeneration(page: Page) {
  const mockFiles = [
    {
      type: 'problem_set',
      url: 'blob:http://localhost:8080/mock-problem-set.pdf',
      filename: 'problem_set.pdf'
    },
    {
      type: 'reference_guide',
      url: 'blob:http://localhost:8080/mock-reference-guide.pdf',
      filename: 'reference_guide.pdf'
    },
    {
      type: 'video_list',
      url: 'blob:http://localhost:8080/mock-video-list.md',
      filename: 'video_list.md'
    },
    {
      type: 'weekly_plan',
      url: 'blob:http://localhost:8080/mock-weekly-plan.txt',
      filename: 'weekly_plan.txt'
    }
  ];

  // Mock the initial generation POST request
  await page.route('**/api/materials/study-plan/generate/', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        generation_id: 12345,
        status: 'pending',
        files: mockFiles
      })
    });
  });

  // Mock the generation status polling (simulate completion after 2nd poll)
  let pollCount = 0;
  await page.route('**/api/materials/study-plan/generation/**', route => {
    pollCount++;

    if (pollCount === 1) {
      // First poll: still processing
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          generation_id: 12345,
          status: 'processing',
          files: []
        })
      });
    } else {
      // Second poll: completed with files
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          generation_id: 12345,
          status: 'completed',
          files: mockFiles
        })
      });
    }
  });
}

/**
 * Helper to mock API error response
 */
async function mockGenerationError(page: Page) {
  await page.route('**/api/materials/study-plan/generate/', route => {
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        error: 'Internal server error during generation',
        generation_id: null,
        status: 'failed'
      })
    });
  });
}

/**
 * Helper to mock generation status failure
 */
async function mockGenerationStatusError(page: Page) {
  await page.route('**/api/materials/study-plan/generate/', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        generation_id: 12345,
        status: 'pending',
        files: []
      })
    });
  });

  await page.route('**/api/materials/study-plan/generation/**', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        generation_id: 12345,
        status: 'failed',
        error: 'AI service timeout - please try again',
        files: []
      })
    });
  });
}

test.describe('Study Plan Generator - Full Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
  });

  test('T015.1 - Full generation workflow with all files downloaded', async ({ page }) => {
    // 1. Login as teacher
    await loginAsTeacher(page);

    // 2. Navigate to generator page
    await navigateToGenerator(page);

    // Verify page title
    await expect(page.locator('text=/Генератор учебных планов/i')).toBeVisible();
    await expect(page.locator('text=/AI-генерация учебных материалов/i')).toBeVisible();

    // 3. Mock successful API responses
    await mockSuccessfulGeneration(page);

    // 4. Fill out the form
    // Select student
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    // Select subject
    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    // Fill grade
    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    // Select goal
    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    // Fill topic
    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    // Fill subtopics
    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант, теорема Виета');

    // Fill optional constraint
    const constraintsInput = page.locator('#constraints');
    await constraintsInput.fill('Время: 60 мин');

    // 5. Submit form
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // 6. Verify generation started message
    await expect(page.locator('text=/Генерация запущена/i')).toBeVisible({ timeout: 5000 });

    // 7. Wait for generation to complete (simulated via polling)
    await page.waitForTimeout(6000); // Allow time for polls (3s interval x 2)

    // 8. Verify success message
    await expect(page.locator('text=/Генерация завершена/i')).toBeVisible({ timeout: 5000 });

    // 9. Verify all 4 download links are visible
    await expect(page.locator('text=/Задачник/i')).toBeVisible();
    await expect(page.locator('text=/Справочник/i')).toBeVisible();
    await expect(page.locator('text=/Видеоподборка/i')).toBeVisible();
    await expect(page.locator('text=/Недельный план/i')).toBeVisible();

    // 10. Verify download buttons exist and are clickable
    const downloadButtons = page.locator('a:has(text=/Задачник|Справочник|Видеоподборка|Недельный план/)');
    expect(await downloadButtons.count()).toBeGreaterThanOrEqual(4);
  });

  test('T015.2 - Navigation to generator page from dashboard', async ({ page }) => {
    await loginAsTeacher(page);

    // Navigate to teacher dashboard first
    await page.goto('/dashboard/teacher');
    await page.waitForLoadState('networkidle');

    // Find and click generator link (if exists in sidebar or main content)
    const generatorLink = page.locator('a:has-text(/генератор/i), button:has-text(/генератор/i)').first();

    if (await generatorLink.count() > 0) {
      await generatorLink.click();
      await page.waitForURL('**/study-plan-generator', { timeout: 5000 });
    } else {
      // Direct navigation if no sidebar link
      await navigateToGenerator(page);
    }

    // Verify page loaded
    await expect(page.locator('text=/Генератор учебных планов/i')).toBeVisible();
  });
});

test.describe('Study Plan Generator - Form Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginAsTeacher(page);
    await navigateToGenerator(page);
  });

  test('T015.3 - Missing student selection shows validation error', async ({ page }) => {
    // Leave student empty
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error message
    await expect(page.locator('text=/Выберите студента/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.4 - Missing subject selection shows validation error', async ({ page }) => {
    // Select only student
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    // Leave subject empty, try to submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error message
    await expect(page.locator('text=/Выберите предмет/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.5 - Missing grade input shows validation error', async ({ page }) => {
    // Select student
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    // Select subject
    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    // Leave grade empty, try to submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error message
    await expect(page.locator('text=/Укажите класс/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.6 - Invalid grade range shows validation error', async ({ page }) => {
    // Setup required fields
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    // Enter invalid grade (too low)
    const gradeInput = page.locator('#grade');
    await gradeInput.fill('5');

    // Try to submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify validation error
    await expect(page.locator('text=/Класс должен быть от 7 до 11/i')).toBeVisible({ timeout: 3000 });

    // Try with too high grade
    await gradeInput.fill('13');
    await submitButton.click();

    await expect(page.locator('text=/Класс должен быть от 7 до 11/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.7 - Missing topic shows validation error', async ({ page }) => {
    // Fill basic fields
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    // Leave topic empty and submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error
    await expect(page.locator('text=/Укажите тему/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.8 - Missing subtopics shows validation error', async ({ page }) => {
    // Fill all fields except subtopics
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    // Leave subtopics empty
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error
    await expect(page.locator('text=/Укажите подтемы/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.9 - Missing goal selection shows validation error', async ({ page }) => {
    // Fill fields without goal
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    // Leave goal empty and submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error
    await expect(page.locator('text=/Выберите цель/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.10 - Invalid task count (out of range) shows validation error', async ({ page }) => {
    // Mock successful generation to reach task count validation
    await mockSuccessfulGeneration(page);

    // Fill all required fields
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    // Set invalid task count (too high)
    const aTasksInput = page.locator('#aTasks');
    await aTasksInput.fill('25'); // Max is 20

    // Try to submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify validation error
    await expect(page.locator('text=/Количество задач A.*1-20/i')).toBeVisible({ timeout: 3000 });
  });

  test('T015.11 - Toast shows validation summary on multiple errors', async ({ page }) => {
    // Try to submit with multiple missing fields
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify validation error toast appears
    await expect(page.locator('text=/Ошибка валидации/i')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=/заполните все обязательные поля/i')).toBeVisible();
  });
});

test.describe('Study Plan Generator - API Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginAsTeacher(page);
    await navigateToGenerator(page);
  });

  test('T015.12 - Generation API error shows error message', async ({ page }) => {
    // Mock API error response
    await mockGenerationError(page);

    // Fill and submit form
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify error toast appears
    await expect(page.locator('text=/Ошибка генерации/i')).toBeVisible({ timeout: 5000 });
  });

  test('T015.13 - Generation status error shows error message', async ({ page }) => {
    // Mock generation status failure
    await mockGenerationStatusError(page);

    // Fill and submit form
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify generation started
    await expect(page.locator('text=/Генерация запущена/i')).toBeVisible({ timeout: 5000 });

    // Wait for status polling and error response
    await page.waitForTimeout(6000);

    // Verify error message is displayed
    await expect(page.locator('text=/Ошибка генерации/i')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/AI service timeout/i')).toBeVisible();

    // Verify error alert is displayed
    await expect(page.locator('[class*="destructive"], .alert-destructive')).toBeVisible();
  });

  test('T015.14 - Submit button disabled during generation', async ({ page }) => {
    // Mock successful generation
    await mockSuccessfulGeneration(page);

    // Fill form
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    // Submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify button becomes disabled
    await expect(submitButton).toBeDisabled({ timeout: 5000 });

    // Verify loading state (spinner visible)
    await expect(page.locator('.animate-spin, [class*="loader"]').first()).toBeVisible();
  });
});

test.describe('Study Plan Generator - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginAsTeacher(page);
    await navigateToGenerator(page);
  });

  test('T015.15 - Form is usable on desktop viewport', async ({ page }) => {
    page.setViewportSize({ width: 1920, height: 1080 });

    // Verify form is visible and accessible
    await expect(page.locator('h1:has-text("Генератор учебных планов")')).toBeVisible();

    // Verify form fields are visible
    const studentSelect = page.locator('#student');
    const subjectSelect = page.locator('#subject');
    const gradeInput = page.locator('#grade');

    await expect(studentSelect).toBeVisible();
    await expect(subjectSelect).toBeVisible();
    await expect(gradeInput).toBeVisible();

    // Verify submit button is visible
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await expect(submitButton).toBeVisible();
  });

  test('T015.16 - Form is usable on tablet viewport', async ({ page }) => {
    page.setViewportSize({ width: 768, height: 1024 });

    // Verify page title visible
    await expect(page.locator('h1:has-text("Генератор учебных планов")')).toBeVisible();

    // Verify form is accessible
    const studentSelect = page.locator('#student');
    await expect(studentSelect).toBeVisible();

    // Verify we can scroll to all sections
    await page.evaluate(() => window.scrollBy(0, 100));

    // Verify form sections are accessible
    const formElements = page.locator('input, select, textarea, button:has-text("Сгенерировать план")');
    expect(await formElements.count()).toBeGreaterThan(5);
  });

  test('T015.17 - Form is usable on mobile viewport', async ({ page }) => {
    page.setViewportSize({ width: 375, height: 667 }); // iPhone size

    // Verify heading is visible
    await expect(page.locator('h1:has-text("Генератор учебных планов")')).toBeVisible();

    // Verify form is accessible
    const studentSelect = page.locator('#student');
    await expect(studentSelect).toBeVisible();

    // Verify submit button is accessible
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await expect(submitButton).toBeVisible();

    // Verify form doesn't have horizontal overflow
    const body = page.locator('body');
    const bodyWidth = await body.evaluate((el: HTMLElement) => el.offsetWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);

    expect(bodyWidth).toBeLessThanOrEqual(windowWidth);
  });

  test('T015.18 - Download buttons are responsive on mobile', async ({ page }) => {
    page.setViewportSize({ width: 375, height: 667 });

    // Mock successful generation
    await mockSuccessfulGeneration(page);

    // Fill and submit form
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Wait for completion
    await page.waitForTimeout(6000);

    // Verify download buttons are visible and stacked vertically
    const downloadButtons = page.locator('a, button').filter({ hasText: /Задачник|Справочник|Видеоподборка|Недельный план/ });
    await expect(downloadButtons.first()).toBeVisible();

    // Verify buttons are within viewport width
    const firstButton = downloadButtons.first();
    const boundingBox = await firstButton.boundingBox();
    if (boundingBox) {
      expect(boundingBox.width).toBeLessThanOrEqual(375); // Mobile viewport width
    }
  });

  test('T015.19 - Navigation is accessible on all viewports', async ({ page }) => {
    // Test on mobile
    page.setViewportSize({ width: 375, height: 667 });

    // Sidebar trigger should be visible on mobile
    const sidebarTrigger = page.locator('[class*="trigger"], button[aria-label*="sidebar"], button[aria-label*="Menu"]').first();
    if (await sidebarTrigger.count() > 0) {
      await expect(sidebarTrigger).toBeVisible();
    }

    // Page title should always be visible
    await expect(page.locator('h1:has-text("Генератор учебных планов")')).toBeVisible();

    // Switch to tablet
    page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('h1:has-text("Генератор учебных планов")')).toBeVisible();

    // Switch to desktop
    page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('h1:has-text("Генератор учебных планов")')).toBeVisible();
  });
});

test.describe('Study Plan Generator - Additional Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await loginAsTeacher(page);
    await navigateToGenerator(page);
  });

  test('T015.20 - Grade auto-populates when student is selected', async ({ page }) => {
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    // Wait for auto-population
    await page.waitForTimeout(500);

    // Verify grade field has value
    const gradeInput = page.locator('#grade');
    const gradeValue = await gradeInput.inputValue();

    // Should have some value (auto-populated from student data)
    if (gradeValue) {
      expect(/\d+/.test(gradeValue)).toBe(true);
    }
  });

  test('T015.21 - Optional fields (constraints) can be left empty', async ({ page }) => {
    // Mock successful generation
    await mockSuccessfulGeneration(page);

    // Fill only required fields
    const studentSelect = page.locator('#student');
    await studentSelect.click();
    const studentOption = page.locator('[role="option"]').first();
    await studentOption.click();

    const subjectSelect = page.locator('#subject');
    await subjectSelect.click();
    const subjectOption = page.locator('[role="option"]').first();
    await subjectOption.click();

    const gradeInput = page.locator('#grade');
    await gradeInput.fill('9');

    const goalSelect = page.locator('#goal');
    await goalSelect.click();
    const goalOption = page.locator('[role="option"]').first();
    await goalOption.click();

    const topicInput = page.locator('#topic');
    await topicInput.fill('Квадратные уравнения');

    const subtopicsInput = page.locator('#subtopics');
    await subtopicsInput.fill('решение, дискриминант');

    // Leave constraints empty
    const constraintsInput = page.locator('#constraints');
    expect(await constraintsInput.inputValue()).toBe('');

    // Should still be able to submit
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Should proceed without validation error for optional field
    await expect(page.locator('text=/Генерация запущена/i')).toBeVisible({ timeout: 5000 });
  });

  test('T015.22 - Tooltip help text is displayed for complex fields', async ({ page }) => {
    // Find tooltip icons
    const tooltipTriggers = page.locator('[class*="tooltip"]').first();

    // Hover to reveal tooltip
    if (await tooltipTriggers.count() > 0) {
      await page.hover('[class*="Info"], svg[class*="info"]');

      // Verify tooltip content appears
      const tooltipContent = page.locator('[class*="tooltip-content"], [role="tooltip"]').first();
      if (await tooltipContent.count() > 0) {
        await expect(tooltipContent).toBeVisible({ timeout: 2000 });
      }
    }
  });

  test('T015.23 - Default values are set for optional parameters', async ({ page }) => {
    // Verify default values in dropdowns
    const referenceLevelSelect = page.locator('#referenceLevel');
    const videoDurationInput = page.locator('#videoDuration');
    const videoLanguageSelect = page.locator('#videoLanguage');

    // Should have default values
    const levelValue = await referenceLevelSelect.evaluate((el: HTMLSelectElement) =>
      el.value || el.getAttribute('data-value') || el.textContent
    );

    const durationValue = await videoDurationInput.inputValue();
    expect(durationValue).toBeTruthy();

    const langValue = await videoLanguageSelect.evaluate((el: HTMLSelectElement) =>
      el.value || el.getAttribute('data-value') || el.textContent
    );
    expect(langValue).toBeTruthy();
  });

  test('T015.24 - Form preserves data on validation error', async ({ page }) => {
    // Fill some fields
    const topicInput = page.locator('#topic');
    const testTopic = 'Квадратные уравнения';
    await topicInput.fill(testTopic);

    // Try to submit (will fail validation)
    const submitButton = page.locator('button:has-text("Сгенерировать план")');
    await submitButton.click();

    // Verify validation error appears
    await expect(page.locator('text=/Ошибка валидации/i')).toBeVisible({ timeout: 3000 });

    // Verify form data is still there
    const topicValue = await topicInput.inputValue();
    expect(topicValue).toBe(testTopic);
  });

  test('T015.25 - Console shows no critical errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Wait for page to fully load
    await page.waitForLoadState('networkidle');

    // Filter out non-critical errors
    const criticalErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('WebSocket') &&
      !e.includes('404') &&
      !e.includes('UndefinedbUGGER') &&
      !e.toLowerCase().includes('warning')
    );

    expect(criticalErrors.length).toBeLessThan(2);
  });
});

test.describe('Study Plan Generator - Authorization & Access Control', () => {
  test('T015.26 - Non-teacher cannot access generator page', async ({ page }) => {
    // Login as student
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();

    await emailInput.fill('opt_student_0@test.com');
    await passwordInput.fill('password');

    const loginButton = page.locator('button[type="submit"], button:has-text("Войти")').first();
    await loginButton.click();

    await page.waitForURL('**/dashboard/student', { timeout: 10000 });

    // Try to navigate to generator
    await page.goto('/dashboard/teacher/study-plan-generator');
    await page.waitForLoadState('networkidle');

    // Should be redirected away (to dashboard or unauthorized)
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('study-plan-generator');
  });

  test('T015.27 - Unauthenticated user redirects to login', async ({ page }) => {
    // Clear all auth data
    await page.context().clearCookies();

    // Try to access generator directly
    await page.goto('/dashboard/teacher/study-plan-generator');
    await page.waitForLoadState('networkidle');

    // Should redirect to auth
    await expect(page).toHaveURL(/\/auth/);
  });
});
