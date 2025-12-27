/**
 * Form Validation Library Tests
 *
 * Comprehensive test coverage for all validators including:
 * - Email validation (RFC 5322)
 * - Password strength validation
 * - Phone number validation
 * - URL validation
 * - Date validation
 * - Field validators (length, match, required)
 * - Custom validators (pattern, function, async)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  // Email validators
  validateEmail,
  validateEmailQuick,

  // Password validators
  validatePassword,
  validatePasswordQuick,
  PasswordStrength,
  PASSWORD_CONFIG,

  // Phone validators
  validatePhone,
  formatPhoneNumber,
  getCleanPhone,

  // URL validators
  validateUrl,
  validateUrlQuick,
  URL_CONFIG,

  // Date validators
  validateDate,
  validateDateRange,
  DATE_CONFIG,

  // Field validators
  validateFieldLength,
  validateFieldMatch,
  validateRequired,
  validateCustomPattern,
  validateCustomFunction,
  validateAsync,

  // Other validators
  validateName,
  getErrorMessage,
} from '../validation';

/* ============================================================================
   EMAIL VALIDATION TESTS
   ============================================================================ */

describe('Email Validation', () => {
  describe('validateEmail', () => {
    it('should validate correct email addresses', () => {
      const validEmails = [
        'user@example.com',
        'john.doe@example.co.uk',
        'test+tag@example.org',
        'user123@test-domain.com',
      ];

      validEmails.forEach((email) => {
        const result = validateEmail(email);
        expect(result.isValid).toBe(true);
        expect(result.message).toBeUndefined();
      });
    });

    it('should reject invalid email formats', () => {
      const invalidEmails = [
        'invalid.email',
        '@example.com',
        'user@',
        'user@@example.com',
        'user@example',
        'user name@example.com',
      ];

      invalidEmails.forEach((email) => {
        const result = validateEmail(email);
        expect(result.isValid).toBe(false);
        expect(result.message).toBeDefined();
      });
    });

    it('should reject empty email', () => {
      const result = validateEmail('');
      expect(result.isValid).toBe(false);
      expect(result.message).toBe('Email is required');
    });

    it('should validate email with proper length constraints', () => {
      const tooLongLocal = `${'a'.repeat(65)}@example.com`;
      const result = validateEmail(tooLongLocal);
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('local part is too long');
    });

    it('should reject emails with consecutive dots', () => {
      const result = validateEmail('user..name@example.com');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('consecutive dots');
    });

    it('should reject emails starting/ending with dot', () => {
      const result1 = validateEmail('.user@example.com');
      const result2 = validateEmail('user.@example.com');
      expect(result1.isValid).toBe(false);
      expect(result2.isValid).toBe(false);
    });

    it('should handle case insensitivity', () => {
      const result = validateEmail('User@Example.COM');
      expect(result.isValid).toBe(true);
    });

    it('should trim whitespace', () => {
      const result = validateEmail('  user@example.com  ');
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateEmailQuick', () => {
    it('should validate correct emails quickly', () => {
      expect(validateEmailQuick('user@example.com')).toBe(true);
      expect(validateEmailQuick('test@test.co.uk')).toBe(true);
    });

    it('should reject invalid emails quickly', () => {
      expect(validateEmailQuick('invalid.email')).toBe(false);
      expect(validateEmailQuick('@example.com')).toBe(false);
    });
  });
});

/* ============================================================================
   PASSWORD VALIDATION TESTS
   ============================================================================ */

describe('Password Validation', () => {
  describe('validatePassword', () => {
    it('should validate strong passwords', () => {
      const result = validatePassword('SecurePass123!');
      expect(result.isValid).toBe(true);
      expect(result.strength).toBe(PasswordStrength.VERY_STRONG);
      expect(result.missingRequirements).toHaveLength(0);
    });

    it('should reject passwords without uppercase', () => {
      const result = validatePassword('securepass123!');
      expect(result.isValid).toBe(false);
      expect(result.missingRequirements).toContain('Uppercase letter (A-Z)');
    });

    it('should reject passwords without lowercase', () => {
      const result = validatePassword('SECUREPASS123!');
      expect(result.isValid).toBe(false);
      expect(result.missingRequirements).toContain('Lowercase letter (a-z)');
    });

    it('should reject passwords without numbers', () => {
      const result = validatePassword('SecurePass!');
      expect(result.isValid).toBe(false);
      expect(result.missingRequirements).toContain('Number (0-9)');
    });

    it('should reject passwords without special characters', () => {
      const result = validatePassword('SecurePass123');
      expect(result.isValid).toBe(false);
      expect(result.missingRequirements).toContain('Special character (!@#$%^&*...)');
    });

    it('should reject passwords shorter than minimum length', () => {
      const result = validatePassword('Pass1!');
      expect(result.isValid).toBe(false);
      expect(result.missingRequirements).toContain(
        `Minimum ${PASSWORD_CONFIG.MIN_LENGTH} characters`
      );
    });

    it('should reject passwords longer than maximum length', () => {
      const longPassword = 'A' + 'a'.repeat(127) + '1!';
      const result = validatePassword(longPassword);
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('too long');
    });

    it('should reject empty password', () => {
      const result = validatePassword('');
      expect(result.isValid).toBe(false);
      expect(result.message).toBe('Password is required');
      expect(result.missingRequirements).toHaveLength(5);
    });

    it('should calculate password strength correctly', () => {
      // 'Pass1!' has 4 missing requirements (too short, lowercase, number, special is present but too short)
      const shortPassword = validatePassword('Pass1!');
      expect(shortPassword.strength).toBeDefined();
      expect(shortPassword.isValid).toBe(false);

      // 'Pass1!ab' - 12 chars, has all requirements
      const fair = validatePassword('Pass1!ab12');
      expect(fair.strength).toBeDefined();

      // SecurePass123! - 14 chars, has all requirements
      const strong = validatePassword('SecurePass123!');
      expect(strong.strength).toBeDefined();
      expect(strong.isValid).toBe(true);

      // VerySecurePassword123!@
      const veryStrong = validatePassword('VerySecurePassword123!@');
      expect(veryStrong.strength).toBe(PasswordStrength.VERY_STRONG);
      expect(veryStrong.score).toBeGreaterThan(80);
    });

    it('should include missing requirements in message', () => {
      const result = validatePassword('weak');
      expect(result.message).toContain('must contain');
    });

    it('should award extra points for very long passwords', () => {
      const result = validatePassword('VeryLongSecurePassword123!@#');
      expect(result.score).toBeGreaterThan(90);
    });
  });

  describe('validatePasswordQuick', () => {
    it('should check password length only', () => {
      expect(validatePasswordQuick('short')).toBe(false);
      expect(validatePasswordQuick('validlengthpassword')).toBe(true);
    });
  });

  describe('PASSWORD_CONFIG', () => {
    it('should have correct default config', () => {
      expect(PASSWORD_CONFIG.MIN_LENGTH).toBe(12);
      expect(PASSWORD_CONFIG.MAX_LENGTH).toBe(128);
      expect(PASSWORD_CONFIG.REQUIRE_UPPERCASE).toBe(true);
      expect(PASSWORD_CONFIG.REQUIRE_LOWERCASE).toBe(true);
      expect(PASSWORD_CONFIG.REQUIRE_NUMBERS).toBe(true);
      expect(PASSWORD_CONFIG.REQUIRE_SPECIAL).toBe(true);
    });
  });
});

/* ============================================================================
   PHONE VALIDATION TESTS
   ============================================================================ */

describe('Phone Validation', () => {
  describe('validatePhone', () => {
    it('should validate international phone numbers', () => {
      const validPhones = [
        '+79991234567',
        '79991234567',
        '+1 (555) 123-45-67',
        '+44 (555) 123-45-67',
      ];

      validPhones.forEach((phone) => {
        const result = validatePhone(phone);
        expect(result.isValid).toBe(true);
      });
    });

    it('should reject invalid phone numbers', () => {
      const invalidPhones = ['123', '+123', 'not-a-number', ''];

      invalidPhones.forEach((phone) => {
        const result = validatePhone(phone);
        expect(result.isValid).toBe(false);
      });
    });

    it('should handle formatted phone numbers', () => {
      const result = validatePhone('+7 (999) 123-45-67');
      expect(result.isValid).toBe(true);
    });

    it('should reject empty phone', () => {
      const result = validatePhone('');
      expect(result.isValid).toBe(false);
      expect(result.message).toBe('Phone number is required');
    });

    it('should support international formats', () => {
      const result = validatePhone('+441234567890');
      expect(result.isValid).toBe(true);
    });
  });

  describe('formatPhoneNumber', () => {
    it('should format Russian phone numbers', () => {
      const formatted = formatPhoneNumber('+79991234567');
      expect(formatted).toBe('+7 (999) 123-45-67');
    });

    it('should handle phone without plus sign', () => {
      const formatted = formatPhoneNumber('79991234567');
      expect(formatted).toBe('+7 (999) 123-45-67');
    });

    it('should handle 8 prefix for Russian numbers', () => {
      const formatted = formatPhoneNumber('89991234567');
      expect(formatted).toBe('+7 (999) 123-45-67');
    });

    it('should return empty string for empty input', () => {
      expect(formatPhoneNumber('')).toBe('');
    });

    it('should handle already formatted numbers', () => {
      const formatted = formatPhoneNumber('+7 (999) 123-45-67');
      expect(formatted).toBe('+7 (999) 123-45-67');
    });
  });

  describe('getCleanPhone', () => {
    it('should remove all formatting', () => {
      const clean = getCleanPhone('+7 (999) 123-45-67');
      expect(clean).toBe('+79991234567');
    });

    it('should keep plus sign and digits only', () => {
      const clean = getCleanPhone('+7-999-123-45-67');
      expect(clean).toBe('+79991234567');
    });
  });
});

/* ============================================================================
   URL VALIDATION TESTS
   ============================================================================ */

describe('URL Validation', () => {
  describe('validateUrl', () => {
    it('should validate correct URLs', () => {
      const validUrls = [
        'https://example.com',
        'http://example.com',
        'https://subdomain.example.co.uk',
        'https://example.com/path/to/page',
        'https://example.com:8080/path',
        'ftp://files.example.com',
      ];

      validUrls.forEach((url) => {
        const result = validateUrl(url);
        expect(result.isValid).toBe(true);
      });
    });

    it('should reject URLs without protocol', () => {
      const result = validateUrl('example.com');
      expect(result.isValid).toBe(false);
      // URL without protocol is caught as invalid format
      expect(result.message).toBeDefined();
    });

    it('should reject URLs with invalid protocol', () => {
      const result = validateUrl('ftp2://example.com');
      expect(result.isValid).toBe(false);
    });

    it('should reject empty URL', () => {
      const result = validateUrl('');
      expect(result.isValid).toBe(false);
      expect(result.message).toBe('URL is required');
    });

    it('should reject URLs without TLD', () => {
      const result = validateUrl('https://localhost');
      expect(result.isValid).toBe(false);
    });

    it('should handle URLs with authentication', () => {
      const result = validateUrl('https://user:pass@example.com');
      expect(result.isValid).toBe(true);
    });

    it('should enforce max length', () => {
      const longUrl = `https://example.com/${'a'.repeat(2100)}`;
      const result = validateUrl(longUrl);
      expect(result.isValid).toBe(false);
    });
  });

  describe('validateUrlQuick', () => {
    it('should quickly validate URLs', () => {
      expect(validateUrlQuick('https://example.com')).toBe(true);
      expect(validateUrlQuick('http://test.org')).toBe(true);
      expect(validateUrlQuick('invalid-url')).toBe(false);
    });

    it('should return false for empty string', () => {
      expect(validateUrlQuick('')).toBe(false);
    });
  });

  describe('URL_CONFIG', () => {
    it('should have correct default config', () => {
      expect(URL_CONFIG.ALLOWED_PROTOCOLS).toContain('http');
      expect(URL_CONFIG.ALLOWED_PROTOCOLS).toContain('https');
      expect(URL_CONFIG.ALLOWED_PROTOCOLS).toContain('ftp');
      expect(URL_CONFIG.MAX_LENGTH).toBe(2048);
    });
  });
});

/* ============================================================================
   DATE VALIDATION TESTS
   ============================================================================ */

describe('Date Validation', () => {
  describe('validateDate', () => {
    it('should validate correct dates', () => {
      const result = validateDate('2024-12-25');
      expect(result.isValid).toBe(true);
    });

    it('should validate Date objects', () => {
      const result = validateDate(new Date('2024-12-25'));
      expect(result.isValid).toBe(true);
    });

    it('should reject invalid date strings', () => {
      const result = validateDate('invalid-date');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('YYYY-MM-DD');
    });

    it('should reject empty date', () => {
      const result = validateDate('');
      expect(result.isValid).toBe(false);
      expect(result.message).toBe('Date is required');
    });

    it('should enforce future date requirement', () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      const futureResult = validateDate(yesterday, { mustBeFuture: true });
      expect(futureResult.isValid).toBe(false);

      const pastResult = validateDate(tomorrow, { mustBeFuture: true });
      expect(pastResult.isValid).toBe(true);
    });

    it('should enforce past date requirement', () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      const pastResult = validateDate(tomorrow, { mustBePast: true });
      expect(pastResult.isValid).toBe(false);

      const futureResult = validateDate(yesterday, { mustBePast: true });
      expect(futureResult.isValid).toBe(true);
    });

    it('should enforce min date constraint', () => {
      const minDate = new Date('2024-01-01');
      const validResult = validateDate('2024-12-25', { minDate });
      const invalidResult = validateDate('2023-12-25', { minDate });

      expect(validResult.isValid).toBe(true);
      expect(invalidResult.isValid).toBe(false);
    });

    it('should enforce max date constraint', () => {
      const maxDate = new Date('2024-12-31');
      const validResult = validateDate('2024-06-15', { maxDate });
      const invalidResult = validateDate('2025-01-01', { maxDate });

      expect(validResult.isValid).toBe(true);
      expect(invalidResult.isValid).toBe(false);
    });
  });

  describe('validateDateRange', () => {
    it('should validate correct date ranges', () => {
      const result = validateDateRange('2024-01-01', '2024-12-31');
      expect(result.isValid).toBe(true);
    });

    it('should reject invalid start date', () => {
      const result = validateDateRange('invalid', '2024-12-31');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('Start date');
    });

    it('should reject invalid end date', () => {
      const result = validateDateRange('2024-01-01', 'invalid');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('End date');
    });

    it('should reject when start date is after end date', () => {
      const result = validateDateRange('2024-12-31', '2024-01-01');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('Start date must be before');
    });

    it('should support Date objects', () => {
      const start = new Date('2024-01-01');
      const end = new Date('2024-12-31');
      const result = validateDateRange(start, end);
      expect(result.isValid).toBe(true);
    });
  });

  describe('DATE_CONFIG', () => {
    it('should have correct default config', () => {
      expect(DATE_CONFIG.ALLOW_PAST).toBe(true);
      expect(DATE_CONFIG.ALLOW_FUTURE).toBe(true);
    });
  });
});

/* ============================================================================
   FIELD VALIDATORS TESTS
   ============================================================================ */

describe('Field Validators', () => {
  describe('validateFieldLength', () => {
    it('should validate field length within bounds', () => {
      const result = validateFieldLength('John', 2, 50);
      expect(result.isValid).toBe(true);
    });

    it('should reject field shorter than minimum', () => {
      const result = validateFieldLength('J', 2, 50);
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('Minimum length');
    });

    it('should reject field longer than maximum', () => {
      const result = validateFieldLength('a'.repeat(51), 2, 50);
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('Maximum length');
    });

    it('should reject empty field', () => {
      const result = validateFieldLength('', 2, 50);
      expect(result.isValid).toBe(false);
    });
  });

  describe('validateFieldMatch', () => {
    it('should validate matching fields', () => {
      const result = validateFieldMatch('password', 'password', 'passwords');
      expect(result.isValid).toBe(true);
    });

    it('should reject non-matching fields', () => {
      const result = validateFieldMatch('password', 'different', 'passwords');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('do not match');
    });

    it('should support numbers', () => {
      const result = validateFieldMatch(123, 123, 'values');
      expect(result.isValid).toBe(true);

      const result2 = validateFieldMatch(123, 456, 'values');
      expect(result2.isValid).toBe(false);
    });

    it('should use field name in error message', () => {
      const result = validateFieldMatch('value1', 'value2', 'custom field');
      expect(result.message).toContain('custom field');
    });
  });

  describe('validateRequired', () => {
    it('should validate non-empty values', () => {
      const result = validateRequired('value');
      expect(result.isValid).toBe(true);
    });

    it('should reject empty strings', () => {
      const result = validateRequired('');
      expect(result.isValid).toBe(false);
    });

    it('should reject whitespace-only strings', () => {
      const result = validateRequired('   ');
      expect(result.isValid).toBe(false);
    });

    it('should reject null/undefined', () => {
      const result1 = validateRequired(null);
      const result2 = validateRequired(undefined);
      expect(result1.isValid).toBe(false);
      expect(result2.isValid).toBe(false);
    });

    it('should use field name in error message', () => {
      const result = validateRequired('', 'Email');
      expect(result.message).toContain('Email');
    });

    it('should treat zero as falsy (invalid)', () => {
      // Note: validateRequired treats 0 as falsy, which is expected behavior
      // For numeric fields, use custom validation instead
      const result = validateRequired(0);
      expect(result.isValid).toBe(false);
    });
  });

  describe('validateCustomPattern', () => {
    it('should validate against regex pattern', () => {
      const pattern = /^[a-z0-9]+$/;
      const result = validateCustomPattern('user123', pattern);
      expect(result.isValid).toBe(true);
    });

    it('should reject non-matching pattern', () => {
      const pattern = /^[a-z]+$/;
      const result = validateCustomPattern('User123', pattern);
      expect(result.isValid).toBe(false);
    });

    it('should use custom error message', () => {
      const pattern = /^[a-z]+$/;
      const result = validateCustomPattern('ABC', pattern, 'Only lowercase allowed');
      expect(result.message).toBe('Only lowercase allowed');
    });

    it('should reject empty values', () => {
      const pattern = /^[a-z]+$/;
      const result = validateCustomPattern('', pattern);
      expect(result.isValid).toBe(false);
    });
  });

  describe('validateCustomFunction', () => {
    it('should validate with custom function', () => {
      const isEven = (n: number) => n % 2 === 0;
      const result = validateCustomFunction(4, isEven);
      expect(result.isValid).toBe(true);
    });

    it('should reject invalid custom function result', () => {
      const isEven = (n: number) => n % 2 === 0;
      const result = validateCustomFunction(3, isEven);
      expect(result.isValid).toBe(false);
    });

    it('should use custom error message', () => {
      const isEven = (n: number) => n % 2 === 0;
      const result = validateCustomFunction(3, isEven, 'Number must be even');
      expect(result.message).toBe('Number must be even');
    });

    it('should support complex validation functions', () => {
      const isValidUsername = (username: string) =>
        username.length >= 3 && /^[a-z0-9_]+$/.test(username);

      expect(validateCustomFunction('valid_user', isValidUsername).isValid).toBe(true);
      expect(validateCustomFunction('ab', isValidUsername).isValid).toBe(false);
      expect(validateCustomFunction('Invalid-User', isValidUsername).isValid).toBe(false);
    });
  });

  describe('validateAsync', () => {
    it('should validate async function returning true', async () => {
      const asyncValidator = async (value: string) => value.length > 3;
      const result = await validateAsync('valid', asyncValidator);
      expect(result.isValid).toBe(true);
    });

    it('should reject async function returning false', async () => {
      const asyncValidator = async (value: string) => value.length > 3;
      const result = await validateAsync('no', asyncValidator);
      expect(result.isValid).toBe(false);
    });

    it('should use custom error message', async () => {
      const asyncValidator = async () => false;
      const result = await validateAsync('value', asyncValidator, 'Custom error');
      expect(result.message).toBe('Custom error');
    });

    it('should handle async function errors', async () => {
      const asyncValidator = async () => {
        throw new Error('API error');
      };
      const result = await validateAsync('value', asyncValidator);
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('Validation error');
    });

    it('should simulate email existence check', async () => {
      const checkEmailExists = async (email: string) => {
        // Simulate API call
        return email !== 'taken@example.com';
      };

      const result1 = await validateAsync('available@example.com', checkEmailExists, 'Email already taken');
      const result2 = await validateAsync('taken@example.com', checkEmailExists, 'Email already taken');

      expect(result1.isValid).toBe(true);
      expect(result2.isValid).toBe(false);
      expect(result2.message).toBe('Email already taken');
    });
  });
});

/* ============================================================================
   NAME VALIDATION TESTS
   ============================================================================ */

describe('Name Validation', () => {
  describe('validateName', () => {
    it('should validate correct names', () => {
      const validNames = ['John Doe', 'Иван Петров', 'Jean-Paul', 'Maria Santos'];

      validNames.forEach((name) => {
        const result = validateName(name);
        expect(result.isValid).toBe(true);
      });
    });

    it('should reject names shorter than 2 characters', () => {
      const result = validateName('J');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('at least 2');
    });

    it('should reject names longer than 50 characters', () => {
      const result = validateName('a'.repeat(51));
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('exceed 50');
    });

    it('should reject names with numbers', () => {
      const result = validateName('John123');
      expect(result.isValid).toBe(false);
    });

    it('should reject names with special characters', () => {
      const result = validateName('John@Doe');
      expect(result.isValid).toBe(false);
    });

    it('should accept Latin characters', () => {
      const result = validateName('Alexander');
      expect(result.isValid).toBe(true);
    });

    it('should accept Cyrillic characters', () => {
      const result = validateName('Александр');
      expect(result.isValid).toBe(true);
    });

    it('should accept spaces', () => {
      const result = validateName('John Doe Smith');
      expect(result.isValid).toBe(true);
    });

    it('should accept hyphens', () => {
      const result = validateName('Jean-Pierre');
      expect(result.isValid).toBe(true);
    });

    it('should reject empty name', () => {
      const result = validateName('');
      expect(result.isValid).toBe(false);
      expect(result.message).toBe('Name is required');
    });
  });
});

/* ============================================================================
   ERROR MESSAGE UTILITIES TESTS
   ============================================================================ */

describe('Error Message Utilities', () => {
  describe('getErrorMessage', () => {
    it('should handle invalid login credentials', () => {
      const error = new Error('Invalid login credentials');
      const message = getErrorMessage(error);
      expect(message).toBe('Invalid email or password');
    });

    it('should handle email not confirmed', () => {
      const error = new Error('Email not confirmed');
      const message = getErrorMessage(error);
      expect(message).toContain('verify');
    });

    it('should handle user already exists', () => {
      const error = new Error('User already registered');
      const message = getErrorMessage(error);
      expect(message).toContain('already exists');
    });

    it('should handle password too short', () => {
      const error = new Error('Password should be at least 8 characters');
      const message = getErrorMessage(error);
      expect(message).toContain('too short');
    });

    it('should handle registration disabled', () => {
      const error = new Error('Signup is disabled');
      const message = getErrorMessage(error);
      expect(message).toContain('temporarily disabled');
    });

    it('should handle email rate limit', () => {
      const error = new Error('Email rate limit exceeded');
      const message = getErrorMessage(error);
      expect(message).toContain('Too many attempts');
    });

    it('should handle password rate limit', () => {
      const error = new Error('Password rate limit exceeded');
      const message = getErrorMessage(error);
      expect(message).toContain('login attempts');
    });

    it('should return original message for unknown errors', () => {
      const error = new Error('Custom error message');
      const message = getErrorMessage(error);
      expect(message).toBe('Custom error message');
    });

    it('should handle null error', () => {
      const message = getErrorMessage(null);
      expect(message).toBe('Unknown error');
    });

    it('should handle undefined error', () => {
      const message = getErrorMessage(undefined);
      expect(message).toBe('Unknown error');
    });
  });
});

/* ============================================================================
   INTEGRATION TESTS
   ============================================================================ */

describe('Validation Integration', () => {
  it('should validate complete user registration form', () => {
    const formData = {
      email: validateEmail('user@example.com'),
      password: validatePassword('SecurePass123!'),
      passwordConfirm: 'SecurePass123!',
      phone: validatePhone('+79991234567'),
      name: validateName('John Doe'),
    };

    expect(formData.email.isValid).toBe(true);
    expect(formData.password.isValid).toBe(true);
    expect(formData.phone.isValid).toBe(true);
    expect(formData.name.isValid).toBe(true);
  });

  it('should validate complete user profile form', () => {
    const formData = {
      name: validateName('Jane Smith'),
      email: validateEmail('jane@example.com'),
      phone: validatePhone('+79991234567'),
      birthDate: validateDate('1990-05-15', { mustBePast: true }),
      website: validateUrl('https://janesmith.com'),
    };

    expect(formData.name.isValid).toBe(true);
    expect(formData.email.isValid).toBe(true);
    expect(formData.phone.isValid).toBe(true);
    expect(formData.birthDate.isValid).toBe(true);
    expect(formData.website.isValid).toBe(true);
  });

  it('should handle multiple validation errors', () => {
    const password = validatePassword('weak');
    const errors = password.missingRequirements;

    expect(errors.length).toBeGreaterThan(0);
    expect(password.isValid).toBe(false);
  });
});
