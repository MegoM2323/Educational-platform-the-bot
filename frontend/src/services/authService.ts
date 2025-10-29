// Унифицированный сервис аутентификации
import { unifiedAPI as apiClient, User } from '@/integrations/api/unifiedClient';
import { secureStorage } from '@/utils/secureStorage';

export interface AuthResult {
  user: User;
  token: string;
  refresh_token?: string;
  expires_at: string;
}

export interface LoginRequest {
  email: string;
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

  private constructor() {
    this.initializeFromStorage();
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  private initializeFromStorage(): void {
    try {
      const storedToken = this.getStoredToken();
      const storedUser = this.getStoredUser();
      const storedRefreshToken = this.getStoredRefreshToken();
      const storedExpiry = this.getStoredTokenExpiry();

      console.log('AuthService init:', {
        hasToken: !!storedToken,
        hasUser: !!storedUser,
        hasExpiry: !!storedExpiry,
        expiry: storedExpiry,
        now: Date.now(),
        isExpired: storedExpiry ? Date.now() >= storedExpiry : 'no expiry'
      });

      if (storedToken && storedUser && storedExpiry) {
        // Проверяем, не истек ли токен
        if (Date.now() < storedExpiry) {
          this.token = storedToken;
          this.user = storedUser;
          this.refreshToken = storedRefreshToken;
          this.tokenExpiry = storedExpiry;
          apiClient.setToken(storedToken);
          console.log('AuthService: user authenticated', this.user);
        } else {
          // Токен истек, пытаемся обновить
          console.log('AuthService: token expired, refreshing');
          this.refreshTokenIfNeeded();
        }
      } else {
        console.log('AuthService: no stored credentials');
      }
    } catch (error) {
      console.error('Ошибка инициализации аутентификации:', error);
      this.clearStorage();
    }
  }

  private getStoredToken(): string | null {
    try {
      return secureStorage.getAuthToken();
    } catch (e) {
      // Fallbacks for tests/local: support multiple key formats
      // 1) Plain token
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
      
      // Устанавливаем токен и пользователя
      this.token = token;
      this.user = user;
      this.tokenExpiry = Date.now() + (24 * 60 * 60 * 1000); // 24 часа по умолчанию
      
      // Сохраняем в безопасное хранилище
      const ttl = 24 * 60 * 60 * 1000; // 24 часа
      this.setStoredToken(token, ttl);
      this.setStoredUser(user, ttl);
      this.setStoredTokenExpiry(this.tokenExpiry);
      
      // Устанавливаем токен в API клиент
      apiClient.setToken(token);
      
      // Уведомляем подписчиков
      this.notifyAuthStateChange(user);
      
      return {
        user,
        token,
        expires_at: new Date(this.tokenExpiry).toISOString()
      };
    } catch (error) {
      console.error('Ошибка входа:', error);
      throw error;
    }
  }

  public async logout(): Promise<void> {
    try {
      await apiClient.logout();
    } catch (error) {
      console.error('Ошибка выхода:', error);
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
    if (!this.refreshToken || !this.tokenExpiry) {
      return null;
    }

    // Проверяем, нужно ли обновлять токен (за 5 минут до истечения)
    const refreshThreshold = 5 * 60 * 1000; // 5 минут
    if (Date.now() < this.tokenExpiry - refreshThreshold) {
      return this.token;
    }

    try {
      // Здесь должен быть вызов API для обновления токена
      // Пока что просто возвращаем текущий токен
      // TODO: Реализовать вызов /auth/refresh/ endpoint
      console.warn('Обновление токена не реализовано');
      return this.token;
    } catch (error) {
      console.error('Ошибка обновления токена:', error);
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
        console.error('Ошибка в callback аутентификации:', error);
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
  public authenticateWith(user: User, token: string, ttlMs: number = 24 * 60 * 60 * 1000): void {
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
