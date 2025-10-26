// Устаревший хук useAuth - используйте AuthContext вместо этого
import { useAuth as useAuthContext } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export const useAuth = () => {
  const authContext = useAuthContext();
  const navigate = useNavigate();

  const signOut = async () => {
    await authContext.logout();
    navigate('/auth');
  };

  return {
    user: authContext.user,
    loading: authContext.isLoading,
    signOut
  };
};
