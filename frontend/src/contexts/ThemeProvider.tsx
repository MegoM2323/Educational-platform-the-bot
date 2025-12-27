/**
 * ThemeProvider Component
 *
 * Provides dark mode support with:
 * - System preference detection
 * - localStorage persistence
 * - Smooth transitions
 * - SSR safety
 * - React context integration
 */

import React, { useEffect, useCallback, useMemo, ReactNode } from 'react';
import { useUI, useTheme as useUITheme } from './UIContext';
import {
  Theme,
  ThemeMode,
  initializeTheme,
  transitionTheme,
  onSystemThemeChange,
  saveTheme,
  resolveTheme,
} from '@/styles/themes';
import { logger } from '@/utils/logger';

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: ThemeMode;
}

/**
 * ThemeProvider component
 *
 * Handles theme initialization, persistence, and system preference detection
 * Integrates with UIContext for state management
 *
 * Usage:
 * <ThemeProvider defaultTheme="system">
 *   <App />
 * </ThemeProvider>
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultTheme = 'system',
}) => {
  const { setTheme } = useUI();
  const { theme } = useUITheme();

  // Initialize theme on mount
  useEffect(() => {
    try {
      // Initialize theme from localStorage or system preference
      const initialTheme = initializeTheme();
      logger.debug('[ThemeProvider] Theme initialized:', initialTheme);
    } catch (error) {
      logger.error('[ThemeProvider] Failed to initialize theme:', error);
    }
  }, []);

  // Listen for system theme changes
  useEffect(() => {
    const unsubscribe = onSystemThemeChange((systemTheme) => {
      logger.debug('[ThemeProvider] System theme changed to:', systemTheme);

      // Only apply if user has 'system' preference
      const savedTheme = localStorage.getItem('theme-mode') as ThemeMode | null;
      if (savedTheme === 'system' || !savedTheme) {
        setTheme(systemTheme);
        Theme.apply(systemTheme);
      }
    });

    return unsubscribe;
  }, [setTheme]);

  // Apply theme changes
  useEffect(() => {
    try {
      const resolvedTheme = resolveTheme(theme as ThemeMode);
      transitionTheme(resolvedTheme);
      saveTheme(theme as ThemeMode);
      logger.debug('[ThemeProvider] Theme applied:', theme, '-> resolved:', resolvedTheme);
    } catch (error) {
      logger.error('[ThemeProvider] Failed to apply theme:', error);
    }
  }, [theme]);

  return <>{children}</>;
};

/**
 * useThemeMode hook
 *
 * Get and set theme mode with full support for light/dark/system
 *
 * Usage:
 * const { mode, resolvedTheme, setMode, toggleTheme } = useThemeMode();
 */
export const useThemeMode = () => {
  const { setTheme } = useUI();
  const { theme } = useUITheme();

  const resolvedTheme = useMemo(
    () => resolveTheme(theme as ThemeMode),
    [theme]
  );

  const isDark = useMemo(() => resolvedTheme === 'dark', [resolvedTheme]);

  const setMode = useCallback(
    (mode: ThemeMode) => {
      setTheme(mode as 'light' | 'dark');
      saveTheme(mode);
    },
    [setTheme]
  );

  const toggleTheme = useCallback(() => {
    const newTheme = resolvedTheme === 'dark' ? 'light' : 'dark';
    setMode(newTheme);
  }, [resolvedTheme, setMode]);

  return useMemo(
    () => ({
      mode: theme as ThemeMode,
      resolvedTheme,
      setMode,
      toggleTheme,
      isDark,
    }),
    [theme, resolvedTheme, setMode, toggleTheme, isDark]
  );
};

/**
 * useSystemTheme hook
 *
 * Check system theme preference and listen for changes
 *
 * Usage:
 * const { systemTheme, systemPrefersDark } = useSystemTheme();
 */
export const useSystemTheme = () => {
  const [systemTheme, setSystemTheme] = React.useState<'light' | 'dark'>('light');

  useEffect(() => {
    // Set initial system theme
    setSystemTheme(Theme.getSystem());

    // Listen for changes
    const unsubscribe = onSystemThemeChange((theme) => {
      setSystemTheme(theme);
    });

    return unsubscribe;
  }, []);

  return useMemo(
    () => ({
      systemTheme,
      systemPrefersDark: systemTheme === 'dark',
    }),
    [systemTheme]
  );
};

/**
 * useDarkMode hook
 *
 * Simple hook to check if dark mode is enabled
 *
 * Usage:
 * const isDark = useDarkMode();
 */
export const useDarkMode = (): boolean => {
  const { isDark } = useThemeMode();
  return isDark;
};

/**
 * useToggleTheme hook
 *
 * Simple hook to toggle between light and dark mode
 *
 * Usage:
 * const toggleTheme = useToggleTheme();
 * <button onClick={toggleTheme}>Toggle</button>
 */
export const useToggleTheme = (): (() => void) => {
  const { toggleTheme } = useThemeMode();
  return toggleTheme;
};

export default ThemeProvider;
