import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson, LessonFilters } from '@/types/scheduling';

export const useStudentSchedule = (filters?: LessonFilters) => {
  const query = useQuery({
    queryKey: ['lessons', 'student', filters],
    queryFn: () => schedulingAPI.getMySchedule(filters)
  });

  const lessonsBySubject = useMemo(() => {
    const grouped = new Map<string, Lesson[]>();
    (query.data || []).forEach(lesson => {
      const key = lesson.subject_name || lesson.subject;
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
