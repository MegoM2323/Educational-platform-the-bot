import { useQuery } from '@tanstack/react-query';
import { adminAPI } from '@/integrations/api/adminAPI';

interface UseAdminScheduleParams {
  teacher_id?: string;
  subject_id?: string;
  student_id?: string;
  date_from?: string;
  date_to?: string;
  status?: string;
}

export const useAdminSchedule = (params: UseAdminScheduleParams = {}) => {
  const {
    data: scheduleData,
    isLoading: scheduleLoading,
    error: scheduleError,
    refetch: refetchSchedule
  } = useQuery({
    // Spread params properties to avoid mutable object reference in queryKey
    // This ensures proper cache invalidation when individual params change
    queryKey: ['admin', 'schedule', params?.teacher_id, params?.subject_id, params?.student_id, params?.date_from, params?.date_to, params?.status],
    queryFn: () => adminAPI.getSchedule(params),
    // Only enable query when required date range is provided
    enabled: !!(params?.date_from && params?.date_to),
    staleTime: 60000, // 1 minute
  });

  const {
    data: filtersData,
    isLoading: filtersLoading,
    error: filtersError,
  } = useQuery({
    queryKey: ['admin', 'schedule', 'filters'],
    queryFn: () => adminAPI.getScheduleFilters(),
    staleTime: 300000, // 5 minutes
  });

  return {
    lessons: scheduleData?.lessons ?? [],
    teachers: filtersData?.teachers ?? [],
    subjects: filtersData?.subjects ?? [],
    students: filtersData?.students ?? [],
    isLoading: scheduleLoading || filtersLoading,
    error: scheduleError?.message,
    filtersError: filtersError?.message,
    refetch: refetchSchedule,
  };
};