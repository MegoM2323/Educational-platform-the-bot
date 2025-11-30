import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { profileAPI, UserProfile, ProfileUpdateData, ApiResponse } from '@/integrations/api/profileAPI';
import { useToast } from '@/hooks/use-toast';
import { logger } from '@/utils/logger';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';

/**
 * Hook configuration for profile queries
 */
const PROFILE_QUERY_CONFIG = {
  staleTime: 5 * 60 * 1000, // 5 minutes
  gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  retry: 2,
  refetchOnWindowFocus: false,
  refetchOnMount: true,
  refetchOnReconnect: true,
};

// ============================================================================
// Student Profile Hooks
// ============================================================================

/**
 * Hook for fetching current student's profile
 * GET /api/auth/profile/student/me/
 *
 * @returns Query result with student profile data
 *
 * @example
 * const { data, isLoading, error } = useStudentProfile();
 *
 * if (isLoading) return <div>Loading...</div>;
 * if (error) return <div>Error: {error.message}</div>;
 *
 * return <div>{data?.user.full_name}</div>;
 */
export const useStudentProfile = (): UseQueryResult<UserProfile, Error> => {
  return useQuery({
    queryKey: ['studentProfile'],
    queryFn: async (): Promise<UserProfile> => {
      logger.debug('[useStudentProfile] Fetching student profile...');

      try {
        const response = await profileAPI.getMyStudentProfile();

        if (!response.success) {
          throw new Error(response.error || 'Failed to fetch student profile');
        }

        if (!response.data) {
          throw new Error('No student profile data returned');
        }

        logger.debug('[useStudentProfile] Student profile loaded successfully');
        return response.data;
      } catch (error) {
        logger.error('[useStudentProfile] Error:', error);
        throw error;
      }
    },
    ...PROFILE_QUERY_CONFIG,
  });
};

/**
 * Hook for updating current student's profile
 * PATCH /api/auth/profile/student/me/
 *
 * @returns Mutation object with updateAsync function
 *
 * @example
 * const { mutate, isPending } = useUpdateStudentProfile();
 *
 * const handleUpdate = async (data) => {
 *   mutate(data, {
 *     onSuccess: () => console.log('Updated!'),
 *     onError: (error) => console.error(error),
 *   });
 * };
 */
export const useUpdateStudentProfile = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: ProfileUpdateData): Promise<UserProfile> => {
      logger.debug('[useUpdateStudentProfile] Updating student profile...');

      const response = await profileAPI.updateStudentProfile(data);

      if (!response.success) {
        throw new Error(response.error || 'Failed to update student profile');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUpdateStudentProfile] Student profile updated successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['studentProfile'] });
      queryClient.setQueryData(['studentProfile'], data);
      toast({
        title: 'Success',
        description: 'Student profile updated successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUpdateStudentProfile] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to update student profile',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Hook for uploading student avatar
 * POST /api/auth/profile/student/me/upload_avatar/
 *
 * @returns Mutation object with upload function
 *
 * @example
 * const { mutate, isPending } = useUploadStudentAvatar();
 *
 * const handleUpload = (file: File) => {
 *   mutate(file);
 * };
 */
export const useUploadStudentAvatar = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (file: File): Promise<UserProfile> => {
      logger.debug('[useUploadStudentAvatar] Uploading avatar...');

      // Validate file
      if (!file.type.startsWith('image/')) {
        throw new Error('Please upload an image file');
      }

      if (file.size > 5 * 1024 * 1024) {
        throw new Error('File size must be less than 5MB');
      }

      const response = await profileAPI.uploadStudentAvatar(file);

      if (!response.success) {
        throw new Error(response.error || 'Failed to upload avatar');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUploadStudentAvatar] Avatar uploaded successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['studentProfile'] });
      queryClient.setQueryData(['studentProfile'], data);
      toast({
        title: 'Success',
        description: 'Avatar uploaded successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUploadStudentAvatar] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to upload avatar',
        variant: 'destructive',
      });
    },
  });
};

// ============================================================================
// Teacher Profile Hooks
// ============================================================================

/**
 * Hook for fetching current teacher's profile
 * GET /api/auth/profile/teacher/me/
 */
export const useTeacherProfile = (): UseQueryResult<UserProfile, Error> => {
  return useQuery({
    queryKey: ['teacherProfile'],
    queryFn: async (): Promise<UserProfile> => {
      logger.debug('[useTeacherProfile] Fetching teacher profile...');

      try {
        const response = await profileAPI.getMyTeacherProfile();

        if (!response.success) {
          throw new Error(response.error || 'Failed to fetch teacher profile');
        }

        if (!response.data) {
          throw new Error('No teacher profile data returned');
        }

        logger.debug('[useTeacherProfile] Teacher profile loaded successfully');
        return response.data;
      } catch (error) {
        logger.error('[useTeacherProfile] Error:', error);
        throw error;
      }
    },
    ...PROFILE_QUERY_CONFIG,
  });
};

/**
 * Hook for updating current teacher's profile
 * PATCH /api/auth/profile/teacher/me/
 */
export const useUpdateTeacherProfile = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: ProfileUpdateData): Promise<UserProfile> => {
      logger.debug('[useUpdateTeacherProfile] Updating teacher profile...');

      const response = await profileAPI.updateTeacherProfile(data);

      if (!response.success) {
        throw new Error(response.error || 'Failed to update teacher profile');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUpdateTeacherProfile] Teacher profile updated successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['teacherProfile'] });
      queryClient.setQueryData(['teacherProfile'], data);
      toast({
        title: 'Success',
        description: 'Teacher profile updated successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUpdateTeacherProfile] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to update teacher profile',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Hook for uploading teacher avatar
 * POST /api/auth/profile/teacher/me/upload_avatar/
 */
export const useUploadTeacherAvatar = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (file: File): Promise<UserProfile> => {
      logger.debug('[useUploadTeacherAvatar] Uploading avatar...');

      if (!file.type.startsWith('image/')) {
        throw new Error('Please upload an image file');
      }

      if (file.size > 5 * 1024 * 1024) {
        throw new Error('File size must be less than 5MB');
      }

      const response = await profileAPI.uploadTeacherAvatar(file);

      if (!response.success) {
        throw new Error(response.error || 'Failed to upload avatar');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUploadTeacherAvatar] Avatar uploaded successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['teacherProfile'] });
      queryClient.setQueryData(['teacherProfile'], data);
      toast({
        title: 'Success',
        description: 'Avatar uploaded successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUploadTeacherAvatar] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to upload avatar',
        variant: 'destructive',
      });
    },
  });
};

// ============================================================================
// Tutor Profile Hooks
// ============================================================================

/**
 * Hook for fetching current tutor's profile
 * GET /api/auth/profile/tutor/me/
 */
export const useTutorProfile = (): UseQueryResult<UserProfile, Error> => {
  return useQuery({
    queryKey: ['tutorProfile'],
    queryFn: async (): Promise<UserProfile> => {
      logger.debug('[useTutorProfile] Fetching tutor profile...');

      try {
        const response = await profileAPI.getMyTutorProfile();

        if (!response.success) {
          throw new Error(response.error || 'Failed to fetch tutor profile');
        }

        if (!response.data) {
          throw new Error('No tutor profile data returned');
        }

        logger.debug('[useTutorProfile] Tutor profile loaded successfully');
        return response.data;
      } catch (error) {
        logger.error('[useTutorProfile] Error:', error);
        throw error;
      }
    },
    ...PROFILE_QUERY_CONFIG,
  });
};

/**
 * Hook for updating current tutor's profile
 * PATCH /api/auth/profile/tutor/me/
 */
export const useUpdateTutorProfile = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: ProfileUpdateData): Promise<UserProfile> => {
      logger.debug('[useUpdateTutorProfile] Updating tutor profile...');

      const response = await profileAPI.updateTutorProfile(data);

      if (!response.success) {
        throw new Error(response.error || 'Failed to update tutor profile');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUpdateTutorProfile] Tutor profile updated successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tutorProfile'] });
      queryClient.setQueryData(['tutorProfile'], data);
      toast({
        title: 'Success',
        description: 'Tutor profile updated successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUpdateTutorProfile] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to update tutor profile',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Hook for uploading tutor avatar
 * POST /api/auth/profile/tutor/me/upload_avatar/
 */
export const useUploadTutorAvatar = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (file: File): Promise<UserProfile> => {
      logger.debug('[useUploadTutorAvatar] Uploading avatar...');

      if (!file.type.startsWith('image/')) {
        throw new Error('Please upload an image file');
      }

      if (file.size > 5 * 1024 * 1024) {
        throw new Error('File size must be less than 5MB');
      }

      const response = await profileAPI.uploadTutorAvatar(file);

      if (!response.success) {
        throw new Error(response.error || 'Failed to upload avatar');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUploadTutorAvatar] Avatar uploaded successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tutorProfile'] });
      queryClient.setQueryData(['tutorProfile'], data);
      toast({
        title: 'Success',
        description: 'Avatar uploaded successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUploadTutorAvatar] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to upload avatar',
        variant: 'destructive',
      });
    },
  });
};

// ============================================================================
// Parent Profile Hooks
// ============================================================================

/**
 * Hook for fetching current parent's profile
 * GET /api/auth/profile/parent/me/
 */
export const useParentProfile = (): UseQueryResult<UserProfile, Error> => {
  return useQuery({
    queryKey: ['parentProfile'],
    queryFn: async (): Promise<UserProfile> => {
      logger.debug('[useParentProfile] Fetching parent profile...');

      try {
        const response = await profileAPI.getMyParentProfile();

        if (!response.success) {
          throw new Error(response.error || 'Failed to fetch parent profile');
        }

        if (!response.data) {
          throw new Error('No parent profile data returned');
        }

        logger.debug('[useParentProfile] Parent profile loaded successfully');
        return response.data;
      } catch (error) {
        logger.error('[useParentProfile] Error:', error);
        throw error;
      }
    },
    ...PROFILE_QUERY_CONFIG,
  });
};

/**
 * Hook for updating current parent's profile
 * PATCH /api/auth/profile/parent/me/
 */
export const useUpdateParentProfile = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: ProfileUpdateData): Promise<UserProfile> => {
      logger.debug('[useUpdateParentProfile] Updating parent profile...');

      const response = await profileAPI.updateParentProfile(data);

      if (!response.success) {
        throw new Error(response.error || 'Failed to update parent profile');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUpdateParentProfile] Parent profile updated successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['parentProfile'] });
      queryClient.setQueryData(['parentProfile'], data);
      toast({
        title: 'Success',
        description: 'Parent profile updated successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUpdateParentProfile] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to update parent profile',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Hook for uploading parent avatar
 * POST /api/auth/profile/parent/me/upload_avatar/
 */
export const useUploadParentAvatar = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (file: File): Promise<UserProfile> => {
      logger.debug('[useUploadParentAvatar] Uploading avatar...');

      if (!file.type.startsWith('image/')) {
        throw new Error('Please upload an image file');
      }

      if (file.size > 5 * 1024 * 1024) {
        throw new Error('File size must be less than 5MB');
      }

      const response = await profileAPI.uploadParentAvatar(file);

      if (!response.success) {
        throw new Error(response.error || 'Failed to upload avatar');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useUploadParentAvatar] Avatar uploaded successfully');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['parentProfile'] });
      queryClient.setQueryData(['parentProfile'], data);
      toast({
        title: 'Success',
        description: 'Avatar uploaded successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useUploadParentAvatar] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to upload avatar',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Unified hook for profile API operations
 * Provides updateProfile and uploadAvatar methods that work with any user role
 * Used by ProfilePage component
 *
 * This hook automatically detects the current user's role and calls the appropriate
 * profile API methods (student, teacher, tutor, or parent).
 *
 * @example
 * const { updateProfile, uploadAvatar, isLoading, error } = useProfileAPI();
 *
 * const handleUpdate = async (data: ProfileUpdateData) => {
 *   try {
 *     const result = await updateProfile(data);
 *     console.log('Profile updated:', result);
 *   } catch (err) {
 *     console.error('Failed to update:', err);
 *   }
 * };
 *
 * const handleAvatarUpload = async (file: File) => {
 *   try {
 *     const result = await uploadAvatar(file);
 *     console.log('Avatar uploaded:', result);
 *   } catch (err) {
 *     console.error('Failed to upload:', err);
 *   }
 * };
 */
export const useProfileAPI = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Update user profile based on their role
   * Automatically determines which profile API method to call
   *
   * @param data - Profile update data
   * @returns Updated user profile
   * @throws Error if user is not authenticated or role is unknown
   */
  const updateProfile = async (data: ProfileUpdateData): Promise<UserProfile> => {
    logger.debug('[useProfileAPI.updateProfile] Starting profile update');

    // Validate user authentication
    if (!user) {
      const errorMsg = 'User not authenticated';
      logger.error('[useProfileAPI.updateProfile] Error:', errorMsg);
      setError(errorMsg);
      throw new Error(errorMsg);
    }

    setIsLoading(true);
    setError(null);

    try {
      let response: ApiResponse<UserProfile>;

      // Determine role and call appropriate API method
      switch (user.role) {
        case 'student':
          logger.debug('[useProfileAPI.updateProfile] Updating student profile');
          response = await profileAPI.updateStudentProfile(data);
          break;

        case 'teacher':
          logger.debug('[useProfileAPI.updateProfile] Updating teacher profile');
          response = await profileAPI.updateTeacherProfile(data);
          break;

        case 'tutor':
          logger.debug('[useProfileAPI.updateProfile] Updating tutor profile');
          response = await profileAPI.updateTutorProfile(data);
          break;

        case 'parent':
          logger.debug('[useProfileAPI.updateProfile] Updating parent profile');
          response = await profileAPI.updateParentProfile(data);
          break;

        default:
          const unknownRoleError = `Unknown user role: ${user.role}`;
          logger.error('[useProfileAPI.updateProfile] Error:', unknownRoleError);
          setError(unknownRoleError);
          throw new Error(unknownRoleError);
      }

      // Handle API response
      if (!response.success) {
        const errorMsg = response.error || 'Failed to update profile';
        logger.error('[useProfileAPI.updateProfile] API Error:', errorMsg);
        setError(errorMsg);
        throw new Error(errorMsg);
      }

      if (!response.data) {
        const errorMsg = 'No response data from server';
        logger.error('[useProfileAPI.updateProfile] Error:', errorMsg);
        setError(errorMsg);
        throw new Error(errorMsg);
      }

      logger.debug('[useProfileAPI.updateProfile] Profile updated successfully');
      return response.data;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error occurred';
      logger.error('[useProfileAPI.updateProfile] Error:', err);
      setError(errorMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Upload user avatar based on their role
   * Automatically determines which avatar upload API method to call
   *
   * @param file - Avatar file to upload
   * @returns Updated user profile with new avatar URL
   * @throws Error if user is not authenticated, role is unknown, or file validation fails
   */
  const uploadAvatar = async (file: File): Promise<UserProfile> => {
    logger.debug('[useProfileAPI.uploadAvatar] Starting avatar upload');

    // Validate user authentication
    if (!user) {
      const errorMsg = 'User not authenticated';
      logger.error('[useProfileAPI.uploadAvatar] Error:', errorMsg);
      setError(errorMsg);
      throw new Error(errorMsg);
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      const errorMsg = 'Please upload an image file (JPEG, PNG, WebP, or GIF)';
      logger.error('[useProfileAPI.uploadAvatar] Error:', errorMsg);
      setError(errorMsg);
      throw new Error(errorMsg);
    }

    // Validate file size (5MB max)
    const maxSizeBytes = 5 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const errorMsg = 'File size must be less than 5MB';
      logger.error('[useProfileAPI.uploadAvatar] Error:', errorMsg);
      setError(errorMsg);
      throw new Error(errorMsg);
    }

    setIsLoading(true);
    setError(null);

    try {
      let response: ApiResponse<UserProfile>;

      // Determine role and call appropriate API method
      switch (user.role) {
        case 'student':
          logger.debug('[useProfileAPI.uploadAvatar] Uploading student avatar');
          response = await profileAPI.uploadStudentAvatar(file);
          break;

        case 'teacher':
          logger.debug('[useProfileAPI.uploadAvatar] Uploading teacher avatar');
          response = await profileAPI.uploadTeacherAvatar(file);
          break;

        case 'tutor':
          logger.debug('[useProfileAPI.uploadAvatar] Uploading tutor avatar');
          response = await profileAPI.uploadTutorAvatar(file);
          break;

        case 'parent':
          logger.debug('[useProfileAPI.uploadAvatar] Uploading parent avatar');
          response = await profileAPI.uploadParentAvatar(file);
          break;

        default:
          const unknownRoleError = `Unknown user role: ${user.role}`;
          logger.error('[useProfileAPI.uploadAvatar] Error:', unknownRoleError);
          setError(unknownRoleError);
          throw new Error(unknownRoleError);
      }

      // Handle API response
      if (!response.success) {
        const errorMsg = response.error || 'Failed to upload avatar';
        logger.error('[useProfileAPI.uploadAvatar] API Error:', errorMsg);
        setError(errorMsg);
        throw new Error(errorMsg);
      }

      if (!response.data) {
        const errorMsg = 'No response data from server';
        logger.error('[useProfileAPI.uploadAvatar] Error:', errorMsg);
        setError(errorMsg);
        throw new Error(errorMsg);
      }

      logger.debug('[useProfileAPI.uploadAvatar] Avatar uploaded successfully');
      return response.data;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error occurred';
      logger.error('[useProfileAPI.uploadAvatar] Error:', err);
      setError(errorMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    updateProfile,
    uploadAvatar,
    isLoading,
    error,
  };
};

/**
 * Hook for reactivating a deactivated profile
 * POST /api/profile/reactivate/
 *
 * @returns Mutation object for reactivating profile
 *
 * @example
 * const { mutate: reactivate, isPending } = useReactivateProfile();
 *
 * const handleReactivate = () => {
 *   reactivate(undefined, {
 *     onSuccess: () => console.log('Profile reactivated!'),
 *     onError: (error) => console.error(error),
 *   });
 * };
 */
export const useReactivateProfile = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (): Promise<UserProfile> => {
      logger.debug('[useReactivateProfile] Reactivating profile...');

      const response = await profileAPI.reactivateProfile();

      if (!response.success) {
        throw new Error(response.error || 'Failed to reactivate profile');
      }

      if (!response.data) {
        throw new Error('No response data');
      }

      logger.debug('[useReactivateProfile] Profile reactivated successfully');
      return response.data;
    },
    onSuccess: (data) => {
      logger.debug('[useReactivateProfile] Invalidating profile cache');
      queryClient.invalidateQueries({ queryKey: ['studentProfile'] });
      queryClient.invalidateQueries({ queryKey: ['teacherProfile'] });
      queryClient.invalidateQueries({ queryKey: ['tutorProfile'] });
      queryClient.invalidateQueries({ queryKey: ['parentProfile'] });

      queryClient.setQueryData(['studentProfile'], data);
      queryClient.setQueryData(['teacherProfile'], data);
      queryClient.setQueryData(['tutorProfile'], data);
      queryClient.setQueryData(['parentProfile'], data);

      toast({
        title: 'Success',
        description: 'Profile reactivated successfully',
      });
    },
    onError: (error: Error) => {
      logger.error('[useReactivateProfile] Error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to reactivate profile',
        variant: 'destructive',
      });
    },
  });
};
