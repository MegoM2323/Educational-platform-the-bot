/**
 * Response Normalizer - utilities for handling API responses
 */

export interface NormalizedResponse {
  success: boolean;
  data: any;
  error?: string;
}

/**
 * Normalize API response to standard format
 * Handles various response formats from Django REST Framework
 */
export function normalizeResponse(response: any): NormalizedResponse {
  // If response already has success field, return as is
  if (typeof response === 'object' && 'success' in response) {
    return {
      success: response.success,
      data: response.data || response,
      error: response.error,
    };
  }

  // If it's an array, wrap in success
  if (Array.isArray(response)) {
    return {
      success: true,
      data: response,
    };
  }

  // If it's an object, treat as success
  if (typeof response === 'object' && response !== null) {
    return {
      success: true,
      data: response,
    };
  }

  // Default
  return {
    success: false,
    data: response,
    error: 'Unknown response format',
  };
}

/**
 * Validate if response data is valid
 */
export function validateResponseData(data: any): boolean {
  if (data === null || data === undefined) {
    return false;
  }
  return true;
}

/**
 * Extract error message from response
 */
export function extractErrorMessage(response: any): string {
  if (typeof response === 'string') {
    return response;
  }

  if (typeof response === 'object' && response !== null) {
    if (response.detail) return response.detail;
    if (response.error) return response.error;
    if (response.message) return response.message;
    if (response.msg) return response.msg;
  }

  return 'Unknown error occurred';
}

/**
 * Check if response indicates an error
 */
export function isResponseError(response: any): boolean {
  if (!response) return true;

  if (typeof response === 'object') {
    if (response.success === false) return true;
    if (response.error) return true;
    if (response.detail && response.status >= 400) return true;
  }

  return false;
}
