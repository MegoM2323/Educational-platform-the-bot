import { ReactNode, useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { Navigate } from 'react-router-dom';
import { useIsAuthenticated } from '@/hooks/useProfile';
import { useAuth } from '@/contexts/AuthContext';
import { Spinner } from '@/components/ui/spinner';
import { authService } from '@/services/authService';

export { Spinner };

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: 'student' | 'teacher' | 'parent' | 'tutor';
}

/**
 * Компонент ProtectedRoute защищает маршруты от неавторизованных пользователей
 * Использует useIsAuthenticated hook для проверки статуса авторизации с fallback к AuthContext
 *
 * FIXES (T002):
 * - Добавлена защита от race condition на инициализации
 * - Timeout защита (5 секунд) от бесконечной загрузки
 * - Консолидированная проверка состояния инициализации
 *
 * FIXES (T003):
 * - Добавлена явная проверка effectiveUser перед проверкой роли
 * - Исправлен возможный undefined доступ к effectiveUser.role
 * - Улучшено логирование для отладки состояний авторизации
 *
 * @param {ReactNode} children - Компонент для отображения если пользователь авторизован
 * @param {string} requiredRole - Опционально: требуемая роль пользователя
 *
 * @example
 * // Базовая защита
 * <ProtectedRoute>
 *   <Dashboard />
 * </ProtectedRoute>
 *
 * // С проверкой роли
 * <ProtectedRoute requiredRole="teacher">
 *   <TeacherDashboard />
 * </ProtectedRoute>
 */
export const ProtectedRoute = ({ children, requiredRole }: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading, user, error } = useIsAuthenticated();
  const { user: authContextUser, isLoading: authContextLoading } = useAuth();
  const [initTimeout, setInitTimeout] = useState(false);

  // FIX (T002): Timeout protection - предотвращает бесконечную загрузку
  // Если инициализация занимает больше 5 секунд, логируем предупреждение
  // и разрешаем редирект на signin
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (isLoading || authContextLoading) {
        logger.warn('[ProtectedRoute] Initialization timeout reached (5s)', {
          isLoading,
          authContextLoading,
          hasUser: !!user,
          hasAuthContextUser: !!authContextUser,
          isAuthServiceInitializing: authService.isInitializing()
        });
        setInitTimeout(true);
      }
    }, 5000);

    return () => clearTimeout(timeoutId);
  }, [isLoading, authContextLoading, user, authContextUser]);

  // FIX (T002): Консолидированная проверка состояния инициализации
  // Проверяем ВСЕ источники загрузки перед тем как принять решение
  // Это предотвращает race condition когда один источник загрузился, а другой еще нет
  const isInitializing =
    (isLoading || authContextLoading || authService.isInitializing()) &&
    !initTimeout;

  // Загрузка - показываем spinner (ждём пока ВСЕ источники инициализируются)
  if (isInitializing) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="text-center">
          <Spinner />
          <p className="mt-4 text-gray-600">Проверка авторизации...</p>
        </div>
      </div>
    );
  }

  // FIX (T002): Консолидированная проверка эффективного пользователя
  // CRITICAL: Use authContextUser as PRIMARY source (fresh from login)
  // Only fallback to user from useProfile if authContextUser is not available
  // This prevents stale cached profile data from overriding fresh login data
  const effectiveUser = authContextUser || user;

  // DEBUG: Log user source for troubleshooting
  if (effectiveUser) {
    logger.debug('[ProtectedRoute] Effective user determined:', {
      source: authContextUser ? 'AuthContext' : 'useProfile',
      userId: effectiveUser.id,
      role: effectiveUser.role,
      requiredRole
    });
  }

  // Ошибка при загрузке профиля (например, сессия истекла)
  // НО: если есть effectiveUser, ошибка профиля не критична (используем fallback)
  if (error && !effectiveUser) {
    logger.debug('[ProtectedRoute] Profile error without fallback user, redirecting to signin');
    return <Navigate to="/auth/signin" replace />;
  }

  // Не авторизован - перенаправляем на страницу входа
  // FALLBACK: если useProfile не загрузился, но AuthContext имеет user - считаем авторизованным
  if (!isAuthenticated && !effectiveUser) {
    logger.debug('[ProtectedRoute] Not authenticated, redirecting to signin', {
      isAuthenticated,
      hasEffectiveUser: !!effectiveUser,
      initTimeout
    });
    return <Navigate to="/auth/signin" replace />;
  }

  // FIX (T003): Explicit effectiveUser null check
  // Если после всех проверок инициализации у нас всё еще нет effectiveUser,
  // это означает что пользователь не авторизован (даже если isAuthenticated стало true)
  if (!effectiveUser) {
    logger.debug('[ProtectedRoute] No effective user after loading, redirecting to signin', {
      isAuthenticated,
      hasUser: !!user,
      hasAuthContextUser: !!authContextUser
    });
    return <Navigate to="/auth/signin" replace />;
  }

  // DEBUG: логирование
  if (requiredRole) {
    logger.debug('[ProtectedRoute] Role check:', {
      requiredRole,
      userFromProfile: user?.role,
      userFromContext: authContextUser?.role,
      effectiveUserRole: effectiveUser.role, // Теперь безопасно - effectiveUser точно существует
      match: effectiveUser.role === requiredRole
    });
  }

  // Проверяем требуемую роль
  // SAFE: effectiveUser гарантированно существует после проверки выше
  if (requiredRole && effectiveUser.role !== requiredRole) {
    return (
      <Navigate to="/unauthorized" replace />
    );
  }

  // Авторизован - показываем компонент
  return <>{children}</>;
};

/**
 * Компонент RoleBasedRoute отображает разные компоненты в зависимости от роли пользователя
 *
 * @example
 * <RoleBasedRoute
 *   student={<StudentDashboard />}
 *   teacher={<TeacherDashboard />}
 *   parent={<ParentDashboard />}
 *   tutor={<TutorDashboard />}
 * />
 */
interface RoleBasedRouteProps {
  student?: ReactNode;
  teacher?: ReactNode;
  parent?: ReactNode;
  tutor?: ReactNode;
  fallback?: ReactNode;
}

export const RoleBasedRoute = ({
  student,
  teacher,
  parent,
  tutor,
  fallback,
}: RoleBasedRouteProps) => {
  const { isAuthenticated, isLoading, user } = useIsAuthenticated();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/signin" replace />;
  }

  switch (user?.role) {
    case 'student':
      return student || fallback || <Navigate to="/auth/signin" replace />;
    case 'teacher':
      return teacher || fallback || <Navigate to="/auth/signin" replace />;
    case 'parent':
      return parent || fallback || <Navigate to="/auth/signin" replace />;
    case 'tutor':
      return tutor || fallback || <Navigate to="/auth/signin" replace />;
    default:
      return fallback || <Navigate to="/auth/signin" replace />;
  }
};

/**
 * Hook для использования внутри компонентов для проверки авторизации
 *
 * @deprecated This hook is currently not used in the codebase.
 * Use useIsAuthenticated() or useAuth() instead for auth checks.
 *
 * IMPORTANT: This hook was designed for React Suspense but had an infinite Promise bug.
 * The bug has been fixed, but the hook is not recommended for use without proper Suspense boundaries.
 *
 * @example
 * const ProfileComponent = () => {
 *   const user = useRequireAuth();
 *
 *   return <h1>{user.full_name}</h1>;
 * };
 */
export const useRequireAuth = () => {
  const { isAuthenticated, isLoading, user, error } = useIsAuthenticated();

  // Fixed: Removed infinite Promise that never resolves
  // For Suspense-like behavior, components should use React Suspense with proper boundaries
  if (isLoading) {
    // Instead of throwing an infinite Promise, return null during loading
    // Components using this hook should handle the loading state themselves
    logger.warn('[useRequireAuth] DEPRECATED: This hook is not actively used. Consider using useIsAuthenticated() instead.');
    return null;
  }

  if (error || !isAuthenticated || !user) {
    throw new Error('User is not authenticated');
  }

  return user;
};
