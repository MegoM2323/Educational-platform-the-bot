# Profile API Client - Usage Guide

## Overview

The `profileAPI` client provides a clean, type-safe interface for managing user profiles in THE_BOT_platform. It supports all user roles (Student, Teacher, Tutor, Parent) and handles role-specific profile data.

## Features

- Full TypeScript support with role-specific type definitions
- Automatic response parsing and error handling
- Built-in caching with 5-minute TTL
- Support for all user roles and their specific profile fields
- Private field filtering (backend enforces visibility rules)
- Batch operations for fetching profiles by role

## Type Definitions

### User Roles

```typescript
type UserRole = 'student' | 'teacher' | 'tutor' | 'parent';
```

### User Profile Structure

```typescript
interface UserProfile {
  user: User;
  profile?: ProfileData;
}

interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  role_display: string;
  phone: string;
  avatar?: string;
  is_verified: boolean;
  date_joined: string;
}
```

### Role-Specific Profile Data

#### Student Profile

```typescript
interface StudentProfileData {
  id: number;
  grade?: string;
  goal?: string; // PRIVATE: not visible to student
  tutor_id?: number | null;
  parent_id?: number | null;
  progress_percentage?: number;
  streak_days?: number;
  total_points?: number;
  accuracy_percentage?: number;
}
```

#### Teacher Profile

```typescript
interface TeacherProfileData {
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
```

#### Tutor Profile

```typescript
interface TutorProfileData {
  id: number;
  specialization?: string;
  experience_years?: number; // PRIVATE: admin only
  bio?: string; // PRIVATE: admin only
}
```

#### Parent Profile

```typescript
interface ParentProfileData {
  id: number;
  // Parent profile currently has no specific fields
}
```

## Usage Examples

### 1. Get Current User's Profile

```typescript
import { profileAPI } from '@/integrations/api/profileAPI';

async function loadMyProfile() {
  const response = await profileAPI.getCurrentUserProfile();

  if (response.success && response.data) {
    const user = response.data.user;
    const profile = response.data.profile;

    console.log(`User: ${user.full_name} (${user.role})`);
    console.log('Profile data:', profile);
  } else {
    console.error('Error:', response.error);
  }
}
```

### 2. Get Profile for Specific User (by ID)

```typescript
async function loadUserProfile(userId: number) {
  const response = await profileAPI.getUserProfile(userId);

  if (response.success) {
    return response.data;
  }
  throw new Error(response.error);
}
```

### 3. Update Current User's Profile

```typescript
async function updateMyProfile() {
  const response = await profileAPI.updateCurrentProfile({
    first_name: 'John',
    last_name: 'Doe',
    phone: '+1234567890',
  });

  if (response.success) {
    console.log('Profile updated successfully');
  } else {
    console.error('Update failed:', response.error);
  }
}
```

### 4. Update Student Profile (role-specific)

```typescript
async function updateStudentProfile(userId: number) {
  const response = await profileAPI.updateUserProfile(userId, {
    grade: '10A',
    goal: 'Improve mathematics skills',
  });

  if (response.success) {
    console.log('Student profile updated');
  }
}
```

### 5. Update Teacher Profile (role-specific)

```typescript
async function updateTeacherProfile(userId: number) {
  const response = await profileAPI.updateUserProfile(userId, {
    experience_years: 5,
    bio: 'Expert in mathematics and physics',
  });

  if (response.success) {
    console.log('Teacher profile updated');
  }
}
```

### 6. Get All Teachers

```typescript
async function loadAllTeachers() {
  const response = await profileAPI.getProfilesByRole('teacher');

  if (response.success && response.data) {
    const teachers = response.data;
    teachers.forEach(profile => {
      console.log(`${profile.user.full_name} - ${profile.profile?.subject}`);
    });
  }
}
```

### 7. Get All Students

```typescript
async function loadAllStudents() {
  const response = await profileAPI.getProfilesByRole('student');

  if (response.success && response.data) {
    return response.data;
  }
}
```

### 8. Pre-fetch Profile (Optimistic Loading)

```typescript
// Fetch and cache profile data before it's needed
async function prefetchUserData() {
  await profileAPI.prefetchProfile();
}
```

### 9. Extract Role-Specific Data

```typescript
async function displayProfileInfo() {
  const response = await profileAPI.getCurrentUserProfile();

  if (response.success && response.data) {
    const profile = response.data;
    const roleSpecificData = profileAPI.extractProfileData(profile);

    if (profile.user.role === 'student') {
      const studentProfile = roleSpecificData as StudentProfileData;
      console.log(`Grade: ${studentProfile.grade}`);
      console.log(`Progress: ${studentProfile.progress_percentage}%`);
    } else if (profile.user.role === 'teacher') {
      const teacherProfile = roleSpecificData as TeacherProfileData;
      console.log(`Subjects: ${teacherProfile.subjects_list?.map(s => s.name).join(', ')}`);
    }
  }
}
```

### 10. Check Profile Completeness

```typescript
async function validateProfile() {
  const response = await profileAPI.getCurrentUserProfile();

  if (response.success && response.data) {
    const isComplete = profileAPI.isProfileComplete(response.data);

    if (isComplete) {
      console.log('Profile is fully loaded');
    } else {
      console.log('Profile data is incomplete');
    }
  }
}
```

## Using in React Components

### Basic Hook Usage

```typescript
import { useEffect, useState } from 'react';
import { profileAPI, UserProfile } from '@/integrations/api/profileAPI';

export function UserProfileCard() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const response = await profileAPI.getCurrentUserProfile();
        if (response.success) {
          setProfile(response.data ?? null);
        } else {
          setError(response.error ?? 'Failed to load profile');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!profile) return <div>No profile data</div>;

  return (
    <div>
      <h2>{profile.user.full_name}</h2>
      <p>Email: {profile.user.email}</p>
      <p>Role: {profile.user.role_display}</p>
      {profile.profile && (
        <div>
          {profile.user.role === 'student' && (
            <p>Grade: {(profile.profile as any).grade}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

### With React Query (Recommended)

```typescript
import { useQuery } from '@tanstack/react-query';
import { profileAPI } from '@/integrations/api/profileAPI';

export function useUserProfile() {
  return useQuery({
    queryKey: ['profile', 'current'],
    queryFn: () => profileAPI.getCurrentUserProfile(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Usage:
export function UserCard() {
  const { data: response, isLoading, error } = useUserProfile();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading profile</div>;

  const profile = response?.data;

  return (
    <div>
      <h2>{profile?.user.full_name}</h2>
      <p>Role: {profile?.user.role_display}</p>
    </div>
  );
}
```

## Caching

The profile API includes automatic caching with a 5-minute TTL:

```typescript
// First call fetches from API
const response1 = await profileAPI.getCurrentUserProfile();

// Second call (within 5 minutes) returns cached data
const response2 = await profileAPI.getCurrentUserProfile();

// Invalidate cache after profile update
await profileAPI.updateCurrentProfile({ first_name: 'Jane' });
// Cache is automatically cleared after successful update

// Or manually clear cache
profileAPI.invalidateCache();

// Subsequent call will fetch fresh data
const response3 = await profileAPI.getCurrentUserProfile();
```

## Error Handling

```typescript
async function safeProfileLoad() {
  try {
    const response = await profileAPI.getCurrentUserProfile();

    if (!response.success) {
      if (response.error?.includes('401')) {
        // Not authenticated - redirect to login
        window.location.href = '/auth';
      } else if (response.error?.includes('404')) {
        // Profile not found
        console.error('Profile not found');
      } else {
        // Generic error
        console.error('Failed to load profile:', response.error);
      }
      return null;
    }

    return response.data;
  } catch (error) {
    console.error('Unexpected error:', error);
    return null;
  }
}
```

## API Response Format

All responses follow the unified API response format:

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}
```

### Success Response Example

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "student@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "role": "student",
      "role_display": "Student",
      "phone": "+1234567890",
      "is_verified": true,
      "date_joined": "2024-01-15T10:30:00Z"
    },
    "profile": {
      "id": 1,
      "grade": "10A",
      "progress_percentage": 75,
      "streak_days": 15,
      "total_points": 450
    }
  },
  "timestamp": "2024-11-23T12:00:00Z"
}
```

### Error Response Example

```json
{
  "success": false,
  "error": "Authentication required or token expired",
  "timestamp": "2024-11-23T12:00:00Z"
}
```

## Important Notes

### Private Fields

Some fields are marked as PRIVATE and are automatically filtered by the backend based on user permissions:

- **Student Profile**: `goal`, `tutor_id`, `parent_id` - students cannot see their own
- **Teacher Profile**: `bio`, `experience_years` - only visible to admin
- **Tutor Profile**: `bio`, `experience_years` - only visible to admin

When these fields are not visible, they will be `undefined` in the response. Check for their existence before using:

```typescript
const response = await profileAPI.getCurrentUserProfile();
const profile = response.data?.profile as StudentProfileData;

// Safe access to private fields
const goal = profile?.goal || 'No goal set';
const tutor = profile?.tutor_id || null;
```

### Authentication

All API endpoints require authentication. If you get a 401 response:

1. Token has expired or is invalid
2. User is not logged in
3. The unified client will attempt to refresh the token automatically
4. If refresh fails, user will be redirected to login

### Rate Limiting

The API does not currently implement rate limiting, but caching is recommended to reduce load:

```typescript
// Pre-fetch critical data on app startup
profileAPI.prefetchProfile();
```

## Best Practices

1. **Use caching**: Let the API cache data to reduce server load
2. **Clear cache after updates**: The API does this automatically, but you can also call `invalidateCache()`
3. **Handle errors gracefully**: Always check `response.success` before accessing `response.data`
4. **Use React Query for complex scenarios**: Better performance and state management
5. **Check private fields safely**: Use optional chaining to avoid undefined errors
6. **Type your data**: Use the provided TypeScript interfaces for type safety

## Troubleshooting

### Profile returns 401 (Unauthorized)

```typescript
// Check if token is still valid
const token = localStorage.getItem('authToken');
if (!token) {
  // Not logged in, redirect to login
  window.location.href = '/auth';
}

// Try refreshing token
const refreshResponse = await unifiedAPI.refreshToken();
if (!refreshResponse.success) {
  // Refresh failed, redirect to login
  window.location.href = '/auth';
}
```

### Profile returns 404 (Not Found)

```typescript
// Profile doesn't exist for this user
const response = await profileAPI.getUserProfile(nonExistentId);
if (response.error?.includes('404')) {
  console.log('User not found or has no profile');
}
```

### Cache not clearing after update

```typescript
// Manually clear cache
profileAPI.invalidateCache();

// Or use the update methods which automatically clear it
await profileAPI.updateCurrentProfile(data);
```

## API Endpoints Referenced

- `GET /api/auth/profile/` - Get current user's profile
- `GET /api/auth/profile/{id}/` - Get specific user's profile
- `PATCH /api/auth/profile/update/` - Update current user's profile
- `PATCH /api/auth/profile/{id}/` - Update specific user's profile (admin)
- `GET /api/auth/profiles/?role={role}` - Get profiles by role

All endpoints are proxied through the unified API client which handles:
- Authentication headers
- Token refresh
- Retry logic
- Response normalization
- Error handling
