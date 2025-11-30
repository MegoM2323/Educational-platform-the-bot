import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { schedulingAPI, TeacherAvailability, CreateAvailabilityData, UpdateAvailabilityData, GenerateSlotsData } from '@/integrations/api/schedulingAPI';
import { toast } from '@/hooks/use-toast';

// Query keys
const TEACHER_AVAILABILITY_KEY = 'teacherAvailability';
const TEACHER_SCHEDULE_KEY = 'teacherSchedule';

// Hook for getting teacher availability templates
export const useTeacherAvailability = (teacherId?: number) => {
  return useQuery({
    queryKey: [TEACHER_AVAILABILITY_KEY, teacherId],
    queryFn: () => schedulingAPI.getTeacherAvailability(teacherId),
    staleTime: 60000, // 1 minute
  });
};

// Hook for getting full teacher schedule
export const useTeacherSchedule = (dateFrom?: string, dateTo?: string) => {
  return useQuery({
    queryKey: [TEACHER_SCHEDULE_KEY, dateFrom, dateTo],
    queryFn: () => schedulingAPI.getMySchedule(dateFrom, dateTo),
    enabled: !!dateFrom && !!dateTo,
    staleTime: 30000, // 30 seconds
  });
};

// Hook for creating availability template
export const useCreateAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateAvailabilityData) => schedulingAPI.createAvailability(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [TEACHER_AVAILABILITY_KEY] });
      queryClient.invalidateQueries({ queryKey: [TEACHER_SCHEDULE_KEY] });
      toast({
        title: 'Успех',
        description: 'Шаблон доступности создан',
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || error.response?.data?.message || 'Не удалось создать шаблон доступности';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    },
  });
};

// Hook for updating availability template
export const useUpdateAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateAvailabilityData }) =>
      schedulingAPI.updateAvailability(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [TEACHER_AVAILABILITY_KEY] });
      queryClient.invalidateQueries({ queryKey: [TEACHER_SCHEDULE_KEY] });
      toast({
        title: 'Успех',
        description: 'Шаблон доступности обновлен',
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || error.response?.data?.message || 'Не удалось обновить шаблон';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    },
  });
};

// Hook for deleting availability template (soft delete)
export const useDeleteAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => schedulingAPI.deleteAvailability(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [TEACHER_AVAILABILITY_KEY] });
      queryClient.invalidateQueries({ queryKey: [TEACHER_SCHEDULE_KEY] });
      toast({
        title: 'Успех',
        description: data.message || 'Шаблон доступности деактивирован',
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || error.response?.data?.message || 'Не удалось удалить шаблон';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    },
  });
};

// Hook for generating time slots from template
export const useGenerateSlots = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ availabilityId, data }: { availabilityId: number; data: GenerateSlotsData }) =>
      schedulingAPI.generateSlots(availabilityId, data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: [TEACHER_SCHEDULE_KEY] });
      toast({
        title: 'Успех',
        description: response.message || `Сгенерировано ${response.slots?.length || 0} слотов`,
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || error.response?.data?.message || 'Не удалось сгенерировать слоты';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    },
  });
};

// Hook for toggling availability active status
export const useToggleAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (availabilityId: number) => schedulingAPI.toggleAvailability(availabilityId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [TEACHER_AVAILABILITY_KEY] });
      queryClient.invalidateQueries({ queryKey: [TEACHER_SCHEDULE_KEY] });
      toast({
        title: 'Успех',
        description: data.message || 'Статус изменен',
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || error.response?.data?.message || 'Не удалось изменить статус';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    },
  });
};
