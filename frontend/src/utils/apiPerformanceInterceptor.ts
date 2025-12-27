/**
 * API Performance Interceptor
 * Automatically tracks API request performance metrics
 *
 * Integration with ApiClient to capture:
 * - Request latency
 * - Response status
 * - Cached responses
 * - Retry attempts
 * - Error responses
 */

import { performanceMonitor } from './performance';
import type { ApiRequest, ApiResponse } from './api';
import { logger } from './logger';

interface RequestMetadata {
  startTime: number;
  method: string;
  endpoint: string;
  retryCount: number;
  cached: boolean;
}

// Store request metadata by request ID
const requestMetadataMap = new Map<string, RequestMetadata>();

/**
 * Generate request ID for tracking
 */
export const generateRequestId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Request interceptor to track API performance
 */
export const apiPerformanceRequestInterceptor = (config: ApiRequest): ApiRequest => {
  const requestId = generateRequestId();

  // Extract endpoint from URL
  const endpoint = new URL(
    config.url.startsWith('http') ? config.url : `http://localhost${config.url}`
  ).pathname;

  // Store metadata
  requestMetadataMap.set(requestId, {
    startTime: performance.now(),
    method: config.method,
    endpoint,
    retryCount: 0,
    cached: config.cache?.enabled || false,
  });

  // Attach request ID to config for response interceptor
  (config as any).__requestId = requestId;

  return config;
};

/**
 * Response interceptor to track API performance
 */
export const apiPerformanceResponseInterceptor = (response: ApiResponse): ApiResponse => {
  const requestId = (response as any).__requestId || '(unknown)';
  const metadata = requestMetadataMap.get(requestId);

  if (!metadata) {
    logger.warn('[ApiPerformanceInterceptor] No metadata found for request', { requestId });
    return response;
  }

  const duration = performance.now() - metadata.startTime;

  // Track in performance monitor
  performanceMonitor.trackApiRequest(
    metadata.method,
    metadata.endpoint,
    duration,
    response.status,
    metadata.cached,
    metadata.retryCount
  );

  // Cleanup
  requestMetadataMap.delete(requestId);

  return response;
};

/**
 * Setup API performance tracking
 * Call this in your API client initialization
 */
export const setupApiPerformanceTracking = (apiClient: any): void => {
  try {
    apiClient.useRequestInterceptor(apiPerformanceRequestInterceptor);
    apiClient.useResponseInterceptor(apiPerformanceResponseInterceptor);

    logger.info('[ApiPerformanceInterceptor] API performance tracking enabled');
  } catch (error) {
    logger.error('[ApiPerformanceInterceptor] Failed to setup API performance tracking', error);
  }
};

/**
 * Manual API call tracking for non-ApiClient requests
 */
export const trackApiCall = (
  method: string,
  endpoint: string,
  duration: number,
  status: number,
  cached: boolean = false,
  retries: number = 0
): void => {
  performanceMonitor.trackApiRequest(
    method,
    endpoint,
    duration,
    status,
    cached,
    retries
  );
};

/**
 * Get average latency for specific method
 */
export const getAverageLatency = (method?: string): number => {
  return performanceMonitor.getAverageApiLatency(method);
};

/**
 * Get latency by method
 */
export const getLatencyByMethod = (): Record<string, number> => {
  return performanceMonitor.getApiLatencyByMethod();
};

export default {
  apiPerformanceRequestInterceptor,
  apiPerformanceResponseInterceptor,
  setupApiPerformanceTracking,
  trackApiCall,
  getAverageLatency,
  getLatencyByMethod,
};
