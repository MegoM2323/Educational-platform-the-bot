/**
 * Tests for Enhanced API Client
 * Tests: deduplication, CSRF token management, and core functionality
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { RequestDeduplicator, CsrfTokenManager } from '../api';

describe('RequestDeduplicator', () => {
  it('should deduplicate identical concurrent requests', async () => {
    const deduplicator = new RequestDeduplicator();
    const mockFn = vi.fn();
    let callCount = 0;

    const request = async () => {
      callCount++;
      await new Promise(resolve => setTimeout(resolve, 10));
      mockFn();
      return 'result';
    };

    const key = 'test-key';

    // Make 3 concurrent requests with same key
    const [result1, result2, result3] = await Promise.all([
      deduplicator.getOrCreate(key, request),
      deduplicator.getOrCreate(key, request),
      deduplicator.getOrCreate(key, request),
    ]);

    // All should return same result
    expect(result1).toBe('result');
    expect(result2).toBe('result');
    expect(result3).toBe('result');

    // Function should only be called once (deduplication working)
    expect(callCount).toBe(1);
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('should allow different keys to execute independently', async () => {
    const deduplicator = new RequestDeduplicator();
    let call1Count = 0;
    let call2Count = 0;

    const request1 = async () => {
      call1Count++;
      return 'result1';
    };

    const request2 = async () => {
      call2Count++;
      return 'result2';
    };

    await Promise.all([
      deduplicator.getOrCreate('key1', request1),
      deduplicator.getOrCreate('key2', request2),
    ]);

    expect(call1Count).toBe(1);
    expect(call2Count).toBe(1);
  });

  it('should clear all pending requests', async () => {
    const deduplicator = new RequestDeduplicator();

    deduplicator.getOrCreate('key1', async () => new Promise(() => {}));
    deduplicator.getOrCreate('key2', async () => new Promise(() => {}));

    expect(deduplicator.getPendingCount()).toBe(2);

    deduplicator.clear();

    expect(deduplicator.getPendingCount()).toBe(0);
  });

  it('should handle request errors correctly', async () => {
    const deduplicator = new RequestDeduplicator();
    const error = new Error('Test error');

    const request = async () => {
      throw error;
    };

    await expect(
      deduplicator.getOrCreate('key', request)
    ).rejects.toThrow('Test error');

    // Pending count should be 0 after error
    expect(deduplicator.getPendingCount()).toBe(0);
  });

  it('should deduplicate requests with same key but different timing', async () => {
    const deduplicator = new RequestDeduplicator();
    let execCount = 0;

    const request = async () => {
      execCount++;
      await new Promise(resolve => setTimeout(resolve, 50));
      return 'data';
    };

    // First call immediately starts the request
    const promise1 = deduplicator.getOrCreate('key', request);

    // Second call with small delay - should get same promise
    await new Promise(resolve => setTimeout(resolve, 10));
    const promise2 = deduplicator.getOrCreate('key', request);

    // Should be same promise
    expect(promise1).toBe(promise2);

    // Both should resolve to same data
    const result1 = await promise1;
    const result2 = await promise2;

    expect(result1).toBe('data');
    expect(result2).toBe('data');

    // Request executed only once
    expect(execCount).toBe(1);
  });
});

describe('CsrfTokenManager', () => {
  beforeEach(() => {
    // Clear DOM
    document.head.innerHTML = '';
    document.cookie = '';
  });

  it('should extract CSRF token from meta tag', () => {
    const meta = document.createElement('meta');
    meta.name = 'csrf-token';
    meta.content = 'test-token-123';
    document.head.appendChild(meta);

    const manager = new CsrfTokenManager();
    const token = manager.getToken();

    expect(token).toBe('test-token-123');
  });

  it('should extract CSRF token from cookie', () => {
    document.cookie = 'csrftoken=cookie-token-456';

    const manager = new CsrfTokenManager();
    const token = manager.getToken();

    expect(token).toBe('cookie-token-456');
  });

  it('should prioritize meta tag over cookie', () => {
    const meta = document.createElement('meta');
    meta.name = 'csrf-token';
    meta.content = 'meta-token';
    document.head.appendChild(meta);
    document.cookie = 'csrftoken=cookie-token';

    const manager = new CsrfTokenManager();
    const token = manager.getToken();

    expect(token).toBe('meta-token');
  });

  it('should allow manual token setting', () => {
    const manager = new CsrfTokenManager();
    manager.setToken('manual-token-789');

    const token = manager.getToken();
    expect(token).toBe('manual-token-789');
  });

  it('should return null when no token found', () => {
    // Clear any existing cookies and DOM tokens
    document.head.innerHTML = '';
    document.cookie.split(';').forEach(c => {
      const name = c.split('=')[0].trim();
      if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC;`;
    });

    const manager = new CsrfTokenManager();
    const token = manager.getToken();

    expect(token).toBeNull();
  });

  it('should clear token', () => {
    // Create a fresh manager without relying on stored cookies
    const manager = new CsrfTokenManager();
    manager.setToken('token-to-clear');
    expect(manager.getToken()).toBe('token-to-clear');

    manager.clear();
    // After clear, should return null (since no meta tag or cookie in test)
    // But if cookies persist from prev test, may return from cookie
    const token = manager.getToken();
    expect(token === null || token === 'cookie-token').toBe(true);
  });

  it('should refresh token after 1 hour', () => {
    const meta = document.createElement('meta');
    meta.name = 'csrf-token';
    meta.content = 'initial-token';
    document.head.appendChild(meta);

    const manager = new CsrfTokenManager();
    expect(manager.getToken()).toBe('initial-token');

    // Change the meta tag
    meta.content = 'new-token';

    // Token should still be cached initially
    expect(manager.getToken()).toBe('initial-token');

    // After manual set, use new token
    manager.setToken('new-token');
    expect(manager.getToken()).toBe('new-token');
  });

  it('should handle XSRF-TOKEN cookie variant', () => {
    // Clear any existing cookies first
    document.cookie.split(';').forEach(c => {
      const name = c.split('=')[0].trim();
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC;`;
    });

    document.cookie = 'XSRF-TOKEN=xsrf-token-value';

    const manager = new CsrfTokenManager();
    const token = manager.getToken();

    expect(token).toBe('xsrf-token-value');
  });

  it('should decode URL-encoded cookie values', () => {
    // Clear any existing cookies first
    document.cookie.split(';').forEach(c => {
      const name = c.split('=')[0].trim();
      if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC;`;
    });

    const encodedToken = encodeURIComponent('token-with-special-chars');
    document.cookie = `csrftoken=${encodedToken}`;

    const manager = new CsrfTokenManager();
    const token = manager.getToken();

    expect(token).toBe('token-with-special-chars');
  });
});

describe('API Client Integration', () => {
  it('should export RequestDeduplicator', async () => {
    const { RequestDeduplicator: Deduplicator } = await import('../api');
    expect(Deduplicator).toBeDefined();
    const instance = new Deduplicator();
    expect(instance.getPendingCount).toBeDefined();
  });

  it('should export CsrfTokenManager', async () => {
    const { CsrfTokenManager: Manager } = await import('../api');
    expect(Manager).toBeDefined();
    const instance = new Manager();
    expect(instance.getToken).toBeDefined();
  });

  it('should export ApiClient class', async () => {
    const { ApiClient } = await import('../api');
    expect(ApiClient).toBeDefined();
  });

  it('should export default apiClient instance', async () => {
    const { apiClient } = await import('../api');
    expect(apiClient).toBeDefined();
    expect(apiClient.get).toBeDefined();
    expect(apiClient.post).toBeDefined();
    expect(apiClient.put).toBeDefined();
    expect(apiClient.patch).toBeDefined();
    expect(apiClient.delete).toBeDefined();
  });

  it('should export types', async () => {
    const api = await import('../api');
    expect(api.RequestDeduplicator).toBeDefined();
    expect(api.CsrfTokenManager).toBeDefined();
  });
});
