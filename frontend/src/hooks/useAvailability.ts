import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  schedulingAPI,
  TeacherAvailability,
  CreateAvailabilityData,
  UpdateAvailabilityData,
} from '@/integrations/api/schedulingAPI';
import { toast } from '@/hooks/use-toast';

export function useAvailability(teacherId?: number) {
  const queryKey = ['teacher-availability', teacherId];

  const { data: availability, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () => schedulingAPI.getTeacherAvailability(teacherId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });

  return {
    availability: availability || [],
    isLoading,
    error,
    refetch,
  };
}

export function useCreateAvailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateAvailabilityData) => schedulingAPI.createAvailability(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-availability'] });
      queryClient.invalidateQueries({ queryKey: ['time-slots'] });

      toast({
        title: 'Успех',
        description: 'Расписание доступности создано',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.detail || 'Не удалось создать расписание',
        variant: 'destructive',
      });
    },
  });
}

export function useUpdateAvailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateAvailabilityData }) =>
      schedulingAPI.updateAvailability(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-availability'] });
      queryClient.invalidateQueries({ queryKey: ['time-slots'] });

      toast({
        title: 'Успех',
        description: 'Расписание обновлено',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.detail || 'Не удалось обновить расписание',
        variant: 'destructive',
      });
    },
  });
}

export function useDeleteAvailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => schedulingAPI.deleteAvailability(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-availability'] });
      queryClient.invalidateQueries({ queryKey: ['time-slots'] });

      toast({
        title: 'Успех',
        description: 'Расписание удалено',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.detail || 'Не удалось удалить расписание',
        variant: 'destructive',
      });
    },
  });
}