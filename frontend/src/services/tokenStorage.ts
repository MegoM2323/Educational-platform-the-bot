/**
 * Token Storage Service
 * Управление JWT токенами в localStorage
 */

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

    return {
      accessToken: localStorage.getItem(TOKEN_KEY),
      refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
    };
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
