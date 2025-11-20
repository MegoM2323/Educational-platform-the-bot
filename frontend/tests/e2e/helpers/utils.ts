import { Page, expect } from '@playwright/test';

/**
 * Ждать пока toast уведомление появится
 */
export async function waitForToast(
  page: Page,
  messagePattern: string | RegExp,
  timeout: number = 5000
): Promise<void> {
  const toastLocator = page.locator(`text=${messagePattern}`).first();
  await expect(toastLocator).toBeVisible({ timeout });
}

/**
 * Проверить что показывается сообщение об ошибке
 */
export async function expectErrorMessage(
  page: Page,
  errorPattern: string | RegExp = /ошибк|error/i,
  timeout: number = 5000
): Promise<void> {
  const errorLocator = page.locator(`text=${errorPattern}`).first();
  await expect(errorLocator).toBeVisible({ timeout });
}

/**
 * Проверить что показывается сообщение об успехе
 */
export async function expectSuccessMessage(
  page: Page,
  successPattern: string | RegExp = /успешно|success/i,
  timeout: number = 5000
): Promise<void> {
  const successLocator = page.locator(`text=${successPattern}`).first();
  await expect(successLocator).toBeVisible({ timeout });
}

/**
 * Заполнить форму с множественными полями
 */
export async function fillForm(
  page: Page,
  fields: Record<string, string | number>
): Promise<void> {
  for (const [selector, value] of Object.entries(fields)) {
    await page.fill(selector, String(value));
  }
}

/**
 * Кликнуть по кнопке и дождаться навигации
 */
export async function clickAndWaitForNavigation(
  page: Page,
  buttonSelector: string,
  expectedUrl?: string | RegExp
): Promise<void> {
  await Promise.all([
    expectedUrl ? page.waitForURL(expectedUrl, { timeout: 10000 }) : page.waitForLoadState('networkidle'),
    page.click(buttonSelector),
  ]);
}

/**
 * Скриншот при ошибке
 */
export async function screenshotOnError(
  page: Page,
  testName: string,
  error: Error
): Promise<void> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const screenshotPath = `test-results/screenshots/${testName}-${timestamp}.png`;

  try {
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath}`);
  } catch (screenshotError) {
    console.error('Failed to take screenshot:', screenshotError);
  }

  throw error;
}

/**
 * Ждать когда элемент станет видимым
 */
export async function waitForElement(
  page: Page,
  selector: string,
  timeout: number = 10000
): Promise<void> {
  await page.waitForSelector(selector, { state: 'visible', timeout });
}

/**
 * Проверить что на странице есть текст
 */
export async function expectPageHasText(
  page: Page,
  text: string | RegExp,
  timeout: number = 5000
): Promise<void> {
  const textLocator = page.locator(`text=${text}`).first();
  await expect(textLocator).toBeVisible({ timeout });
}

/**
 * Подождать загрузку данных (исчезновение спиннера)
 */
export async function waitForLoadingComplete(page: Page, timeout: number = 10000): Promise<void> {
  // Ждем пока индикаторы загрузки исчезнут
  const loadingIndicators = [
    'text=/загрузка|loading/i',
    '[data-loading="true"]',
    '.loading',
    '.spinner',
  ];

  for (const indicator of loadingIndicators) {
    const locator = page.locator(indicator).first();
    if (await locator.count() > 0) {
      await locator.waitFor({ state: 'hidden', timeout });
    }
  }
}

/**
 * Получить текст элемента
 */
export async function getElementText(page: Page, selector: string): Promise<string> {
  const element = page.locator(selector);
  return await element.textContent() || '';
}

/**
 * Проверить что URL содержит параметр
 */
export function expectUrlContains(page: Page, substring: string): void {
  const url = page.url();
  if (!url.includes(substring)) {
    throw new Error(`Expected URL to contain "${substring}", but got: ${url}`);
  }
}

/**
 * Прокрутить к элементу
 */
export async function scrollToElement(page: Page, selector: string): Promise<void> {
  await page.locator(selector).scrollIntoViewIfNeeded();
}

/**
 * Генерация случайного email для тестов
 */
export function generateRandomEmail(prefix: string = 'test'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 10000);
  return `${prefix}-${timestamp}-${random}@test.com`;
}

/**
 * Генерация случайного имени
 */
export function generateRandomName(prefix: string = 'Test'): string {
  const random = Math.floor(Math.random() * 10000);
  return `${prefix} ${random}`;
}

/**
 * Ждать определенное время (использовать осторожно!)
 */
export async function wait(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}
