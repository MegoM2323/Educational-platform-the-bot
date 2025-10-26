// Migration script to replace old API clients with unified client
// This file provides backward compatibility during the transition period

import { unifiedAPI } from './unifiedClient';

// Re-export unified API as the main API client for backward compatibility
export const apiClient = unifiedAPI;

// Re-export all types from unified client
export type {
  ApiResponse,
  User,
  LoginRequest,
  LoginResponse,
  StudentDashboard,
  TeacherDashboard,
  ParentDashboard,
  ChatMessage,
  MessageThread,
  ChatRoom,
  Payment,
  CreatePaymentRequest,
  Application,
  CreateApplicationRequest,
} from './unifiedClient';

// Legacy API methods for backward compatibility
export const legacyAPI = {
  // Authentication methods (same as unified API)
  login: unifiedAPI.login.bind(unifiedAPI),
  logout: unifiedAPI.logout.bind(unifiedAPI),
  getProfile: unifiedAPI.getProfile.bind(unifiedAPI),
  updateProfile: unifiedAPI.updateProfile.bind(unifiedAPI),
  changePassword: unifiedAPI.changePassword.bind(unifiedAPI),
  
  // Utility methods
  setToken: unifiedAPI.setToken.bind(unifiedAPI),
  getToken: unifiedAPI.getToken.bind(unifiedAPI),
  isAuthenticated: unifiedAPI.isAuthenticated.bind(unifiedAPI),
  
  // Generic request method for backward compatibility
  request: async <T>(endpoint: string, options: RequestInit = {}): Promise<{ data?: T; error?: string }> => {
    const response = await unifiedAPI.request<T>(endpoint, options);
    return {
      data: response.data,
      error: response.error,
    };
  },
};

// Export both for gradual migration
export { unifiedAPI };
