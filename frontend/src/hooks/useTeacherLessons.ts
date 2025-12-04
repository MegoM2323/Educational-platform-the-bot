import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import { Lesson, LessonCreatePayload, LessonUpdatePayload } from '@/types/scheduling';
import { toast } from 'sonner';

export const useTeacherLessons = (filters?: Record<string, any>) => {
  const queryClient = useQueryClient();

  const lessonsQuery = useQuery({
    queryKey: ['lessons', 'teacher', filters],
    queryFn: () => schedulingAPI.getLessons(filters)
  });

  const createMutation = useMutation({
    mutationFn: (payload: LessonCreatePayload) => schedulingAPI.createLesson(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lessons'] });
      toast.success('Урок успешно создан');
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: LessonUpdatePayload }) =>
      schedulingAPI.updateLesson(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lessons'] });
      toast.success('Урок успешно обновлён');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => schedulingAPI.deleteLesson(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lessons'] });
      toast.success('Урок успешно удалён');
    }
  });

  return {
    lessons: lessonsQuery.data || [],
    isLoading: lessonsQuery.isLoading,
    error: lessonsQuery.error,
    createLesson: createMutation.mutate,
    updateLesson: updateMutation.mutate,
    deleteLesson: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending
  };
};
