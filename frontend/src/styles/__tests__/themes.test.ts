/**
 * Theme System Tests
 *
 * Tests for:
 * - Theme definitions and colors
 * - Theme switching and persistence
 * - System preference detection
 * - CSS variable application
 * - WCAG AA contrast compliance
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  Theme,
  LIGHT_THEME,
  DARK_THEME,
  CONTRAST_RATIOS,
  THEME_STORAGE_KEY,
  getSystemTheme,
  resolveTheme,
  applyTheme,
  onSystemThemeChange,
  getSavedTheme,
  saveTheme,
  initializeTheme,
  systemPrefersDark,
  getThemeColors,
} from '../themes';

describe('Theme System', () => {
  // Mock localStorage
  let store: Record<string, string> = {};

  beforeEach(() => {
    store = {};
    localStorage.clear();

    // Mock localStorage
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(
      (key: string) => store[key] || null
    );
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(
      (key: string, value: string) => {
        store[key] = value;
      }
    );
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(
      (key: string) => {
        delete store[key];
      }
    );

    // Clear all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Theme Definitions', () => {
    it('should have all required color properties', () => {
      const requiredColors = [
        'background',
        'foreground',
        'primary',
        'secondary',
        'destructive',
        'success',
        'border',
        'ring',
      ];

      requiredColors.forEach((color) => {
        expect(LIGHT_THEME).toHaveProperty(color);
        expect(DARK_THEME).toHaveProperty(color);
      });
    });

    it('should have valid HSL color values', () => {
      const hslRegex = /^\d+\s\d+%\s\d+%$/;
      const nonColorKeys = ['gradient', 'shadow'];

      Object.entries(LIGHT_THEME).forEach(([key, value]) => {
        // Skip gradient and shadow properties
        if (!nonColorKeys.some((k) => key.toLowerCase().includes(k))) {
          if (typeof value === 'string') {
            expect(value).toMatch(hslRegex);
          }
        }
      });

      Object.entries(DARK_THEME).forEach(([key, value]) => {
        // Skip gradient and shadow properties
        if (!nonColorKeys.some((k) => key.toLowerCase().includes(k))) {
          if (typeof value === 'string') {
            expect(value).toMatch(hslRegex);
          }
        }
      });
    });

    it('should have distinct background and foreground colors', () => {
      expect(LIGHT_THEME.background).not.toEqual(LIGHT_THEME.foreground);
      expect(DARK_THEME.background).not.toEqual(DARK_THEME.foreground);
    });

    it('should define shadows for both themes', () => {
      expect(LIGHT_THEME.shadowSm).toBeDefined();
      expect(LIGHT_THEME.shadowMd).toBeDefined();
      expect(LIGHT_THEME.shadowLg).toBeDefined();
      expect(LIGHT_THEME.shadowGlow).toBeDefined();

      expect(DARK_THEME.shadowSm).toBeDefined();
      expect(DARK_THEME.shadowMd).toBeDefined();
      expect(DARK_THEME.shadowLg).toBeDefined();
      expect(DARK_THEME.shadowGlow).toBeDefined();
    });

    it('should define gradients for both themes', () => {
      expect(LIGHT_THEME.gradientPrimary).toContain('linear-gradient');
      expect(LIGHT_THEME.gradientSecondary).toContain('linear-gradient');
      expect(LIGHT_THEME.gradientHero).toContain('linear-gradient');

      expect(DARK_THEME.gradientPrimary).toContain('linear-gradient');
      expect(DARK_THEME.gradientSecondary).toContain('linear-gradient');
      expect(DARK_THEME.gradientHero).toContain('linear-gradient');
    });
  });

  describe('Theme Utilities', () => {
    it('should get theme colors correctly', () => {
      expect(getThemeColors('light')).toEqual(LIGHT_THEME);
      expect(getThemeColors('dark')).toEqual(DARK_THEME);
    });

    it('should resolve theme modes correctly', () => {
      expect(resolveTheme('light')).toBe('light');
      expect(resolveTheme('dark')).toBe('dark');
    });

    it('should check system preference for system mode', () => {
      // Mock matchMedia
      const mockMatchMedia = vi.fn(() => ({
        matches: true,
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      vi.stubGlobal('matchMedia', mockMatchMedia);
      expect(systemPrefersDark()).toBe(true);

      // Restore
      vi.unstubAllGlobals();
    });
  });

  describe('localStorage Persistence', () => {
    it('should save theme to localStorage', () => {
      saveTheme('dark');
      expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');

      saveTheme('light');
      expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');

      saveTheme('system');
      expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('system');
    });

    it('should retrieve saved theme from localStorage', () => {
      localStorage.setItem(THEME_STORAGE_KEY, 'dark');
      expect(getSavedTheme()).toBe('dark');

      localStorage.setItem(THEME_STORAGE_KEY, 'light');
      expect(getSavedTheme()).toBe('light');
    });

    it('should return null for invalid saved theme', () => {
      localStorage.setItem(THEME_STORAGE_KEY, 'invalid');
      expect(getSavedTheme()).toBeNull();
    });

    it('should return null when no theme is saved', () => {
      expect(getSavedTheme()).toBeNull();
    });
  });

  describe('CSS Variable Application', () => {
    beforeEach(() => {
      // Create a mock document element
      document.documentElement.className = '';
      document.documentElement.style.cssText = '';
    });

    it('should apply light theme CSS variables', () => {
      applyTheme('light');

      expect(document.documentElement.classList.contains('dark')).toBe(false);
      expect(document.documentElement.style.colorScheme).toBe('light');
    });

    it('should apply dark theme CSS variables', () => {
      applyTheme('dark');

      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(document.documentElement.style.colorScheme).toBe('dark');
    });

    it('should set all CSS variables correctly', () => {
      applyTheme('light');

      const bgVar = document.documentElement.style.getPropertyValue('--background');
      expect(bgVar).toBe(LIGHT_THEME.background);

      const fgVar = document.documentElement.style.getPropertyValue('--foreground');
      expect(fgVar).toBe(LIGHT_THEME.foreground);
    });

    it('should toggle dark class on theme change', () => {
      applyTheme('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);

      applyTheme('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);

      applyTheme('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('System Theme Detection', () => {
    it('should detect system theme preference', () => {
      const mockMatchMedia = vi.fn((query) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      vi.stubGlobal('matchMedia', mockMatchMedia);

      const systemTheme = getSystemTheme();
      expect(['light', 'dark']).toContain(systemTheme);

      vi.unstubAllGlobals();
    });

    it('should listen for system theme changes', () => {
      const mockAddEventListener = vi.fn();
      const mockRemoveEventListener = vi.fn();

      const mockMatchMedia = vi.fn(() => ({
        matches: false,
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: mockAddEventListener,
        removeEventListener: mockRemoveEventListener,
        dispatchEvent: vi.fn(),
      }));

      vi.stubGlobal('matchMedia', mockMatchMedia);

      const callback = vi.fn();
      const unsubscribe = onSystemThemeChange(callback);

      expect(mockAddEventListener).toHaveBeenCalled();

      unsubscribe();
      expect(mockRemoveEventListener).toHaveBeenCalled();

      vi.unstubAllGlobals();
    });
  });

  describe('Theme Initialization', () => {
    it('should initialize with system theme when no preference saved', () => {
      const mockMatchMedia = vi.fn(() => ({
        matches: false, // Light mode
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      vi.stubGlobal('matchMedia', mockMatchMedia);

      const theme = initializeTheme();
      expect(['light', 'dark']).toContain(theme);

      vi.unstubAllGlobals();
    });

    it('should initialize with saved preference over system', () => {
      localStorage.setItem(THEME_STORAGE_KEY, 'dark');

      const theme = initializeTheme();
      expect(theme).toBe('dark');
    });

    it('should apply theme on initialization', () => {
      localStorage.setItem(THEME_STORAGE_KEY, 'dark');
      initializeTheme();

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('Contrast Compliance', () => {
    it('should define contrast ratios for light theme', () => {
      expect(CONTRAST_RATIOS.light).toBeDefined();
      expect(CONTRAST_RATIOS.light.foreground_vs_background).toBeGreaterThanOrEqual(
        4.5
      );
      expect(CONTRAST_RATIOS.light.primary_vs_white).toBeGreaterThanOrEqual(4.5);
    });

    it('should define contrast ratios for dark theme', () => {
      expect(CONTRAST_RATIOS.dark).toBeDefined();
      expect(CONTRAST_RATIOS.dark.foreground_vs_background).toBeGreaterThanOrEqual(
        4.5
      );
      expect(CONTRAST_RATIOS.dark.primary_vs_background).toBeGreaterThanOrEqual(
        4.5
      );
    });

    it('should meet WCAG AA minimum contrast ratio', () => {
      const wcagAA = 4.5;

      Object.values(CONTRAST_RATIOS.light).forEach((ratio) => {
        expect(ratio).toBeGreaterThanOrEqual(wcagAA);
      });

      Object.values(CONTRAST_RATIOS.dark).forEach((ratio) => {
        expect(ratio).toBeGreaterThanOrEqual(wcagAA);
      });
    });
  });

  describe('Theme Namespace', () => {
    it('should export all utilities through Theme namespace', () => {
      expect(Theme.LIGHT).toEqual(LIGHT_THEME);
      expect(Theme.DARK).toEqual(DARK_THEME);
      expect(Theme.STORAGE_KEY).toBe(THEME_STORAGE_KEY);
    });

    it('should have all utility methods', () => {
      expect(typeof Theme.getSystem).toBe('function');
      expect(typeof Theme.resolve).toBe('function');
      expect(typeof Theme.apply).toBe('function');
      expect(typeof Theme.transition).toBe('function');
      expect(typeof Theme.onSystemChange).toBe('function');
      expect(typeof Theme.getSaved).toBe('function');
      expect(typeof Theme.save).toBe('function');
      expect(typeof Theme.initialize).toBe('function');
      expect(typeof Theme.systemPrefersDark).toBe('function');
      expect(typeof Theme.getColors).toBe('function');
      expect(typeof Theme.checkContrast).toBe('function');
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing window gracefully', () => {
      const originalWindow = global.window;
      // @ts-ignore
      delete global.window;

      // These should not throw
      expect(() => getSystemTheme()).not.toThrow();
      expect(() => getSavedTheme()).not.toThrow();
      expect(() => saveTheme('dark')).not.toThrow();

      global.window = originalWindow;
    });

    it('should handle multiple theme changes', () => {
      applyTheme('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);

      applyTheme('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);

      applyTheme('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);

      applyTheme('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should persist theme across storage access', () => {
      saveTheme('dark');
      expect(getSavedTheme()).toBe('dark');

      saveTheme('light');
      expect(getSavedTheme()).toBe('light');

      saveTheme('dark');
      expect(getSavedTheme()).toBe('dark');
    });
  });
});
