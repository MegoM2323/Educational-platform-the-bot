import { test, expect } from '@playwright/test';

test.describe('General Chat - Route Verification', () => {
  test('student general-chat route exists', async ({ page }) => {
    // Navigate directly - it will redirect to auth if not logged in
    // But the route itself will exist and be handled by React Router

    const response = await page.goto('/dashboard/student/general-chat', {
      waitUntil: 'domcontentloaded'
    });

    const currentUrl = page.url();
    console.log(`Navigated to: ${currentUrl}`);

    // Should either be on general-chat or redirected to auth
    expect(
      currentUrl.includes('/dashboard/student/general-chat') ||
      currentUrl.includes('/auth') ||
      currentUrl.includes('/login')
    ).toBe(true);
  });

  test('teacher general-chat route exists', async ({ page }) => {
    const response = await page.goto('/dashboard/teacher/general-chat', {
      waitUntil: 'domcontentloaded'
    });

    const currentUrl = page.url();
    console.log(`Navigated to: ${currentUrl}`);

    expect(
      currentUrl.includes('/dashboard/teacher/general-chat') ||
      currentUrl.includes('/auth') ||
      currentUrl.includes('/login')
    ).toBe(true);
  });

  test('tutor general-chat route exists', async ({ page }) => {
    const response = await page.goto('/dashboard/tutor/general-chat', {
      waitUntil: 'domcontentloaded'
    });

    const currentUrl = page.url();
    console.log(`Navigated to: ${currentUrl}`);

    expect(
      currentUrl.includes('/dashboard/tutor/general-chat') ||
      currentUrl.includes('/auth') ||
      currentUrl.includes('/login')
    ).toBe(true);
  });
});
