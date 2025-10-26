// Unit tests for error handling in Unified API Client
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UnifiedAPIClient } from '../unifiedClient';

// Mock fetch globally
global.fetch = vi.fn();
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

describe('Error Handling in UnifiedAPIClient', () => {
  let client: UnifiedAPIClient;
  const mockFetch = vi.mocked(fetch);

  beforeEach(() => {
    client = new UnifiedAPIClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Network Error Classification', () => {
    it('should classify network errors correctly', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error: Unable to connect to server');
    });

    it('should classify authentication errors correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({
          success: false,
          error: 'Unauthorized',
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Unauthorized');
    });

    it('should classify validation errors correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({
          success: false,
          error: 'Invalid input data',
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid input data');
    });

    it('should classify server errors correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({
          success: false,
          error: 'Internal server error',
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Internal server error');
    });
  });

  describe('Retry Logic', () => {
    it('should retry network errors up to max retries', async () => {
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'));

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(4); // 1 initial + 3 retries
    });

    it('should not retry authentication errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({
          success: false,
          error: 'Unauthorized',
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should retry server errors once', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: () => Promise.resolve({
            success: false,
            error: 'Internal server error',
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { status: 'ok' },
          }),
        } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should use exponential backoff for retries', async () => {
      const startTime = Date.now();
      
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { status: 'ok' },
          }),
        } as Response);

      await client.healthCheck();

      const endTime = Date.now();
      const totalTime = endTime - startTime;
      
      // Should have waited at least 1000ms + 2000ms = 3000ms for retries
      expect(totalTime).toBeGreaterThanOrEqual(2900); // Allow some margin for execution time
    });
  });

  describe('Token Refresh', () => {
    it('should attempt token refresh on 401 errors', async () => {
      client.setToken('expired-token');
      
      // Mock refresh token in localStorage
      vi.mocked(localStorage.getItem).mockReturnValue('refresh-token');

      // First call returns 401, refresh call succeeds, second call succeeds
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: () => Promise.resolve({
            success: false,
            error: 'Token expired',
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: {
              token: 'new-token',
              refresh_token: 'new-refresh-token',
            },
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { status: 'ok' },
          }),
        } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(localStorage.setItem).toHaveBeenCalledWith('authToken', 'new-token');
    });

    it('should clear tokens if refresh fails', async () => {
      client.setToken('expired-token');
      
      // Mock refresh token in localStorage
      vi.mocked(localStorage.getItem).mockReturnValue('invalid-refresh-token');

      // First call returns 401, refresh call fails
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: () => Promise.resolve({
            success: false,
            error: 'Token expired',
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: () => Promise.resolve({
            success: false,
            error: 'Invalid refresh token',
          }),
        } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(localStorage.removeItem).toHaveBeenCalledWith('authToken');
      expect(localStorage.removeItem).toHaveBeenCalledWith('refreshToken');
    });
  });

  describe('Request Queue Management', () => {
    it('should prevent duplicate requests', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { status: 'ok' },
        }),
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      // Make multiple identical requests
      const promises = [
        client.healthCheck(),
        client.healthCheck(),
        client.healthCheck(),
      ];

      const results = await Promise.all(promises);

      // All results should be identical
      expect(results[0]).toEqual(results[1]);
      expect(results[1]).toEqual(results[2]);
      
      // Fetch should only be called once
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should handle different requests independently', async () => {
      const mockResponse1 = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { status: 'ok' },
        }),
      } as Response;

      const mockResponse2 = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { user: { id: 1 } },
        }),
      } as Response;

      mockFetch
        .mockResolvedValueOnce(mockResponse1)
        .mockResolvedValueOnce(mockResponse2);

      // Make different requests
      const [healthResult, profileResult] = await Promise.all([
        client.healthCheck(),
        client.getProfile(),
      ]);

      expect(healthResult.success).toBe(true);
      expect(profileResult.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Message Transformation', () => {
    it('should provide user-friendly error messages', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({
          success: false,
          data: {
            error: 'Database connection failed',
            detail: 'Unable to connect to database server',
          },
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Database connection failed');
    });

    it('should fallback to generic error message when no specific error provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({
          success: false,
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Server error occurred');
    });

    it('should handle malformed JSON responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Ошибка парсинга ответа сервера');
    });
  });

  describe('Custom Retry Configuration', () => {
    it('should respect custom retry configuration', async () => {
      const customClient = new UnifiedAPIClient(
        'http://localhost:8000/api',
        'ws://localhost:8000/ws',
        {
          maxRetries: 1,
          baseDelay: 100,
          maxDelay: 200,
          backoffMultiplier: 2,
        }
      );

      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { status: 'ok' },
          }),
        } as Response);

      const startTime = Date.now();
      const result = await customClient.healthCheck();
      const endTime = Date.now();

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(3); // 1 initial + 2 retries (maxRetries: 1)
      
      // Should have waited at least 100ms + 200ms = 300ms
      expect(endTime - startTime).toBeGreaterThanOrEqual(290);
    });
  });
});
