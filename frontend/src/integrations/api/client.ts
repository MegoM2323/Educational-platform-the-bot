// Legacy API client - now uses unified client
// This file is kept for backward compatibility during migration
export { apiClient, legacyAPI } from './migration';

// Re-export all types for backward compatibility
export type {
  ApiResponse,
  User,
  LoginRequest,
  LoginResponse,
} from './unifiedClient';