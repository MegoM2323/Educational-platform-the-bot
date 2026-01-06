import { ApiResponse } from './unifiedClient';
import { logger } from '../../utils/logger';

// Error handling types
export interface ApiErrorResponse<T = any> {
  success: false;
  error: string;
  details?: Record<string, any>;
  data?: T;
}

export interface ApiSuccessResponse<T = any> {
  success: true;
  data: T;
}

export type ApiResult<T = any> = ApiSuccessResponse<T> | ApiErrorResponse<T>;

// HTTP status code to user-friendly message mapping
const HTTP_ERROR_MESSAGES: Record<number, string> = {
  400: 'Проверьте введенные данные',
  401: 'Ошибка аутентификации. Пожалуйста, войдите',
  403: 'Доступ запрещен. У вас нет прав на это действие',
  404: 'Запрашиваемый ресурс не найден',
  409: 'Конфликт: ресурс уже существует или невозможно выполнить операцию',
  429: 'Слишком много запросов. Попробуйте позже',
  500: 'Ошибка сервера. Попробуйте позже',
  502: 'Сервер недоступен. Попробуйте позже',
  503: 'Сервис временно недоступен. Попробуйте позже',
};

// Helper: Check if response is an error
export function isError<T = any>(response: ApiResponse<T> | ApiResult<T>): response is ApiErrorResponse<T> {
  return !response.success;
}

// Helper: Check if response is successful
export function isSuccess<T = any>(response: ApiResponse<T> | ApiResult<T>): response is ApiSuccessResponse<T> {
  return response.success;
}

// Helper: Extract error message from response
function extractErrorMessage(
  error: any,
  statusCode?: number
): { message: string; details?: Record<string, any> } {
  // If it's an API error with details
  if (error?.error && typeof error.error === 'string') {
    return {
      message: error.error,
      details: error.details
    };
  }

  // If it's a response-like object with error field
  if (typeof error === 'object' && error.error && typeof error.error === 'string') {
    return {
      message: error.error,
      details: error.details
    };
  }

  // Django REST Framework validation errors
  if (typeof error === 'object' && error !== null) {
    const fieldErrors = Object.entries(error)
      .filter(([key]) => key !== 'detail' && key !== 'error' && key !== 'non_field_errors')
      .map(([field, messages]: [string, any]) => {
        const msgs = Array.isArray(messages) ? messages.join(', ') : String(messages);
        return `${field}: ${msgs}`;
      });

    if (fieldErrors.length > 0) {
      return {
        message: fieldErrors.join('; '),
        details: error
      };
    }

    // Detail field from Django
    if (error.detail && typeof error.detail === 'string') {
      return {
        message: error.detail,
        details: error
      };
    }

    // Generic error message
    if (error.message && typeof error.message === 'string') {
      return {
        message: error.message,
        details: error
      };
    }
  }

  // Fallback to HTTP status code message
  if (statusCode && HTTP_ERROR_MESSAGES[statusCode]) {
    return {
      message: HTTP_ERROR_MESSAGES[statusCode]
    };
  }

  // Default error message
  return {
    message: 'Произошла ошибка при выполнении операции'
  };
}

// Main error handler
export function handleError(
  error: any,
  context?: {
    operation?: string;
    statusCode?: number;
  }
): ApiErrorResponse {
  const operation = context?.operation || 'API operation';
  const statusCode = context?.statusCode;

  const { message, details } = extractErrorMessage(error, statusCode);

  logger.error(`[AdminAPI] ${operation} failed:`, {
    statusCode,
    message,
    error,
    details
  });

  return {
    success: false,
    error: message,
    details
  };
}

// Safe wrapper for API calls with comprehensive error handling
export async function safeApiCall<T>(
  operation: string,
  apiCall: () => Promise<ApiResponse<T>>
): Promise<ApiResult<T>> {
  try {
    const response = await apiCall();

    if (!response.success) {
      return handleError(response, { operation }) as ApiErrorResponse<T>;
    }

    return {
      success: true,
      data: response.data as T
    };
  } catch (error) {
    return handleError(error, { operation }) as ApiErrorResponse<T>;
  }
}

// Specific error handlers for common cases

export function handleValidationError(
  error: Record<string, any>,
  fieldName?: string
): ApiErrorResponse {
  const messages = [];

  if (fieldName && error[fieldName]) {
    const fieldErrors = Array.isArray(error[fieldName]) ? error[fieldName] : [error[fieldName]];
    messages.push(`${fieldName}: ${fieldErrors.join(', ')}`);
  } else {
    for (const [key, value] of Object.entries(error)) {
      if (key !== 'detail' && key !== 'error') {
        const msgs = Array.isArray(value) ? value.join(', ') : String(value);
        messages.push(`${key}: ${msgs}`);
      }
    }
  }

  const message = messages.join('; ') || 'Ошибка валидации данных';

  logger.error('[AdminAPI] Validation error:', { error, message });

  return {
    success: false,
    error: message,
    details: error
  };
}

export function handleConflictError(
  resource: string,
  field?: string
): ApiErrorResponse {
  const message = field
    ? `${resource} с этим значением ${field} уже существует`
    : `${resource} уже существует`;

  logger.error('[AdminAPI] Conflict error:', { resource, field, message });

  return {
    success: false,
    error: message
  };
}

export function handleNotFoundError(
  resource: string,
  id?: string | number
): ApiErrorResponse {
  const message = id
    ? `${resource} с ID ${id} не найден`
    : `${resource} не найден`;

  logger.error('[AdminAPI] Not found error:', { resource, id, message });

  return {
    success: false,
    error: message
  };
}

export function handleAuthError(reason?: string): ApiErrorResponse {
  const message = reason || 'Ошибка аутентификации. Пожалуйста, войдите';

  logger.error('[AdminAPI] Authentication error:', { reason, message });

  return {
    success: false,
    error: message
  };
}

export function handleNetworkError(): ApiErrorResponse {
  const message = 'Ошибка сети. Проверьте подключение к интернету';

  logger.error('[AdminAPI] Network error');

  return {
    success: false,
    error: message
  };
}
