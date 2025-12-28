/**
 * Message validation constants and utilities
 */

export const MAX_MESSAGE_LENGTH = 10000;
export const MIN_MESSAGE_LENGTH = 1;

export interface ValidationResult {
  isValid: boolean;
  error: string | null;
}

/**
 * Validates message content before sending
 * @param content - Message content to validate
 * @param hasFile - Whether a file is attached
 * @returns Validation result with error message if invalid
 */
export const validateMessage = (content: string, hasFile: boolean = false): ValidationResult => {
  const trimmed = content.trim();

  if (trimmed.length < MIN_MESSAGE_LENGTH && !hasFile) {
    return {
      isValid: false,
      error: 'Сообщение не может быть пустым',
    };
  }

  if (trimmed.length > MAX_MESSAGE_LENGTH) {
    return {
      isValid: false,
      error: `Сообщение слишком длинное (максимум ${MAX_MESSAGE_LENGTH} символов)`,
    };
  }

  return {
    isValid: true,
    error: null,
  };
};
