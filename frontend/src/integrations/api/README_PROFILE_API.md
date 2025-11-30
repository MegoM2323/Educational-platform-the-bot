# Profile API Client

Complete API client for managing user profiles in THE_BOT_platform frontend.

## Quick Start

```typescript
import { profileAPI } from '@/integrations/api/profileAPI';

// Get current user's profile
const response = await profileAPI.getCurrentUserProfile();
if (response.success) {
  console.log(response.data?.user);
  console.log(response.data?.profile);
}
```

## Files Overview

### Core Files

1. **`profileAPI.ts`** - Main API client implementation
   - All methods for profile management
   - Type definitions for all roles
   - Caching functionality
   - Error handling

2. **`PROFILE_API_USAGE.md`** - Comprehensive usage guide
   - Detailed examples for all methods
   - Type definitions reference
   - React integration patterns
   - Best practices

3. **`profileAPI.examples.tsx`** - React component examples
   - Simple components for reference
   - React Query integration examples
   - Error handling patterns
   - Real-world usage scenarios

4. **`profileAPI.integration-test.ts`** - Manual integration tests
   - Test functions for all API methods
   - Can be run from browser console
   - Validates API structure and caching
   - Error scenario testing

## API Methods

### Core Methods

#### `getCurrentUserProfile()`
Get profile for authenticated user.

```typescript
const response = await profileAPI.getCurrentUserProfile();
// Returns: ApiResponse<UserProfile>
```

#### `getUserProfile(userId: number)`
Get profile for specific user.

```typescript
const response = await profileAPI.getUserProfile(123);
// Returns: ApiResponse<UserProfile>
```

#### `updateCurrentProfile(data: ProfileUpdateData)`
Update current user's profile.

```typescript
const response = await profileAPI.updateCurrentProfile({
  first_name: 'John',
  phone: '+1234567890'
});
// Returns: ApiResponse<UserProfile>
```

#### `updateUserProfile(userId: number, data: ProfileUpdateData)`
Update specific user's profile (admin).

```typescript
const response = await profileAPI.updateUserProfile(123, {
  grade: '10A'
});
// Returns: ApiResponse<UserProfile>
```

#### `getProfilesByRole(role: UserRole)`
Get all profiles for specific role.

```typescript
const response = await profileAPI.getProfilesByRole('teacher');
// Returns: ApiResponse<UserProfile[]>
```

### Utility Methods

#### `prefetchProfile()`
Pre-fetch and cache profile data.

```typescript
await profileAPI.prefetchProfile();
```

#### `invalidateCache()`
Clear all cached profile data.

```typescript
profileAPI.invalidateCache();
```

#### `extractProfileData(profile: UserProfile)`
Extract role-specific profile data.

```typescript
const profileData = profileAPI.extractProfileData(profile);
```

#### `isProfileComplete(profile: UserProfile)`
Check if profile has all required fields.

```typescript
const complete = profileAPI.isProfileComplete(profile);
```

## Type Definitions

### Main Types

```typescript
// User information
interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: 'student' | 'teacher' | 'tutor' | 'parent';
  role_display: string;
  phone: string;
  avatar?: string;
  is_verified: boolean;
  date_joined: string;
}

// Complete profile
interface UserProfile {
  user: User;
  profile?: ProfileData;
}

// API response
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}
```

### Role-Specific Types

```typescript
// Student
interface StudentProfileData {
  id: number;
  grade?: string;
  goal?: string; // Private
  tutor_id?: number | null; // Private
  parent_id?: number | null; // Private
  progress_percentage?: number;
  streak_days?: number;
  total_points?: number;
  accuracy_percentage?: number;
}

// Teacher
interface TeacherProfileData {
  id: number;
  subject?: string;
  experience_years?: number; // Private
  bio?: string; // Private
  subjects_list?: Array<{ id: number; name: string; color?: string }>;
}

// Tutor
interface TutorProfileData {
  id: number;
  specialization?: string;
  experience_years?: number; // Private
  bio?: string; // Private
}

// Parent
interface ParentProfileData {
  id: number;
}
```

## Features

### Automatic Caching
- 5-minute TTL for all GET requests
- Automatic cache invalidation on updates
- Manual cache control available

```typescript
// Returns cached data (fast)
const response1 = await profileAPI.getCurrentUserProfile();

// Clear cache if needed
profileAPI.invalidateCache();

// Next call fetches fresh data
const response2 = await profileAPI.getCurrentUserProfile();
```

### Error Handling
All methods handle errors gracefully:

```typescript
const response = await profileAPI.getCurrentUserProfile();

if (!response.success) {
  if (response.error?.includes('401')) {
    // Not authenticated
  } else if (response.error?.includes('404')) {
    // Not found
  } else {
    // Generic error
  }
}
```

### Type Safety
Full TypeScript support with strict typing:

```typescript
const response = await profileAPI.getCurrentUserProfile();

if (response.success && response.data) {
  // response.data is typed as UserProfile
  const user = response.data.user; // User type
  const profile = response.data.profile; // ProfileData type
}
```

## React Integration

### With useState/useEffect

```typescript
import { useEffect, useState } from 'react';
import { profileAPI, UserProfile } from '@/integrations/api/profileAPI';

export function MyComponent() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    profileAPI.getCurrentUserProfile().then(response => {
      if (response.success) {
        setProfile(response.data ?? null);
      }
      setLoading(false);
    });
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!profile) return <div>No profile</div>;

  return <div>{profile.user.full_name}</div>;
}
```

### With React Query (Recommended)

```typescript
import { useQuery } from '@tanstack/react-query';
import { profileAPI } from '@/integrations/api/profileAPI';

export function useUserProfile() {
  return useQuery({
    queryKey: ['user', 'profile'],
    queryFn: () => profileAPI.getCurrentUserProfile(),
    staleTime: 5 * 60 * 1000,
  });
}

export function MyComponent() {
  const { data: response, isLoading } = useUserProfile();

  if (isLoading) return <div>Loading...</div>;

  return <div>{response?.data?.user.full_name}</div>;
}
```

## Endpoints Used

The client uses these backend endpoints:

- `GET /api/auth/profile/` - Current user's profile
- `GET /api/auth/profile/{id}/` - Specific user's profile
- `PATCH /api/auth/profile/update/` - Update current user
- `PATCH /api/auth/profile/{id}/` - Update specific user
- `GET /api/auth/profiles/?role={role}` - Profiles by role

All requests are authenticated automatically by the unified API client.

## Private Fields

Some profile fields are restricted based on user role:

**Student Profile** (student cannot view own):
- `goal` - Learning goal
- `tutor_id` - Assigned tutor
- `parent_id` - Assigned parent

**Teacher Profile** (admin only):
- `bio` - Biography
- `experience_years` - Years of experience

**Tutor Profile** (admin only):
- `bio` - Biography
- `experience_years` - Years of experience

The backend automatically filters these fields. Check for their existence:

```typescript
const profile = response.data?.profile as StudentProfileData;
const goal = profile?.goal || 'Not available'; // Safe access
```

## Testing

### Manual Tests

Run integration tests from browser console:

```typescript
import { profileAPITests } from '@/integrations/api/profileAPI.integration-test';

// Quick test
await profileAPITests.quickTest();

// All tests
await profileAPITests.runAllTests();

// Specific test
await profileAPITests.testGetProfilesByRole('teacher');
await profileAPITests.testCaching();
```

### Expected Test Results

- Profile data structure validation
- Caching behavior verification
- Error handling scenarios
- Authorization testing
- Performance measurement

## Performance

### Caching

Profiles are cached for 5 minutes to reduce API calls:

```typescript
// Fast (cached)
await profileAPI.getCurrentUserProfile(); // ~5ms from cache

// Slow (fresh)
await profileAPI.getCurrentUserProfile(); // ~100-500ms from API
```

### Batch Requests

Get all users of specific role:

```typescript
// Single API call returns all teachers
const response = await profileAPI.getProfilesByRole('teacher');
const teacherCount = response.data?.length ?? 0;
```

## Best Practices

1. **Cache profile data on app startup**
   ```typescript
   // In your App component
   useEffect(() => {
     profileAPI.prefetchProfile();
   }, []);
   ```

2. **Handle 401 responses for authentication**
   ```typescript
   if (response.error?.includes('401')) {
     // Redirect to login
     window.location.href = '/auth';
   }
   ```

3. **Use React Query for complex scenarios**
   ```typescript
   // Better state management and caching
   const { data, isLoading, error } = useQuery({
     queryKey: ['profile'],
     queryFn: () => profileAPI.getCurrentUserProfile()
   });
   ```

4. **Check private fields safely**
   ```typescript
   // Always use optional chaining for private fields
   const goal = profile?.goal ?? 'Not set';
   ```

5. **Clear cache after updates**
   ```typescript
   // Already done automatically, but can be manual
   await profileAPI.updateCurrentProfile(data);
   profileAPI.invalidateCache(); // Only if needed
   ```

## Troubleshooting

### Getting 401 (Unauthorized)

```typescript
// Check authentication
if (response.error?.includes('401')) {
  // Token may have expired
  // Unified client attempts refresh automatically
  // If still fails, user needs to re-login
}
```

### Getting 404 (Not Found)

```typescript
// User or profile doesn't exist
if (response.error?.includes('404')) {
  console.log('Profile not found');
}
```

### Cache not clearing

```typescript
// Force clear cache
profileAPI.invalidateCache();

// Or let it expire naturally (5 minutes)
```

### Private fields showing as undefined

```typescript
// This is normal - backend filters based on permissions
const goal = profile?.goal;
if (goal === undefined) {
  console.log('Field is private or not available');
}
```

## Related Files

- `/profileAPI.ts` - Main implementation
- `/PROFILE_API_USAGE.md` - Detailed usage guide
- `/profileAPI.examples.tsx` - Component examples
- `/profileAPI.integration-test.ts` - Test functions
- `/unifiedClient.ts` - Base API client

## Support

For issues or questions:

1. Check `PROFILE_API_USAGE.md` for detailed examples
2. Review `profileAPI.examples.tsx` for component patterns
3. Run integration tests: `profileAPITests.runAllTests()`
4. Check backend logs for API errors
5. Verify authentication token is valid

## Version

Current version: 1.0.0

Supports all user roles: Student, Teacher, Tutor, Parent
