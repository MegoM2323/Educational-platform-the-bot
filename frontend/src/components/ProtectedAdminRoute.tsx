import { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';

interface ProtectedAdminRouteProps {
  children: ReactNode;
}

export const ProtectedAdminRoute = ({ children }: ProtectedAdminRouteProps) => {
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

  if (!user.is_staff) {
    // Недостаточно прав — отправляем в личный кабинет по роли
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


