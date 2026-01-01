import { useQuery } from '@tanstack/react-query';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson, LessonFilters } from '@/types/scheduling';
import { logger } from '@/utils/logger';

/**
 * Hook для получения расписания конкретного студента тьютора
 * @param studentId - ID студента (может быть null, в этом случае запрос отключен)
 * @param filters - Фильтры для расписания
 */
export const useTutorStudentSchedule = (studentId: string | null, filters?: LessonFilters) => {
  const queryKey = [
    'tutor',
    'student',
    studentId,
    filters?.date_from ?? null,
    filters?.date_to ?? null,
    filters?.subject ?? null,
    filters?.status ?? null,
  ] as const;

  const query = useQuery<Lesson[]>({
    queryKey,
    queryFn: async () => {
      if (!studentId) {
        logger.warn('[useTutorStudentSchedule] studentId is null, returning empty array');
        return [];
      }

      try {
        logger.debug('[useTutorStudentSchedule] Fetching schedule for student:', studentId);
        const lessons = await schedulingAPI.getStudentSchedule(studentId, filters);
        logger.debug('[useTutorStudentSchedule] Fetched lessons:', lessons?.length || 0);
        return lessons || [];
      } catch (error) {
        logger.error('[useTutorStudentSchedule] Error fetching schedule:', error);
        throw error;
      }
    },
    enabled: !!studentId,
    staleTime: 30000, // 30 секунд
    gcTime: 60000, // 1 минута
    retry: 2,
  });

  return {
    lessons: query.data || [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
};
