import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';

/**
 * Unauthorized Page
 * Displayed when user tries to access a route they don't have permission for
 *
 * Examples:
 * - Student tries to access /profile/teacher (requires teacher role)
 * - Teacher tries to access /profile/student (requires student role)
 * - Non-admin tries to access /admin (requires admin role)
 */
export const Unauthorized = () => {
  const navigate = useNavigate();

  const handleGoBack = () => {
    navigate(-1);
  };

  const handleGoHome = () => {
    navigate('/');
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-red-50 to-orange-50">
      <div className="text-center max-w-md px-6">
        <div className="mb-8 flex justify-center">
          <div className="relative">
            <div className="absolute inset-0 bg-red-500 rounded-full opacity-20 animate-pulse"></div>
            <ShieldAlert className="w-24 h-24 text-red-600 relative z-10" />
          </div>
        </div>

        <h1 className="text-5xl font-bold text-gray-900 mb-4">403</h1>
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Доступ запрещён</h2>

        <p className="text-gray-600 mb-8">
          У вас нет прав для доступа к этой странице. Пожалуйста, войдите с правильной ролью или вернитесь на главную страницу.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            onClick={handleGoBack}
            variant="outline"
            className="w-full sm:w-auto"
          >
            Назад
          </Button>
          <Button
            onClick={handleGoHome}
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white"
          >
            На главную
          </Button>
        </div>

        <div className="mt-12 text-sm text-gray-500">
          <p>Если вы считаете, что это ошибка, обратитесь к администратору</p>
        </div>
      </div>
    </div>
  );
};

export default Unauthorized;
