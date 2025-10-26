// React Context для управления состоянием аутентификации
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authService, AuthResult, LoginRequest, User } from '@/services/authService';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<AuthResult>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Инициализация состояния аутентификации
    const initializeAuth = async () => {
      try {
        const currentUser = authService.getCurrentUser();
        const isAuth = authService.isAuthenticated();
        
        if (isAuth && currentUser) {
          setUser(currentUser);
        } else {
          setUser(null);
        }
      } catch (error) {
        console.error('Ошибка инициализации аутентификации:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();

    // Подписываемся на изменения состояния аутентификации
    const unsubscribe = authService.onAuthStateChange((newUser) => {
      setUser(newUser);
      setIsLoading(false);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const login = async (credentials: LoginRequest): Promise<AuthResult> => {
    setIsLoading(true);
    try {
      const result = await authService.login(credentials);
      setUser(result.user);
      return result;
    } catch (error) {
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
    } catch (error) {
      console.error('Ошибка выхода:', error);
      // Даже если произошла ошибка, очищаем состояние
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshToken = async (): Promise<string | null> => {
    try {
      return await authService.refreshTokenIfNeeded();
    } catch (error) {
      console.error('Ошибка обновления токена:', error);
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
