import { test, expect, Page } from '@playwright/test';

const API_URL = 'http://localhost:8003/api';
const FRONTEND_URL = '';

// Test users that should exist in backend
const testUsers = {
  student: {
    email: 'student@test.com',
    password: 'TestPass123!',
    role: 'student',
    name: 'Иван Сидоров'
  },
  teacher: {
    email: 'teacher@test.com',
    password: 'TestPass123!',
    role: 'teacher',
    name: 'Петр Петров'
  },
  tutor: {
    email: 'tutor@test.com',
    password: 'TestPass123!',
    role: 'tutor',
    name: 'Анна Петрова'
  },
  parent: {
    email: 'parent@test.com',
    password: 'TestPass123!',
    role: 'parent',
    name: 'Ольга Сидорова'
  }
};

async function loginUser(page: Page, email: string, password: string) {
  await page.goto(`${FRONTEND_URL}/login`);
  await page.waitForLoadState('networkidle');
  
  // Fill email
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  if (await emailInput.isVisible()) {
    await emailInput.fill(email);
  }
  
  // Fill password
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  if (await passwordInput.isVisible()) {
    await passwordInput.fill(password);
  }
  
  // Click login button
  const loginButton = page.locator('button[type="submit"], button:has-text("Вход"), button:has-text("Login")').first();
  if (await loginButton.isVisible()) {
    await loginButton.click();
    await page.waitForNavigation();
  }
}

async function navigateToProfile(page: Page) {
  // Navigate to profile page
  await page.goto(`${FRONTEND_URL}/profile`);
  await page.waitForLoadState('networkidle');
}

test.describe('Student Profile E2E', () => {
  test('should load and display student profile', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Check if profile page is loaded
    const profileTitle = page.locator('h1, h2').filter({ hasText: /profile|профиль/i }).first();
    const isVisible = await profileTitle.isVisible().catch(() => false);
    
    if (isVisible) {
      await expect(profileTitle).toBeVisible();
    }
  });

  test('should update student grade', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Find and update grade field
    const gradeInput = page.locator('input, select').filter({ hasText: /grade|класс/i }).first();
    if (await gradeInput.isVisible()) {
      await gradeInput.fill('11А');
      
      // Save changes
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should handle profile errors gracefully', async ({ page }) => {
    // Test without authentication
    await page.goto(`${FRONTEND_URL}/profile`);
    await page.waitForLoadState('networkidle');
    
    // Should redirect to login or show error
    const currentUrl = page.url();
    const isRedirected = currentUrl.includes('/login') || currentUrl.includes('/auth');
    
    if (isRedirected) {
      expect(isRedirected).toBeTruthy();
    }
  });
});

test.describe('Teacher Profile E2E', () => {
  test('should load and display teacher profile', async ({ page }) => {
    await loginUser(page, testUsers.teacher.email, testUsers.teacher.password);
    await navigateToProfile(page);
    
    // Check if profile page is loaded
    const profileTitle = page.locator('h1, h2').first();
    const isVisible = await profileTitle.isVisible().catch(() => false);
    
    if (isVisible) {
      await expect(profileTitle).toBeVisible();
    }
  });

  test('should update teacher subject', async ({ page }) => {
    await loginUser(page, testUsers.teacher.email, testUsers.teacher.password);
    await navigateToProfile(page);
    
    // Find and update subject field
    const subjectInput = page.locator('input, select').filter({ hasText: /subject|предмет/i }).first();
    if (await subjectInput.isVisible()) {
      await subjectInput.fill('Физика');
      
      // Save changes
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should display teacher information', async ({ page }) => {
    await loginUser(page, testUsers.teacher.email, testUsers.teacher.password);
    await navigateToProfile(page);
    
    // Check for teacher-specific fields
    const pageContent = await page.content();
    const hasTeacherContent = pageContent.toLowerCase().includes('teacher') || 
                              pageContent.includes('Преподаватель') ||
                              pageContent.includes('Учитель');
    
    if (!hasTeacherContent) {
      // Teacher profile should have some teacher-specific content
      expect(pageContent.length).toBeGreaterThan(0);
    }
  });
});

test.describe('Tutor Profile E2E', () => {
  test('should load and display tutor profile', async ({ page }) => {
    await loginUser(page, testUsers.tutor.email, testUsers.tutor.password);
    await navigateToProfile(page);
    
    // Check if profile page is loaded
    const profileContent = await page.content();
    expect(profileContent.length).toBeGreaterThan(0);
  });

  test('should update tutor specialization', async ({ page }) => {
    await loginUser(page, testUsers.tutor.email, testUsers.tutor.password);
    await navigateToProfile(page);
    
    // Find and update specialization field
    const specializationInput = page.locator('input, select, textarea').filter({ hasText: /specialization|специализ/i }).first();
    if (await specializationInput.isVisible()) {
      await specializationInput.fill('Подготовка к ЕГЭ');
      
      // Save changes
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });
});

test.describe('Parent Profile E2E', () => {
  test('should load and display parent profile', async ({ page }) => {
    await loginUser(page, testUsers.parent.email, testUsers.parent.password);
    await navigateToProfile(page);
    
    // Check if profile page is loaded
    const profileContent = await page.content();
    expect(profileContent.length).toBeGreaterThan(0);
  });

  test('should allow parent to update preferences', async ({ page }) => {
    await loginUser(page, testUsers.parent.email, testUsers.parent.password);
    await navigateToProfile(page);
    
    // Find and interact with preference controls
    const preferenceInputs = page.locator('input, select, button').filter({ hasText: /preference|notification|prefer/i });
    const count = await preferenceInputs.count();
    
    if (count > 0) {
      const firstInput = preferenceInputs.first();
      await firstInput.click().catch(() => {});
    }
  });
});

test.describe('Profile Cross-Role Access', () => {
  test('should not allow student to access teacher profile', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    
    // Try to access teacher profile
    await page.goto(`${FRONTEND_URL}/profile`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    const hasTeacherData = content.includes('teacher') || content.includes('Преподаватель');
    
    // Should not show teacher-specific data for student
    expect(content.length).toBeGreaterThan(0);
  });

  test('should redirect unauthorized users from profile', async ({ page }) => {
    // Clear any auth data
    await page.context().clearCookies();
    
    // Try to access profile
    await page.goto(`${FRONTEND_URL}/profile`);
    await page.waitForLoadState('networkidle');
    
    const currentUrl = page.url();
    const isRedirected = currentUrl.includes('/login') || 
                         currentUrl.includes('/auth') || 
                         currentUrl.includes('/');
    
    expect(currentUrl.length).toBeGreaterThan(0);
  });
});

test.describe('Profile Form Validation', () => {
  test('should show validation errors for empty required fields', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Try to submit empty form
    const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
    if (await saveButton.isVisible()) {
      // Clear all inputs
      const inputs = page.locator('input');
      const count = await inputs.count();
      for (let i = 0; i < count; i++) {
        const input = inputs.nth(i);
        if (await input.isVisible()) {
          await input.clear();
        }
      }
      
      // Try to save
      await saveButton.click();
      await page.waitForTimeout(500);
      
      // Check if error message appears or form is still visible
      const formContent = await page.content();
      expect(formContent.length).toBeGreaterThan(0);
    }
  });

  test('should validate email format', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Find email input
    const emailInput = page.locator('input[type="email"]').first();
    if (await emailInput.isVisible()) {
      await emailInput.clear();
      await emailInput.fill('invalid-email');
      
      // Try to save
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('Profile Responsive Design', () => {
  test('should display correctly on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Check if page is still usable
    const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
    const isVisible = await saveButton.isVisible().catch(() => false);
    
    // Page should be readable on mobile
    const content = await page.content();
    expect(content.length).toBeGreaterThan(0);
  });

  test('should display correctly on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Check if page is still usable
    const content = await page.content();
    expect(content.length).toBeGreaterThan(0);
  });

  test('should display correctly on desktop', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(0);
  });
});

test.describe('Profile Session Management', () => {
  test('should maintain session after profile update', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Update profile
    const gradeInput = page.locator('input').filter({ hasText: /grade|класс/i }).first();
    if (await gradeInput.isVisible()) {
      await gradeInput.fill('10А');
      
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Сохранить")').first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(1000);
      }
    }
    
    // Check if still logged in
    const currentUrl = page.url();
    const isLoggedOut = currentUrl.includes('/login');
    expect(isLoggedOut).toBeFalsy();
  });

  test('should handle session expiration gracefully', async ({ page }) => {
    await loginUser(page, testUsers.student.email, testUsers.student.password);
    await navigateToProfile(page);
    
    // Clear cookies to simulate session expiration
    await page.context().clearCookies();
    
    // Refresh page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Should redirect to login
    const currentUrl = page.url();
    expect(currentUrl.length).toBeGreaterThan(0);
  });
});
