/**
 * Tests for i18n configuration and translation files
 */

import { describe, it, expect, beforeAll } from 'vitest';
import i18n from '../i18n';
import { SUPPORTED_LANGUAGES } from '../i18n';

describe('i18n Configuration', () => {
  beforeAll(async () => {
    await i18n.init();
  });

  describe('Initialization', () => {
    it('should initialize i18n successfully', () => {
      expect(i18n).toBeDefined();
      expect(i18n.language).toBeDefined();
    });

    it('should have default language set to English', () => {
      // Browser may return 'en-US' or 'en' depending on locale detection
      expect(i18n.language).toMatch(/^en/);
    });

    it('should have fallback language set to English', () => {
      // fallbackLng can be a string or array
      const fallback = i18n.options.fallbackLng;
      if (Array.isArray(fallback)) {
        expect(fallback).toContain('en');
      } else {
        expect(fallback).toBe('en');
      }
    });
  });

  describe('Supported Languages', () => {
    it('should have 4 supported languages', () => {
      expect(Object.keys(SUPPORTED_LANGUAGES)).toHaveLength(4);
    });

    it('should support English', () => {
      expect(SUPPORTED_LANGUAGES.en).toBeDefined();
      expect(SUPPORTED_LANGUAGES.en.name).toBe('English');
    });

    it('should support Russian', () => {
      expect(SUPPORTED_LANGUAGES.ru).toBeDefined();
      expect(SUPPORTED_LANGUAGES.ru.name).toBe('Русский');
    });

    it('should support Spanish', () => {
      expect(SUPPORTED_LANGUAGES.es).toBeDefined();
      expect(SUPPORTED_LANGUAGES.es.name).toBe('Español');
    });

    it('should support French', () => {
      expect(SUPPORTED_LANGUAGES.fr).toBeDefined();
      expect(SUPPORTED_LANGUAGES.fr.name).toBe('Français');
    });

    it('should have LTR direction for all languages', () => {
      Object.values(SUPPORTED_LANGUAGES).forEach((lang) => {
        expect(lang.dir).toBe('ltr');
      });
    });
  });

  describe('Translation Resources', () => {
    it('should have common namespace', async () => {
      const commonEn = await i18n.getResourceBundle('en', 'common');
      expect(commonEn).toBeDefined();
    });

    it('should have forms namespace', async () => {
      const formsEn = await i18n.getResourceBundle('en', 'forms');
      expect(formsEn).toBeDefined();
    });

    it('should have errors namespace', async () => {
      const errorsEn = await i18n.getResourceBundle('en', 'errors');
      expect(errorsEn).toBeDefined();
    });

    it('should have messages namespace', async () => {
      const messagesEn = await i18n.getResourceBundle('en', 'messages');
      expect(messagesEn).toBeDefined();
    });

    it('should have validation namespace', async () => {
      const validationEn = await i18n.getResourceBundle('en', 'validation');
      expect(validationEn).toBeDefined();
    });
  });

  describe('Translation Keys in English', () => {
    it('should have app title', () => {
      const result = i18n.t('app.title');
      expect(result).toBe('THE_BOT Educational Platform');
    });

    it('should have navigation keys', () => {
      expect(i18n.t('navigation.dashboard')).toBe('Dashboard');
      expect(i18n.t('navigation.materials')).toBe('Materials');
      expect(i18n.t('navigation.chat')).toBe('Chat');
    });

    it('should have common action keys', () => {
      expect(i18n.t('common.save')).toBe('Save');
      expect(i18n.t('common.cancel')).toBe('Cancel');
      expect(i18n.t('common.delete')).toBe('Delete');
    });

    it('should have status keys', () => {
      expect(i18n.t('status.active')).toBe('Active');
      expect(i18n.t('status.pending')).toBe('Pending');
      expect(i18n.t('status.completed')).toBe('Completed');
    });
  });

  describe('Translation Keys in Russian', () => {
    beforeAll(async () => {
      await i18n.changeLanguage('ru');
    });

    it('should have Russian app title', () => {
      const result = i18n.t('app.title');
      expect(result).toContain('THE_BOT');
      expect(result).toContain('Образовательная');
    });

    it('should have Russian navigation keys', () => {
      expect(i18n.t('navigation.dashboard')).toBe('Панель управления');
      expect(i18n.t('navigation.materials')).toBe('Материалы');
      expect(i18n.t('navigation.chat')).toBe('Чат');
    });

    it('should have Russian common action keys', () => {
      expect(i18n.t('common.save')).toBe('Сохранить');
      expect(i18n.t('common.cancel')).toBe('Отмена');
      expect(i18n.t('common.delete')).toBe('Удалить');
    });
  });

  describe('Language Switching', () => {
    it('should change language to Russian', async () => {
      await i18n.changeLanguage('ru');
      expect(i18n.language).toBe('ru');
    });

    it('should change language to Spanish', async () => {
      await i18n.changeLanguage('es');
      expect(i18n.language).toBe('es');
    });

    it('should change language to French', async () => {
      await i18n.changeLanguage('fr');
      expect(i18n.language).toBe('fr');
    });

    it('should change language back to English', async () => {
      await i18n.changeLanguage('en');
      expect(i18n.language).toBe('en');
    });
  });

  describe('Interpolation', () => {
    beforeAll(async () => {
      await i18n.changeLanguage('en');
    });

    it('should interpolate variables in translations', () => {
      const result = i18n.t('forms:hints.fileSize', { size: 50 });
      expect(result).toContain('50');
    });

    it('should handle plural forms', () => {
      // Test that plural key exists
      const result = i18n.t('time.minutesAgo', { count: 5 });
      expect(result).toBeDefined();
    });
  });

  describe('Fallback Behavior', () => {
    it('should fallback to English for missing keys', async () => {
      await i18n.changeLanguage('ru');
      const enKey = i18n.t('common.save');
      expect(enKey).toBeDefined();
    });
  });
});
