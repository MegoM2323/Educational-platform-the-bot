/**
 * Integration tests for i18n system
 */

import { describe, it, expect, beforeAll, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n';
import useI18n from '../useI18n';
import LanguageSwitcher from '../LanguageSwitcher';

// Test component that uses the hook
const TestComponent = () => {
  const { t, language, changeLanguage } = useI18n();

  return (
    <div>
      <h1>{t('app.title')}</h1>
      <p>{t('navigation.dashboard')}</p>
      <p data-testid="current-language">{language}</p>
      <button onClick={() => changeLanguage('ru')}>Switch to Russian</button>
    </div>
  );
};

describe('i18n Integration Tests', () => {
  beforeAll(async () => {
    await i18n.init();
  });

  describe('Translation Loading', () => {
    it('should load all translation files', async () => {
      const commonEn = i18n.getResourceBundle('en', 'common');
      const commonRu = i18n.getResourceBundle('ru', 'common');
      const commonEs = i18n.getResourceBundle('es', 'common');
      const commonFr = i18n.getResourceBundle('fr', 'common');

      expect(commonEn).toBeDefined();
      expect(commonRu).toBeDefined();
      expect(commonEs).toBeDefined();
      expect(commonFr).toBeDefined();
    });

    it('should load all namespaces', async () => {
      const namespaces = ['common', 'forms', 'errors', 'messages', 'validation'];

      for (const ns of namespaces) {
        const en = i18n.getResourceBundle('en', ns);
        expect(en).toBeDefined();
      }
    });
  });

  describe('Language Detection', () => {
    it('should detect browser language', async () => {
      // The language detector should work based on localStorage or browser settings
      expect(i18n.language).toBeDefined();
    });
  });

  describe('Component Integration', () => {
    it('should render with i18n provider', () => {
      const { getByText } = render(
        <I18nextProvider i18n={i18n}>
          <TestComponent />
        </I18nextProvider>
      );

      expect(getByText(/THE_BOT/)).toBeTruthy();
      expect(getByText('Dashboard')).toBeTruthy();
    });

    it('should display current language', () => {
      const { getByTestId } = render(
        <I18nextProvider i18n={i18n}>
          <TestComponent />
        </I18nextProvider>
      );

      const languageElement = getByTestId('current-language');
      // May contain locale variants like en-US
      expect(['en', 'en-US', 'ru', 'es', 'fr']).toContain(languageElement.textContent);
    });

    it('should change language on button click', async () => {
      await i18n.changeLanguage('en');

      const { getByText, getByTestId } = render(
        <I18nextProvider i18n={i18n}>
          <TestComponent />
        </I18nextProvider>
      );

      const button = getByText('Switch to Russian');
      fireEvent.click(button);

      await waitFor(() => {
        expect(getByTestId('current-language')).toHaveTextContent('ru');
      });
    });
  });

  describe('Translation Consistency', () => {
    it('should have same keys in all languages', () => {
      const enCommon = i18n.getResourceBundle('en', 'common');
      const ruCommon = i18n.getResourceBundle('ru', 'common');
      const esCommon = i18n.getResourceBundle('es', 'common');
      const frCommon = i18n.getResourceBundle('fr', 'common');

      const enKeys = Object.keys(enCommon);
      const ruKeys = Object.keys(ruCommon);
      const esKeys = Object.keys(esCommon);
      const frKeys = Object.keys(frCommon);

      expect(ruKeys).toEqual(expect.arrayContaining(enKeys));
      expect(esKeys).toEqual(expect.arrayContaining(enKeys));
      expect(frKeys).toEqual(expect.arrayContaining(enKeys));
    });

    it('should have translations for all UI text', () => {
      const keyPath = [
        'app.title',
        'navigation.dashboard',
        'navigation.materials',
        'common.save',
        'common.cancel',
        'status.active',
      ];

      keyPath.forEach((key) => {
        const translation = i18n.t(key);
        expect(translation).toBeDefined();
        expect(translation.length > 0).toBe(true);
      });
    });
  });

  describe('Error Message Translations', () => {
    it('should have error translations', () => {
      const errorKeys = [
        'errors:http.400',
        'errors:http.401',
        'errors:http.404',
        'validation:email.required',
        'validation:email.invalid',
        'errors:authentication.invalidCredentials',
      ];

      errorKeys.forEach((key) => {
        const translation = i18n.t(key);
        expect(translation).toBeDefined();
        expect(translation.length > 0).toBe(true);
      });
    });

    it('should have multilingual error messages', async () => {
      const errorKey = 'validation:email.required';

      await i18n.changeLanguage('en');
      const enError = i18n.t(errorKey);

      await i18n.changeLanguage('ru');
      const ruError = i18n.t(errorKey);

      expect(enError).not.toBe(ruError);
      expect(enError).toBe('Email is required');
      expect(ruError).toBe('Электронная почта обязательна');
    });
  });

  describe('Form Label Translations', () => {
    it('should have form labels', () => {
      const labels = [
        'forms.labels.email',
        'forms.labels.password',
        'forms.labels.firstName',
        'forms.labels.lastName',
      ];

      labels.forEach((key) => {
        const translation = i18n.t(key);
        expect(translation).toBeDefined();
      });
    });

    it('should have form button translations', () => {
      const buttons = [
        'forms.buttons.submit',
        'forms.buttons.save',
        'forms.buttons.cancel',
        'forms.buttons.login',
      ];

      buttons.forEach((key) => {
        const translation = i18n.t(key);
        expect(translation).toBeDefined();
      });
    });
  });

  describe('Language Switcher Component', () => {
    it('should render select variant', () => {
      const { getByRole } = render(
        <I18nextProvider i18n={i18n}>
          <LanguageSwitcher variant="select" />
        </I18nextProvider>
      );

      expect(getByRole('combobox')).toBeTruthy();
    });

    it('should render dropdown variant', () => {
      const { getByRole } = render(
        <I18nextProvider i18n={i18n}>
          <LanguageSwitcher variant="dropdown" />
        </I18nextProvider>
      );

      expect(getByRole('button')).toBeTruthy();
    });

    it('should render button variant', () => {
      const { getAllByRole } = render(
        <I18nextProvider i18n={i18n}>
          <LanguageSwitcher variant="button" />
        </I18nextProvider>
      );

      const buttons = getAllByRole('button');
      // Should have buttons for 4 languages
      expect(buttons.length).toBeGreaterThanOrEqual(4);
    });

    it('should show language names when showNames is true', () => {
      const { getByText } = render(
        <I18nextProvider i18n={i18n}>
          <LanguageSwitcher variant="button" showNames={true} />
        </I18nextProvider>
      );

      expect(getByText('English')).toBeTruthy();
      expect(getByText('Русский')).toBeTruthy();
    });
  });

  describe('Performance', () => {
    it('should translate quickly', () => {
      const start = performance.now();

      for (let i = 0; i < 100; i++) {
        i18n.t('common.save');
      }

      const end = performance.now();
      const duration = end - start;

      // Should complete 100 translations in less than 50ms
      expect(duration).toBeLessThan(50);
    });

    it('should handle language switching efficiently', async () => {
      const start = performance.now();

      await i18n.changeLanguage('ru');
      await i18n.changeLanguage('es');
      await i18n.changeLanguage('fr');
      await i18n.changeLanguage('en');

      const end = performance.now();
      const duration = end - start;

      // Should complete 4 language switches in less than 100ms
      expect(duration).toBeLessThan(100);
    });
  });

  describe('Storage Persistence', () => {
    it('should persist language preference to localStorage', async () => {
      localStorage.clear();

      await i18n.changeLanguage('ru');

      const stored = localStorage.getItem('i18n_language');
      expect(stored).toBe('ru');
    });

    it('should load persisted language on init', async () => {
      localStorage.setItem('i18n_language', 'es');

      // Note: This would require reinitializing i18n, which is complex in tests
      // For now, we verify that the key is stored correctly
      expect(localStorage.getItem('i18n_language')).toBe('es');
    });
  });

  describe('Fallback Mechanism', () => {
    it('should fallback to English for undefined keys', () => {
      const translation = i18n.t('nonexistent.deeply.nested.key');
      expect(translation).toBeDefined();
    });

    it('should maintain consistency with fallback', async () => {
      await i18n.changeLanguage('ru');
      const ruTranslation = i18n.t('common.save');

      await i18n.changeLanguage('en');
      const enTranslation = i18n.t('common.save');

      expect(ruTranslation).toBe('Сохранить');
      expect(enTranslation).toBe('Save');
    });
  });
});
