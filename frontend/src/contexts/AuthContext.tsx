// React Context для управления состоянием аутентификации
import { logger } from '@/utils/logger';
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authService, AuthResult, LoginRequest, User } from '@/services/authService';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<AuthResult>;
  logout: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Начинаем с true, чтобы дождаться инициализации

  useEffect(() => {
    // Инициализация состояния аутентификации с задержкой для улучшения LCP
    const initializeAuth = async () => {
      // Небольшая задержка для улучшения LCP
      await new Promise(resolve => setTimeout(resolve, 0));

      try {
        // Ждем завершения инициализации authService (включая refresh токена если нужно)
        await authService.waitForInitialization();

        const currentUser = authService.getCurrentUser();
        const isAuth = authService.isAuthenticated();

        logger.debug('AuthContext init:', {
          currentUser,
          isAuth,
          hasUser: !!currentUser,
          isInitializing: authService.isInitializing()
        });

        if (isAuth && currentUser) {
          setUser(currentUser);
          logger.debug('AuthContext: user set', currentUser);
        } else {
          setUser(null);
          logger.debug('AuthContext: user not authenticated');
        }
      } catch (error) {
        logger.error('Ошибка инициализации аутентификации:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
        logger.debug('AuthContext: isLoading set to false');
      }
    };

    initializeAuth();

    // Дополнительная проверка через короткую задержку — покрывает кейс, когда тесты
    // устанавливают localStorage уже после первого рендера страницы
    const delayedCheck = setTimeout(() => {
      try {
        const currentUser = authService.getCurrentUser();
        if (authService.isAuthenticated() && currentUser) {
          setUser(currentUser);
          setIsLoading(false);
        }
      } catch {}
    }, 150);

    // Реакция на изменения localStorage (например, из Playwright)
    const onStorage = () => {
      try {
        const currentUser = authService.getCurrentUser();
        if (authService.isAuthenticated() && currentUser) {
          setUser(currentUser);
          setIsLoading(false);
        }
      } catch {}
    };
    window.addEventListener('storage', onStorage);

    // Подписываемся на изменения состояния аутентификации
    const unsubscribe = authService.onAuthStateChange((newUser) => {
      setUser(newUser);
      setIsLoading(false);
    });

    return () => {
      unsubscribe();
      window.removeEventListener('storage', onStorage);
      clearTimeout(delayedCheck);
    };
  }, []);

  const login = async (credentials: LoginRequest): Promise<AuthResult> => {
    setIsLoading(true);
    try {
      const result = await authService.login(credentials);

      logger.debug('AuthContext.login: setting user after successful login', {
        userId: result.user?.id,
        role: result.user?.role,
      });

      setUser(result.user);

      // Small delay to ensure token is properly set before any subsequent operations
      await new Promise(resolve => setTimeout(resolve, 100));

      return result;
    } catch (error) {
      logger.error('AuthContext.login: login failed', error);
      setUser(null);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authService.logout();
      setUser(null);
      // Ensure navigation to auth page after successful logout
      if (typeof window !== 'undefined') {
        window.location.href = '/auth';
      }
    } catch (error) {
      logger.error('Ошибка выхода:', error);
      // Даже если произошла ошибка, очищаем состояние
      setUser(null);
      // Force navigation even on error
      if (typeof window !== 'undefined') {
        window.location.href = '/auth';
      }
    } finally {
      setIsLoading(false);
    }
  };

  const refreshToken = async (): Promise<string | null> => {
    try {
      return await authService.refreshTokenIfNeeded();
    } catch (error) {
      logger.error('Ошибка обновления токена:', error);
      setUser(null);
      return null;
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    signOut: logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth должен использоваться внутри AuthProvider');
  }
  return context;
};

// Хук для проверки аутентификации без подписки на изменения
export const useAuthState = (): { user: User | null; isAuthenticated: boolean } => {
  const { user, isAuthenticated } = useAuth();
  return { user, isAuthenticated };
};

// Хук для проверки роли пользователя
export const useUserRole = (): string | null => {
  const { user } = useAuth();
  return user?.role || null;
};

// Хук для проверки, является ли пользователь определенной роли
export const useIsRole = (role: string): boolean => {
  const { user } = useAuth();
  return user?.role === role;
};
