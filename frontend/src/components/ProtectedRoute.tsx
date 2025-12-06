import { ReactNode } from 'react';
import { logger } from '@/utils/logger';
import { Navigate } from 'react-router-dom';
import { useIsAuthenticated } from '@/hooks/useProfile';
import { useAuth } from '@/contexts/AuthContext';
import { Spinner } from '@/components/ui/spinner'

export { Spinner };

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: 'student' | 'teacher' | 'parent' | 'tutor';
}

/**
 * Компонент ProtectedRoute защищает маршруты от неавторизованных пользователей
 * Использует useIsAuthenticated hook для проверки статуса авторизации с fallback к AuthContext
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
  const authContextUser = useAuth().user;

  // Загрузка - показываем spinner
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="text-center">
          <Spinner />
          <p className="mt-4 text-gray-600">Проверка авторизации...</p>
        </div>
      </div>
    );
  }

  // Ошибка при загрузке профиля (например, сессия истекла)
  if (error) {
    return <Navigate to="/auth" replace />;
  }

  // Не авторизован - перенаправляем на страницу входа
  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  // Используем user из профиля или fallback к AuthContext
  const effectiveUser = user || authContextUser;

  // DEBUG: логирование
  if (requiredRole) {
    logger.debug('[ProtectedRoute] Role check:', {
      requiredRole,
      userFromProfile: user?.role,
      userFromContext: authContextUser?.role,
      effectiveUserRole: effectiveUser?.role,
      match: effectiveUser?.role === requiredRole
    });
  }

  // Проверяем требуемую роль
  if (requiredRole && effectiveUser?.role !== requiredRole) {
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
    return <Navigate to="/auth" replace />;
  }

  switch (user?.role) {
    case 'student':
      return student || fallback || <Navigate to="/auth" replace />;
    case 'teacher':
      return teacher || fallback || <Navigate to="/auth" replace />;
    case 'parent':
      return parent || fallback || <Navigate to="/auth" replace />;
    case 'tutor':
      return tutor || fallback || <Navigate to="/auth" replace />;
    default:
      return fallback || <Navigate to="/auth" replace />;
  }
};

/**
 * Hook для использования внутри компонентов для проверки авторизации
 * Выбрасывает ошибку если пользователь не авторизован
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

  if (isLoading) {
    throw new Promise(() => {}); // Suspense-like behavior
  }

  if (error || !isAuthenticated || !user) {
    throw new Error('User is not authenticated');
  }

  return user;
};
