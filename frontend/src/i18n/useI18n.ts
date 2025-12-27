/**
 * Custom hook for internationalization
 *
 * Provides convenient access to i18n functions with TypeScript support
 */

import { useTranslation } from 'react-i18next';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from './i18n';

export interface UseI18nReturn {
  /**
   * Translation function
   * @example t('common.welcome')
   * @example t('common.hello', { name: 'John' })
   */
  t: (key: string, options?: Record<string, any>) => string;

  /**
   * Current language code (en, ru, es, fr)
   */
  language: SupportedLanguage;

  /**
   * Change language
   * @example changeLanguage('ru')
   */
  changeLanguage: (lang: SupportedLanguage) => Promise<void>;

  /**
   * Supported languages configuration
   */
  supportedLanguages: typeof SUPPORTED_LANGUAGES;

  /**
   * Check if a language is RTL (right-to-left)
   */
  isRTL: boolean;

  /**
   * Get formatted date string
   * @example formatDate(new Date(), 'medium')
   */
  formatDate: (date: Date | string | number, style?: 'short' | 'medium' | 'long' | 'full') => string;

  /**
   * Get formatted number string
   * @example formatNumber(1234.56)
   */
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;

  /**
   * Get formatted currency string
   * @example formatCurrency(99.99, 'USD')
   */
  formatCurrency: (value: number, currency?: string) => string;
}

/**
 * Hook for using translations and localization
 *
 * @returns Object with translation function and utilities
 *
 * @example
 * const { t, language, changeLanguage } = useI18n();
 *
 * return (
 *   <div>
 *     <h1>{t('common.welcome')}</h1>
 *     <select value={language} onChange={(e) => changeLanguage(e.target.value)}>
 *       <option value="en">English</option>
 *       <option value="ru">Русский</option>
 *     </select>
 *   </div>
 * );
 */
export const useI18n = (): UseI18nReturn => {
  const { t: i18nT, i18n } = useTranslation();

  const language = (i18n.language as SupportedLanguage) || 'en';

  const changeLanguage = async (lang: SupportedLanguage): Promise<void> => {
    await i18n.changeLanguage(lang);
    localStorage.setItem('i18n_language', lang);
    document.documentElement.lang = lang;
  };

  const isRTL = SUPPORTED_LANGUAGES[language]?.dir === 'rtl';

  const formatDate = (
    date: Date | string | number,
    style: 'short' | 'medium' | 'long' | 'full' = 'medium'
  ): string => {
    const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;

    const styleMap = {
      short: { dateStyle: 'short' } as Intl.DateTimeFormatOptions,
      medium: { dateStyle: 'medium' } as Intl.DateTimeFormatOptions,
      long: { dateStyle: 'long' } as Intl.DateTimeFormatOptions,
      full: { dateStyle: 'full' } as Intl.DateTimeFormatOptions,
    };

    return new Intl.DateTimeFormat(language, styleMap[style]).format(dateObj);
  };

  const formatNumber = (value: number, options?: Intl.NumberFormatOptions): string => {
    return new Intl.NumberFormat(language, options).format(value);
  };

  const formatCurrency = (value: number, currency: string = 'USD'): string => {
    return new Intl.NumberFormat(language, {
      style: 'currency',
      currency,
    }).format(value);
  };

  /**
   * Wrapper around i18next's t function with type safety
   */
  const t = (key: string, options?: Record<string, any>): string => {
    return i18nT(key, options);
  };

  return {
    t,
    language,
    changeLanguage,
    supportedLanguages: SUPPORTED_LANGUAGES,
    isRTL,
    formatDate,
    formatNumber,
    formatCurrency,
  };
};

export default useI18n;
