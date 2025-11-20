import { test, expect } from '@playwright/test';

test.describe('Проверка исправлений лендинга', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8080');
  });

  test('Фото основателя видимо и имеет правильные стили', async ({ page }) => {
    // Скроллим к секции founder
    await page.locator('#founder').scrollIntoViewIfNeeded();

    // Проверяем что изображение основателя присутствует
    const founderImg = page.locator('img[alt="Александр Тимошкин"]').first();
    await expect(founderImg).toBeVisible();

    // Проверяем что у него есть brightness/contrast классы для улучшения видимости
    const imgClasses = await founderImg.getAttribute('class');
    expect(imgClasses).toContain('brightness-110');
    expect(imgClasses).toContain('contrast-110');
  });

  test('Карточки университетов имеют фоновые изображения', async ({ page }) => {
    // Проверяем секцию с университетами
    const universitiesSection = page.locator('text=Наши выпускники поступают в').locator('..');
    await universitiesSection.scrollIntoViewIfNeeded();

    // Проверяем что есть фоновые изображения platform-screenshot
    const screenshot1 = page.locator('img[src="/images/landing/platform-screenshot-1.png"]');
    await expect(screenshot1).toBeVisible();

    const screenshot2 = page.locator('img[src="/images/landing/platform-screenshot-2.png"]');
    await expect(screenshot2).toBeVisible();

    const screenshot3 = page.locator('img[src="/images/landing/platform-screenshot-3.png"]');
    await expect(screenshot3).toBeVisible();
  });

  test('Адаптивность фото основателя (mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.locator('#founder').scrollIntoViewIfNeeded();

    const founderImg = page.locator('img[alt="Александр Тимошкин"]').first();
    await expect(founderImg).toBeVisible();

    const boundingBox = await founderImg.boundingBox();
    // На mobile должно быть w-32 h-32 = 128px
    expect(boundingBox?.width).toBeGreaterThan(100);
    expect(boundingBox?.width).toBeLessThan(150);
  });

  test('Адаптивность фото основателя (tablet)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.locator('#founder').scrollIntoViewIfNeeded();

    const founderImg = page.locator('img[alt="Александр Тимошкин"]').first();
    await expect(founderImg).toBeVisible();

    const boundingBox = await founderImg.boundingBox();
    // На tablet должно быть w-48 h-48 = 192px
    expect(boundingBox?.width).toBeGreaterThan(180);
    expect(boundingBox?.width).toBeLessThan(210);
  });

  test('Адаптивность фото основателя (desktop)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.locator('#founder').scrollIntoViewIfNeeded();

    const founderImg = page.locator('img[alt="Александр Тимошкин"]').first();
    await expect(founderImg).toBeVisible();

    const boundingBox = await founderImg.boundingBox();
    // На desktop должно быть w-64 h-64 = 256px
    expect(boundingBox?.width).toBeGreaterThan(245);
    expect(boundingBox?.width).toBeLessThan(270);
  });

  test('Карточки университетов адаптивны (mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });

    const universitiesSection = page.locator('text=Наши выпускники поступают в').locator('..');
    await universitiesSection.scrollIntoViewIfNeeded();

    // Проверяем что карточки видимы
    const cards = page.locator('img[src*="platform-screenshot"]');
    expect(await cards.count()).toBe(3);
  });

  test('Текст поверх фона карточек читаем (имеет оверлей)', async ({ page }) => {
    const universitiesSection = page.locator('text=Наши выпускники поступают в').locator('..');
    await universitiesSection.scrollIntoViewIfNeeded();

    // Проверяем наличие темного оверлея для читаемости
    const overlay = page.locator('.bg-gradient-to-b.from-black\\/60').first();
    await expect(overlay).toBeVisible();

    // Проверяем что текст "100%" виден
    const percentText = page.locator('text=100%').first();
    await expect(percentText).toBeVisible();
  });
});
