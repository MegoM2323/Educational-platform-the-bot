/**
 * i18n Configuration
 *
 * Internationalization setup using react-i18next with support for:
 * - English (en)
 * - Russian (ru)
 * - Spanish (es)
 * - French (fr)
 *
 * Features:
 * - Browser language detection
 * - Fallback to English
 * - Language persistence in localStorage
 * - Locale-aware formatting (dates, numbers)
 * - Dynamic language switching
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import enCommon from './locales/en/common.json';
import enForms from './locales/en/forms.json';
import enErrors from './locales/en/errors.json';
import enMessages from './locales/en/messages.json';
import enValidation from './locales/en/validation.json';

import ruCommon from './locales/ru/common.json';
import ruForms from './locales/ru/forms.json';
import ruErrors from './locales/ru/errors.json';
import ruMessages from './locales/ru/messages.json';
import ruValidation from './locales/ru/validation.json';

import esCommon from './locales/es/common.json';
import esForms from './locales/es/forms.json';
import esErrors from './locales/es/errors.json';
import esMessages from './locales/es/messages.json';
import esValidation from './locales/es/validation.json';

import frCommon from './locales/fr/common.json';
import frForms from './locales/fr/forms.json';
import frErrors from './locales/fr/errors.json';
import frMessages from './locales/fr/messages.json';
import frValidation from './locales/fr/validation.json';

/**
 * Translation resources structure
 */
const resources = {
  en: {
    common: enCommon,
    forms: enForms,
    errors: enErrors,
    messages: enMessages,
    validation: enValidation,
  },
  ru: {
    common: ruCommon,
    forms: ruForms,
    errors: ruErrors,
    messages: ruMessages,
    validation: ruValidation,
  },
  es: {
    common: esCommon,
    forms: esForms,
    errors: esErrors,
    messages: esMessages,
    validation: esValidation,
  },
  fr: {
    common: frCommon,
    forms: frForms,
    errors: frErrors,
    messages: frMessages,
    validation: frValidation,
  },
};

/**
 * Supported languages configuration
 */
export const SUPPORTED_LANGUAGES = {
  en: { name: 'English', dir: 'ltr' },
  ru: { name: 'Русский', dir: 'ltr' },
  es: { name: 'Español', dir: 'ltr' },
  fr: { name: 'Français', dir: 'ltr' },
} as const;

export type SupportedLanguage = keyof typeof SUPPORTED_LANGUAGES;

/**
 * Initialize i18n
 */
i18n
  .use(LanguageDetector) // Detect browser language
  .use(initReactI18next) // React binding
  .init({
    resources,
    fallbackLng: 'en',
    defaultNS: 'common',
    fallbackNS: 'common',
    ns: ['common', 'forms', 'errors', 'messages', 'validation'],

    // Interpolation settings
    interpolation: {
      escapeValue: false, // React already escapes values
      prefix: '{{',
      suffix: '}}',
    },

    // Language detector configuration
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18n_language',
    },

    // React binding configuration
    react: {
      useSuspense: false, // Disable Suspense for better UX
      bindI18n: 'languageChanged loaded',
      bindI18nStore: 'added removed',
      transEmptyNodeValue: '',
      transSupportBasicHtmlNodes: true,
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'p'],
    },

    // Load languages lazily (optional)
    load: 'languageOnly',
  });

export default i18n;
