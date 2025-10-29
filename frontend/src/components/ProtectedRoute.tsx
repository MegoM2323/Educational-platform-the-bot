import { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
}

export const ProtectedRoute = ({ children, requiredRole }: ProtectedRouteProps) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  // Проверка соответствия роли при необходимости
  if (requiredRole && user.role !== requiredRole) {
    // Редиректим в корректный кабинет пользователя
    const roleToPath: Record<string, string> = {
      student: '/dashboard/student',
      teacher: '/dashboard/teacher',
      tutor: '/dashboard/tutor',
      parent: '/dashboard/parent',
    };
    return <Navigate to={roleToPath[user.role] || '/'} replace />;
  }

  return <>{children}</>;
};
