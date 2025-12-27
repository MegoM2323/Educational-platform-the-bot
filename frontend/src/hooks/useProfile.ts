import { useQuery, useQueryClient } from '@tanstack/react-query';
import { unifiedAPI, User, ApiResponse } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Тип ответа для профиля пользователя
 */
export interface ProfileResponse {
  user: User;
  profile?: Record<string, any>;
}

/**
 * Custom hook для управления профилем пользователя с кешированием через TanStack Query
 *
 * Использует роль пользователя из AuthContext для определения правильного API endpoint:
 * - student: /api/profile/student/
 * - teacher: /api/profile/teacher/
 * - tutor: /api/profile/tutor/
 * - parent: /api/profile/parent/
 *
 * @returns {Object} Объект с данными профиля и функциями управления
 * @returns {ProfileResponse | undefined} profileData - Данные профиля пользователя
 * @returns {boolean} isLoading - Флаг загрузки профиля
 * @returns {Error | null} error - Ошибка при загрузке профиля
 * @returns {Function} refetch - Функция для принудительного обновления профиля
 *
 * @example
 * // Использование в компоненте
 * const { profileData, isLoading, error, refetch } = useProfile();
 *
 * if (isLoading) return <div>Загружаю профиль...</div>;
 * if (error) return <div>Ошибка: {error.message}</div>;
 *
 * return (
 *   <div>
 *     <h1>{profileData?.user.full_name}</h1>
 *     <button onClick={() => refetch()}>Обновить</button>
 *   </div>
 * );
 */
export const useProfile = () => {
  const queryClient = useQueryClient();
  const { user: authUser, isLoading: isAuthLoading } = useAuth();

  const {
    data,
    isLoading,
    error,
    refetch,
    isError,
  } = useQuery({
    queryKey: ['profile', authUser?.role],
    queryFn: async (): Promise<ProfileResponse> => {
      logger.debug('[useProfile] Fetching profile...', {
        userRole: authUser?.role,
        userId: authUser?.id,
      });

      try {
        const response = await unifiedAPI.getProfile();

        // Обрабатываем ошибки
        if (!response.success) {
          const errorMessage = response.error || 'Не удалось загрузить профиль';

          // При 401/403 - профиль недоступен (пользователь не авторизован, токен истёк или нет прав)
          // UnifiedClient уже попробовал обновить токен, если это не сработало - сессия истекла
          if (errorMessage.includes('401') || errorMessage.includes('403') ||
              errorMessage.includes('Authentication') || errorMessage.includes('Forbidden')) {
            logger.warn('[useProfile] Authentication/Permission error (401/403), clearing profile cache', {
              errorMessage,
            });

            // Очищаем только кеш профиля, не все запросы (предотвращаем каскадные рефетчи)
            queryClient.removeQueries({ queryKey: ['profile'] });

            // Выбрасываем ошибку, чтобы ProtectedRoute/компоненты обработали редирект
            throw new Error('Сессия истекла или нет прав доступа. Пожалуйста, авторизуйтесь снова');
          }

          // При 404 - профиль не найден
          if (errorMessage.includes('404') || errorMessage.includes('not found')) {
            logger.error('[useProfile] Profile not found (404)');
            throw new Error('Профиль пользователя не найден');
          }

          // Другие ошибки (сеть, сервер)
          logger.error('[useProfile] Error loading profile:', errorMessage);
          throw new Error(errorMessage || 'Неизвестная ошибка при загрузке профиля');
        }

        // Успешно получили данные
        if (!response.data) {
          logger.warn('[useProfile] Response is successful but data is empty');
          throw new Error('Данные профиля отсутствуют');
        }

        logger.debug('[useProfile] Profile loaded successfully', {
          userId: response.data.user?.id,
          email: response.data.user?.email,
          role: response.data.user?.role,
        });

        return response.data;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка';
        logger.error('[useProfile] Query function error:', errorMessage);
        throw err;
      }
    },

    // Конфигурация кеширования
    staleTime: 1000 * 60 * 5, // 5 минут - данные свежие в течение 5 минут
    gcTime: 1000 * 60 * 10, // 10 минут - кеш хранится 10 минут

    // Конфигурация повторов с учётом типа ошибки
    retry: (failureCount, error) => {
      const errorMessage = error instanceof Error ? error.message : String(error);

      // 401/403 - не повторяем (токен невалиден или истёк, refresh уже попробован в unifiedClient)
      if (errorMessage.includes('401') || errorMessage.includes('Authentication') ||
          errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
        logger.debug('[useProfile] Auth error detected, no retries');
        return false;
      }

      // 404 - не повторяем (профиль не существует)
      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        logger.debug('[useProfile] Not found error, no retries');
        return false;
      }

      // Сетевые/серверные ошибки - повторяем до 3 раз
      if (failureCount < 3) {
        logger.debug('[useProfile] Network/server error, retry attempt:', failureCount + 1);
        return true;
      }

      return false;
    },

    // Экспоненциальная задержка между повторами: 1s, 2s, 4s
    retryDelay: (attemptIndex) => Math.min(1000 * Math.pow(2, attemptIndex), 10000),

    // Конфигурация рефетча
    refetchOnWindowFocus: false, // Не обновляем при фокусе на окно (профиль медленно меняется)
    refetchOnMount: true, // Загружаем при монтировании компонента
    refetchOnReconnect: true, // Загружаем при восстановлении соединения

    // Конфигурация обработки ошибок
    throwOnError: true, // Выбрасываем ошибку, чтобы она была доступна в error

    // Запускаем запрос как только AuthContext загрузится (даже если user=null)
    // Если токена нет - API вернет 401, обработаем в queryFn
    // Это решает race condition: login → navigate → ProtectedRoute монтируется до обновления AuthContext
    enabled: !isAuthLoading,
  });

  return {
    profileData: data,
    isLoading: isLoading || isAuthLoading,
    error: error as Error | null,
    refetch,
    isError,
    user: data?.user,
  };
};

/**
 * Hook для получения только пользователя из профиля
 *
 * @returns {User | undefined} Данные пользователя
 *
 * @example
 * const user = useProfileUser();
 * logger.debug(user?.full_name);
 */
export const useProfileUser = (): User | undefined => {
  const { user } = useProfile();
  return user;
};

/**
 * Hook для проверки авторизации пользователя
 *
 * @returns {Object} Объект с информацией об авторизации
 * @returns {boolean} isAuthenticated - Авторизован ли пользователь
 * @returns {boolean} isLoading - Загружаются ли данные
 * @returns {User | undefined} user - Данные пользователя если авторизован
 *
 * @example
 * const { isAuthenticated, isLoading, user } = useIsAuthenticated();
 *
 * if (isLoading) return <div>Проверка авторизации...</div>;
 * if (!isAuthenticated) return <Navigate to="/auth" />;
 *
 * return <Dashboard user={user} />;
 */
export const useIsAuthenticated = () => {
  const { profileData, isLoading, error } = useProfile();

  return {
    isAuthenticated: !!profileData?.user && !error,
    isLoading,
    user: profileData?.user,
    error,
  };
};
