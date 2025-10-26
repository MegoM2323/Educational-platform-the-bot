// Unit tests for API migration compatibility
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, legacyAPI } from '../migration';
import { unifiedAPI } from '../unifiedClient';

// Mock the unified API
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    login: vi.fn(),
    logout: vi.fn(),
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
    setToken: vi.fn(),
    getToken: vi.fn(),
    isAuthenticated: vi.fn(),
    request: vi.fn(),
  },
}));

describe('API Migration Compatibility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('apiClient (main export)', () => {
    it('should be the same instance as unifiedAPI', () => {
      expect(apiClient).toBe(unifiedAPI);
    });

    it('should have all unifiedAPI methods', () => {
      expect(typeof apiClient.login).toBe('function');
      expect(typeof apiClient.logout).toBe('function');
      expect(typeof apiClient.getProfile).toBe('function');
      expect(typeof apiClient.updateProfile).toBe('function');
      expect(typeof apiClient.changePassword).toBe('function');
      expect(typeof apiClient.setToken).toBe('function');
      expect(typeof apiClient.getToken).toBe('function');
      expect(typeof apiClient.isAuthenticated).toBe('function');
    });
  });

  describe('legacyAPI', () => {
    it('should have authentication methods', () => {
      expect(typeof legacyAPI.login).toBe('function');
      expect(typeof legacyAPI.logout).toBe('function');
      expect(typeof legacyAPI.getProfile).toBe('function');
      expect(typeof legacyAPI.updateProfile).toBe('function');
      expect(typeof legacyAPI.changePassword).toBe('function');
    });

    it('should have utility methods', () => {
      expect(typeof legacyAPI.setToken).toBe('function');
      expect(typeof legacyAPI.getToken).toBe('function');
      expect(typeof legacyAPI.isAuthenticated).toBe('function');
    });

    it('should have generic request method', () => {
      expect(typeof legacyAPI.request).toBe('function');
    });

    it('should delegate login to unifiedAPI', async () => {
      const mockCredentials = { email: 'test@example.com', password: 'password' };
      const mockResponse = { success: true, data: { token: 'test-token' } };
      
      vi.mocked(unifiedAPI.login).mockResolvedValue(mockResponse);

      const result = await legacyAPI.login(mockCredentials);

      expect(unifiedAPI.login).toHaveBeenCalledWith(mockCredentials);
      expect(result).toBe(mockResponse);
    });

    it('should delegate logout to unifiedAPI', async () => {
      const mockResponse = { success: true };
      
      vi.mocked(unifiedAPI.logout).mockResolvedValue(mockResponse);

      const result = await legacyAPI.logout();

      expect(unifiedAPI.logout).toHaveBeenCalled();
      expect(result).toBe(mockResponse);
    });

    it('should delegate getProfile to unifiedAPI', async () => {
      const mockResponse = { success: true, data: { user: { id: 1 } } };
      
      vi.mocked(unifiedAPI.getProfile).mockResolvedValue(mockResponse);

      const result = await legacyAPI.getProfile();

      expect(unifiedAPI.getProfile).toHaveBeenCalled();
      expect(result).toBe(mockResponse);
    });

    it('should delegate updateProfile to unifiedAPI', async () => {
      const mockProfileData = { first_name: 'Updated' };
      const mockResponse = { success: true, data: { id: 1, first_name: 'Updated' } };
      
      vi.mocked(unifiedAPI.updateProfile).mockResolvedValue(mockResponse);

      const result = await legacyAPI.updateProfile(mockProfileData);

      expect(unifiedAPI.updateProfile).toHaveBeenCalledWith(mockProfileData);
      expect(result).toBe(mockResponse);
    });

    it('should delegate changePassword to unifiedAPI', async () => {
      const mockPasswordData = {
        old_password: 'old',
        new_password: 'new',
        new_password_confirm: 'new',
      };
      const mockResponse = { success: true };
      
      vi.mocked(unifiedAPI.changePassword).mockResolvedValue(mockResponse);

      const result = await legacyAPI.changePassword(mockPasswordData);

      expect(unifiedAPI.changePassword).toHaveBeenCalledWith(mockPasswordData);
      expect(result).toBe(mockResponse);
    });

    it('should delegate setToken to unifiedAPI', () => {
      const testToken = 'test-token';
      
      legacyAPI.setToken(testToken);

      expect(unifiedAPI.setToken).toHaveBeenCalledWith(testToken);
    });

    it('should delegate getToken to unifiedAPI', () => {
      const mockToken = 'test-token';
      
      vi.mocked(unifiedAPI.getToken).mockReturnValue(mockToken);

      const result = legacyAPI.getToken();

      expect(unifiedAPI.getToken).toHaveBeenCalled();
      expect(result).toBe(mockToken);
    });

    it('should delegate isAuthenticated to unifiedAPI', () => {
      vi.mocked(unifiedAPI.isAuthenticated).mockReturnValue(true);

      const result = legacyAPI.isAuthenticated();

      expect(unifiedAPI.isAuthenticated).toHaveBeenCalled();
      expect(result).toBe(true);
    });

    it('should delegate request to unifiedAPI with correct format', async () => {
      const mockResponse = { success: true, data: { test: 'data' } };
      const mockRequestOptions = { method: 'POST', body: '{"test": "data"}' };
      
      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await legacyAPI.request('/test-endpoint', mockRequestOptions);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/test-endpoint', mockRequestOptions);
      expect(result).toEqual({ data: { test: 'data' }, error: undefined });
    });

    it('should handle request errors correctly', async () => {
      const mockResponse = { success: false, error: 'Test error' };
      const mockRequestOptions = { method: 'GET' };
      
      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await legacyAPI.request('/test-endpoint', mockRequestOptions);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/test-endpoint', mockRequestOptions);
      expect(result).toEqual({ data: undefined, error: 'Test error' });
    });
  });
});
