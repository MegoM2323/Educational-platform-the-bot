/**
import { logger } from '@/utils/logger';
 * Profile API Usage Examples - React Components
 *
 * This file contains practical examples of how to use the profileAPI client
 * in real React components. These are for reference and testing purposes.
 *
 * DO NOT import these components directly in production - they are examples only.
 * Copy and adapt the patterns shown here for your actual components.
 */

import { useEffect, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  profileAPI,
  UserProfile,
  StudentProfileData,
  TeacherProfileData,
  ProfileUpdateData,
} from './profileAPI';

// ============================================================================
// Example 1: Simple Profile Loading Component
// ============================================================================

/**
 * Basic component that loads and displays current user's profile
 * Shows error and loading states
 */
export function SimpleProfileCard() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setLoading(true);
        const response = await profileAPI.getCurrentUserProfile();

        if (response.success && response.data) {
          setProfile(response.data);
          setError(null);
        } else {
          setError(response.error || 'Failed to load profile');
          setProfile(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setProfile(null);
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  if (loading) {
    return <div className="profile-card loading">Loading profile...</div>;
  }

  if (error) {
    return <div className="profile-card error">Error: {error}</div>;
  }

  if (!profile) {
    return <div className="profile-card empty">No profile data available</div>;
  }

  const { user, profile: profileData } = profile;

  return (
    <div className="profile-card">
      <h2>{user.full_name}</h2>
      <div className="profile-info">
        <p>
          <strong>Email:</strong> {user.email}
        </p>
        <p>
          <strong>Role:</strong> {user.role_display}
        </p>
        {user.phone && (
          <p>
            <strong>Phone:</strong> {user.phone}
          </p>
        )}
        <p>
          <strong>Joined:</strong> {new Date(user.date_joined).toLocaleDateString()}
        </p>
      </div>

      {profileData && (
        <div className="profile-specific">
          {user.role === 'student' && (
            <StudentProfileInfo profile={profileData as StudentProfileData} />
          )}
          {user.role === 'teacher' && (
            <TeacherProfileInfo profile={profileData as TeacherProfileData} />
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Example 2: Student Profile Display
// ============================================================================

interface StudentProfileInfoProps {
  profile: StudentProfileData;
}

function StudentProfileInfo({ profile }: StudentProfileInfoProps) {
  return (
    <div className="student-profile">
      <h3>Student Info</h3>
      {profile.grade && (
        <p>
          <strong>Grade:</strong> {profile.grade}
        </p>
      )}
      {profile.progress_percentage !== undefined && (
        <p>
          <strong>Progress:</strong> {profile.progress_percentage}%
        </p>
      )}
      {profile.streak_days !== undefined && (
        <p>
          <strong>Streak:</strong> {profile.streak_days} days
        </p>
      )}
      {profile.total_points !== undefined && (
        <p>
          <strong>Points:</strong> {profile.total_points}
        </p>
      )}
      {profile.accuracy_percentage !== undefined && (
        <p>
          <strong>Accuracy:</strong> {profile.accuracy_percentage}%
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Example 3: Teacher Profile Display
// ============================================================================

interface TeacherProfileInfoProps {
  profile: TeacherProfileData;
}

function TeacherProfileInfo({ profile }: TeacherProfileInfoProps) {
  return (
    <div className="teacher-profile">
      <h3>Teacher Info</h3>
      {profile.subject && (
        <p>
          <strong>Subject:</strong> {profile.subject}
        </p>
      )}
      {profile.subjects_list && profile.subjects_list.length > 0 && (
        <div>
          <strong>Teaches:</strong>
          <ul>
            {profile.subjects_list.map((subject) => (
              <li key={subject.id}>{subject.name}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Example 4: Profile Update Form
// ============================================================================

/**
 * Form component for updating user profile
 * Uses local state for form fields and handles validation
 */
export function ProfileUpdateForm() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const updateData: ProfileUpdateData = {};

      if (firstName) updateData.first_name = firstName;
      if (lastName) updateData.last_name = lastName;
      if (phone) updateData.phone = phone;

      const response = await profileAPI.updateCurrentProfile(updateData);

      if (response.success) {
        setSuccess(true);
        setFirstName('');
        setLastName('');
        setPhone('');
        // Optionally: reload profile
        // await profileAPI.prefetchProfile();
      } else {
        setError(response.error || 'Failed to update profile');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="profile-update-form">
      <div className="form-group">
        <label htmlFor="firstName">First Name</label>
        <input
          id="firstName"
          type="text"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          placeholder="Enter first name"
        />
      </div>

      <div className="form-group">
        <label htmlFor="lastName">Last Name</label>
        <input
          id="lastName"
          type="text"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          placeholder="Enter last name"
        />
      </div>

      <div className="form-group">
        <label htmlFor="phone">Phone</label>
        <input
          id="phone"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Enter phone number"
        />
      </div>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">Profile updated successfully!</div>}

      <button type="submit" disabled={loading}>
        {loading ? 'Updating...' : 'Update Profile'}
      </button>
    </form>
  );
}

// ============================================================================
// Example 5: Using React Query (Recommended)
// ============================================================================

/**
 * Custom hook for profile management using React Query
 * Provides automatic caching, refetching, and state management
 */
export function useUserProfile() {
  return useQuery({
    queryKey: ['user', 'profile', 'current'],
    queryFn: async () => {
      const response = await profileAPI.getCurrentUserProfile();
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch profile');
      }
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
}

/**
 * Custom hook for updating profile using React Query
 */
export function useUpdateProfile() {
  return useMutation({
    mutationFn: async (data: ProfileUpdateData) => {
      const response = await profileAPI.updateCurrentProfile(data);
      if (!response.success) {
        throw new Error(response.error || 'Failed to update profile');
      }
      return response.data;
    },
  });
}

/**
 * Component using React Query hooks
 */
export function ProfileCardWithQuery() {
  const { data: profile, isLoading, error } = useUserProfile();

  if (isLoading) {
    return <div>Loading profile...</div>;
  }

  if (error) {
    return <div>Error: {error instanceof Error ? error.message : 'Unknown error'}</div>;
  }

  if (!profile) {
    return <div>No profile data</div>;
  }

  return (
    <div className="profile-card">
      <h2>{profile.user.full_name}</h2>
      <p>Email: {profile.user.email}</p>
      <p>Role: {profile.user.role_display}</p>
    </div>
  );
}

/**
 * Form using React Query mutation
 */
export function ProfileUpdateFormWithQuery() {
  const mutation = useUpdateProfile();
  const [firstName, setFirstName] = useState('');

  const handleUpdate = async () => {
    try {
      await mutation.mutateAsync({
        first_name: firstName,
      });
    } catch (error) {
      logger.error('Update failed:', error);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={firstName}
        onChange={(e) => setFirstName(e.target.value)}
        placeholder="First name"
      />
      <button onClick={handleUpdate} disabled={mutation.isPending}>
        {mutation.isPending ? 'Updating...' : 'Update'}
      </button>
      {mutation.isError && <p>Error: {mutation.error?.message}</p>}
      {mutation.isSuccess && <p>Profile updated!</p>}
    </div>
  );
}

// ============================================================================
// Example 6: User Selection Dropdown
// ============================================================================

/**
 * Component that loads all students for selection
 */
export function StudentSelector() {
  const [students, setStudents] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    const loadStudents = async () => {
      setLoading(true);
      try {
        const response = await profileAPI.getProfilesByRole('student');
        if (response.success && response.data) {
          setStudents(response.data);
        }
      } finally {
        setLoading(false);
      }
    };

    loadStudents();
  }, []);

  return (
    <select
      value={selectedId || ''}
      onChange={(e) => setSelectedId(parseInt(e.target.value))}
      disabled={loading}
    >
      <option value="">Select a student...</option>
      {students.map((profile) => (
        <option key={profile.user.id} value={profile.user.id}>
          {profile.user.full_name} ({(profile.profile as StudentProfileData)?.grade || 'N/A'})
        </option>
      ))}
    </select>
  );
}

// ============================================================================
// Example 7: Profile with Caching Demo
// ============================================================================

/**
 * Component demonstrating profile caching behavior
 */
export function ProfileCachingDemo() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loadTime, setLoadTime] = useState<number>(0);
  const [cacheStatus, setCacheStatus] = useState<'initial' | 'cache' | 'fresh'>('initial');

  const loadProfile = async () => {
    const startTime = performance.now();

    const response = await profileAPI.getCurrentUserProfile();

    const endTime = performance.now();
    const duration = endTime - startTime;

    setLoadTime(duration);

    if (response.success && response.data) {
      setProfile(response.data);
      setCacheStatus(duration < 50 ? 'cache' : 'fresh'); // Arbitrary threshold
    }
  };

  return (
    <div className="cache-demo">
      <button onClick={loadProfile}>Load Profile</button>

      {profile && (
        <div>
          <h3>{profile.user.full_name}</h3>
          <p>Load time: {loadTime.toFixed(2)}ms</p>
          <p>Source: {cacheStatus === 'cache' ? 'Cache' : 'Fresh fetch'}</p>
        </div>
      )}

      <button onClick={() => profileAPI.invalidateCache()}>Clear Cache</button>
    </div>
  );
}

// ============================================================================
// Example 8: Error Handling Patterns
// ============================================================================

/**
 * Component demonstrating error handling patterns
 */
export function ProfileWithErrorHandling() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorType, setErrorType] = useState<'auth' | 'notfound' | 'generic' | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const loadProfile = async () => {
    setStatus('loading');
    setErrorType(null);

    try {
      const response = await profileAPI.getCurrentUserProfile();

      if (!response.success) {
        setStatus('error');

        // Classify error
        if (response.error?.includes('401')) {
          setErrorType('auth');
        } else if (response.error?.includes('404')) {
          setErrorType('notfound');
        } else {
          setErrorType('generic');
        }

        return;
      }

      if (response.data) {
        setProfile(response.data);
        setStatus('success');
      }
    } catch (error) {
      setStatus('error');
      setErrorType('generic');
    }
  };

  return (
    <div className="profile-error-demo">
      <button onClick={loadProfile}>Load Profile</button>

      {status === 'loading' && <p>Loading...</p>}

      {status === 'error' && (
        <div className="error">
          {errorType === 'auth' && (
            <div>
              <p>You are not authenticated. Please log in.</p>
              <a href="/auth">Go to login</a>
            </div>
          )}
          {errorType === 'notfound' && <p>Profile not found. Please try again later.</p>}
          {errorType === 'generic' && <p>An error occurred. Please try again.</p>}
        </div>
      )}

      {status === 'success' && profile && (
        <div>
          <h3>{profile.user.full_name}</h3>
          <p>Email: {profile.user.email}</p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Export all examples (for testing/storybook purposes only)
// ============================================================================

export const examples = {
  SimpleProfileCard,
  ProfileUpdateForm,
  ProfileCardWithQuery,
  ProfileUpdateFormWithQuery,
  StudentSelector,
  ProfileCachingDemo,
  ProfileWithErrorHandling,
};
