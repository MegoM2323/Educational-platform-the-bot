// Унифицированный сервис аутентификации
import { unifiedAPI as apiClient, User } from '@/integrations/api/unifiedClient';
import { secureStorage } from '@/utils/secureStorage';
import { logger } from '@/utils/logger';

export interface AuthResult {
  user: User;
  token: string;
  refresh_token?: string;
  expires_at: string;
}

export interface LoginRequest {
  email?: string;
  username?: string;
  password: string;
}

export interface TokenResponse {
  token: string;
  refresh_token?: string;
  expires_at: string;
}

class AuthService {
  private static instance: AuthService;
  private user: User | null = null;
  private token: string | null = null;
  private refreshToken: string | null = null;
  private tokenExpiry: number | null = null;
  private authStateCallbacks: ((user: User | null) => void)[] = [];
  private isRefreshing: boolean = false;
  private initializationPromise: Promise<void> | null = null;

  private constructor() {
    this.initializationPromise = this.initializeFromStorage();
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  private async initializeFromStorage(): Promise<void> {
    try {
      const storedToken = this.getStoredToken();
      const storedUser = this.getStoredUser();
      const storedRefreshToken = this.getStoredRefreshToken();
      const storedExpiry = this.getStoredTokenExpiry();

      logger.debug('AuthService init:', {
        hasToken: !!storedToken,
        hasUser: !!storedUser,
        hasExpiry: !!storedExpiry,
        expiry: storedExpiry,
        now: Date.now(),
        isExpired: storedExpiry ? Date.now() >= storedExpiry : 'no expiry'
      });

      // If we have token and user, consider it valid authentication
      // expiry is optional - if missing, use default 7 days
      if (storedToken && storedUser) {
        // Check if token is expired (if expiry is set)
        const tokenExpired = storedExpiry && Date.now() >= storedExpiry;

        if (!tokenExpired) {
          this.token = storedToken;
          this.user = storedUser;
          this.refreshToken = storedRefreshToken;
          // If no expiry in storage, set default (7 days from now)
          this.tokenExpiry = storedExpiry || (Date.now() + (7 * 24 * 60 * 60 * 1000));
          apiClient.setToken(storedToken);
          logger.debug('AuthService: user authenticated', this.user);
        } else {
          // Токен истек, пытаемся обновить
          logger.debug('AuthService: token expired, attempting refresh');
          this.isRefreshing = true;
          try {
            // Временно устанавливаем старый токен для refresh запроса
            this.token = storedToken;
            apiClient.setToken(storedToken);

            // Добавляем timeout protection (5 секунд)
            await Promise.race([
              this.refreshTokenIfNeeded(),
              new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Token refresh timeout after 5s')), 5000)
              ),
            ]);
            logger.debug('AuthService: token refreshed successfully during init');
          } catch (err) {
            logger.error('AuthService: Failed to refresh token during init:', err);
            this.clearStorage();
            this.user = null;
            this.token = null;
          } finally {
            this.isRefreshing = false;
          }
        }
      } else {
        logger.debug('AuthService: no stored credentials (missing token or user)');
      }
    } catch (error) {
      logger.error('Ошибка инициализации аутентификации:', error);
      this.clearStorage();
    }
  }

  private getStoredToken(): string | null {
    // First check tokenStorage key (auth_token) - used by unifiedClient
    const tokenStorageKey = localStorage.getItem('auth_token');
    if (tokenStorageKey) return tokenStorageKey;

    try {
      // Second try secureStorage (bot_platform_auth_token with encryption)
      return secureStorage.getAuthToken();
    } catch (e) {
      // Fallback for other key formats
      // 1) Plain authToken key
      const plain = localStorage.getItem('authToken');
      if (plain) return plain;
      // 2) SecureStorage-like JSON under bot_platform_auth_token
      const item = localStorage.getItem('bot_platform_auth_token');
      if (item) {
        try { const parsed = JSON.parse(item); return parsed?.data || null; } catch { /* ignore */ }
      }
      return null;
    }
  }

  private getStoredUser(): User | null {
    try {
      return secureStorage.getUserData();
    } catch (e) {
      // Fallbacks for tests/local
      const raw = localStorage.getItem('userData');
      if (raw) { try { return JSON.parse(raw) as User; } catch { /* ignore */ }
      }
      const item = localStorage.getItem('bot_platform_user_data');
      if (item) {
        try { const parsed = JSON.parse(item); const data = parsed?.data; return data ? JSON.parse(data) as User : null; } catch { /* ignore */ }
      }
      return null;
    }
  }

  private getStoredRefreshToken(): string | null {
    return secureStorage.getRefreshToken();
  }

  private getStoredTokenExpiry(): number | null {
    // Primary secure storage
    const expiry = (() => { try { return secureStorage.getItem('token_expiry'); } catch { return null; } })();
    if (expiry) {
      const parsed = parseInt(expiry, 10);
      if (!isNaN(parsed)) return parsed;
    }
    // Fallback: bot_platform_token_expiry JSON
    const item = localStorage.getItem('bot_platform_token_expiry');
    if (item) {
      try { const parsed = JSON.parse(item); const data = parseInt(parsed?.data, 10); return isNaN(data) ? null : data; } catch { /* ignore */ }
    }
    // Fallback: plain key
    const plain = localStorage.getItem('token_expiry');
    if (plain) { const n = parseInt(plain, 10); return isNaN(n) ? null : n; }
    return null;
  }

  private setStoredToken(token: string, ttl?: number): void {
    secureStorage.setAuthToken(token, ttl);
  }

  private setStoredUser(user: User, ttl?: number): void {
    secureStorage.setUserData(user, ttl);
  }

  private setStoredRefreshToken(refreshToken: string, ttl?: number): void {
    secureStorage.setRefreshToken(refreshToken, ttl);
  }

  private setStoredTokenExpiry(expiry: number): void {
    secureStorage.setItem('token_expiry', expiry.toString());
  }

  private clearStorage(): void {
    secureStorage.clearAuthData();
  }

  public async login(credentials: LoginRequest): Promise<AuthResult> {
    try {
      const response = await apiClient.login(credentials);

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Ошибка входа');
      }

      const { token, user } = response.data;

      logger.debug('[AuthService.login] Login successful:', {
        username: user?.username,
        role: user?.role,
        tokenLength: token?.length
      });

      // Устанавливаем токен и пользователя
      this.token = token;
      this.user = user;
      this.tokenExpiry = Date.now() + (7 * 24 * 60 * 60 * 1000); // 7 дней по умолчанию

      // CRITICAL: Убедиться, что токен установлен в API клиент ПЕРЕД тем, как сохранить
      // Это гарантирует, что следующие запросы будут использовать правильный токен
      apiClient.setToken(token);

      // Сохраняем в безопасное хранилище (secureStorage)
      // NOTE: unifiedClient.login() already saved token to tokenStorage (auth_token, refresh_token keys)
      // We also save to secureStorage for backward compatibility
      const ttl = 7 * 24 * 60 * 60 * 1000; // 7 дней
      this.setStoredToken(token, ttl);
      this.setStoredUser(user, ttl);
      this.setStoredTokenExpiry(this.tokenExpiry);

      // Уведомляем подписчиков
      this.notifyAuthStateChange(user);

      logger.debug('[AuthService.login] User and token saved to secureStorage:', {
        currentUser: this.user?.username,
        currentRole: this.user?.role,
        hasToken: !!this.token,
        tokenInApiClient: !!apiClient.getToken()
      });

      return {
        user,
        token,
        expires_at: new Date(this.tokenExpiry).toISOString()
      };
    } catch (error) {
      logger.error('Ошибка входа:', error);
      throw error;
    }
  }

  public async logout(): Promise<void> {
    try {
      await apiClient.logout();
    } catch (error) {
      logger.error('Ошибка выхода:', error);
    } finally {
      // Очищаем состояние независимо от результата запроса
      this.token = null;
      this.user = null;
      this.refreshToken = null;
      this.tokenExpiry = null;
      
      this.clearStorage();
      apiClient.setToken('');
      
      // Уведомляем подписчиков
      this.notifyAuthStateChange(null);
    }
  }

  public async waitForInitialization(): Promise<void> {
    if (this.initializationPromise) {
      await this.initializationPromise;
    }
  }

  public isInitializing(): boolean {
    return this.isRefreshing;
  }

  public getCurrentUser(): User | null {
    return this.user;
  }

  public isAuthenticated(): boolean {
    return !!this.token && !!this.user;
  }

  public getToken(): string | null {
    return this.token;
  }

  public async refreshTokenIfNeeded(): Promise<string | null> {
    // Если нет токена или срока действия, возвращаем null
    if (!this.token || !this.tokenExpiry) {
      logger.debug('[AuthService.refreshTokenIfNeeded] No token or expiry');
      return null;
    }

    // Проверяем, нужно ли обновлять токен (за 5 минут до истечения)
    const refreshThreshold = 5 * 60 * 1000; // 5 минут
    const timeUntilExpiry = this.tokenExpiry - Date.now();

    logger.debug('[AuthService.refreshTokenIfNeeded]', {
      timeUntilExpiry,
      refreshThreshold,
      needsRefresh: timeUntilExpiry < refreshThreshold
    });

    if (timeUntilExpiry >= refreshThreshold) {
      return this.token;
    }

    try {
      logger.debug('[AuthService.refreshTokenIfNeeded] Token expiring soon, refreshing...');

      // Вызываем API для обновления токена
      const response = await apiClient.refreshToken();

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Не удалось обновить токен');
      }

      const { token, user } = response.data;

      // Обновляем токен и данные пользователя
      this.token = token;
      this.user = user;
      this.tokenExpiry = Date.now() + (7 * 24 * 60 * 60 * 1000); // 7 дней

      // Сохраняем в безопасное хранилище
      const ttl = 7 * 24 * 60 * 60 * 1000;
      this.setStoredToken(token, ttl);
      this.setStoredUser(user, ttl);
      this.setStoredTokenExpiry(this.tokenExpiry);

      // Устанавливаем новый токен в API клиент
      apiClient.setToken(token);

      logger.debug('[AuthService.refreshTokenIfNeeded] Token refreshed successfully');

      // Уведомляем подписчиков
      this.notifyAuthStateChange(user);

      return this.token;
    } catch (error) {
      logger.error('[AuthService.refreshTokenIfNeeded] Error refreshing token:', error);
      // При ошибке обновления выполняем logout
      await this.logout();
      return null;
    }
  }

  public onAuthStateChange(callback: (user: User | null) => void): () => void {
    this.authStateCallbacks.push(callback);
    
    // Возвращаем функцию для отписки
    return () => {
      const index = this.authStateCallbacks.indexOf(callback);
      if (index > -1) {
        this.authStateCallbacks.splice(index, 1);
      }
    };
  }

  private notifyAuthStateChange(user: User | null): void {
    this.authStateCallbacks.forEach(callback => {
      try {
        callback(user);
      } catch (error) {
        logger.error('Ошибка в callback аутентификации:', error);
      }
    });
  }

  // Метод для проверки и обновления токена перед запросами
  public async ensureValidToken(): Promise<string | null> {
    if (!this.isAuthenticated()) {
      return null;
    }

    const validToken = await this.refreshTokenIfNeeded();
    if (validToken) {
      return validToken;
    }

    // Если токен недействителен, выходим
    await this.logout();
    return null;
  }

  // DEV/E2E helper: установить пользователя и токен извне (например, из страницы Auth при фолбэке)
  public authenticateWith(user: User, token: string, ttlMs: number = 7 * 24 * 60 * 60 * 1000): void {
    this.token = token;
    this.user = user;
    this.tokenExpiry = Date.now() + ttlMs;
    this.setStoredToken(token, ttlMs);
    this.setStoredUser(user, ttlMs);
    this.setStoredTokenExpiry(this.tokenExpiry);
    apiClient.setToken(token);
    this.notifyAuthStateChange(user);
  }
}

// Экспортируем singleton instance
export const authService = AuthService.getInstance();

// Экспортируем класс для тестирования
export { AuthService };
