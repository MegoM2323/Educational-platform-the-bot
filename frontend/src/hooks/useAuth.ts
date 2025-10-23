import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient, User } from '@/integrations/api/client';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Проверяем, есть ли токен в localStorage
    const checkAuth = async () => {
      const token = localStorage.getItem('authToken');
      const userData = localStorage.getItem('userData');
      
      if (token && userData) {
        try {
          // Устанавливаем токен в API клиент
          apiClient.setToken(token);
          
          // Проверяем, действителен ли токен
          const response = await apiClient.getProfile();
          
          if (response.data) {
            setUser(response.data.user);
          } else {
            // Токен недействителен, очищаем localStorage
            localStorage.removeItem('authToken');
            localStorage.removeItem('userData');
            setUser(null);
          }
        } catch (error) {
          console.error('Auth check error:', error);
          localStorage.removeItem('authToken');
          localStorage.removeItem('userData');
          setUser(null);
        }
      } else {
        setUser(null);
      }
      
      setLoading(false);
    };

    checkAuth();
  }, []);

  const signOut = async () => {
    try {
      await apiClient.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    setUser(null);
    navigate('/auth');
  };

  return {
    user,
    loading,
    signOut
  };
};
