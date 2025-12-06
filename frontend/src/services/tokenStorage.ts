/**
 * Token Storage Service
 * Управление JWT токенами в localStorage
 */

import { logger } from '@/utils/logger';

const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export const tokenStorage = {
  /**
   * Получить сохраненные токены
   */
  getTokens(): { accessToken: string | null; refreshToken: string | null } {
    if (typeof window === 'undefined') {
      return { accessToken: null, refreshToken: null };
    }

    const accessToken = localStorage.getItem(TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

    if (accessToken) {
      logger.debug('[tokenStorage.getTokens]', {
        hasAccessToken: true,
        accessTokenLength: accessToken.length,
        hasRefreshToken: !!refreshToken
      });
    }

    return { accessToken, refreshToken };
  },

  /**
   * Сохранить токены
   */
  saveTokens(token: string, refreshToken?: string): void {
    if (typeof window === 'undefined') return;

    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }

    logger.debug('[tokenStorage.saveTokens]', {
      tokenLength: token.length,
      hasRefreshToken: !!refreshToken,
      refreshTokenLength: refreshToken?.length || 0
    });
  },

  /**
   * Очистить токены
   */
  clearTokens(): void {
    if (typeof window === 'undefined') return;

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  /**
   * Получить только access token
   */
  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Получить только refresh token
   */
  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
};
