// React Context для управления состоянием аутентификации
import { logger } from '@/utils/logger';
import React, { createContext, useContext, useEffect, useState, ReactNode, useMemo, useCallback } from 'react';
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
      const contextInitStart = Date.now();

      // Небольшая задержка для улучшения LCP
      await new Promise(resolve => setTimeout(resolve, 0));

      try {
        logger.debug('[AuthContext] Starting initialization...');

        // ✅ FIX (T002): Reduced timeout from 15s to 5s
        // AuthService no longer refreshes tokens on init, so initialization is fast (< 1s)
        // 5s timeout is a safety net for edge cases
        const timeoutPromise = new Promise((resolve) =>
          setTimeout(() => {
            const elapsed = Date.now() - contextInitStart;
            logger.warn(`[AuthContext] Initialization timeout after ${elapsed}ms, continuing without auth`);
            resolve(null);
          }, 5000)
        );

        await Promise.race([
          authService.waitForInitialization(),
          timeoutPromise
        ]);

        const currentUser = authService.getCurrentUser();
        const isAuth = authService.isAuthenticated();

        const contextInitDuration = Date.now() - contextInitStart;
        logger.debug('[AuthContext] Init complete:', {
          hasUser: !!currentUser,
          isAuth,
          userId: currentUser?.id,
          userRole: currentUser?.role,
          isInitializing: authService.isInitializing(),
          durationMs: contextInitDuration
        });

        if (isAuth && currentUser) {
          setUser(currentUser);
          logger.debug('[AuthContext] User authenticated:', {
            userId: currentUser.id,
            role: currentUser.role
          });
        } else {
          setUser(null);
          logger.debug('[AuthContext] User not authenticated');
        }
      } catch (error) {
        logger.error('[AuthContext] Initialization error:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
        logger.debug('[AuthContext] isLoading set to false');
      }
    };

    initializeAuth();

    // Дополнительная проверка через короткую задержку — покрывает кейс, когда тесты
    // устанавливают localStorage уже после первого рендера страницы
    const delayedCheck = setTimeout(() => {
      try {
        const currentUser = authService.getCurrentUser();
        if (authService.isAuthenticated() && currentUser) {
          logger.debug('[AuthContext] Delayed check: user found, updating state');
          setUser(currentUser);
          setIsLoading(false);
        }
      } catch (error) {
        logger.error('[AuthContext] Delayed check error:', error);
      }
    }, 150);

    // Реакция на изменения localStorage (например, из Playwright или другая вкладка)
    const onStorage = () => {
      try {
        const currentUser = authService.getCurrentUser();
        if (authService.isAuthenticated() && currentUser) {
          logger.debug('[AuthContext] Storage event: user found, updating state');
          setUser(currentUser);
          setIsLoading(false);
        }
      } catch (error) {
        logger.error('[AuthContext] Storage event error:', error);
      }
    };
    window.addEventListener('storage', onStorage);

    // Подписываемся на изменения состояния аутентификации
    const unsubscribe = authService.onAuthStateChange((newUser) => {
      logger.debug('[AuthContext] Auth state changed:', {
        hasUser: !!newUser,
        userId: newUser?.id,
        role: newUser?.role
      });
      setUser(newUser);
      setIsLoading(false);
    });

    return () => {
      unsubscribe();
      window.removeEventListener('storage', onStorage);
      clearTimeout(delayedCheck);
    };
  }, []);

  const login = useCallback(async (credentials: LoginRequest): Promise<AuthResult> => {
    setIsLoading(true);
    try {
      logger.debug('[AuthContext.login] Starting login...');

      const result = await authService.login(credentials);

      logger.debug('[AuthContext.login] Login successful, setting user:', {
        userId: result.user?.id,
        role: result.user?.role,
      });

      setUser(result.user);

      logger.debug('[AuthContext.login] User state updated, login complete');

      return result;
    } catch (error) {
      logger.error('[AuthContext.login] Login failed:', error);
      setUser(null);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
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
  }, []);

  const refreshToken = useCallback(async (): Promise<string | null> => {
    try {
      return await authService.refreshTokenIfNeeded();
    } catch (error) {
      logger.error('Ошибка обновления токена:', error);
      setUser(null);
      return null;
    }
  }, []);

  const value: AuthContextType = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      signOut: logout,
      refreshToken,
    }),
    [user, isLoading, login, logout, refreshToken]
  );

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
  return useMemo(() => user?.role === role, [user?.role, role]);
};

// Selectors to prevent re-renders
export const useAuthUser = () => {
  const { user } = useAuth();
  return useMemo(() => user, [user?.id, user?.role, user?.email]);
};

export const useAuthLoading = () => {
  const { isLoading } = useAuth();
  return isLoading;
};

export const useAuthMethods = () => {
  const { login, logout, refreshToken } = useAuth();
  return useMemo(() => ({ login, logout, refreshToken }), [login, logout, refreshToken]);
};
