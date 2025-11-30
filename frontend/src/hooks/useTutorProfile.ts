import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileAPI, UserProfile } from '@/integrations/api/profileAPI';
import { toast } from 'sonner';

export const useTutorProfile = () => {
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tutorProfile'],
    queryFn: async () => {
      const response = await profileAPI.getMyTutorProfile();
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to fetch tutor profile');
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
      const response = await profileAPI.updateTutorProfile(formData);
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to update tutor profile');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tutorProfile'] });
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
