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

      if (storedToken && storedUser && storedExpiry) {
        // Проверяем, не истек ли токен
        if (Date.now() < storedExpiry) {
          this.token = storedToken;
          this.user = storedUser;
          this.refreshToken = storedRefreshToken;
          this.tokenExpiry = storedExpiry;
          apiClient.setToken(storedToken);
        } else {
          // Токен истек, пытаемся обновить
          this.refreshTokenIfNeeded();
        }
      }
    } catch (error) {
      console.error('Ошибка инициализации аутентификации:', error);
      this.clearStorage();
    }
  }

  private getStoredToken(): string | null {
    return secureStorage.getAuthToken();
  }

  private getStoredUser(): User | null {
    return secureStorage.getUserData();
  }

  private getStoredRefreshToken(): string | null {
    return secureStorage.getRefreshToken();
  }

  private getStoredTokenExpiry(): number | null {
    const expiry = secureStorage.getItem('token_expiry');
    return expiry ? parseInt(expiry, 10) : null;
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
}

// Экспортируем singleton instance
export const authService = AuthService.getInstance();

// Экспортируем класс для тестирования
export { AuthService };
