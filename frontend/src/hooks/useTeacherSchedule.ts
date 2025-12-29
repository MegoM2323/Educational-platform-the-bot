import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson } from '@/types/scheduling';
import { logger } from '@/utils/logger';

// Query keys
const TEACHER_SCHEDULE_KEY = 'teacherSchedule';

// Availability hooks are commented out until backend endpoints are implemented
// See useAvailability.ts for the availability feature hooks when they're ready

// Hook for getting full teacher schedule with computed values
export const useTeacherSchedule = (dateFrom?: string, dateTo?: string) => {
  const query = useQuery({
    queryKey: [TEACHER_SCHEDULE_KEY, dateFrom, dateTo],
    queryFn: async () => {
      try {
        return await schedulingAPI.getMySchedule({ date_from: dateFrom, date_to: dateTo });
      } catch (error) {
        logger.error('Error fetching teacher schedule:', error);
        throw error;
      }
    },
    enabled: !!dateFrom && !!dateTo,
    staleTime: 30000, // 30 seconds
  });

  // Group lessons by date
  const lessonsByDate = useMemo(() => {
    const grouped = new Map<string, Lesson[]>();
    (query.data || []).forEach(lesson => {
      const key = lesson.date;
      if (key && !grouped.has(key)) {
        grouped.set(key, []);
      }
      if (key) {
        grouped.get(key)!.push(lesson);
      }
    });
    return Object.fromEntries(grouped);
  }, [query.data]);

  // Filter upcoming lessons
  const upcomingLessons = useMemo(() => {
    return (query.data || []).filter(lesson => lesson.is_upcoming);
  }, [query.data]);

  // Filter today's lessons
  const todayLessons = useMemo(() => {
    const today = new Date().toISOString().split('T')[0];
    return (query.data || []).filter(lesson => lesson.date === today);
  }, [query.data]);

  return {
    lessons: query.data || [],
    lessonsByDate,
    upcomingLessons,
    todayLessons,
    isLoading: query.isLoading,
    error: query.error,
  };
};

// ===== AVAILABILITY HOOKS REMOVED =====
// The following hooks have been removed because the backend API endpoints don't exist yet:
// - useTeacherAvailability
// - useCreateAvailability
// - useUpdateAvailability
// - useDeleteAvailability
// - useGenerateSlots
// - useToggleAvailability
//
// When the backend implements these endpoints, refer to frontend/src/hooks/useAvailability.ts
// for the availability feature implementation.
