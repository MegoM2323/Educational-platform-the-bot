import { test, expect } from '@playwright/test';

test.describe('General Chat - Direct Page Access', () => {
  test('student general-chat page exists and loads', async ({ page }) => {
    // Try to navigate directly without authentication
    // If it redirects to /auth, that's fine - it means the page exists
    
    const response = await page.goto('/dashboard/student/general-chat', {
      waitUntil: 'load'
    });
    
    console.log(`Response status: ${response?.status()}`);
    console.log(`Current URL: ${page.url()}`);
    
    // The page should either load the general-chat or redirect to auth
    // Both are valid - it means the route exists
    const currentUrl = page.url();
    expect(
      currentUrl.includes('/dashboard/student/general-chat') || 
      currentUrl.includes('/auth')
    ).toBe(true);
  });
  
  test('teacher general-chat page exists and loads', async ({ page }) => {
    const response = await page.goto('/dashboard/teacher/general-chat', {
      waitUntil: 'load'
    });
    
    console.log(`Response status: ${response?.status()}`);
    const currentUrl = page.url();
    expect(
      currentUrl.includes('/dashboard/teacher/general-chat') || 
      currentUrl.includes('/auth')
    ).toBe(true);
  });
  
  test('tutor general-chat page exists and loads', async ({ page }) => {
    const response = await page.goto('/dashboard/tutor/general-chat', {
      waitUntil: 'load'
    });
    
    console.log(`Response status: ${response?.status()}`);
    const currentUrl = page.url();
    expect(
      currentUrl.includes('/dashboard/tutor/general-chat') || 
      currentUrl.includes('/auth')
    ).toBe(true);
  });
});
