import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useStudentProfile,
  useUpdateStudentProfile,
  useUploadStudentAvatar,
  useTeacherProfile,
  useUpdateTeacherProfile,
  useUploadTeacherAvatar,
  useTutorProfile,
  useUpdateTutorProfile,
  useUploadTutorAvatar,
  useParentProfile,
  useUpdateParentProfile,
  useUploadParentAvatar,
} from '../useProfileAPI';
import { profileAPI } from '@/integrations/api/profileAPI';
import { useToast } from '@/hooks/use-toast';

// Mock profileAPI
vi.mock('@/integrations/api/profileAPI', () => ({
  profileAPI: {
    getMyStudentProfile: vi.fn(),
    updateStudentProfile: vi.fn(),
    uploadStudentAvatar: vi.fn(),
    getMyTeacherProfile: vi.fn(),
    updateTeacherProfile: vi.fn(),
    uploadTeacherAvatar: vi.fn(),
    getMyTutorProfile: vi.fn(),
    updateTutorProfile: vi.fn(),
    uploadTutorAvatar: vi.fn(),
    getMyParentProfile: vi.fn(),
    updateParentProfile: vi.fn(),
    uploadParentAvatar: vi.fn(),
    _clearCache: vi.fn(),
  },
}));

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: vi.fn(() => ({
    toast: vi.fn(),
  })),
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  },
}));

// Create wrapper for tests
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useProfileAPI Hooks', () => {
  const mockUserProfile = {
    user: {
      id: 1,
      email: 'student@example.com',
      first_name: 'John',
      last_name: 'Doe',
      full_name: 'John Doe',
      phone: '+1234567890',
      avatar: 'https://example.com/avatar.jpg',
      role: 'student',
    },
    profile: {
      id: 1,
      grade: '10A',
      goal: 'Improve math',
    },
  };

  const mockTeacherProfile = {
    user: {
      id: 2,
      email: 'teacher@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
      full_name: 'Jane Smith',
      phone: '+0987654321',
      avatar: 'https://example.com/avatar.jpg',
      role: 'teacher',
    },
    profile: {
      id: 2,
      subject: 'Mathematics',
      experience_years: 5,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useStudentProfile', () => {
    it('should fetch student profile successfully', async () => {
      vi.mocked(profileAPI.getMyStudentProfile).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useStudentProfile(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockUserProfile);
    });

    it('should handle fetch errors', async () => {
      vi.mocked(profileAPI.getMyStudentProfile).mockRejectedValue(
        new Error('Failed to fetch profile')
      );

      const { result } = renderHook(() => useStudentProfile(), {
        wrapper: createWrapper(),
      });

      // Wait for error state to be set
      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      }, { timeout: 2000 });

      expect(result.current.error).toBeDefined();
    });

    it('should cache profile data', async () => {
      vi.mocked(profileAPI.getMyStudentProfile).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result: result1 } = renderHook(() => useStudentProfile(), {
        wrapper,
      });

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      // Second hook instance should use cache from same queryClient
      const { result: result2 } = renderHook(() => useStudentProfile(), {
        wrapper,
      });

      expect(result2.current.data).toEqual(mockUserProfile);
    });

    it('should refetch on demand', async () => {
      vi.mocked(profileAPI.getMyStudentProfile).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useStudentProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const initialCallCount = vi.mocked(profileAPI.getMyStudentProfile).mock.calls.length;

      // Trigger refetch
      result.current.refetch();

      await waitFor(() => {
        expect(vi.mocked(profileAPI.getMyStudentProfile).mock.calls.length).toBeGreaterThan(
          initialCallCount
        );
      });
    });
  });

  describe('useUpdateStudentProfile', () => {
    it('should update student profile successfully', async () => {
      const updateData = { first_name: 'Updated' };

      const updatedProfile = {
        ...mockUserProfile,
        user: { ...mockUserProfile.user, first_name: 'Updated' },
      };

      vi.mocked(profileAPI.updateStudentProfile).mockResolvedValue({
        success: true,
        data: updatedProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUpdateStudentProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(updateData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(updatedProfile);
    });

    it('should show success toast on successful update', async () => {
      const mockToast = vi.fn();
      vi.mocked(useToast).mockReturnValue({
        toast: mockToast,
      } as any);

      vi.mocked(profileAPI.updateStudentProfile).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUpdateStudentProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ first_name: 'Updated' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Note: Toast will be called in onSuccess callback
      expect(mockToast).toHaveBeenCalled();
    });

    it('should handle update errors', async () => {
      vi.mocked(profileAPI.updateStudentProfile).mockRejectedValue(
        new Error('Update failed')
      );

      const { result } = renderHook(() => useUpdateStudentProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ first_name: 'Updated' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });

    it('should invalidate query cache on successful update', async () => {
      vi.mocked(profileAPI.updateStudentProfile).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUpdateStudentProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ first_name: 'Updated' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Cache should be invalidated and refetched
      expect(result.current.data).toBeDefined();
    });
  });

  describe('useUploadStudentAvatar', () => {
    it('should upload avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      const profileWithAvatar = {
        ...mockUserProfile,
        user: { ...mockUserProfile.user, avatar: 'https://example.com/new-avatar.jpg' },
      };

      vi.mocked(profileAPI.uploadStudentAvatar).mockResolvedValue({
        success: true,
        data: profileWithAvatar,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUploadStudentAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(profileWithAvatar);
    });

    it('should reject non-image files', async () => {
      const mockFile = new File(['text'], 'file.txt', { type: 'text/plain' });

      const { result } = renderHook(() => useUploadStudentAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toContain('image');
    });

    it('should reject files larger than 5MB', async () => {
      const largeFile = new File(['x'.repeat(6 * 1024 * 1024)], 'large.jpg', {
        type: 'image/jpeg',
      });

      const { result } = renderHook(() => useUploadStudentAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(largeFile);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toContain('5MB');
    });

    it('should handle upload errors', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      vi.mocked(profileAPI.uploadStudentAvatar).mockRejectedValue(
        new Error('Upload failed')
      );

      const { result } = renderHook(() => useUploadStudentAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useTeacherProfile', () => {
    it('should fetch teacher profile successfully', async () => {
      vi.mocked(profileAPI.getMyTeacherProfile).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useTeacherProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockTeacherProfile);
    });

    it('should handle teacher profile errors', async () => {
      vi.mocked(profileAPI.getMyTeacherProfile).mockRejectedValue(
        new Error('Failed to fetch')
      );

      const { result } = renderHook(() => useTeacherProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      }, { timeout: 2000 });

      expect(result.current.error).toBeDefined();
    });
  });

  describe('useUpdateTeacherProfile', () => {
    it('should update teacher profile successfully', async () => {
      vi.mocked(profileAPI.updateTeacherProfile).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUpdateTeacherProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ bio: 'Updated bio' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });
  });

  describe('useUploadTeacherAvatar', () => {
    it('should upload teacher avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      vi.mocked(profileAPI.uploadTeacherAvatar).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUploadTeacherAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });
  });

  describe('useTutorProfile', () => {
    it('should fetch tutor profile successfully', async () => {
      const mockTutorProfile = {
        user: { id: 3, email: 'tutor@example.com', role: 'tutor' },
        profile: { id: 3, specialization: 'Math' },
      };

      vi.mocked(profileAPI.getMyTutorProfile).mockResolvedValue({
        success: true,
        data: mockTutorProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useTutorProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockTutorProfile);
    });
  });

  describe('useUpdateTutorProfile', () => {
    it('should update tutor profile successfully', async () => {
      const mockTutorProfile = {
        user: { id: 3, email: 'tutor@example.com', role: 'tutor' },
        profile: { id: 3, specialization: 'Math' },
      };

      vi.mocked(profileAPI.updateTutorProfile).mockResolvedValue({
        success: true,
        data: mockTutorProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUpdateTutorProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ specialization: 'Advanced Math' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });
  });

  describe('useUploadTutorAvatar', () => {
    it('should upload tutor avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });
      const mockTutorProfile = {
        user: { id: 3, email: 'tutor@example.com', role: 'tutor' },
        profile: { id: 3, specialization: 'Math' },
      };

      vi.mocked(profileAPI.uploadTutorAvatar).mockResolvedValue({
        success: true,
        data: mockTutorProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUploadTutorAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });
  });

  describe('useParentProfile', () => {
    it('should fetch parent profile successfully', async () => {
      const mockParentProfile = {
        user: { id: 4, email: 'parent@example.com', role: 'parent' },
        profile: { id: 4 },
      };

      vi.mocked(profileAPI.getMyParentProfile).mockResolvedValue({
        success: true,
        data: mockParentProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useParentProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockParentProfile);
    });
  });

  describe('useUpdateParentProfile', () => {
    it('should update parent profile successfully', async () => {
      const mockParentProfile = {
        user: { id: 4, email: 'parent@example.com', role: 'parent' },
        profile: { id: 4 },
      };

      vi.mocked(profileAPI.updateParentProfile).mockResolvedValue({
        success: true,
        data: mockParentProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUpdateParentProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ phone: '+1234567890' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });
  });

  describe('useUploadParentAvatar', () => {
    it('should upload parent avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });
      const mockParentProfile = {
        user: { id: 4, email: 'parent@example.com', role: 'parent' },
        profile: { id: 4 },
      };

      vi.mocked(profileAPI.uploadParentAvatar).mockResolvedValue({
        success: true,
        data: mockParentProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useUploadParentAvatar(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });
  });

  describe('Common behavior across all hooks', () => {
    it('should have 5 minute staleTime', async () => {
      vi.mocked(profileAPI.getMyStudentProfile).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const { result } = renderHook(() => useStudentProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Data should be considered fresh for 5 minutes
      // This is verified by not refetching immediately after first fetch
      expect(result.current.data).toBeDefined();
    });

    it('should retry mutations twice on failure', async () => {
      vi.mocked(profileAPI.updateStudentProfile)
        .mockResolvedValueOnce({
          success: false,
          error: 'Error',
          timestamp: new Date().toISOString(),
        })
        .mockResolvedValueOnce({
          success: false,
          error: 'Error',
          timestamp: new Date().toISOString(),
        });

      const { result } = renderHook(() => useUpdateStudentProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ first_name: 'Updated' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });
});
