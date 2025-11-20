/**
 * Cache Invalidation Manager
 * Управление инвалидацией кеша для API endpoints
 */

import { cacheService } from './cacheService';
import { logger } from '@/utils/logger';

class CacheInvalidationManager {
  /**
   * Инвалидировать кеш для конкретного endpoint
   */
  async invalidateEndpoint(endpoint: string): Promise<void> {
    try {
      // Нормализуем endpoint (убираем начальный слеш если есть)
      const normalizedEndpoint = endpoint.startsWith('/')
        ? endpoint.substring(1)
        : endpoint;

      // Очищаем кеш для этого endpoint
      cacheService.delete(normalizedEndpoint);

      // Также очищаем все варианты этого endpoint с параметрами
      cacheService.clearPattern(normalizedEndpoint);

      logger.info(`[CacheInvalidation] Invalidated cache for endpoint: ${endpoint}`);
    } catch (error) {
      logger.error('[CacheInvalidation] Failed to invalidate cache:', error);
    }
  }

  /**
   * Инвалидировать кеш по паттерну
   */
  async invalidatePattern(pattern: string): Promise<void> {
    try {
      cacheService.clearPattern(pattern);
      logger.info(`[CacheInvalidation] Invalidated cache by pattern: ${pattern}`);
    } catch (error) {
      logger.error('[CacheInvalidation] Failed to invalidate cache by pattern:', error);
    }
  }

  /**
   * Очистить весь кеш
   */
  async invalidateAll(): Promise<void> {
    try {
      cacheService.clear();
      logger.info('[CacheInvalidation] Cleared all cache');
    } catch (error) {
      logger.error('[CacheInvalidation] Failed to clear all cache:', error);
    }
  }

  /**
   * Инвалидировать кеш для множества endpoints
   */
  async invalidateEndpoints(endpoints: string[]): Promise<void> {
    await Promise.all(endpoints.map((endpoint) => this.invalidateEndpoint(endpoint)));
  }
}

export const cacheInvalidationManager = new CacheInvalidationManager();
