import { chromium, firefox, webkit, BrowserContext } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';
const API_URL = process.env.API_URL || 'http://localhost:8000';

/**
 * Setup configuration for E2E tests
 * This can be imported by test files that need special setup
 */
export const testConfig = {
  baseUrl: BASE_URL,
  apiUrl: API_URL,
  timeout: 30000,
  slowMo: process.env.SLOW_MO ? parseInt(process.env.SLOW_MO) : 0,
};

/**
 * Common test utilities
 */
export const testUtils = {
  /**
   * Wait for element with retry
   */
  async waitForElement(page: any, selector: string, timeout = 5000) {
    try {
      await page.waitForSelector(selector, { timeout });
      return true;
    } catch (e) {
      return false;
    }
  },

  /**
   * Safe click with retry
   */
  async safeClick(page: any, locator: any, retries = 3) {
    for (let i = 0; i < retries; i++) {
      try {
        const isVisible = await locator.isVisible({ timeout: 2000 }).catch(() => false);
        if (isVisible) {
          await locator.click();
          return true;
        }
      } catch (e) {
        if (i === retries - 1) throw e;
        await page.waitForTimeout(100);
      }
    }
    return false;
  },

  /**
   * Safe fill with clear
   */
  async safeFill(page: any, locator: any, text: string) {
    try {
      // Triple click to select all
      await locator.click({ clickCount: 3 });
      await page.keyboard.press('Delete');
      await locator.fill(text);
      return true;
    } catch (e) {
      console.error('SafeFill error:', e);
      return false;
    }
  },
};

/**
 * Health check - verify backend and frontend are running
 */
export async function healthCheck() {
  console.log('Checking system health...');

  try {
    // Check frontend
    const frontendResponse = await fetch(BASE_URL, { timeout: 5000 }).catch(e => ({
      ok: false,
      error: e.message,
    }));
    console.log(`Frontend (${BASE_URL}): ${frontendResponse.ok ? '✓' : '✗'}`);

    // Check backend
    const backendResponse = await fetch(`${API_URL}/health/`, { timeout: 5000 }).catch(e => ({
      ok: false,
      error: e.message,
    }));
    console.log(`Backend (${API_URL}): ${backendResponse.ok ? '✓' : '✗'}`);

    if (!frontendResponse.ok || !backendResponse.ok) {
      console.warn('⚠️  Some services may not be fully ready');
    }
  } catch (e) {
    console.warn('⚠️  Health check failed:', e);
  }
}
