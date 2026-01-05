/**
 * Form Validation Library - Real-world Usage Examples
 *
 * This file contains practical examples of integrating the validation library
 * with React Hook Form and component state management.
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  validateEmail,
  validatePassword,
  validatePhone,
  validateUrl,
  validateDate,
  validateName,
  validateFieldMatch,
  validateAsync,
  validateFieldLength,
  formatPhoneNumber,
} from './validation';

/* ============================================================================
   EXAMPLE 1: Simple Registration Form with React Hook Form
   ============================================================================ */

/**
 * Basic registration form using React Hook Form validators
 */
export function SimpleRegistrationForm() {
  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const password = watch('password');

  const onSubmit = async (data: any) => {
    console.log('Form data:', data);
    // Submit to API
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="form-group">
        <label>Email</label>
        <input
          {...register('email', {
            validate: (value) => {
              const result = validateEmail(value);
              return result.isValid || result.message;
            }
          })}
          type="email"
          placeholder="user@example.com"
          autoComplete="username"
        />
        {errors.email && <span className="error">{errors.email.message}</span>}
      </div>

      <div className="form-group">
        <label>Password</label>
        <input
          {...register('password', {
            validate: (value) => {
              const result = validatePassword(value);
              return result.isValid || result.message;
            }
          })}
          type="password"
          placeholder="SecurePass123!"
          autoComplete="new-password"
        />
        {errors.password && <span className="error">{errors.password.message}</span>}
      </div>

      <div className="form-group">
        <label>Confirm Password</label>
        <input
          {...register('passwordConfirm', {
            validate: (value) => {
              const result = validateFieldMatch(value, password, 'Passwords');
              return result.isValid || result.message;
            }
          })}
          type="password"
          placeholder="SecurePass123!"
          autoComplete="new-password"
        />
        {errors.passwordConfirm && <span className="error">{errors.passwordConfirm.message}</span>}
      </div>

      <button type="submit">Register</button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 2: Advanced Registration with Zod Schema
   ============================================================================ */

/**
 * Registration form using Zod for schema validation
 * Combines Zod's power with custom validators
 */

const registrationSchema = z
  .object({
    name: z.string().refine(
      (name) => validateName(name).isValid,
      'Invalid name format'
    ),
    email: z.string().email().refine(
      (email) => validateEmail(email).isValid,
      'Invalid email format'
    ),
    phone: z.string().refine(
      (phone) => validatePhone(phone).isValid,
      'Invalid phone number'
    ),
    password: z.string().refine(
      (password) => validatePassword(password).isValid,
      'Password does not meet requirements'
    ),
    passwordConfirm: z.string(),
  })
  .refine(
    (data) => data.password === data.passwordConfirm,
    {
      message: "Passwords don't match",
      path: ['passwordConfirm'],
    }
  );

type RegistrationFormData = z.infer<typeof registrationSchema>;

export function AdvancedRegistrationForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<RegistrationFormData>({
    resolver: zodResolver(registrationSchema),
  });

  const onSubmit = async (data: RegistrationFormData) => {
    console.log('Valid data:', data);
    // Submit to API
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="form-group">
        <label>Full Name</label>
        <input
          {...register('name')}
          placeholder="John Doe"
        />
        {errors.name && <span className="error">{errors.name.message}</span>}
      </div>

      <div className="form-group">
        <label>Email</label>
        <input
          {...register('email')}
          type="email"
          placeholder="john@example.com"
          autoComplete="username"
        />
        {errors.email && <span className="error">{errors.email.message}</span>}
      </div>

      <div className="form-group">
        <label>Phone</label>
        <input
          {...register('phone')}
          placeholder="+79991234567"
          autoComplete="tel"
        />
        {errors.phone && <span className="error">{errors.phone.message}</span>}
      </div>

      <div className="form-group">
        <label>Password</label>
        <input
          {...register('password')}
          type="password"
          placeholder="SecurePass123!"
          autoComplete="new-password"
        />
        {errors.password && <span className="error">{errors.password.message}</span>}
      </div>

      <div className="form-group">
        <label>Confirm Password</label>
        <input
          {...register('passwordConfirm')}
          type="password"
          placeholder="SecurePass123!"
          autoComplete="new-password"
        />
        {errors.passwordConfirm && <span className="error">{errors.passwordConfirm.message}</span>}
      </div>

      <button type="submit">Create Account</button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 3: Password Input with Real-time Strength Indicator
   ============================================================================ */

/**
 * Password input with live strength indicator
 * Shows requirements and strength level as user types
 */

export function PasswordInput() {
  const [password, setPassword] = useState('');
  const { register, handleSubmit, formState: { errors } } = useForm();

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPassword(e.target.value);
  };

  const result = password ? validatePassword(password) : null;

  return (
    <form onSubmit={handleSubmit((data) => console.log(data))}>
      <div className="form-group">
        <label>Password</label>
        <input
          {...register('password', {
            validate: (value) => {
              const res = validatePassword(value);
              return res.isValid || res.message;
            }
          })}
          onChange={handlePasswordChange}
          type="password"
          placeholder="Enter strong password"
          autoComplete="new-password"
        />
        {errors.password && <span className="error">{errors.password.message}</span>}

        {result && (
          <div className="password-strength">
            <div className={`strength-bar strength-${result.strength}`}>
              <div className="fill" style={{ width: `${result.score}%` }}></div>
            </div>
            <div className="strength-label">
              Strength: <strong>{result.strength || 'weak'}</strong>
            </div>

            {result.missingRequirements && result.missingRequirements.length > 0 && (
              <ul className="requirements">
                <li className={result.missingRequirements.some(r => r.includes('characters')) ? 'missing' : 'met'}>
                  ✓ 12+ characters
                </li>
                <li className={result.missingRequirements.some(r => r.includes('Uppercase')) ? 'missing' : 'met'}>
                  ✓ Uppercase letter
                </li>
                <li className={result.missingRequirements.some(r => r.includes('Lowercase')) ? 'missing' : 'met'}>
                  ✓ Lowercase letter
                </li>
                <li className={result.missingRequirements.some(r => r.includes('Number')) ? 'missing' : 'met'}>
                  ✓ Number
                </li>
                <li className={result.missingRequirements.some(r => r.includes('Special')) ? 'missing' : 'met'}>
                  ✓ Special character
                </li>
              </ul>
            )}
          </div>
        )}
      </div>

      <button type="submit" disabled={!result?.isValid}>
        Submit
      </button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 4: Profile Form with Multiple Validators
   ============================================================================ */

/**
 * User profile update form demonstrating multiple validator types
 */

export function ProfileForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();

  const onSubmit = (data: any) => {
    console.log('Profile data:', data);
    // Submit to API
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <h2>Update Profile</h2>

      <div className="form-group">
        <label>First Name</label>
        <input
          {...register('firstName', {
            validate: (value) => {
              const result = validateName(value);
              return result.isValid || result.message;
            }
          })}
          placeholder="John"
        />
        {errors.firstName && <span className="error">{errors.firstName.message}</span>}
      </div>

      <div className="form-group">
        <label>Email</label>
        <input
          {...register('email', {
            validate: (value) => {
              const result = validateEmail(value);
              return result.isValid || result.message;
            }
          })}
          type="email"
          placeholder="john@example.com"
        />
        {errors.email && <span className="error">{errors.email.message}</span>}
      </div>

      <div className="form-group">
        <label>Phone</label>
        <input
          {...register('phone', {
            validate: (value) => {
              if (!value) return true; // optional
              const result = validatePhone(value);
              return result.isValid || result.message;
            }
          })}
          placeholder="+7 (999) 123-45-67"
        />
        {errors.phone && <span className="error">{errors.phone.message}</span>}
      </div>

      <div className="form-group">
        <label>Website (optional)</label>
        <input
          {...register('website', {
            validate: (value) => {
              if (!value) return true; // optional
              const result = validateUrl(value);
              return result.isValid || result.message;
            }
          })}
          type="url"
          placeholder="https://example.com"
        />
        {errors.website && <span className="error">{errors.website.message}</span>}
      </div>

      <div className="form-group">
        <label>Birth Date</label>
        <input
          {...register('birthDate', {
            validate: (value) => {
              if (!value) return true; // optional
              const result = validateDate(value, { mustBePast: true });
              return result.isValid || result.message;
            }
          })}
          type="date"
        />
        {errors.birthDate && <span className="error">{errors.birthDate.message}</span>}
      </div>

      <button type="submit">Update Profile</button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 5: Async Email Uniqueness Check
   ============================================================================ */

/**
 * Form with async validation for email uniqueness
 * Checks if email is already registered via API
 */

export function EmailUnicenessForm() {
  const [checking, setChecking] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm();

  const checkEmailAvailable = async (email: string): Promise<boolean> => {
    try {
      setChecking(true);
      const response = await fetch(`/api/check-email?email=${email}`);
      return response.ok; // true if email is available
    } catch (error) {
      return false; // assume taken on error
    } finally {
      setChecking(false);
    }
  };

  const validateEmailField = async (email: string) => {
    // First check format
    const formatResult = validateEmail(email);
    if (!formatResult.isValid) {
      return formatResult.message;
    }

    // Then check availability
    setChecking(true);
    const availabilityResult = await validateAsync(
      email,
      checkEmailAvailable,
      'Email already registered'
    );
    setChecking(false);

    return availabilityResult.isValid || availabilityResult.message;
  };

  const onSubmit = (data: any) => {
    console.log('Validated data:', data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="form-group">
        <label>Email</label>
        <input
          {...register('email', {
            validate: validateEmailField
          })}
          type="email"
          placeholder="user@example.com"
          autoComplete="username"
        />
        {errors.email && (
          <span className="error">
            {errors.email.message}
            {checking && ' (checking...)'}
          </span>
        )}
      </div>

      <button type="submit" disabled={checking}>
        {checking ? 'Checking email...' : 'Register'}
      </button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 6: Phone Input with Formatting
   ============================================================================ */

/**
 * Phone input with automatic formatting display
 */

export function PhoneInput() {
  const [phone, setPhone] = useState('');
  const { register, handleSubmit, formState: { errors } } = useForm();

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPhone(e.target.value);
  };

  const displayPhone = formatPhoneNumber(phone);

  return (
    <form onSubmit={handleSubmit((data) => console.log(data))}>
      <div className="form-group">
        <label>Phone Number</label>
        <input
          {...register('phone', {
            validate: (value) => {
              const result = validatePhone(value);
              return result.isValid || result.message;
            }
          })}
          onChange={handlePhoneChange}
          placeholder="+7 (999) 123-45-67"
          value={phone}
        />
        {errors.phone && <span className="error">{errors.phone.message}</span>}

        {phone && (
          <div className="phone-preview">
            <small>Formatted: <strong>{displayPhone}</strong></small>
          </div>
        )}
      </div>

      <button type="submit">Submit</button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 7: Form Field with Custom Validation
   ============================================================================ */

/**
 * Custom username validation with regex pattern
 */

import { validateCustomPattern } from './validation';

export function UsernameInput() {
  const { register, handleSubmit, formState: { errors } } = useForm();

  const onSubmit = (data: any) => {
    console.log('Username:', data.username);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="form-group">
        <label>Username</label>
        <input
          {...register('username', {
            validate: (value) => {
              const result = validateCustomPattern(
                value,
                /^[a-z0-9_]{3,20}$/,
                'Username must be 3-20 characters (lowercase, numbers, underscore only)'
              );
              return result.isValid || result.message;
            }
          })}
          placeholder="john_doe123"
        />
        {errors.username && <span className="error">{errors.username.message}</span>}
        <small>3-20 characters: lowercase letters, numbers, underscore</small>
      </div>

      <button type="submit">Create Username</button>
    </form>
  );
}

/* ============================================================================
   EXAMPLE 8: Validation State Management Hook
   ============================================================================ */

/**
 * Custom hook for managing validation state across multiple fields
 */

interface FieldValidation {
  value: string;
  error: string;
  isValid: boolean;
}

export function useFormValidation(initialValues: Record<string, string>) {
  const [fields, setFields] = useState<Record<string, FieldValidation>>(
    Object.entries(initialValues).reduce((acc, [key, value]) => ({
      ...acc,
      [key]: { value, error: '', isValid: false }
    }), {})
  );

  const updateField = (fieldName: string, value: string, validator: (v: string) => any) => {
    const result = validator(value);
    setFields((prev) => ({
      ...prev,
      [fieldName]: {
        value,
        error: result.isValid ? '' : result.message,
        isValid: result.isValid
      }
    }));
  };

  const isFormValid = Object.values(fields).every((field) => field.isValid);

  return { fields, updateField, isFormValid };
}

/**
 * Component using the validation hook
 */

export function FormWithValidationHook() {
  const { fields, updateField, isFormValid } = useFormValidation({
    email: '',
    password: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isFormValid) {
      console.log('Form data:', {
        email: fields.email.value,
        password: fields.password.value
      });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Email</label>
        <input
          value={fields.email.value}
          onChange={(e) => updateField('email', e.target.value, validateEmail)}
          placeholder="email@example.com"
          className={fields.email.error ? 'error' : 'valid'}
          autoComplete="username"
        />
        {fields.email.error && <span className="error">{fields.email.error}</span>}
      </div>

      <div className="form-group">
        <label>Password</label>
        <input
          type="password"
          value={fields.password.value}
          onChange={(e) => updateField('password', e.target.value, validatePassword)}
          placeholder="SecurePass123!"
          className={fields.password.error ? 'error' : 'valid'}
          autoComplete="new-password"
        />
        {fields.password.error && <span className="error">{fields.password.error}</span>}
      </div>

      <button type="submit" disabled={!isFormValid}>
        {isFormValid ? 'Submit' : 'Fill in all fields'}
      </button>
    </form>
  );
}
