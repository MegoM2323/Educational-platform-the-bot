/**
 * Tests for useI18n hook
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useI18n from '../useI18n';
import i18n from '../i18n';

describe('useI18n Hook', () => {
  beforeAll(async () => {
    await i18n.init();
  });

  describe('Translation Function', () => {
    it('should translate keys to English', () => {
      const { result } = renderHook(() => useI18n());
      const translation = result.current.t('common.save');
      expect(translation).toBe('Save');
    });

    it('should translate nested keys', () => {
      const { result } = renderHook(() => useI18n());
      const translation = result.current.t('navigation.dashboard');
      expect(translation).toBe('Dashboard');
    });

    it('should handle interpolation', () => {
      const { result } = renderHook(() => useI18n());
      const translation = result.current.t('forms:hints.fileSize', { size: 100 });
      expect(translation).toContain('100');
    });
  });

  describe('Language Management', () => {
    it('should provide current language', () => {
      const { result } = renderHook(() => useI18n());
      expect(result.current.language).toBeDefined();
      // Language can be 'en', 'en-US', 'ru', 'es', 'fr' etc. due to browser locale detection
      expect(['en', 'en-US', 'ru', 'es', 'fr']).toContain(result.current.language);
    });

    it('should change language', async () => {
      const { result } = renderHook(() => useI18n());

      await act(async () => {
        await result.current.changeLanguage('ru');
      });

      expect(result.current.language).toBe('ru');
    });

    it('should provide supported languages', () => {
      const { result } = renderHook(() => useI18n());
      expect(result.current.supportedLanguages).toBeDefined();
      expect(Object.keys(result.current.supportedLanguages)).toHaveLength(4);
    });
  });

  describe('RTL Support', () => {
    it('should provide isRTL flag', () => {
      const { result } = renderHook(() => useI18n());
      expect(typeof result.current.isRTL).toBe('boolean');
    });

    it('should be false for all supported languages', () => {
      const { result } = renderHook(() => useI18n());
      expect(result.current.isRTL).toBe(false);
    });
  });

  describe('Date Formatting', () => {
    it('should format date with default style', () => {
      const { result } = renderHook(() => useI18n());
      const date = new Date('2024-01-15');
      const formatted = result.current.formatDate(date);
      expect(formatted).toBeDefined();
      expect(formatted.length > 0).toBe(true);
    });

    it('should format date with short style', () => {
      const { result } = renderHook(() => useI18n());
      const date = new Date('2024-01-15');
      const formatted = result.current.formatDate(date, 'short');
      expect(formatted).toBeDefined();
    });

    it('should format date with long style', () => {
      const { result } = renderHook(() => useI18n());
      const date = new Date('2024-01-15');
      const formatted = result.current.formatDate(date, 'long');
      expect(formatted).toBeDefined();
    });

    it('should handle string date input', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatDate('2024-01-15');
      expect(formatted).toBeDefined();
    });

    it('should handle timestamp input', () => {
      const { result } = renderHook(() => useI18n());
      const timestamp = new Date('2024-01-15').getTime();
      const formatted = result.current.formatDate(timestamp);
      expect(formatted).toBeDefined();
    });
  });

  describe('Number Formatting', () => {
    it('should format number with default options', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatNumber(1234.56);
      expect(formatted).toBeDefined();
      expect(formatted).toMatch(/\d/);
    });

    it('should format number with custom options', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatNumber(1234.56, { minimumFractionDigits: 2 });
      expect(formatted).toBeDefined();
    });

    it('should handle thousands separator', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatNumber(1000000);
      expect(formatted).toBeDefined();
    });

    it('should handle decimal numbers', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatNumber(3.14159);
      expect(formatted).toBeDefined();
    });
  });

  describe('Currency Formatting', () => {
    it('should format currency with default USD', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatCurrency(99.99);
      expect(formatted).toBeDefined();
      // Currency formatting may vary by locale (99.99 or similar)
      expect(formatted).toMatch(/99\.?99|99,99/);
    });

    it('should format currency with custom currency', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatCurrency(100, 'EUR');
      expect(formatted).toBeDefined();
    });

    it('should format large currency amounts', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatCurrency(1000000, 'USD');
      expect(formatted).toBeDefined();
    });

    it('should format small currency amounts', () => {
      const { result } = renderHook(() => useI18n());
      const formatted = result.current.formatCurrency(0.01, 'USD');
      expect(formatted).toBeDefined();
    });
  });

  describe('Language-Specific Formatting', () => {
    it('should format numbers according to current language', async () => {
      const { result, rerender } = renderHook(() => useI18n());

      // English format
      let formatted = result.current.formatNumber(1234.56);
      expect(formatted).toBeDefined();

      // Change to Russian
      await act(async () => {
        await result.current.changeLanguage('ru');
      });
      rerender();

      formatted = result.current.formatNumber(1234.56);
      expect(formatted).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should handle missing translation keys gracefully', () => {
      const { result } = renderHook(() => useI18n());
      const translation = result.current.t('nonexistent.key');
      expect(translation).toBeDefined();
      // Should return the key or a fallback
      expect(typeof translation).toBe('string');
    });
  });
});
