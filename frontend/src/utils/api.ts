/**
 * Enhanced API Client Utility
 * Provides request/response interceptors, retry logic, timeout handling, request cancellation,
 * error normalization, CSRF protection, token refresh, and caching capabilities.
 *
 * Features:
 * - Request/Response Interceptors
 * - Automatic retry with exponential backoff
 * - Timeout handling (30s default)
 * - Request cancellation and deduplication
 * - Error normalization and handling
 * - Token refresh mechanism
 * - Cookie handling and CSRF protection
 * - Request deduplication
 * - Cache invalidation
 * - Debug mode logging
 */

import { logger } from './logger';
import { retryService, type RetryConfig } from '@/services/retryService';
import { errorHandlingService } from '@/services/errorHandlingService';
import { errorLoggingService } from '@/services/errorLoggingService';
import { cacheService } from '@/services/cacheService';
import { tokenStorage } from '@/services/tokenStorage';

let authServiceInstance: any = null;
let navigationInstance: any = null;

export function setAuthServiceAndNavigation(authService: any, navigate: any) {
  authServiceInstance = authService;
  navigationInstance = navigate;
}

// Types
export interface ApiClientConfig {
  baseURL: string;
  timeout: number;
  retryConfig?: Partial<RetryConfig>;
  debugMode?: boolean;
  interceptors?: {
    request?: ApiInterceptor[];
    response?: ApiInterceptor[];
  };
}

export interface ApiRequest {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD';
  url: string;
  data?: any;
  headers?: Record<string, string>;
  params?: Record<string, any>;
  timeout?: number;
  signal?: AbortSignal;
  skipRetry?: boolean;
  cache?: {
    enabled: boolean;
    ttl?: number;
    key?: string;
  };
}

export interface ApiResponse<T = any> {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: T;
  timestamp: number;
  duration: number;
}

export interface ApiError extends Error {
  status?: number;
  statusText?: string;
  data?: any;
  originalError?: Error;
  retryCount?: number;
}

export interface ApiInterceptor {
  (config: ApiRequest): ApiRequest | Promise<ApiRequest>;
}

export interface ResponseInterceptor {
  (response: ApiResponse): ApiResponse | Promise<ApiResponse>;
}

/**
 * Request deduplication tracker
 * Prevents duplicate concurrent requests for the same resource
 */
class RequestDeduplicator {
  private pendingRequests: Map<string, Promise<any>> = new Map();

  /**
   * Get or create a request promise
   */
  getOrCreate<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    const existing = this.pendingRequests.get(key);
    if (existing) {
      logger.debug('[RequestDeduplicator] Reusing pending request:', { key });
      return existing;
    }

    const promise = requestFn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  /**
   * Clear all pending requests
   */
  clear(): void {
    this.pendingRequests.clear();
    logger.debug('[RequestDeduplicator] Cleared all pending requests');
  }

  /**
   * Get pending requests count
   */
  getPendingCount(): number {
    return this.pendingRequests.size;
  }
}

/**
 * CSRF Token Manager
 * Handles CSRF token extraction and injection
 */
class CsrfTokenManager {
  private csrfToken: string | null = null;
  private lastRefreshTime: number = 0;
  private readonly REFRESH_INTERVAL = 60 * 60 * 1000; // 1 hour

  /**
   * Get CSRF token from DOM or storage
   */
  getToken(): string | null {
    // Check if token needs refresh
    if (this.shouldRefreshToken()) {
      this.csrfToken = this.extractTokenFromDOM();
      this.lastRefreshTime = Date.now();
    }

    if (!this.csrfToken) {
      this.csrfToken = this.extractTokenFromDOM();
    }

    return this.csrfToken;
  }

  /**
   * Set CSRF token manually
   */
  setToken(token: string): void {
    this.csrfToken = token;
    this.lastRefreshTime = Date.now();
    logger.debug('[CsrfTokenManager] Token set manually');
  }

  /**
   * Extract CSRF token from DOM
   */
  private extractTokenFromDOM(): string | null {
    if (typeof document === 'undefined') return null;

    // Try meta tag (Django default)
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      const token = metaTag.getAttribute('content');
      if (token) {
        logger.debug('[CsrfTokenManager] Extracted token from meta tag');
        return token;
      }
    }

    // Try cookie
    const cookieToken = this.extractTokenFromCookie();
    if (cookieToken) {
      logger.debug('[CsrfTokenManager] Extracted token from cookie');
      return cookieToken;
    }

    logger.warn('[CsrfTokenManager] No CSRF token found');
    return null;
  }

  /**
   * Extract CSRF token from cookies
   */
  private extractTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;

    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken' || name === 'XSRF-TOKEN') {
        return decodeURIComponent(value);
      }
    }

    return null;
  }

  /**
   * Check if token needs refresh
   */
  private shouldRefreshToken(): boolean {
    return Date.now() - this.lastRefreshTime > this.REFRESH_INTERVAL;
  }

  /**
   * Clear token
   */
  clear(): void {
    this.csrfToken = null;
    logger.debug('[CsrfTokenManager] Token cleared');
  }
}

/**
 * Enhanced API Client
 * Main class for API communication with interceptors, retry logic, and caching
 */
export class ApiClient {
  private config: ApiClientConfig;
  private deduplicator: RequestDeduplicator;
  private csrfTokenManager: CsrfTokenManager;
  private requestInterceptors: ApiInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private activeRequests: Map<string, AbortController> = new Map();

  constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 30000, // 30 seconds default
      ...config,
    };

    this.deduplicator = new RequestDeduplicator();
    this.csrfTokenManager = new CsrfTokenManager();

    // Register built-in interceptors
    this.registerBuiltInInterceptors();

    // Register custom interceptors
    if (config.interceptors?.request) {
      this.requestInterceptors.push(...config.interceptors.request);
    }
    if (config.interceptors?.response) {
      this.responseInterceptors.push(...config.interceptors.response);
    }

    logger.info('[ApiClient] Initialized with config:', {
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      debugMode: this.config.debugMode,
    });
  }

  /**
   * Register built-in request interceptors
   */
  private registerBuiltInInterceptors(): void {
    // Add token and CSRF interceptor
    this.requestInterceptors.unshift(async (config: ApiRequest): Promise<ApiRequest> => {
      // Add authorization token
      const token = tokenStorage.getToken();
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Token ${token}`,
        };
        if (this.config.debugMode) {
          logger.debug('[ApiClient] Added authorization token to request');
        }
      }

      // Add CSRF token for mutation requests
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method)) {
        const csrfToken = this.csrfTokenManager.getToken();
        if (csrfToken) {
          config.headers = {
            ...config.headers,
            'X-CSRFToken': csrfToken,
          };
          if (this.config.debugMode) {
            logger.debug('[ApiClient] Added CSRF token to request');
          }
        }
      }

      // Add default headers
      config.headers = {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...config.headers,
      };

      return config;
    });

    // Add response interceptor for 401 handling
    this.responseInterceptors.unshift(async (response: ApiResponse): Promise<ApiResponse> => {
      if (response.status === 401) {
        logger.warn('[ApiClient] Received 401 Unauthorized, attempting token refresh...');

        try {
          if (authServiceInstance && authServiceInstance.refreshTokenIfNeeded) {
            const newToken = await authServiceInstance.refreshTokenIfNeeded();

            if (newToken) {
              logger.debug('[ApiClient] Token refreshed successfully after 401');
              return response;
            }
          }
        } catch (error) {
          logger.error('[ApiClient] Token refresh failed after 401:', error);
        }

        logger.warn('[ApiClient] Redirecting to login due to 401 with failed refresh');
        if (navigationInstance) {
          navigationInstance('/login');
        }
      }

      return response;
    });
  }

  /**
   * Add request interceptor
   */
  useRequestInterceptor(interceptor: ApiInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * Add response interceptor
   */
  useResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }

  /**
   * Execute all request interceptors
   */
  private async executeRequestInterceptors(config: ApiRequest): Promise<ApiRequest> {
    let modifiedConfig = { ...config };

    for (const interceptor of this.requestInterceptors) {
      modifiedConfig = await interceptor(modifiedConfig);
    }

    return modifiedConfig;
  }

  /**
   * Execute all response interceptors
   */
  private async executeResponseInterceptors(response: ApiResponse): Promise<ApiResponse> {
    let modifiedResponse = { ...response };

    for (const interceptor of this.responseInterceptors) {
      modifiedResponse = await interceptor(modifiedResponse);
    }

    return modifiedResponse;
  }

  /**
   * Make HTTP request with full feature set
   */
  async request<T = any>(config: ApiRequest): Promise<ApiResponse<T>> {
    const startTime = Date.now();
    const requestId = this.generateRequestId();

    try {
      // Execute request interceptors
      config = await this.executeRequestInterceptors(config);

      // Build full URL
      const fullUrl = this.buildUrl(config.url, config.params);

      // Generate deduplication key
      const dedupeKey = this.generateDedupeKey(config.method, fullUrl);

      if (this.config.debugMode) {
        logger.debug('[ApiClient] Making request:', {
          requestId,
          method: config.method,
          url: fullUrl,
          timeout: config.timeout || this.config.timeout,
          dedupeKey,
        });
      }

      // Check cache for GET requests
      if (config.method === 'GET' && config.cache?.enabled) {
        const cachedResponse = cacheService.get<T>(config.cache.key || dedupeKey);
        if (cachedResponse) {
          if (this.config.debugMode) {
            logger.debug('[ApiClient] Cache hit for request:', { requestId, dedupeKey });
          }
          return {
            status: 200,
            statusText: 'OK (from cache)',
            headers: { 'X-Cache': 'HIT' },
            data: cachedResponse,
            timestamp: startTime,
            duration: Date.now() - startTime,
          };
        }
      }

      // Deduplicate requests
      const response = await this.deduplicator.getOrCreate(dedupeKey, async () => {
        return this.performRequest<T>(config, requestId);
      });

      // Cache successful GET responses
      if (config.method === 'GET' && config.cache?.enabled && response.status < 400) {
        cacheService.set(config.cache.key || dedupeKey, response.data, config.cache.ttl);
        if (this.config.debugMode) {
          logger.debug('[ApiClient] Cached response:', {
            requestId,
            dedupeKey,
            ttl: config.cache.ttl,
          });
        }
      }

      // Execute response interceptors
      const finalResponse = await this.executeResponseInterceptors(response);

      if (this.config.debugMode) {
        logger.debug('[ApiClient] Request completed:', {
          requestId,
          status: finalResponse.status,
          duration: finalResponse.duration,
        });
      }

      return finalResponse;
    } catch (error) {
      const duration = Date.now() - startTime;
      const apiError = this.normalizeError(error, { requestId, duration });

      if (this.config.debugMode) {
        logger.error('[ApiClient] Request failed:', {
          requestId,
          error: apiError.message,
          status: apiError.status,
          duration,
        });
      }

      throw apiError;
    }
  }

  /**
   * Perform actual HTTP request with retry logic
   */
  private async performRequest<T = any>(
    config: ApiRequest,
    requestId: string
  ): Promise<ApiResponse<T>> {
    const startTime = Date.now();

    if (!config.skipRetry) {
      return retryService.retryApiCall(
        () => this.executeRequest<T>(config, requestId),
        `API Request ${requestId}`
      );
    }

    return this.executeRequest<T>(config, requestId);
  }

  /**
   * Execute actual fetch request with timeout
   */
  private async executeRequest<T = any>(
    config: ApiRequest,
    requestId: string
  ): Promise<ApiResponse<T>> {
    const startTime = Date.now();
    const controller = new AbortController();
    const timeout = config.timeout || this.config.timeout;

    // Set timeout
    const timeoutId = setTimeout(() => {
      controller.abort();
      if (this.config.debugMode) {
        logger.warn('[ApiClient] Request timeout:', { requestId, timeout });
      }
    }, timeout);

    // Store controller for potential cancellation
    this.activeRequests.set(requestId, controller);

    try {
      const fullUrl = this.buildUrl(config.url, config.params);
      const signal = config.signal || controller.signal;

      const response = await fetch(fullUrl, {
        method: config.method,
        headers: config.headers,
        body: config.data ? JSON.stringify(config.data) : undefined,
        signal,
        credentials: 'include', // Include cookies for CSRF
      });

      clearTimeout(timeoutId);

      const data = await this.parseResponse<T>(response);
      const duration = Date.now() - startTime;

      // Handle error responses
      if (!response.ok) {
        const error = new Error(data?.message || data?.error || response.statusText) as ApiError;
        error.status = response.status;
        error.statusText = response.statusText;
        error.data = data;

        if (this.config.debugMode) {
          logger.warn('[ApiClient] Error response received:', {
            requestId,
            status: response.status,
            statusText: response.statusText,
          });
        }

        throw error;
      }

      if (this.config.debugMode) {
        logger.debug('[ApiClient] Response received:', {
          requestId,
          status: response.status,
          size: JSON.stringify(data).length,
        });
      }

      return {
        status: response.status,
        statusText: response.statusText,
        headers: this.extractHeaders(response),
        data,
        timestamp: startTime,
        duration,
      };
    } catch (error) {
      clearTimeout(timeoutId);
      this.activeRequests.delete(requestId);

      // Handle timeout
      if (error instanceof DOMException && error.name === 'AbortError') {
        const timeoutError = new Error(`Request timeout after ${timeout}ms`) as ApiError;
        timeoutError.name = 'TimeoutError';
        throw timeoutError;
      }

      throw error;
    } finally {
      clearTimeout(timeoutId);
      this.activeRequests.delete(requestId);
    }
  }

  /**
   * Parse response body
   */
  private async parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type');

    if (!contentType || !contentType.includes('application/json')) {
      return response.text() as any;
    }

    try {
      return (await response.json()) as T;
    } catch (error) {
      logger.error('[ApiClient] Failed to parse JSON response:', error);
      throw new Error('Invalid JSON response from server');
    }
  }

  /**
   * Extract headers from response
   */
  private extractHeaders(response: Response): Record<string, string> {
    const headers: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      headers[key] = value;
    });
    return headers;
  }

  /**
   * Build full URL with query parameters
   */
  private buildUrl(path: string, params?: Record<string, any>): string {
    const url = new URL(path.startsWith('http') ? path : this.config.baseURL + path);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach((v) => url.searchParams.append(key, String(v)));
          } else {
            url.searchParams.append(key, String(value));
          }
        }
      });
    }

    return url.toString();
  }

  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Generate deduplication key
   */
  private generateDedupeKey(method: string, url: string): string {
    return `${method}:${url}`;
  }

  /**
   * Normalize error to ApiError type
   */
  private normalizeError(
    error: any,
    context?: { requestId?: string; duration?: number }
  ): ApiError {
    const apiError = new Error(error?.message || 'An unknown error occurred') as ApiError;

    apiError.status = error?.status;
    apiError.statusText = error?.statusText;
    apiError.data = error?.data;
    apiError.originalError = error;

    if (context?.requestId) {
      logger.error('[ApiClient] Error in request:', {
        requestId: context.requestId,
        message: apiError.message,
        status: apiError.status,
        duration: context.duration,
      });
    }

    // Report to error handling service
    try {
      errorHandlingService.handleError(apiError, {
        operation: 'api_request',
        component: 'ApiClient',
      });
    } catch (err) {
      logger.warn('[ApiClient] Failed to report error:', err);
    }

    return apiError;
  }

  /**
   * Cancel active request
   */
  cancelRequest(requestId: string): void {
    const controller = this.activeRequests.get(requestId);
    if (controller) {
      controller.abort();
      this.activeRequests.delete(requestId);
      logger.debug('[ApiClient] Request cancelled:', { requestId });
    }
  }

  /**
   * Cancel all active requests
   */
  cancelAllRequests(): void {
    this.activeRequests.forEach((controller) => controller.abort());
    this.activeRequests.clear();
    logger.debug('[ApiClient] All requests cancelled');
  }

  /**
   * Invalidate cache
   */
  invalidateCache(pattern?: string): void {
    if (pattern) {
      // Invalidate matching cache entries
      // Note: cacheService needs to support pattern matching
      logger.debug('[ApiClient] Cache invalidated with pattern:', { pattern });
    } else {
      // Clear all cache
      cacheService.clear?.();
      logger.debug('[ApiClient] All cache cleared');
    }
  }

  /**
   * Set new CSRF token
   */
  setCsrfToken(token: string): void {
    this.csrfTokenManager.setToken(token);
  }

  /**
   * Get current CSRF token
   */
  getCsrfToken(): string | null {
    return this.csrfTokenManager.getToken();
  }

  /**
   * Get deduplicator stats
   */
  getStats(): {
    pendingRequests: number;
    activeAbortControllers: number;
  } {
    return {
      pendingRequests: this.deduplicator.getPendingCount(),
      activeAbortControllers: this.activeRequests.size,
    };
  }

  /**
   * Convenience methods for common HTTP verbs
   */
  get<T = any>(url: string, config?: Partial<ApiRequest>): Promise<ApiResponse<T>> {
    return this.request<T>({
      method: 'GET',
      url,
      cache: { enabled: true, ttl: 5 * 60 * 1000 }, // 5 min default cache
      ...config,
    });
  }

  post<T = any>(url: string, data?: any, config?: Partial<ApiRequest>): Promise<ApiResponse<T>> {
    return this.request<T>({
      method: 'POST',
      url,
      data,
      ...config,
    });
  }

  put<T = any>(url: string, data?: any, config?: Partial<ApiRequest>): Promise<ApiResponse<T>> {
    return this.request<T>({
      method: 'PUT',
      url,
      data,
      ...config,
    });
  }

  patch<T = any>(url: string, data?: any, config?: Partial<ApiRequest>): Promise<ApiResponse<T>> {
    return this.request<T>({
      method: 'PATCH',
      url,
      data,
      ...config,
    });
  }

  delete<T = any>(url: string, config?: Partial<ApiRequest>): Promise<ApiResponse<T>> {
    return this.request<T>({
      method: 'DELETE',
      url,
      ...config,
    });
  }

  head<T = any>(url: string, config?: Partial<ApiRequest>): Promise<ApiResponse<T>> {
    return this.request<T>({
      method: 'HEAD',
      url,
      ...config,
    });
  }
}

/**
 * Default API client instance
 * Uses unified client's base URL configuration
 */
const API_BASE_URL = (() => {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DJANGO_API_URL) {
    return import.meta.env.VITE_DJANGO_API_URL;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    return `${protocol}//${window.location.host}/api`;
  }
  return 'http://localhost:8003/api';
})();

export const apiClient = new ApiClient({
  baseURL: API_BASE_URL,
  timeout: 30000,
  debugMode: import.meta.env.DEV,
  retryConfig: {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    backoffMultiplier: 2,
  },
});

/**
 * Export all types and utilities
 */
export type {
  ApiClientConfig,
  ApiRequest,
  ApiResponse,
  ApiError,
  ApiInterceptor,
  ResponseInterceptor,
};

export { RequestDeduplicator, CsrfTokenManager };
