import { useState, useEffect } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';
import { useNavigate } from 'react-router-dom';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Получаем текущую сессию
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      setLoading(false);
    };

    getSession();

    // Слушаем изменения аутентификации
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setUser(session?.user ?? null);
        setLoading(false);

        if (event === 'SIGNED_IN' && session?.user) {
          // Получаем роль пользователя для переадресации
          const { data: roles } = await supabase
            .from('user_roles')
            .select('role')
            .eq('user_id', session.user.id);

          const userRole = roles?.[0]?.role || 'student';
          
          // Переадресация в зависимости от роли
          switch (userRole) {
            case 'student':
              navigate('/dashboard/student');
              break;
            case 'teacher':
              navigate('/dashboard/teacher');
              break;
            case 'tutor':
              navigate('/dashboard/tutor');
              break;
            case 'parent':
              navigate('/dashboard/parent');
              break;
            default:
              navigate('/dashboard/student');
          }
        }

        if (event === 'SIGNED_OUT') {
          navigate('/auth');
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [navigate]);

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return {
    user,
    loading,
    signOut
  };
};
