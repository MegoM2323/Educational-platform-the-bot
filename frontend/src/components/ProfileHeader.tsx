import { useProfileUser } from '@/hooks/useProfile';
import { useNavigate } from 'react-router-dom';
import { LogOut, Settings } from 'lucide-react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { useToast } from '@/hooks/use-toast';

/**
 * Компонент ProfileHeader отображает информацию о профиле пользователя в header
 * Использует useProfileUser hook для получения данных пользователя
 *
 * @example
 * import { ProfileHeader } from '@/components/ProfileHeader';
 *
 * export const Header = () => {
 *   return (
 *     <header className="bg-white shadow">
 *       <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
 *         <h1 className="text-2xl font-bold">THE BOT</h1>
 *         <ProfileHeader />
 *       </div>
 *     </header>
 *   );
 * };
 */
export const ProfileHeader = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const user = useProfileUser();

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    try {
      const response = await unifiedAPI.logout();

      if (response.success) {
        toast({
          title: "Успешно",
          description: "Вы вышли из системы",
        });
        navigate('/auth', { replace: true });
      } else {
        throw new Error(response.error || 'Ошибка при выходе');
      }
    } catch (error) {
      console.error('[ProfileHeader] Logout error:', error);
      toast({
        title: "Ошибка",
        description: error instanceof Error ? error.message : 'Ошибка при выходе',
        variant: "destructive",
      });
      // Всё равно перенаправляем на страницу входа
      navigate('/auth', { replace: true });
    }
  };

  return (
    <div className="flex items-center gap-4">
      <div className="text-right">
        <p className="font-semibold text-gray-900">{user.full_name}</p>
        <p className="text-sm text-gray-500">{user.role_display}</p>
      </div>

      {user.avatar && (
        <img
          src={user.avatar}
          alt={user.full_name}
          className="w-10 h-10 rounded-full"
        />
      )}

      <div className="flex gap-2 border-l pl-4">
        <button
          onClick={() => navigate('/profile/edit')}
          title="Настройки профиля"
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
        >
          <Settings size={20} />
        </button>

        <button
          onClick={handleLogout}
          title="Выход"
          className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
        >
          <LogOut size={20} />
        </button>
      </div>
    </div>
  );
};
