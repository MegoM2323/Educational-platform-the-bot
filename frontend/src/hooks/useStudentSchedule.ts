import { useQuery } from '@tanstack/react-query';
import { logger } from '@/utils/logger';
import { useMemo } from 'react';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson, LessonFilters } from '@/types/scheduling';

export const useStudentSchedule = (filters?: LessonFilters) => {
  const query = useQuery({
    // QueryKey структура: каждое поле фильтра отдельно для стабильных ссылок
    // Это предотвращает ненужные ре-рендеры при изменении объекта filters
    queryKey: ['lessons', 'student', filters?.date_from, filters?.date_to, filters?.subject, filters?.status],
    queryFn: async () => {
      try {
        // Используем getMySchedule() - специализированный endpoint для студентов
        // Backend автоматически фильтрует уроки по текущему пользователю
        return await schedulingAPI.getMySchedule(filters);
      } catch (error) {
        logger.error('Error fetching student schedule:', error);
        throw error;
      }
    },
    retry: 1,
    staleTime: 60000, // 1 minute
    refetchOnMount: true,        // FIX F002 - Force fetch on component mount
    refetchOnWindowFocus: false, // Prevent unnecessary refetches
  });

  const lessonsBySubject = useMemo(() => {
    const grouped = new Map<string, Lesson[]>();
    (query.data || []).forEach(lesson => {
      const key = lesson.subject_name || lesson.subject || 'unknown';
      if (!grouped.has(key)) {
        grouped.set(key, []);
      }
      grouped.get(key)!.push(lesson);
    });
    return Object.fromEntries(grouped);
  }, [query.data]);

  const upcomingLessons = useMemo(() => {
    return (query.data || []).filter(lesson => lesson.is_upcoming);
  }, [query.data]);

  return {
    lessons: query.data || [],
    lessonsBySubject,
    upcomingLessons,
    isLoading: query.isLoading,
    error: query.error
  };
};
