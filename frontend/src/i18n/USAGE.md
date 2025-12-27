# i18n Usage Guide

Complete guide for using the internationalization system in the THE_BOT platform.

## Quick Start

### 1. Initialize i18n

The i18n system is automatically initialized in `src/main.tsx`. No additional setup is needed.

### 2. Use Translations in Components

```tsx
import { useI18n } from '@/i18n';

export const MyComponent = () => {
  const { t } = useI18n();

  return (
    <div>
      <h1>{t('common.welcome')}</h1>
      <button>{t('common.save')}</button>
    </div>
  );
};
```

### 3. Add Language Switcher

```tsx
import { LanguageSwitcher } from '@/i18n';

export const Header = () => {
  return (
    <header>
      <h1>My App</h1>
      <LanguageSwitcher variant="select" />
    </header>
  );
};
```

## API Reference

### useI18n Hook

The main hook for accessing translation functions and language management.

```typescript
const {
  t,                    // Translation function
  language,             // Current language code ('en', 'ru', 'es', 'fr')
  changeLanguage,       // Function to change language
  supportedLanguages,   // Object with all supported languages
  isRTL,                // Boolean indicating RTL language
  formatDate,           // Format date according to locale
  formatNumber,         // Format number according to locale
  formatCurrency,       // Format currency according to locale
} = useI18n();
```

#### Translation Function

```typescript
// Simple translation
t('common.save')  // "Save"

// With interpolation
t('hints.fileSize', { size: 50 })  // "File size must be less than 50MB"

// Plural forms
t('time.minutesAgo', { count: 5 })  // "5 minutes ago"
```

#### Formatting Functions

```typescript
// Format date
formatDate(new Date(), 'medium')      // "Jan 15, 2024"
formatDate('2024-01-15', 'long')      // "January 15, 2024"
formatDate(1705276800000, 'short')    // "1/15/24"

// Format number
formatNumber(1234.56)                           // "1,234.56"
formatNumber(3.14159, { maximumFractionDigits: 2 })  // "3.14"

// Format currency
formatCurrency(99.99)              // "$99.99"
formatCurrency(100, 'EUR')         // "€100.00"
```

### LanguageSwitcher Component

```tsx
<LanguageSwitcher
  variant="select"          // 'select', 'dropdown', 'button'
  showNames={true}          // Show language names vs codes
  showIcon={true}           // Show globe icon (dropdown only)
  className=""              // Custom CSS classes
  onLanguageChange={(lang) => console.log(lang)}  // Callback
/>
```

#### Variants

- **select**: HTML select dropdown
  ```tsx
  <LanguageSwitcher variant="select" />
  ```

- **dropdown**: Material-style dropdown menu
  ```tsx
  <LanguageSwitcher variant="dropdown" showIcon={true} />
  ```

- **button**: Button group
  ```tsx
  <LanguageSwitcher variant="button" showNames={true} />
  ```

## Translation Structure

Translations are organized in JSON files by namespace:

```
src/i18n/locales/
├── en/
│   ├── common.json        # Navigation, status, actions
│   ├── forms.json         # Form labels, placeholders, buttons
│   ├── errors.json        # Error messages
│   ├── messages.json      # Info, success, warning messages
│   └── validation.json    # Field validation messages
├── ru/
├── es/
└── fr/
```

### Key Structure

Keys use dot notation for nested values:

```json
{
  "common": {
    "save": "Save",
    "cancel": "Cancel"
  },
  "navigation": {
    "dashboard": "Dashboard",
    "materials": "Materials"
  }
}
```

Access with: `t('common.save')`, `t('navigation.dashboard')`

## Adding New Translations

### 1. Add Key to English

Edit `src/i18n/locales/en/<namespace>.json`:

```json
{
  "myFeature": {
    "title": "My Feature",
    "description": "This is my feature"
  }
}
```

### 2. Add to All Languages

Add the same key structure to:
- `src/i18n/locales/ru/<namespace>.json`
- `src/i18n/locales/es/<namespace>.json`
- `src/i18n/locales/fr/<namespace>.json`

### 3. Use in Component

```tsx
import { useI18n } from '@/i18n';

export const MyFeature = () => {
  const { t } = useI18n();

  return (
    <div>
      <h2>{t('myFeature.title')}</h2>
      <p>{t('myFeature.description')}</p>
    </div>
  );
};
```

## Common Patterns

### Error Messages

```tsx
const { t } = useI18n();

// HTTP errors
t('errors.http.400')  // "Bad Request - Invalid input"
t('errors.http.401')  // "Unauthorized - Please log in"

// Validation errors
t('errors.validation.required')  // "This field is required"
t('errors.validation.email')     // "Please enter a valid email"
```

### Form Fields

```tsx
const { t } = useI18n();

<label>{t('forms.labels.email')}</label>
<input
  placeholder={t('forms.placeholders.enterEmail')}
  type="email"
/>
<button>{t('forms.buttons.submit')}</button>
```

### Status Messages

```tsx
const { t } = useI18n();

<span>{t('status.active')}</span>      // "Active"
<span>{t('status.pending')}</span>     // "Pending"
<span>{t('status.completed')}</span>   // "Completed"
```

### User Messages

```tsx
const { t } = useI18n();

// Success
toast.success(t('messages.success.saved'))  // "Changes saved successfully"

// Error
toast.error(t('messages.info.noData'))      // "No data available"

// Warning
dialog.confirm(t('messages.warning.deleteConfirm'))
```

## Localization Features

### Date Formatting

Dates are automatically formatted according to the current language:

```tsx
const { formatDate } = useI18n();

// English: "Jan 15, 2024"
// Russian: "15 янв. 2024 г."
// Spanish: "15 ene 2024"
formatDate(new Date('2024-01-15'), 'medium')
```

### Number Formatting

Numbers use locale-specific separators:

```tsx
const { formatNumber } = useI18n();

// English: "1,234.56"
// Russian: "1 234,56"
// Spanish: "1.234,56"
// French: "1 234,56"
formatNumber(1234.56)
```

### Currency Formatting

Currency uses locale-specific format and symbol:

```tsx
const { formatCurrency } = useI18n();

// English: "$99.99"
// Russian: "99,99 $"
// Spanish: "99,99 €" (with EUR)
formatCurrency(99.99, 'USD')
```

## Supported Languages

| Code | Name | Direction |
|------|------|-----------|
| en | English | LTR |
| ru | Русский | LTR |
| es | Español | LTR |
| fr | Français | LTR |

## Advanced Features

### Language Detection

The system automatically detects the user's language preference:

1. Check localStorage for saved preference
2. Check browser language setting
3. Check HTML `lang` attribute
4. Fallback to English

### Language Persistence

Selected language is automatically saved to localStorage:

```typescript
await changeLanguage('ru');
// Saved to localStorage as 'i18n_language'
```

### Fallback Language

If a translation is missing in the current language, English is used as fallback.

## Best Practices

### 1. Use Consistent Key Names

Good:
```json
{
  "validation": {
    "email": {
      "required": "Email is required",
      "invalid": "Email is invalid"
    }
  }
}
```

Bad:
```json
{
  "emailRequired": "Email is required",
  "invalidEmail": "Email is invalid"
}
```

### 2. Use Translation Keys Everywhere

Bad:
```tsx
<h1>Welcome to THE_BOT</h1>
```

Good:
```tsx
<h1>{t('app.title')}</h1>
```

### 3. Keep Messages in Lowercase (except proper nouns)

Good:
```json
{
  "common": {
    "save": "save"
  }
}
```

Then use title case in component if needed.

### 4. Use Interpolation for Variables

Bad:
```json
{
  "fileSize50": "File size must be less than 50MB",
  "fileSize100": "File size must be less than 100MB"
}
```

Good:
```json
{
  "hints": {
    "fileSize": "File size must be less than {{size}}MB"
  }
}
```

### 5. Group Related Translations

Good organization:
```
common.json        -> Navigation, status, actions
forms.json         -> Form labels, placeholders
errors.json        -> Error messages
messages.json      -> Success, info, warnings
validation.json    -> Field validation
```

## Troubleshooting

### Translation Not Showing

1. Check key exists in all language files
2. Verify JSON syntax is valid
3. Check that i18n is initialized before component renders
4. Verify namespace is listed in i18n config

### Language Not Changing

1. Check browser console for errors
2. Verify localStorage is enabled
3. Check that language code is valid ('en', 'ru', 'es', 'fr')
4. Ensure all language files are loaded

### Formatting Issues

1. Check current language with `useI18n().language`
2. Verify Intl API is supported in browser
3. Check date/number format options

## Testing

Example test for translated component:

```typescript
import { render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/i18n/i18n';
import MyComponent from './MyComponent';

describe('MyComponent', () => {
  it('should render with translations', () => {
    const { getByText } = render(
      <I18nextProvider i18n={i18n}>
        <MyComponent />
      </I18nextProvider>
    );

    expect(getByText('Save')).toBeTruthy();
  });

  it('should translate to Russian', async () => {
    await i18n.changeLanguage('ru');

    const { getByText } = render(
      <I18nextProvider i18n={i18n}>
        <MyComponent />
      </I18nextProvider>
    );

    expect(getByText('Сохранить')).toBeTruthy();
  });
});
```

## Performance Tips

1. **Use `useI18n` hook instead of `useTranslation`**: Provides better type safety
2. **Don't call `t()` in loops**: Cache the result
3. **Use `i18n.t()` for non-React code**: Direct access to i18n
4. **Lazy load heavy translation namespaces**: If needed

## Resources

- [i18next Documentation](https://www.i18next.com/)
- [react-i18next Documentation](https://react.i18next.com/)
- [Intl API Documentation](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl)
