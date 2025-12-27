// Legacy Django API client - now uses unified client
// This file is kept for backward compatibility during migration
export { unifiedAPI as djangoAPI, UnifiedAPIClient as DjangoAPIClient } from '../api/unifiedClient';

// Re-export all types for backward compatibility
export type {
  Payment,
  CreatePaymentRequest,
  Application,
  CreateApplicationRequest,
} from '../api/unifiedClient';