/**
 * Form Validation Library
 *
 * Comprehensive client-side validation utilities for form inputs.
 * Includes email, password, phone, URL, date, and custom validators.
 * Compatible with React Hook Form and async validation support.
 */

/* ============================================================================
   EMAIL VALIDATION
   ============================================================================ */

/**
 * Email validation result interface
 */
export interface ValidationResult {
  isValid: boolean;
  message?: string;
  errors?: string[];
}

/**
 * Validate email address (RFC 5322 compliant)
 *
 * @param email - Email address to validate
 * @returns Validation result with isValid flag and error message
 *
 * @example
 * validateEmail('user@example.com'); // { isValid: true }
 * validateEmail('invalid.email');    // { isValid: false, message: "..." }
 */
export const validateEmail = (email: string): ValidationResult => {
  if (!email) {
    return { isValid: false, message: "Email is required" };
  }

  const trimmed = email.trim().toLowerCase();

  // RFC 5322 simplified (covers 99.9% of real-world cases)
  // Format: local@domain.tld
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!emailRegex.test(trimmed)) {
    return { isValid: false, message: "Invalid email format" };
  }

  // Additional checks
  const [localPart, domain] = trimmed.split('@');

  if (localPart.length > 64) {
    return { isValid: false, message: "Email local part is too long (max 64 characters)" };
  }

  if (domain.length > 255) {
    return { isValid: false, message: "Email domain is too long (max 255 characters)" };
  }

  // Check for consecutive dots
  if (trimmed.includes('..')) {
    return { isValid: false, message: "Email cannot contain consecutive dots" };
  }

  // Check if starts/ends with dot
  if (localPart.startsWith('.') || localPart.endsWith('.')) {
    return { isValid: false, message: "Email local part cannot start or end with a dot" };
  }

  return { isValid: true };
};

/**
 * Validate email format only (lightweight, for real-time validation)
 */
export const validateEmailQuick = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
};

/* ============================================================================
   PASSWORD VALIDATION
   ============================================================================ */

/**
 * Password strength levels
 */
export enum PasswordStrength {
  WEAK = 'weak',
  FAIR = 'fair',
  GOOD = 'good',
  STRONG = 'strong',
  VERY_STRONG = 'very_strong'
}

/**
 * Password validation result with strength indicator
 */
export interface PasswordValidationResult extends ValidationResult {
  strength?: PasswordStrength;
  score?: number; // 0-100
  missingRequirements?: string[];
}

/**
 * Password strength configuration
 */
export const PASSWORD_CONFIG = {
  MIN_LENGTH: 12,
  MAX_LENGTH: 128,
  REQUIRE_UPPERCASE: true,
  REQUIRE_LOWERCASE: true,
  REQUIRE_NUMBERS: true,
  REQUIRE_SPECIAL: true,
  SPECIAL_CHARS: '!@#$%^&*()_+-=[]{}|;:,.<>?'
};

/**
 * Validate password with strength calculation
 *
 * Requirements:
 * - 12+ characters
 * - At least one uppercase letter (A-Z)
 * - At least one lowercase letter (a-z)
 * - At least one number (0-9)
 * - At least one special character (!@#$%^&*...)
 *
 * @param password - Password to validate
 * @returns Validation result with strength level and missing requirements
 *
 * @example
 * validatePassword('Test@123456');     // { isValid: true, strength: 'strong' }
 * validatePassword('weak');             // { isValid: false, message: "..." }
 */
export const validatePassword = (password: string): PasswordValidationResult => {
  const missingRequirements: string[] = [];
  let score = 0;

  if (!password) {
    return {
      isValid: false,
      message: "Password is required",
      missingRequirements: [
        'Password length (12+ characters)',
        'Uppercase letter (A-Z)',
        'Lowercase letter (a-z)',
        'Number (0-9)',
        'Special character (!@#$%^&*...)'
      ]
    };
  }

  // Check length
  if (password.length < PASSWORD_CONFIG.MIN_LENGTH) {
    missingRequirements.push(`Minimum ${PASSWORD_CONFIG.MIN_LENGTH} characters`);
  } else {
    score += 20;
  }

  if (password.length > PASSWORD_CONFIG.MAX_LENGTH) {
    return {
      isValid: false,
      message: `Password is too long (max ${PASSWORD_CONFIG.MAX_LENGTH} characters)`,
      strength: PasswordStrength.WEAK,
      score: 0
    };
  }

  // Check uppercase
  if (PASSWORD_CONFIG.REQUIRE_UPPERCASE && !/[A-Z]/.test(password)) {
    missingRequirements.push('Uppercase letter (A-Z)');
  } else {
    score += 20;
  }

  // Check lowercase
  if (PASSWORD_CONFIG.REQUIRE_LOWERCASE && !/[a-z]/.test(password)) {
    missingRequirements.push('Lowercase letter (a-z)');
  } else {
    score += 20;
  }

  // Check numbers
  if (PASSWORD_CONFIG.REQUIRE_NUMBERS && !/\d/.test(password)) {
    missingRequirements.push('Number (0-9)');
  } else {
    score += 20;
  }

  // Check special characters
  if (PASSWORD_CONFIG.REQUIRE_SPECIAL && !new RegExp(`[${PASSWORD_CONFIG.SPECIAL_CHARS.replace(/[-\\^$*+?.()|[\]{}]/g, '\\$&')}]`).test(password)) {
    missingRequirements.push('Special character (!@#$%^&*...)');
  } else {
    score += 20;
  }

  // Determine strength level based on missing requirements
  let strength: PasswordStrength;
  if (missingRequirements.length === 0) {
    strength = PasswordStrength.VERY_STRONG;
    if (password.length >= 16) score += 10;
    if (password.length >= 20) score += 10;
  } else if (missingRequirements.length === 1) {
    strength = PasswordStrength.STRONG;
  } else if (missingRequirements.length === 2) {
    strength = PasswordStrength.GOOD;
  } else if (missingRequirements.length === 3) {
    strength = PasswordStrength.FAIR;
  } else {
    strength = PasswordStrength.WEAK;
  }

  const isValid = missingRequirements.length === 0;

  if (!isValid) {
    return {
      isValid: false,
      message: `Password must contain: ${missingRequirements.join(', ')}`,
      strength,
      score: Math.min(score, 100),
      missingRequirements
    };
  }

  return {
    isValid: true,
    strength,
    score: Math.min(score, 100),
    missingRequirements: []
  };
};

/**
 * Quick password validation (length only, for simple forms)
 */
export const validatePasswordQuick = (password: string): boolean => {
  return password.length >= PASSWORD_CONFIG.MIN_LENGTH && password.length <= PASSWORD_CONFIG.MAX_LENGTH;
};

/* ============================================================================
   PHONE VALIDATION
   ============================================================================ */

/**
 * Validate phone number (international format)
 *
 * Accepts:
 * - +79991234567 (international)
 * - 79991234567 (without +)
 * - +7 (999) 123-45-67 (formatted)
 * - (999) 123-45-67 (formatted without country code)
 *
 * Pattern: ^\+?[1-9][\d]{4,15}$ (matches backend Django validator)
 *
 * @param phone - Phone number to validate
 * @returns Validation result with isValid flag and error message
 *
 * @example
 * validatePhone('+79991234567'); // { isValid: true }
 * validatePhone('(999) 123-45-67'); // { isValid: true }
 * validatePhone('123');            // { isValid: false, message: "..." }
 */
export const validatePhone = (phone: string): ValidationResult => {
  if (!phone) {
    return { isValid: false, message: "Phone number is required" };
  }

  // Remove all characters except digits and +
  const cleanPhone = phone.replace(/[^\d+]/g, '');

  // Validation pattern: country code + 4-15 digits (matches Django backend)
  const phoneRegex = /^\+?[1-9][\d]{4,15}$/;
  const isValid = phoneRegex.test(cleanPhone);

  if (!isValid) {
    return {
      isValid: false,
      message: "Phone number must be in international format (e.g., +79991234567 or +7 (999) 123-45-67)"
    };
  }

  return { isValid: true };
};

/**
 * Format phone number to human-readable format
 *
 * Supports:
 * - Russian format: +7 (999) 123-45-67
 * - International format: +XX XXXXX...
 *
 * @param phone - Raw phone number
 * @returns Formatted phone number
 *
 * @example
 * formatPhoneNumber('+79991234567'); // "+7 (999) 123-45-67"
 */
export const formatPhoneNumber = (phone: string): string => {
  if (!phone) return '';

  // Remove all characters except digits and +
  let cleaned = phone.replace(/[^\d+]/g, '');

  // Add + if missing (assume Russia)
  if (!cleaned.startsWith('+') && cleaned.length >= 10) {
    if (cleaned.startsWith('7') && cleaned.length === 11) {
      cleaned = '+' + cleaned;
    } else if (cleaned.startsWith('8') && cleaned.length === 11) {
      cleaned = '+7' + cleaned.substring(1);
    } else if (!cleaned.startsWith('8') && !cleaned.startsWith('7')) {
      // For other countries
      cleaned = '+' + cleaned;
    }
  }

  // Format Russian numbers: +7 (999) 123-45-67
  if (cleaned.startsWith('+7') && cleaned.length === 12) {
    return `${cleaned.slice(0, 2)} (${cleaned.slice(2, 5)}) ${cleaned.slice(5, 8)}-${cleaned.slice(8, 10)}-${cleaned.slice(10, 12)}`;
  }

  // Return as is for other formats
  return cleaned;
};

/**
 * Get clean phone number for backend (digits + plus sign only)
 *
 * @param phone - Formatted phone number
 * @returns Clean phone number (e.g., "+79991234567")
 */
export const getCleanPhone = (phone: string): string => {
  return phone.replace(/[^\d+]/g, '');
};

/* ============================================================================
   URL VALIDATION
   ============================================================================ */

/**
 * URL validation configuration
 */
export const URL_CONFIG = {
  ALLOWED_PROTOCOLS: ['http', 'https', 'ftp'],
  MAX_LENGTH: 2048
};

/**
 * Validate URL with protocol check
 *
 * Requirements:
 * - Valid protocol (http, https, ftp)
 * - Valid domain name
 * - Not exceeding max length
 *
 * @param url - URL to validate
 * @returns Validation result with isValid flag and error message
 *
 * @example
 * validateUrl('https://example.com');   // { isValid: true }
 * validateUrl('example.com');           // { isValid: false, message: "..." }
 * validateUrl('https://example');       // { isValid: false, message: "..." }
 */
export const validateUrl = (url: string): ValidationResult => {
  if (!url) {
    return { isValid: false, message: "URL is required" };
  }

  const trimmed = url.trim();

  if (trimmed.length > URL_CONFIG.MAX_LENGTH) {
    return { isValid: false, message: `URL is too long (max ${URL_CONFIG.MAX_LENGTH} characters)` };
  }

  try {
    const urlObj = new URL(trimmed);

    // Check protocol
    const protocol = urlObj.protocol.slice(0, -1); // Remove trailing colon
    if (!URL_CONFIG.ALLOWED_PROTOCOLS.includes(protocol)) {
      return {
        isValid: false,
        message: `Protocol must be one of: ${URL_CONFIG.ALLOWED_PROTOCOLS.join(', ')}`
      };
    }

    // Check hostname exists
    if (!urlObj.hostname) {
      return { isValid: false, message: "URL must have a valid hostname" };
    }

    // Check for valid TLD (at least one dot in hostname)
    if (!urlObj.hostname.includes('.')) {
      return { isValid: false, message: "Domain must have a valid TLD (e.g., .com)" };
    }

    return { isValid: true };
  } catch (error) {
    return {
      isValid: false,
      message: "Invalid URL format. Use format: https://example.com"
    };
  }
};

/**
 * Validate URL format only (lightweight, for real-time validation)
 */
export const validateUrlQuick = (url: string): boolean => {
  if (!url) return false;
  try {
    new URL(url.trim());
    return true;
  } catch {
    return false;
  }
};

/* ============================================================================
   DATE VALIDATION
   ============================================================================ */

/**
 * Date validation configuration
 */
export const DATE_CONFIG = {
  ALLOW_PAST: true,
  ALLOW_FUTURE: true
};

/**
 * Validate date string or Date object
 *
 * @param dateValue - Date to validate (string 'YYYY-MM-DD' or Date object)
 * @param options - Validation options
 * @returns Validation result with isValid flag and error message
 *
 * @example
 * validateDate('2024-12-25');           // { isValid: true }
 * validateDate('2024-12-25', { mustBeFuture: true }); // Check if future
 * validateDate('invalid-date');         // { isValid: false, message: "..." }
 */
export const validateDate = (
  dateValue: string | Date,
  options?: {
    mustBeFuture?: boolean;
    mustBePast?: boolean;
    minDate?: Date;
    maxDate?: Date;
  }
): ValidationResult => {
  if (!dateValue) {
    return { isValid: false, message: "Date is required" };
  }

  let date: Date;
  if (dateValue instanceof Date) {
    date = dateValue;
  } else if (typeof dateValue === 'string') {
    date = new Date(dateValue);
  } else {
    return { isValid: false, message: "Invalid date format" };
  }

  if (isNaN(date.getTime())) {
    return {
      isValid: false,
      message: "Invalid date. Use format: YYYY-MM-DD"
    };
  }

  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const checkDate = new Date(date);
  checkDate.setHours(0, 0, 0, 0);

  if (options?.mustBeFuture && checkDate <= now) {
    return { isValid: false, message: "Date must be in the future" };
  }

  if (options?.mustBePast && checkDate >= now) {
    return { isValid: false, message: "Date must be in the past" };
  }

  if (options?.minDate) {
    const minDateObj = new Date(options.minDate);
    minDateObj.setHours(0, 0, 0, 0);
    if (checkDate < minDateObj) {
      return {
        isValid: false,
        message: `Date must be after ${options.minDate.toLocaleDateString()}`
      };
    }
  }

  if (options?.maxDate) {
    const maxDateObj = new Date(options.maxDate);
    maxDateObj.setHours(0, 0, 0, 0);
    if (checkDate > maxDateObj) {
      return {
        isValid: false,
        message: `Date must be before ${options.maxDate.toLocaleDateString()}`
      };
    }
  }

  return { isValid: true };
};

/**
 * Validate date range (start date and end date)
 *
 * @param startDate - Start date
 * @param endDate - End date
 * @returns Validation result with isValid flag and error message
 *
 * @example
 * validateDateRange('2024-01-01', '2024-12-31'); // { isValid: true }
 * validateDateRange('2024-12-31', '2024-01-01'); // { isValid: false, message: "..." }
 */
export const validateDateRange = (
  startDate: string | Date,
  endDate: string | Date
): ValidationResult => {
  const startValidation = validateDate(startDate);
  if (!startValidation.isValid) {
    return { isValid: false, message: `Start date: ${startValidation.message}` };
  }

  const endValidation = validateDate(endDate);
  if (!endValidation.isValid) {
    return { isValid: false, message: `End date: ${endValidation.message}` };
  }

  const start = new Date(startDate);
  const end = new Date(endDate);

  if (start > end) {
    return {
      isValid: false,
      message: "Start date must be before end date"
    };
  }

  return { isValid: true };
};

/* ============================================================================
   FIELD VALIDATORS
   ============================================================================ */

/**
 * Validate field length (min and max)
 *
 * @param value - Field value
 * @param minLength - Minimum length
 * @param maxLength - Maximum length
 * @returns Validation result
 *
 * @example
 * validateFieldLength('John', 2, 50);  // { isValid: true }
 * validateFieldLength('J', 2, 50);     // { isValid: false, message: "..." }
 */
export const validateFieldLength = (
  value: string,
  minLength: number,
  maxLength: number
): ValidationResult => {
  if (!value) {
    return { isValid: false, message: "This field is required" };
  }

  if (value.length < minLength) {
    return {
      isValid: false,
      message: `Minimum length is ${minLength} characters`
    };
  }

  if (value.length > maxLength) {
    return {
      isValid: false,
      message: `Maximum length is ${maxLength} characters`
    };
  }

  return { isValid: true };
};

/**
 * Validate that two fields match (e.g., password confirmation)
 *
 * @param value1 - First value
 * @param value2 - Second value
 * @param fieldName - Field name for error message
 * @returns Validation result
 *
 * @example
 * validateFieldMatch('password', 'password', 'passwords'); // { isValid: true }
 * validateFieldMatch('password', 'different', 'passwords'); // { isValid: false }
 */
export const validateFieldMatch = (
  value1: string | number,
  value2: string | number,
  fieldName: string = 'Fields'
): ValidationResult => {
  if (value1 !== value2) {
    return {
      isValid: false,
      message: `${fieldName} do not match`
    };
  }

  return { isValid: true };
};

/**
 * Validate field is not empty
 *
 * @param value - Field value
 * @param fieldName - Field name for error message
 * @returns Validation result
 */
export const validateRequired = (
  value: any,
  fieldName: string = 'This field'
): ValidationResult => {
  if (!value || (typeof value === 'string' && value.trim() === '')) {
    return {
      isValid: false,
      message: `${fieldName} is required`
    };
  }

  return { isValid: true };
};

/**
 * Validate field against custom regex pattern
 *
 * @param value - Field value
 * @param pattern - Regex pattern
 * @param errorMessage - Error message if validation fails
 * @returns Validation result
 *
 * @example
 * validateCustomPattern('user123', /^[a-z0-9]+$/, 'Username can only contain lowercase letters and numbers');
 */
export const validateCustomPattern = (
  value: string,
  pattern: RegExp,
  errorMessage: string = 'Invalid format'
): ValidationResult => {
  if (!value) {
    return { isValid: false, message: 'This field is required' };
  }

  if (!pattern.test(value)) {
    return { isValid: false, message: errorMessage };
  }

  return { isValid: true };
};

/**
 * Validate field with custom function
 *
 * @param value - Field value
 * @param validatorFn - Custom validation function
 * @param errorMessage - Error message if validation fails
 * @returns Validation result
 *
 * @example
 * const isEven = (n) => Number(n) % 2 === 0;
 * validateCustomFunction('4', isEven, 'Number must be even');
 */
export const validateCustomFunction = (
  value: any,
  validatorFn: (value: any) => boolean,
  errorMessage: string = 'Invalid value'
): ValidationResult => {
  if (!validatorFn(value)) {
    return { isValid: false, message: errorMessage };
  }

  return { isValid: true };
};

/**
 * Async validation support (e.g., check if email exists)
 *
 * @param value - Value to validate
 * @param asyncValidatorFn - Async validation function
 * @returns Promise with validation result
 *
 * @example
 * const checkEmailExists = async (email) => {
 *   const response = await fetch(`/api/check-email?email=${email}`);
 *   return response.ok;
 * };
 * validateAsync('user@example.com', checkEmailExists, 'Email already exists');
 */
export const validateAsync = async (
  value: any,
  asyncValidatorFn: (value: any) => Promise<boolean>,
  errorMessage: string = 'Validation failed'
): Promise<ValidationResult> => {
  try {
    const isValid = await asyncValidatorFn(value);
    if (!isValid) {
      return { isValid: false, message: errorMessage };
    }
    return { isValid: true };
  } catch (error) {
    return {
      isValid: false,
      message: `Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`
    };
  }
};

/* ============================================================================
   NAME VALIDATION
   ============================================================================ */

/**
 * Validate name field
 *
 * Requirements:
 * - 2-50 characters
 * - Only letters, spaces, and hyphens
 * - Supports Latin and Cyrillic characters
 *
 * @param name - Name to validate
 * @returns Validation result
 *
 * @example
 * validateName('John Doe');        // { isValid: true }
 * validateName('Иван Петров');    // { isValid: true }
 * validateName('J');               // { isValid: false, message: "..." }
 */
export const validateName = (name: string): ValidationResult => {
  if (!name) {
    return { isValid: false, message: "Name is required" };
  }

  if (name.length < 2) {
    return { isValid: false, message: "Name must be at least 2 characters" };
  }

  if (name.length > 50) {
    return { isValid: false, message: "Name cannot exceed 50 characters" };
  }

  // Allow: Latin, Cyrillic, spaces, hyphens
  const nameRegex = /^[а-яА-ЯёЁa-zA-Z\s\-]+$/;
  if (!nameRegex.test(name)) {
    return {
      isValid: false,
      message: "Name can only contain letters, spaces, and hyphens"
    };
  }

  return { isValid: true };
};

/* ============================================================================
   ERROR MESSAGE UTILITIES
   ============================================================================ */

/**
 * Extract and translate error messages from various sources
 *
 * @param error - Error object
 * @returns Translated error message
 *
 * @example
 * getErrorMessage(new Error('User already exists')); // "User already exists"
 */
export const getErrorMessage = (error: any): string => {
  if (!error) return "Unknown error";

  const message = error.message || error.toString();

  // Common error patterns
  if (message.includes('Invalid login credentials')) {
    return "Invalid email or password";
  }

  if (message.includes('Email not confirmed')) {
    return "Please verify your email before logging in";
  }

  if (message.includes('User already registered') || message.includes('already exists')) {
    return "User with this email already exists";
  }

  if (message.includes('Invalid email')) {
    return "Invalid email address";
  }

  if (message.includes('Password should be at least') || message.includes('too short')) {
    return "Password is too short";
  }

  if (message.includes('Signup is disabled')) {
    return "Registration is temporarily disabled";
  }

  if (message.includes('Email rate limit') || message.includes('Too many requests')) {
    return "Too many attempts. Please try again later";
  }

  if (message.includes('Password rate limit')) {
    return "Too many login attempts. Please try again later";
  }

  return message;
};
