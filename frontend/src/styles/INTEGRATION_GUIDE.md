# Dark Mode Integration Guide

Quick start guide for integrating dark mode into existing components.

## Prerequisites

The theme system is already set up in:
- ✅ `index.css` - CSS variables defined
- ✅ `tailwind.config.ts` - Dark mode configured
- ✅ `AppProvider` - ThemeProvider included

No additional setup needed!

## Quick Integration

### Option 1: Use Tailwind Dark Mode (Recommended)

Update your component CSS classes to use `dark:` prefix:

```tsx
// Before
<div className="bg-white text-black">
  Content
</div>

// After
<div className="bg-white dark:bg-slate-900 text-black dark:text-white">
  Content
</div>
```

### Option 2: Use useThemeMode Hook

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';

export const MyComponent = () => {
  const { isDark } = useThemeMode();

  return (
    <div className={isDark ? 'dark-styles' : 'light-styles'}>
      Content
    </div>
  );
};
```

### Option 3: Use CSS Variables

```tsx
export const MyComponent = () => {
  return (
    <div style={{
      backgroundColor: 'hsl(var(--background))',
      color: 'hsl(var(--foreground))'
    }}>
      Content
    </div>
  );
};
```

## Adding Theme Switcher

### To Header/Navigation

```tsx
import ThemeSwitcher from '@/components/ThemeSwitcher';

export const Header = () => {
  return (
    <header className="flex items-center justify-between">
      <h1>App</h1>
      <ThemeSwitcher variant="dropdown" showLabel />
    </header>
  );
};
```

### To Settings Page

```tsx
import ThemeSwitcher from '@/components/ThemeSwitcher';
import { Card } from '@/components/ui/card';

export const SettingsPage = () => {
  return (
    <Card className="p-6">
      <h2>Theme Settings</h2>
      <ThemeSwitcher variant="dropdown" showLabel />
    </Card>
  );
};
```

### To User Menu

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';
import { Moon, Sun } from 'lucide-react';

export const UserMenu = () => {
  const { toggleTheme, isDark } = useThemeMode();

  return (
    <button onClick={toggleTheme}>
      {isDark ? <Sun /> : <Moon />}
    </button>
  );
};
```

## Common Patterns

### Conditional Styling Based on Theme

```tsx
import { useDarkMode } from '@/contexts/ThemeProvider';

export const ComponentWithThemeStyles = () => {
  const isDark = useDarkMode();

  return (
    <div
      className={`
        rounded-lg p-4
        ${isDark
          ? 'bg-slate-900 text-white shadow-lg'
          : 'bg-white text-slate-900 shadow-sm'
        }
      `}
    >
      Content
    </div>
  );
};
```

### Dynamic Colors from Theme

```tsx
import { useThemeMode } from '@/contexts/ThemeProvider';
import { Theme } from '@/styles/themes';

export const DynamicComponent = () => {
  const { resolvedTheme } = useThemeMode();
  const colors = Theme.getColors(resolvedTheme);

  return (
    <div
      style={{
        backgroundColor: `hsl(${colors.card})`,
        color: `hsl(${colors.cardForeground})`,
        borderColor: `hsl(${colors.border})`
      }}
    >
      Content
    </div>
  );
};
```

### Theme-Aware Images

```tsx
import { useDarkMode } from '@/contexts/ThemeProvider';

export const ThemedImage = () => {
  const isDark = useDarkMode();

  return (
    <img
      src={isDark ? '/logo-dark.png' : '/logo-light.png'}
      alt="Logo"
    />
  );
};
```

### System Preference Detection

```tsx
import { useSystemTheme } from '@/contexts/ThemeProvider';

export const SystemThemeInfo = () => {
  const { systemTheme, systemPrefersDark } = useSystemTheme();

  return (
    <div>
      <p>System preference: {systemTheme}</p>
      <p>Prefers dark: {systemPrefersDark ? 'Yes' : 'No'}</p>
    </div>
  );
};
```

## CSS Classes Reference

### Standard Tailwind Dark Mode

```tsx
// Background colors
<div className="bg-white dark:bg-slate-950">

// Text colors
<div className="text-black dark:text-white">

// Borders
<div className="border-gray-200 dark:border-gray-800">

// Shadows
<div className="shadow-sm dark:shadow-lg">

// Opacity
<div className="bg-black/5 dark:bg-white/5">
```

## Available CSS Variables

```css
/* Base colors */
--background     /* Main background */
--foreground     /* Main text */

/* Components */
--card           /* Card background */
--card-foreground
--popover
--popover-foreground

/* Interactive */
--primary
--primary-foreground
--secondary
--secondary-foreground
--accent
--accent-foreground

/* Status */
--destructive
--destructive-foreground
--success
--success-foreground

/* UI Elements */
--border         /* Border color */
--input          /* Input background */
--ring           /* Focus ring */
--muted
--muted-foreground

/* Sidebar */
--sidebar-background
--sidebar-foreground
--sidebar-primary
--sidebar-primary-foreground
--sidebar-accent
--sidebar-accent-foreground
--sidebar-border
--sidebar-ring

/* Shadows */
--shadow-sm
--shadow-md
--shadow-lg
--shadow-glow

/* Gradients */
--gradient-primary
--gradient-secondary
--gradient-hero
```

## Migration Checklist

### For Existing Components

- [ ] Replace hardcoded colors with Tailwind classes
- [ ] Add `dark:` variants for dark mode support
- [ ] Test component in both light and dark modes
- [ ] Check contrast ratios (WCAG AA minimum 4.5:1)
- [ ] Update related tests
- [ ] Remove inline `style` attributes if possible

### Example Migration

```tsx
// Before
const Button = styled.button`
  background: white;
  color: black;
  border: 1px solid #ddd;
`;

// After
<button className="bg-white dark:bg-slate-900 text-black dark:text-white border border-gray-200 dark:border-gray-800">
  Click me
</button>
```

## Testing Theme Functionality

### Manual Testing

1. Open app in browser
2. Check initial theme matches system preference
3. Click theme toggle button
4. Verify theme changes immediately
5. Refresh page - theme should persist
6. Check colors have sufficient contrast
7. Test on mobile and desktop

### Automated Testing

```tsx
import { render } from '@testing-library/react';
import { useThemeMode } from '@/contexts/ThemeProvider';

// Test theme switching
const { result } = renderHook(() => useThemeMode(), { wrapper: Wrapper });
act(() => result.current.toggleTheme());
expect(result.current.isDark).toBe(true);
```

## Performance Tips

1. **Use Tailwind classes** - compiled at build time, no runtime overhead
2. **Avoid inline styles** - use CSS variables instead
3. **Memoize theme values** - prevents unnecessary re-renders
4. **Lazy load heavy components** - load after theme is set

## Accessibility

### Color Contrast

All colors meet WCAG AA standard (4.5:1 minimum):

```tsx
// ✓ Good - meets WCAG AA
<div className="bg-white text-slate-900">Good contrast</div>

// ✓ Good - meets WCAG AA
<div className="bg-slate-900 text-white">Good contrast</div>

// ✗ Bad - doesn't meet WCAG AA
<div className="bg-white text-gray-400">Poor contrast</div>
```

### Respect System Preference

```tsx
// ✓ Respects system preference
<ThemeSwitcher variant="dropdown" />

// ✗ Forces one theme
<ThemeSwitcher variant="button" />
// Good for user control, but give option for system
```

### Keyboard Navigation

All theme switcher components support:
- Tab navigation
- Enter to activate
- Space to activate
- Arrow keys (in dropdown)

## Troubleshooting

### Theme not changing

1. Check ThemeProvider is in provider hierarchy
2. Verify localStorage is enabled
3. Check browser console for errors
4. Ensure hook is used inside Provider

### Flash on load

This should not happen because:
1. Theme is applied before React renders
2. CSS variables are set immediately
3. No JavaScript needed for theme display

If you see flash:
1. Check that index.css is imported first
2. Verify AppProvider includes ThemeProvider
3. Check for CSS conflicts

### Colors not applying

1. Check CSS variable names are correct
2. Verify `hsl()` syntax in colors
3. Check Tailwind dark mode is enabled
4. Inspect element to see applied styles

## Next Steps

1. Review examples in `ThemeSwitcher.examples.tsx`
2. Integrate theme switcher into your header/navigation
3. Test theme switching works smoothly
4. Update existing components to support dark mode
5. Verify contrast ratios meet WCAG AA
6. Test on real devices/browsers

## Resources

- See `THEMES.md` for complete API reference
- See `ThemeSwitcher.examples.tsx` for UI patterns
- See `themes.test.ts` for test examples
- See `tailwind.config.ts` for Tailwind configuration

## Support

Questions? Check:
1. Component examples in `ThemeSwitcher.examples.tsx`
2. API docs in `THEMES.md`
3. Tests in `__tests__/` directories
4. Tailwind documentation at https://tailwindcss.com/docs/dark-mode
