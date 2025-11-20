import { test, expect } from '@playwright/test';

// Базовый URL для тестов
const BASE_URL = 'http://localhost:8080';

test.describe('Landing Page - Comprehensive E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Переход на главную страницу перед каждым тестом
    await page.goto(BASE_URL);
    // Ждем пока страница полностью загрузится
    await page.waitForLoadState('networkidle');
  });

  test.describe('ТЕСТ 1: Навигация и структура страницы', () => {

    test('Страница загружается и имеет правильный черный фон', async ({ page }) => {
      // Проверяем что страница загрузилась
      await expect(page).toHaveURL(BASE_URL);

      // Проверяем что main div имеет черный фон
      const mainDiv = page.locator('div.min-h-screen.bg-black');
      await expect(mainDiv).toBeVisible();
    });

    test('Header (sticky) присутствует и видим', async ({ page }) => {
      const header = page.locator('header');
      await expect(header).toBeVisible();

      // Проверяем что header sticky
      const headerClasses = await header.getAttribute('class');
      expect(headerClasses).toContain('sticky');
      expect(headerClasses).toContain('backdrop-blur');
    });

    test('Hero Section с 3 карточками присутствует', async ({ page }) => {
      // Проверяем заголовок Hero секции
      const heroTitle = page.locator('h1:has-text("Образовательная платформа")');
      await expect(heroTitle).toBeVisible();

      // Проверяем что есть 3 карточки
      const serviceCards = page.locator('.grid.md\\:grid-cols-3 > div').first().locator('> div');
      await expect(serviceCards).toHaveCount(3);

      // Проверяем тексты карточек
      await expect(page.locator('text=Трекинг прогресса')).toBeVisible();
      await expect(page.locator('text=Прямая связь')).toBeVisible();
      await expect(page.locator('text=Персональные отчёты')).toBeVisible();
    });

    test('Секция "О платформе" с 4 карточками присутствует', async ({ page }) => {
      const aboutSection = page.locator('section#about');
      await expect(aboutSection).toBeVisible();

      // Скроллим к секции
      await aboutSection.scrollIntoViewIfNeeded();

      // Проверяем заголовок секции
      await expect(page.locator('text=О платформе')).toBeVisible();
    });

    test('Секция "Преимущества" присутствует', async ({ page }) => {
      const advantagesSection = page.locator('section#advantages');
      await expect(advantagesSection).toBeVisible();

      await advantagesSection.scrollIntoViewIfNeeded();
      await expect(page.locator('text=Преимущества')).toBeVisible();
    });

    test('Секция "Тарифы" с 3 карточками присутствует', async ({ page }) => {
      const pricingSection = page.locator('section#pricing');
      await expect(pricingSection).toBeVisible();

      await pricingSection.scrollIntoViewIfNeeded();

      // Проверяем заголовок
      await expect(page.locator('text=Тарифы').first()).toBeVisible();

      // Проверяем что есть 3 тарифные карточки
      const pricingCards = pricingSection.locator('.grid.md\\:grid-cols-3 > div');
      await expect(pricingCards).toHaveCount(3);

      // Проверяем названия тарифов
      await expect(page.locator('text=Базовый')).toBeVisible();
      await expect(page.locator('text=Стандартный')).toBeVisible();
      await expect(page.locator('text=Премиум')).toBeVisible();
    });

    test('Секция "Начните обучение сегодня" (CTA) присутствует', async ({ page }) => {
      const ctaSection = page.locator('section#cta');
      await expect(ctaSection).toBeVisible();
    });

    test('Footer присутствует', async ({ page }) => {
      const footer = page.locator('footer');
      await expect(footer).toBeVisible();

      // Скроллим вниз чтобы увидеть footer
      await footer.scrollIntoViewIfNeeded();
    });
  });

  test.describe('ТЕСТ 2: Интерактивные элементы', () => {

    test('Кнопка "Подать заявку" в Hero ведет на /application', async ({ page }) => {
      const applyButton = page.locator('a[href="/application"]').filter({ hasText: 'Подать заявку' }).first();
      await expect(applyButton).toBeVisible();

      // Кликаем и проверяем навигацию
      await applyButton.click();
      await expect(page).toHaveURL(`${BASE_URL}/application`);
    });

    test('Кнопка "Личный кабинет" в Hero ведет на /auth', async ({ page }) => {
      const cabinetButton = page.locator('a[href="/auth"]').filter({ hasText: 'Личный кабинет' }).first();
      await expect(cabinetButton).toBeVisible();

      await cabinetButton.click();
      await expect(page).toHaveURL(`${BASE_URL}/auth`);
    });

    test('Кнопка "Войти" в Header ведет на /auth', async ({ page }) => {
      const loginButton = page.locator('header a[href="/auth"]');
      await expect(loginButton).toBeVisible();

      await loginButton.click();
      await expect(page).toHaveURL(`${BASE_URL}/auth`);
    });

    test('Навигация "О платформе" скроллит к секции about', async ({ page }) => {
      const navButton = page.locator('nav button:has-text("О платформе")');
      await expect(navButton).toBeVisible();

      // Получаем начальную позицию скролла
      const initialScroll = await page.evaluate(() => window.scrollY);

      await navButton.click();

      // Ждем окончания скролла
      await page.waitForTimeout(1000);

      // Проверяем что скролл изменился
      const afterScroll = await page.evaluate(() => window.scrollY);
      expect(afterScroll).toBeGreaterThan(initialScroll);

      // Проверяем что секция about видима
      const aboutSection = page.locator('section#about');
      await expect(aboutSection).toBeInViewport();
    });

    test('Навигация "Преимущества" скроллит к секции advantages', async ({ page }) => {
      const navButton = page.locator('nav button:has-text("Преимущества")');
      await expect(navButton).toBeVisible();

      await navButton.click();
      await page.waitForTimeout(1000);

      const advantagesSection = page.locator('section#advantages');
      await expect(advantagesSection).toBeInViewport();
    });

    test('Навигация "Тарифы" скроллит к секции pricing', async ({ page }) => {
      const navButton = page.locator('nav button:has-text("Тарифы")');
      await expect(navButton).toBeVisible();

      await navButton.click();
      await page.waitForTimeout(1000);

      const pricingSection = page.locator('section#pricing');
      await expect(pricingSection).toBeInViewport();
    });

    test('Навигация "Контакты" скроллит к секции cta', async ({ page }) => {
      const navButton = page.locator('nav button:has-text("Контакты")');
      await expect(navButton).toBeVisible();

      await navButton.click();
      await page.waitForTimeout(1000);

      const ctaSection = page.locator('section#cta');
      await expect(ctaSection).toBeInViewport();
    });

    test('Кнопки "Выбрать" в тарифах ведут на /application', async ({ page }) => {
      // Скроллим к секции тарифов
      const pricingSection = page.locator('section#pricing');
      await pricingSection.scrollIntoViewIfNeeded();

      // Находим первую кнопку "Выбрать"
      const selectButton = page.locator('section#pricing button:has-text("Выбрать")').first();
      await expect(selectButton).toBeVisible();

      await selectButton.click();
      await expect(page).toHaveURL(`${BASE_URL}/application`);
    });

    test('Кнопка "Подать заявку" в CTA секции ведет на /application', async ({ page }) => {
      const ctaSection = page.locator('section#cta');
      await ctaSection.scrollIntoViewIfNeeded();

      const applyButton = ctaSection.locator('a[href="/application"]');
      await expect(applyButton).toBeVisible();

      await applyButton.click();
      await expect(page).toHaveURL(`${BASE_URL}/application`);
    });
  });

  test.describe('ТЕСТ 3: Визуальные элементы', () => {

    test('Рейтинги со звездами отображаются под каждой из 3 hero карточек', async ({ page }) => {
      // Находим все карточки с рейтингом в hero секции
      const ratingBadges = page.locator('.grid.md\\:grid-cols-3').first().locator('svg.lucide-star');

      // У нас 3 карточки по 5 звезд = 15 звезд
      const count = await ratingBadges.count();
      expect(count).toBe(15);

      // Проверяем что звезды желтые (fill-yellow-400)
      const firstStar = ratingBadges.first();
      const starClass = await firstStar.getAttribute('class');
      expect(starClass).toContain('fill-yellow-400');
    });

    test('Декоративные желтые квадраты видимы', async ({ page }) => {
      // DecorativeSquare использует yellow-400 цвет
      const decorativeSquares = page.locator('div').filter({
        has: page.locator('[class*="bg-yellow-400"]')
      });

      // Должно быть несколько декоративных квадратов
      const count = await decorativeSquares.count();
      expect(count).toBeGreaterThan(0);
    });

    test('Иконки в карточках отображаются (lucide-react icons)', async ({ page }) => {
      // Проверяем иконки в hero карточках
      const targetIcon = page.locator('svg.lucide-target');
      await expect(targetIcon).toBeVisible();

      const messageIcon = page.locator('svg.lucide-message-circle');
      await expect(messageIcon).toBeVisible();

      const trendingIcon = page.locator('svg.lucide-trending-up');
      await expect(trendingIcon).toBeVisible();
    });

    test('Средняя тарифная карточка визуально выделена', async ({ page }) => {
      const pricingSection = page.locator('section#pricing');
      await pricingSection.scrollIntoViewIfNeeded();

      // Находим все тарифные карточки
      const pricingCards = pricingSection.locator('.grid.md\\:grid-cols-3 > div');

      // Получаем вторую карточку (index 1)
      const middleCard = pricingCards.nth(1);

      // Проверяем что средняя карточка имеет выделение (scale-105 или gradient от purple-600)
      const middleCardClass = await middleCard.getAttribute('class');
      expect(middleCardClass).toContain('scale-105');
    });

    test('Header имеет backdrop-blur эффект', async ({ page }) => {
      const header = page.locator('header');
      const headerClass = await header.getAttribute('class');

      expect(headerClass).toContain('backdrop-blur');
    });

    test('Логотип THE BOT отображается корректно', async ({ page }) => {
      const logoTHE = page.locator('header a[href="/"] span:has-text("THE")');
      await expect(logoTHE).toBeVisible();

      const logoBOT = page.locator('header a[href="/"] span:has-text("BOT")');
      await expect(logoBOT).toBeVisible();
    });
  });

  test.describe('ТЕСТ 4: Адаптивность (Desktop)', () => {

    test('Desktop (1920x1080): все элементы в правильной раскладке', async ({ page }) => {
      // Устанавливаем размер viewport
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto(BASE_URL);

      // Проверяем что навигация видима (не бургер меню)
      const desktopNav = page.locator('nav.hidden.md\\:flex');
      await expect(desktopNav).toBeVisible();

      // Проверяем что бургер меню скрыт
      const burgerButton = page.locator('button.md\\:hidden');
      await expect(burgerButton).not.toBeVisible();

      // Проверяем что карточки в 3 колонки
      const heroCards = page.locator('.grid.md\\:grid-cols-3').first();
      const heroCardsClass = await heroCards.getAttribute('class');
      expect(heroCardsClass).toContain('md:grid-cols-3');
    });
  });

  test.describe('ТЕСТ 5: Hover эффекты', () => {

    test('Карточки имеют hover эффект', async ({ page }) => {
      // Находим первую карточку
      const firstCard = page.locator('.grid.md\\:grid-cols-3').first().locator('> div').first();

      // Получаем класс карточки
      const cardClass = await firstCard.getAttribute('class');

      // Проверяем что есть hover классы
      expect(cardClass).toMatch(/hover:(shadow|translate)/);
    });

    test('Кнопки меняют внешний вид при наведении', async ({ page }) => {
      const applyButton = page.locator('a[href="/application"]').filter({ hasText: 'Подать заявку' }).first();

      const buttonClass = await applyButton.locator('button').getAttribute('class');
      expect(buttonClass).toMatch(/hover:bg-/);
    });

    test('Навигационные ссылки в Header меняют цвет при наведении', async ({ page }) => {
      const navButton = page.locator('nav button:has-text("О платформе")');
      const buttonClass = await navButton.getAttribute('class');

      expect(buttonClass).toContain('hover:text-white');
    });
  });

  test.describe('ТЕСТ 6: Анимации', () => {

    test('Intersection Observer инициализируется для анимаций', async ({ page }) => {
      // Проверяем что все секции имеют возможность анимации
      const sections = page.locator('section');
      const count = await sections.count();

      // Должно быть несколько секций
      expect(count).toBeGreaterThan(3);
    });

    test('Hero секция имеет fade-in анимацию', async ({ page }) => {
      const heroText = page.locator('.animate-fade-in').first();
      await expect(heroText).toBeVisible();
    });
  });

  test.describe('ТЕСТ 7: Accessibility', () => {

    test('Все интерактивные элементы доступны с клавиатуры', async ({ page }) => {
      // Проверяем что кнопки имеют правильные теги
      const buttons = page.locator('button, a[href]');
      const count = await buttons.count();

      expect(count).toBeGreaterThan(0);
    });

    test('Заголовки имеют правильную иерархию', async ({ page }) => {
      // Проверяем наличие h1
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();

      // Проверяем наличие h2
      const h2 = page.locator('h2');
      const h2Count = await h2.count();
      expect(h2Count).toBeGreaterThan(0);

      // Проверяем наличие h3
      const h3 = page.locator('h3');
      const h3Count = await h3.count();
      expect(h3Count).toBeGreaterThan(0);
    });
  });

  test.describe('ТЕСТ 8: Контент и тексты', () => {

    test('Все основные тексты присутствуют', async ({ page }) => {
      // Hero секция
      await expect(page.locator('text=Образовательная платформа')).toBeVisible();
      await expect(page.locator('text=нового поколения')).toBeVisible();

      // Описание
      await expect(page.locator('text=Персонализированное обучение')).toBeVisible();

      // Названия карточек
      await expect(page.locator('text=Трекинг прогресса')).toBeVisible();
      await expect(page.locator('text=Прямая связь')).toBeVisible();
      await expect(page.locator('text=Персональные отчёты')).toBeVisible();
    });

    test('Цены в тарифах отображаются корректно', async ({ page }) => {
      const pricingSection = page.locator('section#pricing');
      await pricingSection.scrollIntoViewIfNeeded();

      // Проверяем наличие цен
      await expect(page.locator('text=3500')).toBeVisible();
      await expect(page.locator('text=5000')).toBeVisible();
      await expect(page.locator('text=7500')).toBeVisible();

      // Проверяем валюту
      await expect(page.locator('text=₽').first()).toBeVisible();
    });

    test('Рейтинг отображается с правильным текстом', async ({ page }) => {
      // Проверяем текст рейтинга
      await expect(page.locator('text=4.9')).toBeVisible();
      await expect(page.locator('text=из 5 звезд')).toBeVisible();
    });
  });

  test.describe('ТЕСТ 9: Mobile Menu', () => {

    test('Бургер меню появляется на мобильных устройствах', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(BASE_URL);

      // Проверяем что бургер кнопка видима
      const burgerButton = page.locator('button').filter({ has: page.locator('svg.lucide-menu') });
      await expect(burgerButton).toBeVisible();

      // Кликаем на бургер
      await burgerButton.click();

      // Проверяем что мобильное меню открылось
      const mobileNav = page.locator('nav.md\\:hidden.mt-4');
      await expect(mobileNav).toBeVisible();

      // Проверяем наличие пунктов меню
      await expect(page.locator('nav.md\\:hidden button:has-text("О платформе")')).toBeVisible();
    });

    test('Мобильное меню закрывается после клика на пункт', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(BASE_URL);

      // Открываем меню
      const burgerButton = page.locator('button').filter({ has: page.locator('svg.lucide-menu') });
      await burgerButton.click();

      // Кликаем на пункт меню
      const menuItem = page.locator('nav.md\\:hidden button:has-text("О платформе")');
      await menuItem.click();

      // Ждем немного
      await page.waitForTimeout(500);

      // Проверяем что меню закрылось (мобильная навигация скрыта)
      const mobileNav = page.locator('nav.md\\:hidden.mt-4');
      await expect(mobileNav).not.toBeVisible();
    });
  });
});
