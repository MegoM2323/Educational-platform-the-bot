/**
 * E2E тесты бронирования для студента.
 *
 * Feature: Student Scheduling and Booking
 */

import { test, expect } from '@playwright/test';

test.describe('Student Booking Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Логинимся как студент
    await page.goto('/login');
    await page.fill('[name="email"]', 'student@test.com');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should view available time slots', async ({ page }) => {
    // Переход на страницу расписания
    await page.click('[data-testid="nav-schedule"]');
    await page.waitForSelector('[data-testid="schedule-page"]');

    // Выбираем преподавателя
    await page.selectOption('[data-testid="teacher-select"]', 'teacher@test.com');

    // Выбираем предмет
    await page.selectOption('[data-testid="subject-select"]', 'Математика');

    // Выбираем дату
    await page.click('[data-testid="date-picker"]');
    await page.click('[data-testid="date-next-monday"]');

    // Проверяем что слоты отображаются
    await expect(page.locator('[data-testid="time-slot"]')).toHaveCount(6); // 10:00-16:00 по часу
    await expect(page.locator('[data-testid="time-slot-available"]').first()).toBeVisible();
  });

  test('should create a booking', async ({ page }) => {
    // Переход на страницу расписания
    await page.click('[data-testid="nav-schedule"]');

    // Выбираем параметры
    await page.selectOption('[data-testid="teacher-select"]', 'teacher@test.com');
    await page.selectOption('[data-testid="subject-select"]', 'Математика');
    await page.click('[data-testid="date-picker"]');
    await page.click('[data-testid="date-next-monday"]');

    // Кликаем на доступный слот
    await page.click('[data-testid="time-slot-10-00"]');

    // Заполняем модальное окно бронирования
    await page.waitForSelector('[data-testid="booking-modal"]');
    await page.fill('[data-testid="lesson-topic"]', 'Квадратные уравнения');
    await page.fill('[data-testid="lesson-notes"]', 'Подготовка к контрольной');
    await page.fill('[data-testid="student-phone"]', '+7 999 123-45-67');

    // Подтверждаем бронирование
    await page.click('[data-testid="confirm-booking-btn"]');

    // Проверяем успешное создание
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Бронирование создано');

    // Проверяем что слот теперь недоступен
    await expect(page.locator('[data-testid="time-slot-10-00"]')).toHaveClass(/slot-pending/);
  });

  test('should view my bookings', async ({ page }) => {
    // Переход на страницу "Мои брони"
    await page.click('[data-testid="nav-my-bookings"]');
    await page.waitForSelector('[data-testid="bookings-list"]');

    // Проверяем наличие бронирований
    const bookings = page.locator('[data-testid="booking-card"]');
    await expect(bookings).toHaveCount(2); // pending и confirmed

    // Проверяем статусы
    await expect(page.locator('[data-testid="booking-pending"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="booking-confirmed"]').first()).toBeVisible();
  });

  test('should cancel pending booking', async ({ page }) => {
    // Переход на страницу "Мои брони"
    await page.click('[data-testid="nav-my-bookings"]');

    // Находим pending бронирование
    const pendingBooking = page.locator('[data-testid="booking-pending"]').first();
    await pendingBooking.locator('[data-testid="cancel-btn"]').click();

    // Подтверждаем отмену в диалоге
    await page.waitForSelector('[data-testid="cancel-dialog"]');
    await page.fill('[data-testid="cancel-reason"]', 'Изменились планы');
    await page.click('[data-testid="confirm-cancel-btn"]');

    // Проверяем что бронирование отменено
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Бронирование отменено');
    await expect(pendingBooking).toHaveClass(/booking-cancelled/);
  });

  test('should filter bookings by status', async ({ page }) => {
    await page.click('[data-testid="nav-my-bookings"]');

    // Фильтр: только подтвержденные
    await page.selectOption('[data-testid="status-filter"]', 'confirmed');
    await expect(page.locator('[data-testid="booking-card"]')).toHaveCount(1);
    await expect(page.locator('[data-testid="booking-confirmed"]')).toBeVisible();

    // Фильтр: только ожидающие
    await page.selectOption('[data-testid="status-filter"]', 'pending');
    await expect(page.locator('[data-testid="booking-pending"]')).toBeVisible();

    // Фильтр: все
    await page.selectOption('[data-testid="status-filter"]', 'all');
    const allBookings = page.locator('[data-testid="booking-card"]');
    await expect(allBookings.count()).toBeGreaterThan(1);
  });

  test('should see booking details', async ({ page }) => {
    await page.click('[data-testid="nav-my-bookings"]');

    // Кликаем на бронирование для просмотра деталей
    await page.click('[data-testid="booking-card"]').first();

    // Проверяем детали в модальном окне
    await page.waitForSelector('[data-testid="booking-details-modal"]');
    await expect(page.locator('[data-testid="detail-teacher"]')).toContainText('Иван Иванов');
    await expect(page.locator('[data-testid="detail-subject"]')).toContainText('Математика');
    await expect(page.locator('[data-testid="detail-date"]')).toBeVisible();
    await expect(page.locator('[data-testid="detail-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="detail-status"]')).toBeVisible();
  });

  test('should not book slot in the past', async ({ page }) => {
    await page.click('[data-testid="nav-schedule"]');

    // Выбираем прошедшую дату
    await page.click('[data-testid="date-picker"]');
    await page.click('[data-testid="date-yesterday"]');

    // Проверяем что слоты недоступны
    await expect(page.locator('[data-testid="no-slots-message"]')).toContainText('Нет доступных слотов');
  });

  test('should see error when double booking same time', async ({ page }) => {
    await page.click('[data-testid="nav-schedule"]');

    // Первое бронирование
    await page.selectOption('[data-testid="teacher-select"]', 'teacher@test.com');
    await page.selectOption('[data-testid="subject-select"]', 'Математика');
    await page.click('[data-testid="time-slot-11-00"]');
    await page.click('[data-testid="confirm-booking-btn"]');

    // Пытаемся забронировать то же время у другого преподавателя
    await page.selectOption('[data-testid="teacher-select"]', 'teacher2@test.com');
    await page.click('[data-testid="time-slot-11-00"]');
    await page.click('[data-testid="confirm-booking-btn"]');

    // Проверяем ошибку
    await expect(page.locator('[data-testid="error-message"]')).toContainText('У вас уже есть урок в это время');
  });
});

test.describe('Mobile Student Booking', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should work on mobile viewport', async ({ page }) => {
    // Логин
    await page.goto('/login');
    await page.fill('[name="email"]', 'student@test.com');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');

    // Открываем мобильное меню
    await page.click('[data-testid="mobile-menu-btn"]');
    await page.click('[data-testid="mobile-nav-schedule"]');

    // Проверяем адаптивность
    await expect(page.locator('[data-testid="schedule-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="mobile-filters"]')).toBeVisible();
  });
});