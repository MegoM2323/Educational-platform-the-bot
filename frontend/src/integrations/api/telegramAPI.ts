import { unifiedAPI as apiClient, ApiResponse } from './unifiedClient';
import { logger } from '@/utils/logger';

export type { ApiResponse } from './unifiedClient';

export interface GenerateLinkTokenResponse {
  token: string;
  link: string;
  expires_at: string;
  ttl_minutes: number;
}

export interface TelegramProfile {
  telegram_id: number;
  telegram_username: string;
  first_name?: string;
  last_name?: string;
  is_bot?: boolean;
  language_code?: string;
  linked_at: string;
}

export interface TelegramProfileResponse {
  success: boolean;
  data?: TelegramProfile;
  error?: string;
  timestamp: string;
}

export const telegramAPI = {
  async generateLinkToken(): Promise<ApiResponse<GenerateLinkTokenResponse>> {
    try {
      const response = await apiClient.post<GenerateLinkTokenResponse>(
        '/api/accounts/telegram/link-token/'
      );

      if (!response.success) {
        throw new Error(response.error || 'Failed to generate link token');
      }

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate link token';
      logger.error('generateLinkToken error:', { error: message });
      return {
        success: false,
        error: message,
        timestamp: new Date().toISOString(),
      };
    }
  },

  async getTelegramProfile(): Promise<ApiResponse<TelegramProfile>> {
    try {
      const response = await apiClient.get<TelegramProfile>('/api/accounts/telegram/profile/');

      if (!response.success) {
        throw new Error(response.error || 'Failed to get Telegram profile');
      }

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get Telegram profile';
      logger.error('getTelegramProfile error:', { error: message });
      return {
        success: false,
        error: message,
        timestamp: new Date().toISOString(),
      };
    }
  },

  async unlinkTelegram(): Promise<ApiResponse<void>> {
    try {
      const response = await apiClient.delete<void>('/api/accounts/telegram/unlink/');

      if (!response.success) {
        throw new Error(response.error || 'Failed to unlink Telegram');
      }

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to unlink Telegram';
      logger.error('unlinkTelegram error:', { error: message });
      return {
        success: false,
        error: message,
        timestamp: new Date().toISOString(),
      };
    }
  },
};
