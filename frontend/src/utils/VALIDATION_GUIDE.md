# Form Validation Library Guide

Comprehensive client-side validation utilities for React forms with support for React Hook Form, Zod, and custom validators.

## Table of Contents

1. [Overview](#overview)
2. [Email Validation](#email-validation)
3. [Password Validation](#password-validation)
4. [Phone Validation](#phone-validation)
5. [URL Validation](#url-validation)
6. [Date Validation](#date-validation)
7. [Field Validators](#field-validators)
8. [Custom Validators](#custom-validators)
9. [React Hook Form Integration](#react-hook-form-integration)
10. [Examples](#examples)

## Overview

The validation library provides type-safe, composable validators for common form fields. Each validator returns a `ValidationResult` object with `isValid` flag and optional error message.

```typescript
interface ValidationResult {
  isValid: boolean;
  message?: string;
  errors?: string[];
}
```

### Features

- RFC 5322 compliant email validation
- Password strength calculation with missing requirements
- International phone number support
- URL validation with protocol check
- Date range validation
- Field length and matching validators
- Custom regex and function validators
- Async validation support (for API calls)
- Comprehensive error messages
- TypeScript support with full type hints

## Email Validation

### Basic Usage

```typescript
import { validateEmail, validateEmailQuick } from '@/utils/validation';

// Full validation (checks format, length, special cases)
const result = validateEmail('user@example.com');
if (result.isValid) {
  // Email is valid
} else {
  console.error(result.message); // "Invalid email format"
}

// Quick validation (format only, for real-time feedback)
const isValid = validateEmailQuick('user@example.com'); // boolean
```

### What It Checks

- Email format (local@domain.tld)
- Local part length (max 64 characters)
- Domain length (max 255 characters)
- No consecutive dots
- Local part doesn't start/end with dot
- Trimming and case normalization

### Valid Examples

```typescript
validateEmail('john.doe@example.com').isValid // true
validateEmail('test+tag@example.co.uk').isValid // true
validateEmail('user123@test-domain.com').isValid // true
```

### Invalid Examples

```typescript
validateEmail('invalid.email').isValid // false
validateEmail('@example.com').isValid // false
validateEmail('user..name@example.com').isValid // false
```

## Password Validation

### Basic Usage

```typescript
import { validatePassword, PasswordStrength } from '@/utils/validation';

const result = validatePassword('SecurePass123!');

if (result.isValid) {
  console.log(`Password strength: ${result.strength}`); // "very_strong"
  console.log(`Score: ${result.score}`); // 90-100
} else {
  console.log(`Missing: ${result.missingRequirements.join(', ')}`);
  // "Missing: Uppercase letter (A-Z), Number (0-9)"
}
```

### Requirements

- **Minimum 12 characters** (configurable via `PASSWORD_CONFIG.MIN_LENGTH`)
- **Uppercase letter** (A-Z)
- **Lowercase letter** (a-z)
- **Number** (0-9)
- **Special character** (!@#$%^&*()_+-=[]{}|;:,.<>?)

### Strength Levels

```typescript
enum PasswordStrength {
  WEAK = 'weak',           // 4 missing requirements
  FAIR = 'fair',           // 3 missing requirements
  GOOD = 'good',           // 2 missing requirements
  STRONG = 'strong',       // 1 missing requirement
  VERY_STRONG = 'very_strong' // 0 missing + bonus for length
}
```

### Password Score

- 0-20: Weak (many missing requirements)
- 21-40: Fair (3 missing requirements)
- 41-60: Good (2 missing requirements)
- 61-80: Strong (1 missing requirement)
- 81-100: Very Strong (all requirements + length bonus)

### Examples

```typescript
// Strong password
validatePassword('SecurePass123!').isValid // true, strength: "very_strong"

// Missing special character
const result = validatePassword('SecurePass123');
result.isValid // false
result.missingRequirements // ['Special character (!@#$%^&*...)']
result.strength // "strong"
result.score // ~80

// Too short
validatePassword('Pass1!').isValid // false
```

### Quick Validation

```typescript
import { validatePasswordQuick } from '@/utils/validation';

// Check length only (for simple forms)
validatePasswordQuick('password123') // true/false
```

## Phone Validation

### Basic Usage

```typescript
import { validatePhone, formatPhoneNumber, getCleanPhone } from '@/utils/validation';

// Validate phone number
const result = validatePhone('+79991234567');
if (!result.isValid) {
  console.error(result.message);
}

// Format for display
const formatted = formatPhoneNumber('+79991234567');
// "+7 (999) 123-45-67"

// Get clean version for API
const clean = getCleanPhone('+7 (999) 123-45-67');
// "+79991234567"
```

### Supported Formats

- `+79991234567` (international)
- `79991234567` (without +)
- `+7 (999) 123-45-67` (formatted with country code)
- `(999) 123-45-67` (formatted without country code)
- `89991234567` (Russian 8 prefix, converts to +7)

### Pattern

Matches backend Django validator: `^\+?[1-9][\d]{4,15}$`

- Optional `+` sign
- Country code (1-9)
- 4-15 additional digits

### Examples

```typescript
// Valid
validatePhone('+79991234567').isValid // true
validatePhone('+7 (999) 123-45-67').isValid // true
validatePhone('(999) 123-45-67').isValid // true

// Invalid
validatePhone('123').isValid // false
validatePhone('+123').isValid // false
validatePhone('').isValid // false
```

## URL Validation

### Basic Usage

```typescript
import { validateUrl, validateUrlQuick } from '@/utils/validation';

// Full validation
const result = validateUrl('https://example.com');
if (result.isValid) {
  // Valid URL
} else {
  console.error(result.message);
}

// Quick validation (for real-time feedback)
const isValid = validateUrlQuick('https://example.com'); // boolean
```

### What It Checks

- Valid URL format
- Protocol (http, https, ftp)
- Valid hostname
- TLD present (at least one dot in domain)
- Maximum length (2048 characters)

### Allowed Protocols

- `http://`
- `https://`
- `ftp://`

### Examples

```typescript
// Valid
validateUrl('https://example.com').isValid // true
validateUrl('http://subdomain.example.co.uk').isValid // true
validateUrl('https://example.com:8080/path?query=value').isValid // true

// Invalid
validateUrl('example.com').isValid // false (no protocol)
validateUrl('https://localhost').isValid // false (no TLD)
validateUrl('invalid-url').isValid // false
```

## Date Validation

### Basic Usage

```typescript
import { validateDate, validateDateRange } from '@/utils/validation';

// Simple date validation
const result = validateDate('2024-12-25');
if (result.isValid) {
  console.log('Valid date');
}

// Date range validation
const rangeResult = validateDateRange('2024-01-01', '2024-12-31');
if (rangeResult.isValid) {
  console.log('Valid date range');
}
```

### Date Constraints

```typescript
// Must be in the future
validateDate('2025-12-25', { mustBeFuture: true }).isValid // true
validateDate('2020-12-25', { mustBeFuture: true }).isValid // false

// Must be in the past
validateDate('2020-12-25', { mustBePast: true }).isValid // true
validateDate('2025-12-25', { mustBePast: true }).isValid // false

// Minimum date
const minDate = new Date('2024-01-01');
validateDate('2024-12-25', { minDate }).isValid // true
validateDate('2023-12-25', { minDate }).isValid // false

// Maximum date
const maxDate = new Date('2024-12-31');
validateDate('2024-06-15', { maxDate }).isValid // true
validateDate('2025-01-01', { maxDate }).isValid // false
```

### Supported Formats

- String: `'YYYY-MM-DD'` (ISO format)
- Date object: `new Date('2024-12-25')`

### Examples

```typescript
// Birth date (must be in past)
validateDate('1990-05-15', { mustBePast: true }).isValid // true

// Future appointment
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
validateDate(tomorrow, { mustBeFuture: true }).isValid // true

// Valid date range
validateDateRange('2024-01-01', '2024-12-31').isValid // true
validateDateRange('2024-12-31', '2024-01-01').isValid // false
```

## Field Validators

### Field Length

```typescript
import { validateFieldLength } from '@/utils/validation';

// Validate min/max length
const result = validateFieldLength('John', 2, 50);
if (result.isValid) {
  console.log('Valid length');
}
```

### Field Match

```typescript
import { validateFieldMatch } from '@/utils/validation';

// Compare two fields (e.g., password confirmation)
const result = validateFieldMatch(
  password,
  passwordConfirm,
  'passwords'
);

if (!result.isValid) {
  console.error(result.message); // "passwords do not match"
}
```

### Required Field

```typescript
import { validateRequired } from '@/utils/validation';

// Check if field has value
const result = validateRequired(value, 'Email');
if (!result.isValid) {
  console.error(result.message); // "Email is required"
}
```

## Custom Validators

### Custom Pattern

```typescript
import { validateCustomPattern } from '@/utils/validation';

// Validate username: lowercase letters and numbers only
const result = validateCustomPattern(
  'user123',
  /^[a-z0-9_]+$/,
  'Username can only contain lowercase letters, numbers, and underscores'
);
```

### Custom Function

```typescript
import { validateCustomFunction } from '@/utils/validation';

// Custom validation logic
const isEven = (value) => Number(value) % 2 === 0;

const result = validateCustomFunction(
  4,
  isEven,
  'Number must be even'
);
```

### Async Validation

```typescript
import { validateAsync } from '@/utils/validation';

// Check if email already exists (async API call)
const checkEmailExists = async (email) => {
  const response = await fetch(`/api/check-email?email=${email}`);
  return response.ok; // true if email is available
};

const result = await validateAsync(
  'user@example.com',
  checkEmailExists,
  'Email already taken'
);
```

## React Hook Form Integration

### Basic Setup

```typescript
import { useForm } from 'react-hook-form';
import { validateEmail, validatePassword } from '@/utils/validation';

function RegisterForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();

  const onSubmit = (data) => {
    // Form data is valid
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email', {
          validate: (value) => {
            const result = validateEmail(value);
            return result.isValid || result.message;
          }
        })}
      />
      {errors.email && <span>{errors.email.message}</span>}

      <input
        {...register('password', {
          validate: (value) => {
            const result = validatePassword(value);
            return result.isValid || result.message;
          }
        })}
      />
      {errors.password && <span>{errors.password.message}</span>}
    </form>
  );
}
```

### With Zod Schema

```typescript
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { validateEmail, validatePassword } from '@/utils/validation';

const registrationSchema = z.object({
  email: z.string().refine(
    (email) => validateEmail(email).isValid,
    'Invalid email address'
  ),
  password: z.string().refine(
    (password) => validatePassword(password).isValid,
    'Password does not meet requirements'
  ),
  passwordConfirm: z.string(),
}).refine(
  (data) => data.password === data.passwordConfirm,
  {
    message: "Passwords don't match",
    path: ["passwordConfirm"],
  }
);

function RegisterForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(registrationSchema)
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* form fields */}
    </form>
  );
}
```

### Real-time Validation

```typescript
import { useState } from 'react';
import { validatePassword, validateEmail } from '@/utils/validation';

function RegistrationForm() {
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordStrength, setPasswordStrength] = useState(null);

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);

    // Real-time validation
    const result = validatePassword(value);
    setPasswordError(result.isValid ? '' : result.message);
    setPasswordStrength(result.strength);
  };

  return (
    <div>
      <input
        type="password"
        value={password}
        onChange={handlePasswordChange}
        placeholder="Enter password"
      />
      {passwordError && <div className="error">{passwordError}</div>}
      {password && (
        <div className="strength">
          Strength: <span className={`strength-${passwordStrength}`}>
            {passwordStrength}
          </span>
        </div>
      )}
    </div>
  );
}
```

## Examples

### Complete Registration Form

```typescript
import { useForm } from 'react-hook-form';
import {
  validateEmail,
  validatePassword,
  validatePhone,
  validateName,
  validateFieldMatch
} from '@/utils/validation';

function RegistrationForm() {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors }
  } = useForm();

  const password = watch('password');

  const onSubmit = async (data) => {
    // All fields are validated
    const response = await fetch('/api/register', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    // Handle response
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label>Name</label>
        <input
          {...register('name', {
            validate: (value) => {
              const result = validateName(value);
              return result.isValid || result.message;
            }
          })}
        />
        {errors.name && <span>{errors.name.message}</span>}
      </div>

      <div>
        <label>Email</label>
        <input
          type="email"
          {...register('email', {
            validate: (value) => {
              const result = validateEmail(value);
              return result.isValid || result.message;
            }
          })}
        />
        {errors.email && <span>{errors.email.message}</span>}
      </div>

      <div>
        <label>Phone</label>
        <input
          {...register('phone', {
            validate: (value) => {
              const result = validatePhone(value);
              return result.isValid || result.message;
            }
          })}
        />
        {errors.phone && <span>{errors.phone.message}</span>}
      </div>

      <div>
        <label>Password</label>
        <input
          type="password"
          {...register('password', {
            validate: (value) => {
              const result = validatePassword(value);
              return result.isValid || result.message;
            }
          })}
        />
        {errors.password && <span>{errors.password.message}</span>}
      </div>

      <div>
        <label>Confirm Password</label>
        <input
          type="password"
          {...register('passwordConfirm', {
            validate: (value) => {
              const result = validateFieldMatch(value, password, 'Passwords');
              return result.isValid || result.message;
            }
          })}
        />
        {errors.passwordConfirm && <span>{errors.passwordConfirm.message}</span>}
      </div>

      <button type="submit">Register</button>
    </form>
  );
}
```

### Profile Update Form

```typescript
import { useForm } from 'react-hook-form';
import {
  validateName,
  validateEmail,
  validatePhone,
  validateUrl,
  validateDate
} from '@/utils/validation';

function ProfileForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('firstName', {
          validate: (value) => {
            const result = validateName(value);
            return result.isValid || result.message;
          }
        })}
        placeholder="First Name"
      />

      <input
        {...register('email', {
          validate: (value) => {
            const result = validateEmail(value);
            return result.isValid || result.message;
          }
        })}
        type="email"
        placeholder="Email"
      />

      <input
        {...register('phone', {
          validate: (value) => {
            const result = validatePhone(value);
            return result.isValid || result.message;
          }
        })}
        placeholder="Phone"
      />

      <input
        {...register('website', {
          validate: (value) => {
            if (!value) return true; // optional
            const result = validateUrl(value);
            return result.isValid || result.message;
          }
        })}
        type="url"
        placeholder="Website (optional)"
      />

      <input
        type="date"
        {...register('birthDate', {
          validate: (value) => {
            const result = validateDate(value, { mustBePast: true });
            return result.isValid || result.message;
          }
        })}
      />

      <button type="submit">Update Profile</button>
    </form>
  );
}
```

### Async Email Uniqueness Check

```typescript
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { validateEmail, validateAsync } from '@/utils/validation';

function RegistrationForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();

  const checkEmailAvailable = async (email) => {
    const response = await fetch(`/api/check-email?email=${email}`);
    return response.ok; // true if available, false if taken
  };

  const validateEmailField = async (email) => {
    // First check format
    const formatResult = validateEmail(email);
    if (!formatResult.isValid) {
      return formatResult.message;
    }

    // Then check availability
    const availabilityResult = await validateAsync(
      email,
      checkEmailAvailable,
      'Email already registered'
    );
    return availabilityResult.isValid || availabilityResult.message;
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email', {
          validate: validateEmailField
        })}
        type="email"
        placeholder="Email"
      />
      {errors.email && <span className="error">{errors.email.message}</span>}
    </form>
  );
}
```

## Configuration

### Password Requirements

Customize password requirements in `PASSWORD_CONFIG`:

```typescript
import { PASSWORD_CONFIG } from '@/utils/validation';

// Current defaults:
// PASSWORD_CONFIG.MIN_LENGTH = 12
// PASSWORD_CONFIG.MAX_LENGTH = 128
// PASSWORD_CONFIG.REQUIRE_UPPERCASE = true
// PASSWORD_CONFIG.REQUIRE_LOWERCASE = true
// PASSWORD_CONFIG.REQUIRE_NUMBERS = true
// PASSWORD_CONFIG.REQUIRE_SPECIAL = true
// PASSWORD_CONFIG.SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'
```

### URL Protocols

Customize allowed URL protocols in `URL_CONFIG`:

```typescript
import { URL_CONFIG } from '@/utils/validation';

// Current defaults:
// URL_CONFIG.ALLOWED_PROTOCOLS = ['http', 'https', 'ftp']
// URL_CONFIG.MAX_LENGTH = 2048
```

### Date Options

```typescript
import { DATE_CONFIG } from '@/utils/validation';

// Current defaults:
// DATE_CONFIG.ALLOW_PAST = true
// DATE_CONFIG.ALLOW_FUTURE = true
```

## Testing

Run tests with:

```bash
npm test -- src/utils/__tests__/validation.test.ts
```

All validators are fully tested with 109+ test cases covering:
- Valid and invalid inputs
- Edge cases
- Error messages
- Type safety
- Async operations
- Integration scenarios
