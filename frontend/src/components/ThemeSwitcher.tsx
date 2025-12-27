/**
 * ThemeSwitcher Component
 *
 * Provides UI for switching between light, dark, and system theme modes
 *
 * Features:
 * - Toggle button with icon
 * - Dropdown menu for full control
 * - System preference detection
 * - Smooth transitions
 * - Accessibility support
 */

import React, { useState } from 'react';
import { useThemeMode, useSystemTheme } from '@/contexts/ThemeProvider';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import { Moon, Sun, Monitor } from 'lucide-react';
import { ThemeMode } from '@/styles/themes';

interface ThemeSwitcherProps {
  /**
   * Variant: 'button' for simple toggle, 'dropdown' for full menu
   * @default 'button'
   */
  variant?: 'button' | 'dropdown';

  /**
   * Show label text
   * @default false
   */
  showLabel?: boolean;

  /**
   * Custom class name
   */
  className?: string;

  /**
   * Callback when theme changes
   */
  onChange?: (theme: ThemeMode) => void;
}

/**
 * Simple theme toggle button
 */
export const ThemeToggleButton: React.FC<ThemeSwitcherProps> = ({
  showLabel = false,
  className = '',
  onChange,
}) => {
  const { toggleTheme, isDark, resolvedTheme } = useThemeMode();

  const handleToggle = () => {
    toggleTheme();
    onChange?.(isDark ? 'light' : 'dark');
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={handleToggle}
      className={className}
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {isDark ? (
        <Sun className="h-5 w-5" aria-hidden="true" />
      ) : (
        <Moon className="h-5 w-5" aria-hidden="true" />
      )}
      {showLabel && (
        <span className="ml-2 text-sm">
          {isDark ? 'Light' : 'Dark'}
        </span>
      )}
    </Button>
  );
};

/**
 * Full theme switcher dropdown menu
 */
export const ThemeSwitcherDropdown: React.FC<ThemeSwitcherProps> = ({
  showLabel = true,
  className = '',
  onChange,
}) => {
  const { mode, toggleTheme, isDark } = useThemeMode();
  const { systemTheme, systemPrefersDark } = useSystemTheme();
  const [open, setOpen] = useState(false);

  const handleSetTheme = (theme: ThemeMode) => {
    // Update theme through context
    const { setMode } = useThemeMode();
    setMode(theme);
    onChange?.(theme);
    setOpen(false);
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="icon"
        className={className}
        title="Theme settings"
        aria-label="Theme settings"
      >
        {isDark ? (
          <Moon className="h-5 w-5" aria-hidden="true" />
        ) : (
          <Sun className="h-5 w-5" aria-hidden="true" />
        )}
        {showLabel && (
          <span className="ml-2 text-sm capitalize">
            {mode === 'system' ? 'System' : mode}
          </span>
        )}
      </Button>

      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Theme</DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuCheckboxItem
          checked={mode === 'light'}
          onCheckedChange={() => handleSetTheme('light')}
          className="cursor-pointer"
        >
          <Sun className="mr-2 h-4 w-4" aria-hidden="true" />
          <span>Light</span>
        </DropdownMenuCheckboxItem>

        <DropdownMenuCheckboxItem
          checked={mode === 'dark'}
          onCheckedChange={() => handleSetTheme('dark')}
          className="cursor-pointer"
        >
          <Moon className="mr-2 h-4 w-4" aria-hidden="true" />
          <span>Dark</span>
        </DropdownMenuCheckboxItem>

        <DropdownMenuCheckboxItem
          checked={mode === 'system'}
          onCheckedChange={() => handleSetTheme('system')}
          className="cursor-pointer"
        >
          <Monitor className="mr-2 h-4 w-4" aria-hidden="true" />
          <span>System</span>
          {mode === 'system' && (
            <span className="ml-auto text-xs text-muted-foreground">
              ({systemTheme})
            </span>
          )}
        </DropdownMenuCheckboxItem>

        <DropdownMenuSeparator />

        <div className="px-2 py-1.5 text-xs text-muted-foreground">
          <div className="flex items-center justify-between">
            <span>Current:</span>
            <span className="font-semibold capitalize">
              {mode === 'system'
                ? `${systemTheme} (system)`
                : mode}
            </span>
          </div>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

/**
 * Main ThemeSwitcher component
 *
 * Usage:
 * <ThemeSwitcher variant="button" />
 * <ThemeSwitcher variant="dropdown" showLabel />
 */
const ThemeSwitcher: React.FC<ThemeSwitcherProps> = ({
  variant = 'button',
  ...props
}) => {
  if (variant === 'dropdown') {
    return <ThemeSwitcherDropdown {...props} />;
  }

  return <ThemeToggleButton {...props} />;
};

export default ThemeSwitcher;
