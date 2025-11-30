# useProfile Hook - Интеграция в проект

## Файлы созданы

1. **`frontend/src/hooks/useProfile.ts`** - Основной hook
2. **`frontend/src/hooks/useProfile.examples.md`** - Подробные примеры (8 сценариев)
3. **`frontend/src/components/ProfileHeader.tsx`** - Компонент для header
4. **`frontend/src/components/ProtectedRoute.tsx`** - Защита маршрутов

## Быстрая интеграция (5 минут)

### 1. Использовать в Header (самое популярное)

```tsx
// src/components/Header.tsx или src/layouts/MainLayout.tsx

import { ProfileHeader } from '@/components/ProfileHeader';

export const Header = () => {
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
        <h1>THE BOT</h1>
        <ProfileHeader />  {/* Вот так просто! */}
      </div>
    </header>
  );
};
```

### 2. Защитить маршруты (роутинг)

```tsx
// src/App.tsx или src/router.tsx

import { ProtectedRoute, RoleBasedRoute } from '@/components/ProtectedRoute';
import { StudentDashboard } from './pages/StudentDashboard';
import { TeacherDashboard } from './pages/TeacherDashboard';

function App() {
  return (
    <Routes>
      <Route path="/auth" element={<Auth />} />

      {/* Базовая защита */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* С проверкой роли */}
      <Route
        path="/teacher-dashboard"
        element={
          <ProtectedRoute requiredRole="teacher">
            <TeacherDashboard />
          </ProtectedRoute>
        }
      />

      {/* Со множественными вариантами */}
      <Route
        path="/my-dashboard"
        element={
          <RoleBasedRoute
            student={<StudentDashboard />}
            teacher={<TeacherDashboard />}
            parent={<ParentDashboard />}
            tutor={<TutorDashboard />}
          />
        }
      />
    </Routes>
  );
}
```

### 3. Использовать в компонентах

```tsx
// Вариант 1: Получить полный профиль
import { useProfile } from '@/hooks/useProfile';

export const MyComponent = () => {
  const { profileData, isLoading, error, refetch } = useProfile();

  if (isLoading) return <div>Загружаю...</div>;
  if (error) return <div>Ошибка: {error.message}</div>;

  return <div>Привет, {profileData?.user.full_name}!</div>;
};

// Вариант 2: Только пользователь
import { useProfileUser } from '@/hooks/useProfile';

export const MyComponent = () => {
  const user = useProfileUser();
  return <div>Привет, {user?.full_name}!</div>;
};

// Вариант 3: Проверка авторизации
import { useIsAuthenticated } from '@/hooks/useProfile';

export const MyComponent = () => {
  const { isAuthenticated, user } = useIsAuthenticated();

  if (!isAuthenticated) {
    return <div>Вы не авторизованы</div>;
  }

  return <div>Привет, {user?.full_name}!</div>;
};
```

## Примеры использования в существующих компонентах

### Пример 1: Заголовок страницы с информацией о пользователе

```tsx
// src/pages/Profile/ProfilePage.tsx

import { useProfile } from '@/hooks/useProfile';

export const ProfilePage = () => {
  const { profileData, isLoading, error, refetch } = useProfile();

  if (isLoading) {
    return <div>Загружаю профиль...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-100 text-red-700 p-4 rounded">
        {error.message}
        <button
          onClick={() => refetch()}
          className="ml-4 px-4 py-2 bg-red-600 text-white rounded"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">{profileData?.user.full_name}</h1>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <label className="block text-sm text-gray-600">Email</label>
          <p className="text-lg">{profileData?.user.email}</p>
        </div>

        <div>
          <label className="block text-sm text-gray-600">Телефон</label>
          <p className="text-lg">{profileData?.user.phone || '-'}</p>
        </div>

        <div>
          <label className="block text-sm text-gray-600">Роль</label>
          <p className="text-lg">{profileData?.user.role_display}</p>
        </div>

        <div>
          <label className="block text-sm text-gray-600">Дата регистрации</label>
          <p className="text-lg">
            {new Date(profileData?.user.date_joined || '').toLocaleDateString('ru-RU')}
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Обновить данные
        </button>
      </div>
    </div>
  );
};
```

### Пример 2: Навигация зависит от роли

```tsx
// src/components/Navigation.tsx

import { useProfileUser } from '@/hooks/useProfile';

export const Navigation = () => {
  const user = useProfileUser();

  return (
    <nav className="flex gap-4">
      {/* Видно для всех */}
      <a href="/dashboard">Главная</a>

      {/* Видно только для учителей */}
      {user?.role === 'teacher' && (
        <>
          <a href="/teacher/materials">Материалы</a>
          <a href="/teacher/submissions">Работы учеников</a>
        </>
      )}

      {/* Видно только для тьюторов */}
      {user?.role === 'tutor' && (
        <>
          <a href="/tutor/students">Ученики</a>
          <a href="/tutor/reports">Отчёты</a>
        </>
      )}

      {/* Видно только для родителей */}
      {user?.role === 'parent' && (
        <>
          <a href="/parent/children">Дети</a>
          <a href="/parent/payments">Платежи</a>
        </>
      )}

      {/* Видно для админов */}
      {user?.is_staff && (
        <a href="/admin">Администрирование</a>
      )}
    </nav>
  );
};
```

### Пример 3: Условный рендер с обновлением

```tsx
// src/pages/EditProfile/EditProfilePage.tsx

import { useState } from 'react';
import { useProfile } from '@/hooks/useProfile';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { useToast } from '@/hooks/use-toast';

export const EditProfilePage = () => {
  const { profileData, isLoading, refetch } = useProfile();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState({
    first_name: profileData?.user.first_name || '',
    last_name: profileData?.user.last_name || '',
    phone: profileData?.user.phone || '',
  });

  if (isLoading) {
    return <div>Загружаю данные профиля...</div>;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      const response = await unifiedAPI.updateProfile(formData);

      if (response.success) {
        // Обновляем данные в React Query
        await refetch();

        toast({
          title: "Успешно",
          description: "Профиль обновлён",
        });
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      toast({
        title: "Ошибка",
        description: error instanceof Error ? error.message : 'Неизвестная ошибка',
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Редактировать профиль</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Имя</label>
          <input
            type="text"
            value={formData.first_name}
            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            className="w-full px-3 py-2 border rounded"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Фамилия</label>
          <input
            type="text"
            value={formData.last_name}
            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            className="w-full px-3 py-2 border rounded"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Телефон</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full px-3 py-2 border rounded"
          />
        </div>

        <button
          type="submit"
          disabled={isSaving}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {isSaving ? 'Сохраняю...' : 'Сохранить'}
        </button>
      </form>
    </div>
  );
};
```

## Обработка различных сценариев

### Сценарий 1: Сессия истекла (401)

```tsx
import { useEffect } from 'react';
import { useProfile } from '@/hooks/useProfile';
import { useNavigate } from 'react-router-dom';

export const MyComponent = () => {
  const navigate = useNavigate();
  const { error } = useProfile();

  useEffect(() => {
    if (error?.message.includes('Сессия истекла')) {
      // Показываем алерт и перенаправляем
      alert('Ваша сессия истекла. Пожалуйста, авторизуйтесь снова.');
      navigate('/auth', { replace: true });
    }
  }, [error, navigate]);

  // ...
};
```

### Сценарий 2: Профиль не найден (404)

```tsx
import { useProfile } from '@/hooks/useProfile';

export const MyComponent = () => {
  const { error } = useProfile();

  if (error?.message.includes('не найден')) {
    return (
      <div className="text-center p-8">
        <h2>Профиль не найден</h2>
        <p>Пожалуйста, свяжитесь с поддержкой</p>
        <a href="/" className="text-blue-600">Вернуться на главную</a>
      </div>
    );
  }

  // ...
};
```

### Сценарий 3: Ошибка сети

```tsx
import { useProfile } from '@/hooks/useProfile';

export const MyComponent = () => {
  const { isLoading, error, refetch } = useProfile();

  if (error?.message.includes('Unable to connect')) {
    return (
      <div className="text-center p-8">
        <h2>Ошибка соединения</h2>
        <p>Проверьте подключение к интернету</p>
        <button
          onClick={() => refetch()}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  // ...
};
```

## Лучшие практики для вашего проекта

1. **Используйте ProtectedRoute для всех защищённых страниц**
   - Это минимизирует вероятность утечки данных
   - Автоматически обрабатывает редирект на /auth

2. **Используйте RoleBasedRoute для динамических маршрутов**
   - Когда один маршрут должен показывать разные компоненты в зависимости от роли

3. **Не дублируйте запросы профиля**
   - Используйте useProfile один раз в компоненте
   - React Query автоматически кеширует результат
   - Другие компоненты будут использовать закешированные данные

4. **Обновляйте профиль после его изменения**
   - Всегда вызывайте refetch() после обновления профиля
   - Это гарантирует, что UI синхронизирован с сервером

5. **Показывайте состояние загрузки**
   - Всегда проверяйте isLoading перед выводом данных
   - Покажите spinner или skeleton для лучшего UX

## TypeScript tipying

```tsx
import type { ProfileResponse } from '@/hooks/useProfile';
import type { User } from '@/integrations/api/unifiedClient';

// Если нужно типизировать компонент
interface MyComponentProps {
  profile: ProfileResponse;
  user: User;
}

export const MyComponent: React.FC<MyComponentProps> = ({ profile, user }) => {
  // ...
};
```

## Тестирование (если потребуется)

Примеры для Vitest + React Testing Library:

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useProfile } from '@/hooks/useProfile';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('useProfile', () => {
  it('should load profile', async () => {
    const wrapper = ({ children }) => (
      <QueryClientProvider client={new QueryClient()}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useProfile(), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.profileData).toBeDefined();
    });
  });
});
```

## Миграция существующих компонентов

Если у вас уже есть компоненты, которые используют `useAuth` или другие hooks для получения информации о пользователе:

### До:
```tsx
import { useAuth } from '@/hooks/useAuth';

export const MyComponent = () => {
  const { user, loading } = useAuth();
  // ...
};
```

### После:
```tsx
import { useProfileUser } from '@/hooks/useProfile';

export const MyComponent = () => {
  const user = useProfileUser();
  // ...
};
```

## Поддержка и отладка

### Отладка в DevTools

```tsx
// Добавьте это в компонент для отладки
const { profileData, isLoading, error, isError } = useProfile();

useEffect(() => {
  console.log('[Debug] Profile State:', {
    profileData,
    isLoading,
    error: error?.message,
    isError,
  });
}, [profileData, isLoading, error, isError]);
```

### Логирование в продакшене

Хук уже использует logger из utils/logger.ts для логирования:
- `[useProfile] Fetching profile...` - начало загрузки
- `[useProfile] Profile loaded successfully` - успешная загрузка
- `[useProfile] Authentication error (401)` - ошибка авторизации
- `[useProfile] Profile not found (404)` - профиль не найден
