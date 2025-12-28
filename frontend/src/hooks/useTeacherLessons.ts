import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { logger } from '@/utils/logger';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson, LessonCreatePayload, LessonUpdatePayload } from '@/types/scheduling';
import { toast } from 'sonner';

export const useTeacherLessons = (filters?: Record<string, any>) => {
  const queryClient = useQueryClient();

  const lessonsQuery = useQuery({
    queryKey: ['lessons', 'teacher', filters],
    queryFn: () => schedulingAPI.getLessons(filters)
  });

  const createMutation = useMutation({
    mutationFn: (payload: LessonCreatePayload) => schedulingAPI.createLesson(payload),
    onSuccess: async () => {
      // Инвалидировать ВСЕ запросы lessons/teacher независимо от filters
      await queryClient.invalidateQueries({
        queryKey: ['lessons', 'teacher'],
        exact: false  // Важно: также инвалидирует ['lessons', 'teacher', undefined] и любые другие варианты
      });

      // Принудительно рефетчить активные запросы
      await queryClient.refetchQueries({
        queryKey: ['lessons', 'teacher'],
        type: 'active',
        exact: false
      });

      toast.success('Урок успешно создан');
    },
    onError: (error: any) => {
      const errorMessage = error.message || 'Ошибка при создании урока';
      toast.error(errorMessage);
      logger.error('Create lesson error:', error);
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: LessonUpdatePayload }) => {
      logger.info('[useTeacherLessons] Updating lesson', { id, payload });
      return schedulingAPI.updateLesson(id, payload);
    },
    onSuccess: async (data) => {
      logger.info('[useTeacherLessons] Update success, returned data:', data);

      // Инвалидировать React Query кеш
      await queryClient.invalidateQueries({
        queryKey: ['lessons', 'teacher'],
        exact: false,
        refetchType: 'all'
      });
      logger.info('[useTeacherLessons] Invalidation complete');

      // Принудительно рефетчить активные запросы
      await queryClient.refetchQueries({
        queryKey: ['lessons', 'teacher'],
        type: 'active',
        exact: false
      });
      logger.info('[useTeacherLessons] Refetch complete');

      toast.success('Урок успешно обновлён');
    },
    onError: (error: any) => {
      logger.error('[useTeacherLessons] Update error:', error);
      const errorMessage = error.message || 'Ошибка при обновлении урока';
      toast.error(errorMessage);
      logger.error('Update lesson error:', error);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => schedulingAPI.deleteLesson(id),
    onSuccess: async () => {
      // Инвалидировать React Query кеш
      await queryClient.invalidateQueries({
        queryKey: ['lessons', 'teacher'],
        exact: false
      });

      // Принудительно рефетчить активные запросы
      await queryClient.refetchQueries({
        queryKey: ['lessons', 'teacher'],
        type: 'active',
        exact: false
      });

      toast.success('Урок успешно удалён');
    },
    onError: (error: any) => {
      const errorMessage = error.message || 'Ошибка при удалении урока';
      toast.error(errorMessage);
      logger.error('Delete lesson error:', error);
    }
  });

  return {
    lessons: lessonsQuery.data || [],
    isLoading: lessonsQuery.isLoading,
    error: lessonsQuery.error,
    createLesson: createMutation.mutate,
    updateLesson: updateMutation.mutate,
    deleteLesson: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending
  };
};
