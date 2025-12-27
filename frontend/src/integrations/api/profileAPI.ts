import { unifiedAPI as apiClient, ApiResponse, User } from './unifiedClient';
import { logger } from '@/utils/logger';

// Re-export ApiResponse type for use in other modules
export type { ApiResponse } from './unifiedClient';

/**
 * Profile API Client
 * Handles user profile data retrieval and management for all roles:
 * - Student, Teacher, Tutor, Parent
 */

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Student-specific profile data
 * Note: Some fields like 'goal', 'tutor_id', 'parent_id' are private and may not be visible
 * depending on the requesting user's role (backend filters them automatically)
 */
export interface StudentProfileData {
  id: number;
  grade?: string; // Grade is stored as string in backend (CharField)
  goal?: string; // PRIVATE: student doesn't see their own goal
  tutor_id?: number | null; // PRIVATE: student doesn't see
  parent_id?: number | null; // PRIVATE: student doesn't see
  progress_percentage?: number;
  streak_days?: number;
  total_points?: number;
  accuracy_percentage?: number;
  tutor_name?: string;
  parent_name?: string;
}

/**
 * Teacher-specific profile data
 * Note: 'bio' and 'experience_years' are admin-only fields
 */
export interface TeacherProfileData {
  id: number;
  subject?: string;
  experience_years?: number; // PRIVATE: admin only
  bio?: string; // PRIVATE: admin only
  subjects_list?: Array<{
    id: number;
    name: string;
    color?: string;
  }>;
}

/**
 * Tutor-specific profile data
 * Note: 'bio' and 'experience_years' are admin-only fields
 */
export interface TutorProfileData {
  id: number;
  specialization?: string;
  experience_years?: number; // PRIVATE: admin only
  bio?: string; // PRIVATE: admin only
}

/**
 * Parent-specific profile data
 */
export interface ParentProfileData {
  id: number;
  // Parent profile currently has no specific fields
}

/**
 * Union type for role-specific profile data
 */
export type ProfileData = StudentProfileData | TeacherProfileData | TutorProfileData | ParentProfileData;

/**
 * Complete user profile including user info and role-specific data
 */
export interface UserProfile {
  user: User;
  profile?: ProfileData;
  // For backward compatibility, also include flattened profile fields
  [key: string]: any;
}

/**
 * Response from /api/auth/profile/ endpoint
 * Can contain user + profile data depending on implementation
 */
export interface ProfileResponse {
  success: boolean;
  data?: UserProfile;
  error?: string;
  timestamp: string;
}

/**
 * Update request for profile data
 */
export interface ProfileUpdateData {
  // User fields
  email?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  avatar?: string;

  // Student profile fields (grade is stored as CharField in backend)
  grade?: string;
  goal?: string;
  telegram?: string;

  // Teacher/Tutor profile fields
  experience_years?: number;
  bio?: string;
  specialization?: string;

  // Parent profile (no fields currently)
}

/**
 * Profile cache entry with expiration
 */
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

/**
 * Profile API Client
 * Provides methods for retrieving and managing user profiles
 */
export const profileAPI = {
  // Cache management
  _cache: new Map<string, CacheEntry<any>>(),
  _cacheTTL: 5 * 60 * 1000, // 5 minutes default TTL

  /**
   * Get current user's profile
   * Requires authentication
   *
   * @returns User profile with role-specific data
   * @throws Error if not authenticated (401) or profile not found (404)
   *
   * @example
   * try {
   *   const response = await profileAPI.getCurrentUserProfile();
   *   if (response.success && response.data) {
   *     logger.debug('User:', response.data.user);
   *     logger.debug('Profile:', response.data.profile);
   *   }
   * } catch (error) {
   *   logger.error('Failed to load profile:', error);
   * }
   */
  async getCurrentUserProfile(): Promise<ApiResponse<UserProfile>> {
    const cacheKey = '/auth/profile/current';

    // Check cache
    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile>('/auth/profile/');

      // Cache on success
      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Get current student's profile
   * GET /api/profile/student/
   * NEW ENDPOINT - Uses new profile API
   *
   * @returns Student profile with role-specific data
   * @throws Error if not authenticated (401) or profile not found (404)
   */
  async getMyStudentProfile(): Promise<ApiResponse<UserProfile>> {
    const cacheKey = '/profile/student/';

    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile>('/profile/student/');

      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch student profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Update current student's profile
   * PATCH /api/profile/student/
   * NEW ENDPOINT - Uses new profile API with multipart/form-data support
   *
   * @param data - Profile data to update (supports avatar file)
   * @returns Updated student profile
   */
  async updateStudentProfile(data: ProfileUpdateData | FormData): Promise<ApiResponse<UserProfile>> {
    try {
      const isFormData = data instanceof FormData;

      const response = await apiClient.request<UserProfile>('/profile/student/', {
        method: 'PATCH',
        body: isFormData ? data : JSON.stringify(data),
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update student profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Upload student avatar
   * PATCH /api/profile/student/ with FormData
   *
   * @param file - Avatar file to upload
   * @returns Updated student profile with new avatar URL
   */
  async uploadStudentAvatar(file: File): Promise<ApiResponse<UserProfile>> {
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await apiClient.request<UserProfile>('/profile/student/', {
        method: 'PATCH',
        body: formData,
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to upload student avatar',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Get current teacher's profile
   * GET /api/profile/teacher/
   * NEW ENDPOINT - Uses new profile API
   *
   * @returns Teacher profile with role-specific data
   * @throws Error if not authenticated (401) or profile not found (404)
   */
  async getMyTeacherProfile(): Promise<ApiResponse<UserProfile>> {
    const cacheKey = '/profile/teacher/';

    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile>('/profile/teacher/');

      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch teacher profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Update current teacher's profile
   * PATCH /api/profile/teacher/
   * NEW ENDPOINT - Uses new profile API with multipart/form-data and subject_ids support
   *
   * @param data - Profile data to update (supports avatar file and subject_ids)
   * @returns Updated teacher profile
   */
  async updateTeacherProfile(data: ProfileUpdateData | FormData): Promise<ApiResponse<UserProfile>> {
    try {
      const isFormData = data instanceof FormData;

      const response = await apiClient.request<UserProfile>('/profile/teacher/', {
        method: 'PATCH',
        body: isFormData ? data : JSON.stringify(data),
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update teacher profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Upload teacher avatar
   * PATCH /api/profile/teacher/ with FormData
   *
   * @param file - Avatar file to upload
   * @returns Updated teacher profile with new avatar URL
   */
  async uploadTeacherAvatar(file: File): Promise<ApiResponse<UserProfile>> {
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await apiClient.request<UserProfile>('/profile/teacher/', {
        method: 'PATCH',
        body: formData,
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to upload teacher avatar',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Get current tutor's profile
   * GET /api/profile/tutor/
   * NEW ENDPOINT - Uses new profile API
   *
   * @returns Tutor profile with role-specific data
   * @throws Error if not authenticated (401) or profile not found (404)
   */
  async getMyTutorProfile(): Promise<ApiResponse<UserProfile>> {
    const cacheKey = '/profile/tutor/';

    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile>('/profile/tutor/');

      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch tutor profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Update current tutor's profile
   * PATCH /api/profile/tutor/
   * NEW ENDPOINT - Uses new profile API with multipart/form-data support
   *
   * @param data - Profile data to update (supports avatar file)
   * @returns Updated tutor profile
   */
  async updateTutorProfile(data: ProfileUpdateData | FormData): Promise<ApiResponse<UserProfile>> {
    try {
      const isFormData = data instanceof FormData;

      const response = await apiClient.request<UserProfile>('/profile/tutor/', {
        method: 'PATCH',
        body: isFormData ? data : JSON.stringify(data),
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update tutor profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Upload tutor avatar
   * PATCH /api/profile/tutor/ with FormData
   *
   * @param file - Avatar file to upload
   * @returns Updated tutor profile with new avatar URL
   */
  async uploadTutorAvatar(file: File): Promise<ApiResponse<UserProfile>> {
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await apiClient.request<UserProfile>('/profile/tutor/', {
        method: 'PATCH',
        body: formData,
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to upload tutor avatar',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Get current parent's profile
   * GET /api/profile/parent/
   * NEW ENDPOINT - Uses new profile API
   *
   * @returns Parent profile with role-specific data
   * @throws Error if not authenticated (401) or profile not found (404)
   */
  async getMyParentProfile(): Promise<ApiResponse<UserProfile>> {
    const cacheKey = '/profile/parent/';

    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile>('/profile/parent/');

      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch parent profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Update current parent's profile
   * PATCH /api/profile/parent/
   * NEW ENDPOINT - Uses new profile API with multipart/form-data support
   *
   * @param data - Profile data to update (supports avatar file)
   * @returns Updated parent profile
   */
  async updateParentProfile(data: ProfileUpdateData | FormData): Promise<ApiResponse<UserProfile>> {
    try {
      const isFormData = data instanceof FormData;

      const response = await apiClient.request<UserProfile>('/profile/parent/', {
        method: 'PATCH',
        body: isFormData ? data : JSON.stringify(data),
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update parent profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Upload parent avatar
   * PATCH /api/profile/parent/ with FormData
   * NEW ENDPOINT - Uses new profile API
   *
   * @param file - Avatar file to upload
   * @returns Updated parent profile with new avatar URL
   */
  async uploadParentAvatar(file: File): Promise<ApiResponse<UserProfile>> {
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await apiClient.request<UserProfile>('/profile/parent/', {
        method: 'PATCH',
        body: formData,
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to upload parent avatar',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Get profile by user ID
   * May be restricted based on user permissions
   *
   * @param userId - ID of the user to fetch
   * @returns User profile with role-specific data
   *
   * @example
   * const response = await profileAPI.getUserProfile(123);
   * if (response.success) {
   *   logger.debug('User profile:', response.data);
   * }
   */
  async getUserProfile(userId: number): Promise<ApiResponse<UserProfile>> {
    const cacheKey = `/auth/profile/user/${userId}`;

    // Check cache
    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile>(`/auth/profile/${userId}/`);

      // Cache on success
      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch user profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Update current user's profile
   * Clears cache after successful update
   *
   * @param data - Profile data to update (partial update supported)
   * @returns Updated user profile
   *
   * @example
   * const response = await profileAPI.updateCurrentProfile({
   *   first_name: 'John',
   *   last_name: 'Doe',
   *   phone: '+1234567890'
   * });
   */
  async updateCurrentProfile(data: ProfileUpdateData): Promise<ApiResponse<UserProfile>> {
    try {
      const response = await apiClient.request<UserProfile>('/auth/profile/update/', {
        method: 'PATCH',
        body: JSON.stringify(data),
      });

      // Clear cache on successful update
      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Update user profile by ID (admin/staff only)
   * Clears cache after successful update
   *
   * @param userId - ID of the user to update
   * @param data - Profile data to update
   * @returns Updated user profile
   *
   * @example
   * const response = await profileAPI.updateUserProfile(123, {
   *   grade: '10A',
   *   goal: 'Improve math skills'
   * });
   */
  async updateUserProfile(userId: number, data: ProfileUpdateData): Promise<ApiResponse<UserProfile>> {
    try {
      const response = await apiClient.request<UserProfile>(`/auth/profile/${userId}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });

      // Clear cache on successful update
      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update user profile',
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Get profile with specific role
   * Filters by role and returns relevant profile data
   *
   * @param role - User role to filter by ('student' | 'teacher' | 'tutor' | 'parent')
   * @returns List of user profiles with that role
   *
   * @example
   * const response = await profileAPI.getProfilesByRole('teacher');
   * if (response.success && response.data) {
   *   logger.debug('Teachers:', response.data);
   * }
   */
  async getProfilesByRole(
    role: 'student' | 'teacher' | 'tutor' | 'parent'
  ): Promise<ApiResponse<UserProfile[]>> {
    const cacheKey = `/auth/profiles/role/${role}`;

    // Check cache
    const cached = this._getCachedData(cacheKey);
    if (cached) {
      return {
        success: true,
        data: cached,
        timestamp: new Date().toISOString(),
      };
    }

    try {
      const response = await apiClient.request<UserProfile[]>(`/auth/profiles/?role=${role}`);

      // Cache on success
      if (response.success && response.data) {
        this._setCachedData(cacheKey, response.data);
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : `Failed to fetch ${role} profiles`,
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Invalidate profile cache
   * Useful when profile might have been updated externally
   *
   * @example
   * await profileAPI.invalidateCache();
   */
  invalidateCache(): void {
    this._clearCache();
  },

  /**
   * Pre-fetch profile data and cache it
   * Useful for optimistic loading
   *
   * @example
   * await profileAPI.prefetchProfile();
   */
  async prefetchProfile(): Promise<void> {
    await this.getCurrentUserProfile();
  },

  // ============================================================================
  // Private Helper Methods
  // ============================================================================

  /**
   * Get cached data if still valid
   */
  _getCachedData<T>(key: string): T | null {
    const entry = this._cache.get(key) as CacheEntry<T> | undefined;

    if (!entry) {
      return null;
    }

    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      // Cache expired
      this._cache.delete(key);
      return null;
    }

    return entry.data;
  },

  /**
   * Set cached data with TTL
   */
  _setCachedData<T>(key: string, data: T, ttl: number = this._cacheTTL): void {
    this._cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  },

  /**
   * Clear all cached profile data
   */
  _clearCache(): void {
    this._cache.clear();
  },

  /**
   * Extract profile data by role
   * Utility method to safely extract role-specific data
   */
  extractProfileData(profile: UserProfile): ProfileData | null {
    if (!profile || !profile.user) {
      return null;
    }

    const role = profile.user.role;

    switch (role) {
      case 'student':
        return profile.profile as StudentProfileData;
      case 'teacher':
        return profile.profile as TeacherProfileData;
      case 'tutor':
        return profile.profile as TutorProfileData;
      case 'parent':
        return profile.profile as ParentProfileData;
      default:
        return null;
    }
  },

  /**
   * Check if profile is fully loaded
   * Returns true if profile has all expected fields
   */
  isProfileComplete(profile: UserProfile): boolean {
    if (!profile || !profile.user) {
      return false;
    }

    // Check if user has required fields
    const userHasRequired = Boolean(
      profile.user.id &&
      profile.user.email &&
      profile.user.role
    );

    // Check if profile data exists (may be null for parent)
    const profileExists = profile.profile !== undefined;

    return userHasRequired && profileExists;
  },

  /**
   * Reactivate a deactivated profile
   * POST /api/profile/reactivate/
   *
   * @returns Updated profile with is_active=True
   */
  async reactivateProfile(): Promise<ApiResponse<UserProfile>> {
    try {
      const response = await apiClient.request<UserProfile>('/profile/reactivate/', {
        method: 'POST',
      });

      if (response.success) {
        this._clearCache();
      }

      return response;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to reactivate profile',
        timestamp: new Date().toISOString(),
      };
    }
  },
};

// Types are exported above as interfaces and type aliases
// No need for additional export type statements
