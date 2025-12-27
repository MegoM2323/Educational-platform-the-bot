/**
 * i18n Module Exports
 *
 * Main entry point for internationalization features
 */

// Configuration
export { default as i18n, SUPPORTED_LANGUAGES, type SupportedLanguage } from './i18n';

// Hooks
export { useI18n, type UseI18nReturn } from './useI18n';

// Components
export { LanguageSwitcher, type LanguageSwitcherProps, type LanguageSwitcherVariant } from './LanguageSwitcher';
