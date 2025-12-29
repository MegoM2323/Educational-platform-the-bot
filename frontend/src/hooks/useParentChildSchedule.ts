import { useQuery } from '@tanstack/react-query';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson } from '@/types/scheduling';

interface UseParentChildScheduleOptions {
  dateFrom?: string;
  dateTo?: string;
  subjectId?: string;
  status?: string;
}

interface ParentChildScheduleResult {
  student: {
    id: string;
    name: string;
    email: string;
  };
  lessons: Lesson[];
  totalLessons: number;
}

export function useParentChildSchedule(
  childId: string | null,
  options: UseParentChildScheduleOptions = {}
) {
  return useQuery<ParentChildScheduleResult>({
    // queryKey: spread options properties to avoid unstable object references
    // Structure: [scope, feature, childId, ...filter params]
    // This ensures proper cache invalidation when any filter changes
    queryKey: ['lessons', 'parent-child', childId, options?.dateFrom, options?.dateTo, options?.subjectId, options?.status],
    queryFn: async () => {
      if (!childId) throw new Error('No child selected');
      const response = await schedulingAPI.getParentChildSchedule(childId, {
        date_from: options.dateFrom,
        date_to: options.dateTo,
        subject_id: options.subjectId,
        status: options.status,
      });
      return {
        student: response.student,
        lessons: response.lessons,
        totalLessons: response.total_lessons,
      };
    },
    enabled: !!childId,
    staleTime: 30000,
    refetchOnMount: true,
  });
}
