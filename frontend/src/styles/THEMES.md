# Dark Mode Theme System

Comprehensive dark mode support for THE_BOT platform frontend with system preference detection, localStorage persistence, and WCAG AA compliance.

## Features

- Light and dark theme support
- Automatic system preference detection
- User preference persistence (localStorage)
- Smooth theme transitions
- WCAG AA contrast compliance
- CSS variables approach
- TypeScript type safety
- No flash on page load
- Tailwind dark mode integration

## Architecture

### Theme System Files

```
frontend/src/
├── styles/
│   ├── themes.ts                 # Core theme definitions and utilities
│   └── __tests__/
│       └── themes.test.ts        # Theme system tests
├── contexts/
│   ├── ThemeProvider.tsx         # React context provider and hooks
│   └── __tests__/
│       └── ThemeProvider.test.tsx # Provider and hook tests
└── components/
    └── ThemeSwitcher.tsx          # UI components for theme switching
```

## Usage

### Basic Setup

The app is pre-configured with theme support. The `AppProvider` includes `ThemeProvider`:

```tsx
// No additional setup needed - it's already in AppProvider
<AppProvider>
  <App />
</AppProvider>
```

### Using Theme Hooks

#### `useThemeMode()`

Complete theme control:

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';

export const MyComponent = () => {
  const { mode, resolvedTheme, setMode, toggleTheme, isDark } = useThemeMode();

  return (
    <div>
      <p>Current mode: {mode}</p>
      <p>Resolved theme: {resolvedTheme}</p>
      <p>Is dark: {isDark}</p>

      <button onClick={() => setMode('dark')}>Dark</button>
      <button onClick={() => setMode('light')}>Light</button>
      <button onClick={() => setMode('system')}>System</button>
      <button onClick={toggleTheme}>Toggle</button>
    </div>
  );
};
```

#### `useDarkMode()`

Quick dark mode check:

```tsx
import { useDarkMode } from '@/contexts/ThemeProvider';

export const MyComponent = () => {
  const isDark = useDarkMode();

  return (
    <div className={isDark ? 'dark-background' : 'light-background'}>
      Content
    </div>
  );
};
```

#### `useToggleTheme()`

Simple toggle function:

```tsx
import { useToggleTheme } from '@/contexts/ThemeProvider';

export const ThemeToggle = () => {
  const toggleTheme = useToggleTheme();

  return <button onClick={toggleTheme}>Toggle Theme</button>;
};
```

#### `useSystemTheme()`

System preference detection:

```tsx
import { useSystemTheme } from '@/contexts/ThemeProvider';

export const SystemThemeInfo = () => {
  const { systemTheme, systemPrefersDark } = useSystemTheme();

  return (
    <div>
      <p>System preference: {systemTheme}</p>
      <p>Prefers dark: {systemPrefersDark}</p>
    </div>
  );
};
```

### UI Components

#### ThemeSwitcher (Simple Toggle)

```tsx
import ThemeSwitcher from '@/components/ThemeSwitcher';

// Simple button toggle
<ThemeSwitcher variant="button" />

// With label
<ThemeSwitcher variant="button" showLabel />

// With callback
<ThemeSwitcher
  variant="button"
  onChange={(theme) => console.log('Theme changed:', theme)}
/>
```

#### ThemeSwitcher (Dropdown Menu)

```tsx
import ThemeSwitcher from '@/components/ThemeSwitcher';

// Full menu with all options
<ThemeSwitcher variant="dropdown" />

// With label
<ThemeSwitcher variant="dropdown" showLabel />

// Show system preference info
<ThemeSwitcher variant="dropdown" showLabel />
```

#### Individual Components

```tsx
import { ThemeToggleButton, ThemeSwitcherDropdown } from '@/components/ThemeSwitcher';

// Use individually
<ThemeToggleButton />
<ThemeSwitcherDropdown showLabel />
```

## Theme Definitions

### Light Theme Colors

```ts
import { LIGHT_THEME } from '@/styles/themes';

// Light backgrounds, dark text
// Suitable for bright environments
// WCAG AA contrast compliant
```

### Dark Theme Colors

```ts
import { DARK_THEME } from '@/styles/themes';

// Dark backgrounds, light text
// Reduces eye strain in low light
// WCAG AA contrast compliant
```

### Accessing Theme Colors

```tsx
import { Theme } from '@/styles/themes';

// Get colors for current theme
const isDark = useDarkMode();
const colors = Theme.getColors(isDark ? 'dark' : 'light');

console.log(colors.background);  // HSL value
console.log(colors.foreground);  // HSL value
```

## Styling with Themes

### CSS Variables

Colors are available as CSS variables automatically applied:

```css
/* In your CSS */
.component {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  border: 1px solid hsl(var(--border));
}
```

### Tailwind CSS

Use Tailwind's built-in dark mode support:

```tsx
// Light mode by default, dark mode with 'dark' class
<div className="bg-background text-foreground dark:bg-card dark:text-card-foreground">
  Content
</div>

// Shorter syntax
<div className="bg-white dark:bg-slate-900">
  Content
</div>
```

### Responsive Theme Colors

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';
import { Theme } from '@/styles/themes';

export const ResponsiveCard = () => {
  const { resolvedTheme } = useThemeMode();
  const colors = Theme.getColors(resolvedTheme);

  return (
    <div
      style={{
        backgroundColor: `hsl(${colors.card})`,
        color: `hsl(${colors.cardForeground})`,
        boxShadow: colors.shadowMd,
      }}
    >
      Content
    </div>
  );
};
```

## System Preference Detection

### Automatic Detection

The system detects user's OS theme preference:

```tsx
import { useSystemTheme } from '@/contexts/ThemeProvider';

export const SystemPreference = () => {
  const { systemTheme, systemPrefersDark } = useSystemTheme();

  return <p>System prefers: {systemTheme}</p>;
};
```

### Setting to System

Users can set their preference to "System" to always match OS:

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';

export const SettingsPage = () => {
  const { setMode } = useThemeMode();

  return (
    <button onClick={() => setMode('system')}>
      Follow System Preference
    </button>
  );
};
```

## Persistence

### localStorage

User preferences are automatically saved to localStorage:

```ts
// Saved as 'theme-mode' in localStorage
// Values: 'light' | 'dark' | 'system'
```

### No Flash on Reload

Theme is initialized before rendering to prevent flash:

1. Page starts with blank document
2. Theme is read from localStorage
3. Theme is applied to `<html>` element
4. React renders with correct theme

## Contrast Compliance

All colors meet WCAG AA minimum contrast ratio of 4.5:1:

```ts
import { CONTRAST_RATIOS } from '@/styles/themes';

CONTRAST_RATIOS.light.foreground_vs_background; // 8.1:1
CONTRAST_RATIOS.dark.foreground_vs_background;  // 8.2:1
```

## API Reference

### Core Functions

#### `applyTheme(theme: 'light' | 'dark')`

Apply theme to document:

```ts
import { Theme } from '@/styles/themes';

Theme.apply('dark');  // Apply dark theme
```

#### `resolveTheme(theme: ThemeMode)`

Resolve 'system' to actual theme:

```ts
import { Theme } from '@/styles/themes';

const resolved = Theme.resolve('system');  // Returns 'light' or 'dark'
```

#### `getSystemTheme()`

Get system preference:

```ts
import { Theme } from '@/styles/themes';

const systemTheme = Theme.getSystem();  // 'light' or 'dark'
```

#### `saveTheme(theme: ThemeMode)`

Save to localStorage:

```ts
import { Theme } from '@/styles/themes';

Theme.save('dark');
```

#### `getSavedTheme()`

Load from localStorage:

```ts
import { Theme } from '@/styles/themes';

const saved = Theme.getSaved();  // 'light' | 'dark' | 'system' | null
```

#### `initializeTheme()`

Initialize on app load:

```ts
import { Theme } from '@/styles/themes';

const theme = Theme.initialize();  // Returns 'light' or 'dark'
```

#### `onSystemThemeChange(callback)`

Listen for system preference changes:

```ts
import { Theme } from '@/styles/themes';

const unsubscribe = Theme.onSystemChange((theme) => {
  console.log('System theme changed to:', theme);
});

// Later:
unsubscribe();
```

### Hooks

- `useThemeMode()` - Full theme control
- `useDarkMode()` - Check dark mode status
- `useToggleTheme()` - Toggle function
- `useSystemTheme()` - System preference info

### Components

- `<ThemeSwitcher />` - Combined button/dropdown
- `<ThemeToggleButton />` - Simple button
- `<ThemeSwitcherDropdown />` - Full menu

## Example: Settings Page

```tsx
import { useThemeMode, useSystemTheme } from '@/contexts/ThemeProvider';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export const ThemeSettings = () => {
  const { mode, resolvedTheme, setMode } = useThemeMode();
  const { systemTheme } = useSystemTheme();

  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold mb-4">Theme Settings</h2>

      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium">Current Theme</label>
          <p className="text-muted-foreground">
            {mode === 'system'
              ? `System (${systemTheme})`
              : mode}
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant={mode === 'light' ? 'default' : 'outline'}
            onClick={() => setMode('light')}
          >
            Light
          </Button>
          <Button
            variant={mode === 'dark' ? 'default' : 'outline'}
            onClick={() => setMode('dark')}
          >
            Dark
          </Button>
          <Button
            variant={mode === 'system' ? 'default' : 'outline'}
            onClick={() => setMode('system')}
          >
            System
          </Button>
        </div>

        <div className="text-xs text-muted-foreground">
          <p>Your preference is saved automatically.</p>
          <p>System theme will be used if 'System' is selected.</p>
        </div>
      </div>
    </Card>
  );
};
```

## Example: Dynamic Styling

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';
import { Theme } from '@/styles/themes';

export const DynamicComponent = () => {
  const { resolvedTheme } = useThemeMode();
  const colors = Theme.getColors(resolvedTheme);

  return (
    <div
      style={{
        backgroundColor: `hsl(${colors.background})`,
        color: `hsl(${colors.foreground})`,
        padding: '1rem',
        borderRadius: '0.5rem',
        boxShadow: colors.shadowMd,
      }}
    >
      <h3>Dynamic Theme</h3>
      <p>This component adapts to the current theme.</p>
    </div>
  );
};
```

## Testing

### Unit Tests

```bash
npm test src/styles/__tests__/themes.test.ts
npm test src/contexts/__tests__/ThemeProvider.test.tsx
```

### Test Coverage

- Theme definitions and colors
- Theme switching and persistence
- System preference detection
- CSS variable application
- WCAG AA contrast compliance
- localStorage integration
- Hook functionality

## Tailwind Configuration

Dark mode is configured to use class strategy:

```ts
// tailwind.config.ts
export default {
  darkMode: ["class"],
  // ...
}
```

This means:
- Dark mode is enabled by adding `dark` class to HTML element
- CSS utilities work with `dark:` prefix
- No middleware or runtime overhead

## Browser Support

Requires browsers supporting:
- CSS Custom Properties (IE 11 not supported)
- `prefers-color-scheme` media query
- localStorage
- matchMedia API

All modern browsers (Chrome, Firefox, Safari, Edge) are fully supported.

## Performance

- No runtime overhead for theme resolution
- Smooth 300ms transitions
- Minimal layout shifts
- Efficient CSS variable application
- localStorage-backed persistence

## Accessibility

- WCAG AA contrast compliance
- Respects `prefers-color-scheme`
- Keyboard navigation support
- Screen reader friendly
- No color-only information conveyance

## Troubleshooting

### Theme not persisting

Check if localStorage is enabled:

```tsx
// In browser console
localStorage.setItem('test', 'value');
localStorage.getItem('test');
```

### System preference not detected

Verify `prefers-color-scheme` support:

```tsx
const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
```

### Flash on page load

Ensure `ThemeProvider` is mounted:

```tsx
// ✓ Correct - ThemeProvider in provider hierarchy
<AppProvider>
  <App />
</AppProvider>

// ✗ Wrong - ThemeProvider added inside App
<AppProvider>
  <ThemeProvider>
    <App />
  </ThemeProvider>
</AppProvider>
```

## Contributing

When adding new colors:

1. Update both `LIGHT_THEME` and `DARK_THEME`
2. Verify WCAG AA contrast
3. Test with actual components
4. Update tests in `__tests__/themes.test.ts`
5. Update CSS variables in `index.css`

## Future Enhancements

- [ ] Custom theme creator
- [ ] Theme scheduling (dark at night, light during day)
- [ ] Per-component theme overrides
- [ ] Color palette customization
- [ ] Automatic contrast ratio validation
- [ ] Theme preview before saving

## References

- [MDN: prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
- [WCAG Contrast Guidelines](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [Tailwind Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
