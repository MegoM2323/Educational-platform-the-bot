# Profile API - Quick Start Examples

Копируй и адаптируй эти примеры для своих компонентов.

## Пример 1: Простое отображение профиля

```typescript
import { useEffect, useState } from 'react';
import { profileAPI, UserProfile } from '@/integrations/api/profileAPI';

export function MyProfileCard() {
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

  return (
    <div>
      <h2>{profile.user.full_name}</h2>
      <p>Email: {profile.user.email}</p>
      <p>Role: {profile.user.role_display}</p>
    </div>
  );
}
```

## Пример 2: С React Query (рекомендуется)

```typescript
import { useQuery } from '@tanstack/react-query';
import { profileAPI } from '@/integrations/api/profileAPI';

export function useUserProfile() {
  return useQuery({
    queryKey: ['user', 'profile'],
    queryFn: () => profileAPI.getCurrentUserProfile(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function UserCard() {
  const { data: response, isLoading, error } = useUserProfile();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading profile</div>;

  const profile = response?.data;

  return (
    <div>
      <h2>{profile?.user.full_name}</h2>
      <p>Email: {profile?.user.email}</p>
    </div>
  );
}
```

## Пример 3: Форма обновления профиля

```typescript
import { useState } from 'react';
import { profileAPI } from '@/integrations/api/profileAPI';

export function EditProfileForm() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const response = await profileAPI.updateCurrentProfile({
      first_name: firstName,
      last_name: lastName,
      phone: phone,
    });

    if (response.success) {
      setMessage('Profile updated successfully');
      // Clear form
      setFirstName('');
      setLastName('');
      setPhone('');
    } else {
      setMessage(`Error: ${response.error}`);
    }

    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="First Name"
        value={firstName}
        onChange={(e) => setFirstName(e.target.value)}
      />
      <input
        type="text"
        placeholder="Last Name"
        value={lastName}
        onChange={(e) => setLastName(e.target.value)}
      />
      <input
        type="tel"
        placeholder="Phone"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Updating...' : 'Update'}
      </button>
      {message && <p>{message}</p>}
    </form>
  );
}
```

## Пример 4: Список студентов с выбором

```typescript
import { useEffect, useState } from 'react';
import { profileAPI, UserProfile } from '@/integrations/api/profileAPI';

export function StudentsList() {
  const [students, setStudents] = useState<UserProfile[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    profileAPI.getProfilesByRole('student').then(response => {
      if (response.success && response.data) {
        setStudents(response.data);
      }
      setLoading(false);
    });
  }, []);

  if (loading) return <div>Loading students...</div>;

  return (
    <div>
      <h3>Students ({students.length})</h3>
      <select
        value={selectedId || ''}
        onChange={(e) => setSelectedId(parseInt(e.target.value))}
      >
        <option value="">Select a student...</option>
        {students.map((profile) => (
          <option key={profile.user.id} value={profile.user.id}>
            {profile.user.full_name}
          </option>
        ))}
      </select>

      {selectedId && (
        <div>
          <p>Selected student ID: {selectedId}</p>
        </div>
      )}
    </div>
  );
}
```

## Пример 5: Отображение роль-специфичных данных

```typescript
import { profileAPI, UserProfile, StudentProfileData } from '@/integrations/api/profileAPI';

export function ProfileDetails({ profile }: { profile: UserProfile }) {
  const { user } = profile;

  // Динамическое отображение в зависимости от роли
  return (
    <div>
      <h2>{user.full_name}</h2>
      <p>Role: {user.role_display}</p>

      {user.role === 'student' && profile.profile && (
        <StudentInfo profile={profile.profile as StudentProfileData} />
      )}
      {user.role === 'teacher' && profile.profile && (
        <TeacherInfo profile={profile.profile} />
      )}
    </div>
  );
}

function StudentInfo({ profile }: { profile: StudentProfileData }) {
  return (
    <div className="student-info">
      <h3>Student Profile</h3>
      {profile.grade && <p>Grade: {profile.grade}</p>}
      {profile.progress_percentage !== undefined && (
        <p>Progress: {profile.progress_percentage}%</p>
      )}
      {profile.streak_days !== undefined && (
        <p>Streak: {profile.streak_days} days</p>
      )}
    </div>
  );
}

function TeacherInfo({ profile }: { profile: any }) {
  return (
    <div className="teacher-info">
      <h3>Teacher Profile</h3>
      {profile.subject && <p>Subject: {profile.subject}</p>}
      {profile.subjects_list && profile.subjects_list.length > 0 && (
        <div>
          <p>Teaches:</p>
          <ul>
            {profile.subjects_list.map((s: any) => (
              <li key={s.id}>{s.name}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

## Пример 6: Обработка ошибок

```typescript
import { profileAPI } from '@/integrations/api/profileAPI';

export async function loadProfileSafely() {
  try {
    const response = await profileAPI.getCurrentUserProfile();

    if (!response.success) {
      if (response.error?.includes('401')) {
        console.log('Not authenticated - redirect to login');
        // window.location.href = '/auth';
      } else if (response.error?.includes('404')) {
        console.log('Profile not found');
      } else {
        console.log('Error:', response.error);
      }
      return null;
    }

    if (!response.data) {
      console.log('No profile data returned');
      return null;
    }

    return response.data;
  } catch (error) {
    console.error('Unexpected error:', error);
    return null;
  }
}
```

## Пример 7: Предварительная загрузка профиля при инициализации приложения

```typescript
import { useEffect } from 'react';
import { profileAPI } from '@/integrations/api/profileAPI';

export function AppInitializer() {
  useEffect(() => {
    // Pre-fetch profile on app startup
    profileAPI.prefetchProfile().catch(err => {
      console.error('Failed to prefetch profile:', err);
    });
  }, []);

  return null;
}

// Используй в App.tsx:
// <AppInitializer />
```

## Пример 8: Обновление профиля с валидацией

```typescript
import { useState } from 'react';
import { profileAPI, ProfileUpdateData } from '@/integrations/api/profileAPI';

export function ValidatedProfileForm() {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    phone: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (formData.firstName && formData.firstName.length < 2) {
      newErrors.firstName = 'First name must be at least 2 characters';
    }

    if (formData.phone && formData.phone.length < 10) {
      newErrors.phone = 'Phone must be at least 10 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    const updateData: ProfileUpdateData = {};
    if (formData.firstName) updateData.first_name = formData.firstName;
    if (formData.lastName) updateData.last_name = formData.lastName;
    if (formData.phone) updateData.phone = formData.phone;

    const response = await profileAPI.updateCurrentProfile(updateData);

    if (response.success) {
      alert('Profile updated successfully');
      setFormData({ firstName: '', lastName: '', phone: '' });
    } else {
      alert(`Error: ${response.error}`);
    }

    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>First Name</label>
        <input
          type="text"
          value={formData.firstName}
          onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
        />
        {errors.firstName && <span className="error">{errors.firstName}</span>}
      </div>

      <div>
        <label>Last Name</label>
        <input
          type="text"
          value={formData.lastName}
          onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
        />
        {errors.lastName && <span className="error">{errors.lastName}</span>}
      </div>

      <div>
        <label>Phone</label>
        <input
          type="tel"
          value={formData.phone}
          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
        />
        {errors.phone && <span className="error">{errors.phone}</span>}
      </div>

      <button type="submit" disabled={loading}>
        {loading ? 'Updating...' : 'Update Profile'}
      </button>
    </form>
  );
}
```

## Пример 9: Использование с Context API

```typescript
import { createContext, useContext, useEffect, useState } from 'react';
import { profileAPI, UserProfile } from '@/integrations/api/profileAPI';

interface ProfileContextType {
  profile: UserProfile | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const ProfileContext = createContext<ProfileContextType | null>(null);

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = async () => {
    setLoading(true);
    const response = await profileAPI.getCurrentUserProfile();
    if (response.success) {
      setProfile(response.data ?? null);
      setError(null);
    } else {
      setError(response.error ?? 'Failed to load profile');
    }
    setLoading(false);
  };

  useEffect(() => {
    refetch();
  }, []);

  return (
    <ProfileContext.Provider value={{ profile, loading, error, refetch }}>
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error('useProfile must be used within ProfileProvider');
  }
  return context;
}
```

## Пример 10: Проверка прав доступа

```typescript
import { UserProfile } from '@/integrations/api/profileAPI';

export function canEditProfile(userProfile: UserProfile, targetUserId: number): boolean {
  // User can edit their own profile
  if (userProfile.user.id === targetUserId) {
    return true;
  }

  // Admin can edit any profile
  if (userProfile.user.is_staff) {
    return true;
  }

  // Teachers can edit their students
  // (implement based on your business logic)

  return false;
}

export function EditProfileButton({
  userProfile,
  targetUserId,
}: {
  userProfile: UserProfile;
  targetUserId: number;
}) {
  const canEdit = canEditProfile(userProfile, targetUserId);

  if (!canEdit) {
    return <button disabled>No permission to edit</button>;
  }

  return <button onClick={() => {}}>Edit Profile</button>;
}
```

## Советы и лучшие практики

1. **Всегда проверяй response.success:**
   ```typescript
   if (response.success && response.data) {
     // Используй данные
   }
   ```

2. **Используй React Query для сложных сценариев:**
   ```typescript
   const { data, isLoading, error } = useQuery({
     queryKey: ['profile'],
     queryFn: () => profileAPI.getCurrentUserProfile()
   });
   ```

3. **Безопасный доступ к приватным полям:**
   ```typescript
   const goal = profile?.goal || 'Not available';
   ```

4. **Обработка ошибок по типам:**
   ```typescript
   if (response.error?.includes('401')) {
     // Auth error
   } else if (response.error?.includes('404')) {
     // Not found
   }
   ```

5. **Предварительная загрузка критичных данных:**
   ```typescript
   useEffect(() => {
     profileAPI.prefetchProfile();
   }, []);
   ```

## Дополнительная информация

- Подробное руководство: `PROFILE_API_USAGE.md`
- Примеры компонентов: `profileAPI.examples.tsx`
- Справочник: `README_PROFILE_API.md`
- Интеграционные тесты: `profileAPI.integration-test.ts`

## Тестирование в browser console

```typescript
// Импортируй и тестируй
import { profileAPITests } from '@/integrations/api/profileAPI.integration-test'

await profileAPITests.quickTest()
await profileAPITests.runAllTests()
```
