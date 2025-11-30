import { useQuery } from '@tanstack/react-query';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson, LessonFilters } from '@/types/scheduling';

export const useTutorStudentSchedule = (studentId: string | null, filters?: LessonFilters) => {
  const query = useQuery({
    queryKey: ['lessons', 'tutor-student', studentId, filters],
    queryFn: () => (studentId ? schedulingAPI.getStudentSchedule(studentId, filters) : Promise.resolve([])),
    enabled: !!studentId
  });

  return {
    lessons: query.data || [],
    isLoading: query.isLoading,
    error: query.error
  };
};
