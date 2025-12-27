import { describe, it, expect, vi, beforeEach } from 'vitest';
import { profileAPI, UserProfile, ProfileUpdateData } from '../profileAPI';
import { unifiedAPI } from '../unifiedClient';

// Mock unifiedAPI
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
    getToken: vi.fn(() => 'mock-token'),
  },
}));

describe('profileAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    profileAPI._clearCache();
  });

  // Mock data
  const mockUserProfile: UserProfile = {
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
      progress_percentage: 75,
    },
  };

  const mockTeacherProfile: UserProfile = {
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
      subjects_list: [
        { id: 1, name: 'Math', color: '#FF5733' },
        { id: 2, name: 'Physics', color: '#33FF57' },
      ],
    },
  };

  describe('getMyStudentProfile', () => {
    it('should fetch student profile successfully', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.getMyStudentProfile();

      expect(response.success).toBe(true);
      expect(response.data).toEqual(mockUserProfile);
      expect(unifiedAPI.request).toHaveBeenCalledWith('/profile/student/me/');
    });

    it('should return cached data on subsequent calls', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      // First call
      await profileAPI.getMyStudentProfile();

      // Second call (should use cache)
      const response = await profileAPI.getMyStudentProfile();

      expect(response.success).toBe(true);
      expect(response.data).toEqual(mockUserProfile);
      // Should only be called once due to caching
      expect(unifiedAPI.request).toHaveBeenCalledTimes(1);
    });

    it('should handle 404 error', async () => {
      vi.mocked(unifiedAPI.request).mockRejectedValue(
        new Error('Failed to fetch student profile')
      );

      const response = await profileAPI.getMyStudentProfile();

      expect(response.success).toBe(false);
      expect(response.error).toContain('Failed to fetch student profile');
    });

    it('should handle network errors', async () => {
      vi.mocked(unifiedAPI.request).mockRejectedValue(
        new Error('Network error')
      );

      const response = await profileAPI.getMyStudentProfile();

      expect(response.success).toBe(false);
      expect(response.error).toContain('Network error');
    });
  });

  describe('updateStudentProfile', () => {
    it('should update student profile successfully', async () => {
      const updateData: ProfileUpdateData = {
        first_name: 'John',
        last_name: 'Updated',
        grade: '11B',
      };

      const updatedProfile = {
        ...mockUserProfile,
        user: { ...mockUserProfile.user, last_name: 'Updated' },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: updatedProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.updateStudentProfile(updateData);

      expect(response.success).toBe(true);
      expect(response.data).toEqual(updatedProfile);
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/profile/student/me/',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(updateData),
        })
      );
    });

    it('should clear cache on successful update', async () => {
      // Populate cache first
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      await profileAPI.getMyStudentProfile();

      // Then update
      const updateData: ProfileUpdateData = { first_name: 'Updated' };
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      await profileAPI.updateStudentProfile(updateData);

      // Cache should be cleared
      const cachedResponse = await profileAPI.getMyStudentProfile();
      expect(unifiedAPI.request).toHaveBeenCalledTimes(3); // 2 fetches + 1 update
    });

    it('should handle validation errors', async () => {
      const invalidData: ProfileUpdateData = {
        grade: '', // Empty grade
      };

      vi.mocked(unifiedAPI.request).mockRejectedValue(
        new Error('Validation error')
      );

      const response = await profileAPI.updateStudentProfile(invalidData);

      expect(response.success).toBe(false);
    });
  });

  describe('uploadStudentAvatar', () => {
    it('should upload avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      const profileWithAvatar = {
        ...mockUserProfile,
        user: {
          ...mockUserProfile.user,
          avatar: 'https://example.com/new-avatar.jpg',
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: profileWithAvatar,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.uploadStudentAvatar(mockFile);

      expect(response.success).toBe(true);
      expect(response.data).toEqual(profileWithAvatar);

      const callArgs = vi.mocked(unifiedAPI.request).mock.calls[0];
      expect(callArgs[0]).toBe('/profile/student/me/upload_avatar/');
      expect(callArgs[1]?.method).toBe('POST');
    });

    it('should handle invalid file types', async () => {
      const invalidFile = new File(['text'], 'file.txt', { type: 'text/plain' });

      vi.mocked(unifiedAPI.request).mockRejectedValue(
        new Error('Invalid file type')
      );

      const response = await profileAPI.uploadStudentAvatar(invalidFile);

      expect(response.success).toBe(false);
    });

    it('should handle file too large', async () => {
      // Create a mock file larger than typical limit
      const largeFile = new File(['x'.repeat(10 * 1024 * 1024)], 'large.jpg', {
        type: 'image/jpeg',
      });

      vi.mocked(unifiedAPI.request).mockRejectedValue(
        new Error('File too large')
      );

      const response = await profileAPI.uploadStudentAvatar(largeFile);

      expect(response.success).toBe(false);
    });
  });

  describe('getMyTeacherProfile', () => {
    it('should fetch teacher profile successfully', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.getMyTeacherProfile();

      expect(response.success).toBe(true);
      expect(response.data).toEqual(mockTeacherProfile);
      expect(unifiedAPI.request).toHaveBeenCalledWith('/profile/teacher/me/');
    });

    it('should cache teacher profile data', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      await profileAPI.getMyTeacherProfile();
      await profileAPI.getMyTeacherProfile();

      expect(unifiedAPI.request).toHaveBeenCalledTimes(1);
    });
  });

  describe('updateTeacherProfile', () => {
    it('should update teacher profile successfully', async () => {
      const updateData: ProfileUpdateData = {
        bio: 'Updated bio',
        experience_years: 6,
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.updateTeacherProfile(updateData);

      expect(response.success).toBe(true);
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/profile/teacher/me/',
        expect.objectContaining({ method: 'PATCH' })
      );
    });
  });

  describe('uploadTeacherAvatar', () => {
    it('should upload teacher avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTeacherProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.uploadTeacherAvatar(mockFile);

      expect(response.success).toBe(true);
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/profile/teacher/me/upload_avatar/',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('getMyTutorProfile', () => {
    it('should fetch tutor profile successfully', async () => {
      const mockTutorProfile: UserProfile = {
        user: {
          id: 3,
          email: 'tutor@example.com',
          first_name: 'Bob',
          last_name: 'Tutor',
          full_name: 'Bob Tutor',
          phone: '+1111111111',
          avatar: 'https://example.com/avatar.jpg',
          role: 'tutor',
        },
        profile: {
          id: 3,
          specialization: 'Math',
          experience_years: 3,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTutorProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.getMyTutorProfile();

      expect(response.success).toBe(true);
      expect(response.data).toEqual(mockTutorProfile);
      expect(unifiedAPI.request).toHaveBeenCalledWith('/profile/tutor/me/');
    });
  });

  describe('updateTutorProfile', () => {
    it('should update tutor profile successfully', async () => {
      const updateData: ProfileUpdateData = {
        specialization: 'Advanced Math',
      };

      const mockTutorProfile: UserProfile = {
        user: {
          id: 3,
          email: 'tutor@example.com',
          first_name: 'Bob',
          last_name: 'Tutor',
          full_name: 'Bob Tutor',
          phone: '+1111111111',
          avatar: 'https://example.com/avatar.jpg',
          role: 'tutor',
        },
        profile: {
          id: 3,
          specialization: 'Advanced Math',
          experience_years: 3,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTutorProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.updateTutorProfile(updateData);

      expect(response.success).toBe(true);
    });
  });

  describe('uploadTutorAvatar', () => {
    it('should upload tutor avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      const mockTutorProfile: UserProfile = {
        user: {
          id: 3,
          email: 'tutor@example.com',
          first_name: 'Bob',
          last_name: 'Tutor',
          full_name: 'Bob Tutor',
          phone: '+1111111111',
          avatar: 'https://example.com/new-avatar.jpg',
          role: 'tutor',
        },
        profile: {
          id: 3,
          specialization: 'Math',
          experience_years: 3,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockTutorProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.uploadTutorAvatar(mockFile);

      expect(response.success).toBe(true);
    });
  });

  describe('getMyParentProfile', () => {
    it('should fetch parent profile successfully', async () => {
      const mockParentProfile: UserProfile = {
        user: {
          id: 4,
          email: 'parent@example.com',
          first_name: 'Alice',
          last_name: 'Parent',
          full_name: 'Alice Parent',
          phone: '+2222222222',
          avatar: 'https://example.com/avatar.jpg',
          role: 'parent',
        },
        profile: {
          id: 4,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockParentProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.getMyParentProfile();

      expect(response.success).toBe(true);
      expect(response.data).toEqual(mockParentProfile);
      expect(unifiedAPI.request).toHaveBeenCalledWith('/profile/parent/me/');
    });
  });

  describe('updateParentProfile', () => {
    it('should update parent profile successfully', async () => {
      const updateData: ProfileUpdateData = {
        phone: '+3333333333',
      };

      const mockParentProfile: UserProfile = {
        user: {
          id: 4,
          email: 'parent@example.com',
          first_name: 'Alice',
          last_name: 'Parent',
          full_name: 'Alice Parent',
          phone: '+3333333333',
          avatar: 'https://example.com/avatar.jpg',
          role: 'parent',
        },
        profile: {
          id: 4,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockParentProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.updateParentProfile(updateData);

      expect(response.success).toBe(true);
    });
  });

  describe('uploadParentAvatar', () => {
    it('should upload parent avatar successfully', async () => {
      const mockFile = new File(['avatar'], 'avatar.jpg', { type: 'image/jpeg' });

      const mockParentProfile: UserProfile = {
        user: {
          id: 4,
          email: 'parent@example.com',
          first_name: 'Alice',
          last_name: 'Parent',
          full_name: 'Alice Parent',
          phone: '+2222222222',
          avatar: 'https://example.com/new-avatar.jpg',
          role: 'parent',
        },
        profile: {
          id: 4,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockParentProfile,
        timestamp: new Date().toISOString(),
      });

      const response = await profileAPI.uploadParentAvatar(mockFile);

      expect(response.success).toBe(true);
    });
  });

  describe('cache management', () => {
    it('should invalidate cache with invalidateCache()', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      // Populate cache
      await profileAPI.getMyStudentProfile();
      expect(unifiedAPI.request).toHaveBeenCalledTimes(1);

      // Invalidate cache
      profileAPI.invalidateCache();

      // Fetch again should hit API
      await profileAPI.getMyStudentProfile();
      expect(unifiedAPI.request).toHaveBeenCalledTimes(2);
    });

    it('should clear cache on logout', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      await profileAPI.getMyStudentProfile();
      await profileAPI.getMyTeacherProfile();

      profileAPI._clearCache();

      await profileAPI.getMyStudentProfile();
      expect(unifiedAPI.request).toHaveBeenCalledTimes(3);
    });
  });

  describe('error handling', () => {
    it('should include timestamp in error responses', async () => {
      vi.mocked(unifiedAPI.request).mockRejectedValue(
        new Error('API Error')
      );

      const response = await profileAPI.getMyStudentProfile();

      expect(response.success).toBe(false);
      expect(response.timestamp).toBeDefined();
      expect(typeof response.timestamp).toBe('string');
    });

    it('should handle unexpected errors', async () => {
      vi.mocked(unifiedAPI.request).mockRejectedValue(null);

      const response = await profileAPI.getMyStudentProfile();

      expect(response.success).toBe(false);
      expect(response.error).toBeDefined();
    });
  });

  describe('prefetchProfile', () => {
    it('should prefetch profile data', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockUserProfile,
        timestamp: new Date().toISOString(),
      });

      await profileAPI.prefetchProfile();

      const cachedResponse = await profileAPI.getCurrentUserProfile();
      expect(cachedResponse.success).toBe(true);
      // Should only call API once due to caching
      expect(unifiedAPI.request).toHaveBeenCalledTimes(1);
    });
  });
});
