import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileAPI, UserProfile, ProfileUpdateData } from '@/integrations/api/profileAPI';
import { toast } from 'sonner';

export const useStudentProfile = () => {
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['studentProfile'],
    queryFn: async () => {
      const response = await profileAPI.getMyStudentProfile();
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to fetch student profile');
      }
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  const updateMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await profileAPI.updateStudentProfile(formData);
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to update student profile');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['studentProfile'] });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      toast.success('Профиль успешно обновлен');
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : 'Ошибка при обновлении профиля';
      toast.error(message);
    },
  });

  return {
    profile: data,
    isLoading,
    error,
    refetch,
    updateProfile: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
  };
};
