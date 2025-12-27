import { useQuery } from '@tanstack/react-query';
import { schedulingAPI, TimeSlotFilters, TimeSlot } from '@/integrations/api/schedulingAPI';

export function useTimeSlots(filters: TimeSlotFilters, enabled = true) {
  const queryKey = ['time-slots', filters];

  const { data: timeSlots, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () => schedulingAPI.getAvailableTimeSlots(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes - shorter because availability changes frequently
    cacheTime: 5 * 60 * 1000, // 5 minutes
    enabled: enabled && !!filters.from_date && !!filters.to_date,
  });

  return {
    timeSlots: timeSlots || [],
    isLoading,
    error,
    refetch,
  };
}

export function useTeachersWithSubjects() {
  const queryKey = ['teachers-with-subjects'];

  const { data: teachers, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => schedulingAPI.getTeachersWithSubjects(),
    staleTime: 10 * 60 * 1000, // 10 minutes
    cacheTime: 15 * 60 * 1000, // 15 minutes
  });

  return {
    teachers: teachers || [],
    isLoading,
    error,
  };
}