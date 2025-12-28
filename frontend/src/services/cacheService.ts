// Cache Service for API response caching and data management
import { logger } from '@/utils/logger';
// Implements TTL-based caching with browser storage

export interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
  key: string;
}

export interface CacheConfig {
  defaultTTL: number; // Default TTL in milliseconds
  maxSize: number; // Maximum number of cache entries
  storageType: 'memory' | 'localStorage' | 'sessionStorage';
  prefix: string;
}

const DEFAULT_CONFIG: CacheConfig = {
  defaultTTL: 5 * 60 * 1000, // 5 minutes
  maxSize: 100,
  storageType: 'localStorage',
  prefix: 'cache_',
};

// Cache version for invalidation on breaking changes
const CACHE_VERSION = '2.0.0'; // Increment when cache structure changes
const CACHE_VERSION_KEY = 'cache_version';

class CacheService {
  private cache: Map<string, CacheEntry> = new Map();
  private config: CacheConfig;
  private storage: Storage | null = null;

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.initializeStorage();
    this.checkCacheVersion();
    this.loadFromStorage();
  }

  private checkCacheVersion(): void {
    if (!this.storage) return;

    try {
      const storedVersion = this.storage.getItem(CACHE_VERSION_KEY);
      if (storedVersion !== CACHE_VERSION) {
        logger.info(`[CacheService] Cache version mismatch (${storedVersion} -> ${CACHE_VERSION}), clearing old cache`);
        // Clear all cache entries but preserve other localStorage items
        const keys = Object.keys(this.storage);
        const cacheKeys = keys.filter(key => key.startsWith(this.config.prefix));
        cacheKeys.forEach(key => this.storage!.removeItem(key));
        // Update version
        this.storage.setItem(CACHE_VERSION_KEY, CACHE_VERSION);
      }
    } catch (error) {
      logger.error('[CacheService] Failed to check cache version:', error);
    }
  }

  private initializeStorage(): void {
    if (typeof window === 'undefined') return;

    switch (this.config.storageType) {
      case 'localStorage':
        this.storage = localStorage;
        break;
      case 'sessionStorage':
        this.storage = sessionStorage;
        break;
      case 'memory':
        this.storage = null;
        break;
    }
  }

  private getStorageKey(key: string): string {
    return `${this.config.prefix}${key}`;
  }

  private loadFromStorage(): void {
    if (!this.storage) return;

    try {
      const keys = Object.keys(this.storage);
      const cacheKeys = keys.filter(key => key.startsWith(this.config.prefix));
      
      for (const storageKey of cacheKeys) {
        const data = this.storage.getItem(storageKey);
        if (data) {
          const entry = JSON.parse(data) as CacheEntry;
          if (this.isValid(entry)) {
            const key = storageKey.replace(this.config.prefix, '');
            this.cache.set(key, entry);
          } else {
            this.storage.removeItem(storageKey);
          }
        }
      }
    } catch (error) {
      logger.error('Failed to load cache from storage:', error);
    }
  }

  private saveToStorage(key: string, entry: CacheEntry): void {
    if (!this.storage) return;

    try {
      const storageKey = this.getStorageKey(key);
      this.storage.setItem(storageKey, JSON.stringify(entry));
    } catch (error) {
      logger.error('Failed to save cache to storage:', error);
      // Storage might be full, try to clear old entries
      this.cleanupOldEntries();
    }
  }

  private removeFromStorage(key: string): void {
    if (!this.storage) return;

    try {
      const storageKey = this.getStorageKey(key);
      this.storage.removeItem(storageKey);
    } catch (error) {
      logger.error('Failed to remove cache from storage:', error);
    }
  }

  private isValid(entry: CacheEntry): boolean {
    const age = Date.now() - entry.timestamp;
    return age < entry.ttl;
  }

  private cleanupOldEntries(): void {
    const now = Date.now();
    const entriesToRemove: string[] = [];

    for (const [key, entry] of this.cache.entries()) {
      if (!this.isValid(entry)) {
        entriesToRemove.push(key);
      }
    }

    entriesToRemove.forEach(key => {
      this.cache.delete(key);
      this.removeFromStorage(key);
    });

    // If still over max size, remove oldest entries
    if (this.cache.size > this.config.maxSize) {
      const entries = Array.from(this.cache.entries())
        .sort((a, b) => a[1].timestamp - b[1].timestamp);
      
      const toRemove = entries.slice(0, this.cache.size - this.config.maxSize);
      toRemove.forEach(([key]) => {
        this.cache.delete(key);
        this.removeFromStorage(key);
      });
    }
  }

  set<T>(key: string, data: T, ttl?: number): void {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.config.defaultTTL,
      key,
    };

    this.cache.set(key, entry);
    this.saveToStorage(key, entry);
    this.cleanupOldEntries();
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }

    if (!this.isValid(entry)) {
      this.cache.delete(key);
      this.removeFromStorage(key);
      return null;
    }

    return entry.data as T;
  }

  has(key: string): boolean {
    const entry = this.cache.get(key);
    return entry ? this.isValid(entry) : false;
  }

  delete(key: string): void {
    this.cache.delete(key);
    this.removeFromStorage(key);
  }

  clear(): void {
    if (this.storage) {
      const keys = Object.keys(this.storage);
      const cacheKeys = keys.filter(key => key.startsWith(this.config.prefix));
      cacheKeys.forEach(key => this.storage!.removeItem(key));
    }
    this.cache.clear();
  }

  clearExpired(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    for (const [key, entry] of this.cache.entries()) {
      if (!this.isValid(entry)) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach(key => {
      this.cache.delete(key);
      this.removeFromStorage(key);
    });
  }

  getStats() {
    const now = Date.now();
    let validEntries = 0;
    let expiredEntries = 0;

    for (const entry of this.cache.values()) {
      if (this.isValid(entry)) {
        validEntries++;
      } else {
        expiredEntries++;
      }
    }

    return {
      total: this.cache.size,
      valid: validEntries,
      expired: expiredEntries,
      maxSize: this.config.maxSize,
      usage: (this.cache.size / this.config.maxSize) * 100,
    };
  }

  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  // Chat-specific caching with lazy loading support
  setChatMessages(chatId: string, messages: any[], page: number = 1): void {
    const key = `chat_${chatId}_page_${page}`;
    this.set(key, messages, 10 * 60 * 1000); // 10 minutes for chat messages
  }

  getChatMessages(chatId: string, page: number = 1): any[] | null {
    const key = `chat_${chatId}_page_${page}`;
    return this.get<any[]>(key);
  }

  clearChatCache(chatId?: string): void {
    if (chatId) {
      const keysToDelete = this.keys().filter(key => key.startsWith(`chat_${chatId}_`));
      keysToDelete.forEach(key => this.delete(key));
    } else {
      const keysToDelete = this.keys().filter(key => key.startsWith('chat_'));
      keysToDelete.forEach(key => this.delete(key));
    }
  }

  // Dashboard data caching
  setDashboardData(role: string, data: any): void {
    const key = `dashboard_${role}`;
    this.set(key, data, 2 * 60 * 1000); // 2 minutes for dashboard data
  }

  getDashboardData(role: string): any | null {
    const key = `dashboard_${role}`;
    return this.get(key);
  }

  clearDashboardCache(role?: string): void {
    if (role) {
      this.delete(`dashboard_${role}`);
    } else {
      const keysToDelete = this.keys().filter(key => key.startsWith('dashboard_'));
      keysToDelete.forEach(key => this.delete(key));
    }
  }
}

// Export singleton instance
export const cacheService = new CacheService({
  defaultTTL: 5 * 60 * 1000, // 5 minutes
  maxSize: 100,
  storageType: 'localStorage',
});

// Export class for custom instances
export { CacheService };

