# useProfile Hook - Примеры использования

## 1. Базовое использование в компоненте

```tsx
import { useProfile } from '@/hooks/useProfile';

export const ProfileComponent = () => {
  const { profileData, isLoading, error, refetch } = useProfile();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Spinner /> Загружаю профиль...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        <p>Ошибка: {error.message}</p>
        <button
          onClick={() => refetch()}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h1 className="text-2xl font-bold">{profileData?.user.full_name}</h1>
      <p className="text-gray-600">{profileData?.user.email}</p>
      <p className="text-sm text-gray-500">Роль: {profileData?.user.role_display}</p>

      <div className="mt-4 flex gap-2">
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Обновить профиль
        </button>
      </div>
    </div>
  );
};
```

## 2. Использование хука для проверки авторизации (ProtectedRoute)

```tsx
import { Navigate } from 'react-router-dom';
import { useIsAuthenticated } from '@/hooks/useProfile';

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useIsAuthenticated();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner /> Проверка авторизации...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return children;
};

// Использование в App.tsx
<Routes>
  <Route
    path="/dashboard"
    element={
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    }
  />
</Routes>
```

## 3. Использование в Header/Navbar компоненте

```tsx
import { useProfileUser } from '@/hooks/useProfile';
import { Avatar } from '@/components/ui/avatar';

export const Header = () => {
  const user = useProfileUser();

  if (!user) {
    return null; // или показать вход
  }

  return (
    <header className="bg-white shadow">
      <div className="flex justify-between items-center p-4">
        <h1 className="text-2xl font-bold">THE BOT Platform</h1>

        <div className="flex items-center gap-4">
          <span className="text-gray-700">{user.full_name}</span>
          <Avatar
            src={user.avatar}
            fallback={user.first_name[0]}
            alt={user.full_name}
          />
          <button onClick={handleLogout}>Выход</button>
        </div>
      </div>
    </header>
  );
};
```

## 4. Использование с форме редактирования профиля

```tsx
import { useState } from 'react';
import { useProfile } from '@/hooks/useProfile';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { useToast } from '@/hooks/use-toast';

export const EditProfileForm = () => {
  const { profileData, isLoading, refetch } = useProfile();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState({
    first_name: profileData?.user.first_name || '',
    last_name: profileData?.user.last_name || '',
    phone: profileData?.user.phone || '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      const response = await unifiedAPI.updateProfile(formData);

      if (response.success) {
        // Обновляем кеш в React Query
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
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <Spinner />;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
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
  );
};
```

## 5. Условный рендер в зависимости от роли пользователя

```tsx
import { useProfileUser } from '@/hooks/useProfile';

export const RoleBasedComponent = () => {
  const user = useProfileUser();

  if (!user) {
    return <p>Вы не авторизованы</p>;
  }

  return (
    <div>
      {user.role === 'student' && (
        <StudentDashboard />
      )}

      {user.role === 'teacher' && (
        <TeacherDashboard />
      )}

      {user.role === 'parent' && (
        <ParentDashboard />
      )}

      {user.role === 'tutor' && (
        <TutorDashboard />
      )}
    </div>
  );
};
```

## 6. Комбинирование с другими hooks для получения полных данных

```tsx
import { useProfile } from '@/hooks/useProfile';
import { useStudentDashboard } from '@/hooks/useStudent';

export const StudentProfileWithDashboard = () => {
  const { profileData: profile, isLoading: profileLoading } = useProfile();
  const { data: dashboard, isLoading: dashboardLoading } = useStudentDashboard();

  const isLoading = profileLoading || dashboardLoading;

  if (isLoading) {
    return <Spinner />;
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-2">{profile?.user.full_name}</h2>
        <p className="text-gray-600">{profile?.user.email}</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Статистика</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-gray-600">Материалов изучено</p>
            <p className="text-2xl font-bold">{dashboard?.completed_materials}</p>
          </div>
          <div>
            <p className="text-gray-600">Всего материалов</p>
            <p className="text-2xl font-bold">{dashboard?.materials_count}</p>
          </div>
          <div>
            <p className="text-gray-600">Прогресс</p>
            <p className="text-2xl font-bold">{dashboard?.progress_percentage}%</p>
          </div>
        </div>
      </div>
    </div>
  );
};
```

## 7. Использование в контексте (Context API) для глобального состояния

```tsx
import { createContext, useContext, ReactNode } from 'react';
import { useProfile } from '@/hooks/useProfile';

interface UserContextType {
  user: User | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<any>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider = ({ children }: { children: ReactNode }) => {
  const { profileData, isLoading, error, refetch } = useProfile();

  const value: UserContextType = {
    user: profileData?.user,
    isLoading,
    error,
    refetch,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser должен использоваться внутри UserProvider');
  }
  return context;
};

// Использование
<UserProvider>
  <App />
</UserProvider>

// В компонентах
const MyComponent = () => {
  const { user, isLoading } = useUser();
  // ...
};
```

## 8. Обработка ошибок с User Feedback

```tsx
import { useProfile } from '@/hooks/useProfile';
import { AlertDialog } from '@/components/ui/alert-dialog';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';

export const ProfileWithErrorHandling = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { profileData, isLoading, error, refetch } = useProfile();

  // Обрабатываем 401 ошибку (сессия истекла)
  if (error?.message.includes('Сессия истекла')) {
    return (
      <AlertDialog
        title="Сессия истекла"
        description="Ваша сессия истекла. Пожалуйста, авторизуйтесь снова."
        onConfirm={() => navigate('/auth')}
      />
    );
  }

  // Обрабатываем 404 ошибку (профиль не найден)
  if (error?.message.includes('не найден')) {
    return (
      <AlertDialog
        title="Ошибка"
        description="Профиль пользователя не найден. Пожалуйста, свяжитесь с поддержкой."
        actions={
          <button onClick={() => navigate('/')}>На главную</button>
        }
      />
    );
  }

  // Обрабатываем прочие ошибки
  if (error) {
    return (
      <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4">
        <p className="font-bold">Ошибка загрузки профиля</p>
        <p className="mt-1">{error.message}</p>
        <button
          onClick={() => {
            refetch();
            toast({
              description: "Попытка переза ужбозов...",
            });
          }}
          className="mt-2 px-4 py-2 bg-yellow-600 text-white rounded text-sm"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  if (isLoading) {
    return <Spinner text="Загружаю профиль..." />;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h1>{profileData?.user.full_name}</h1>
      <p>{profileData?.user.email}</p>
    </div>
  );
};
```

## Конфигурация Query

### Что означает каждая конфигурация:

- **staleTime: 5 минут** - Данные считаются "свежими" в течение 5 минут. Это значит, что если запрос выполнен менее 5 минут назад, новый запрос не будет выполнен.

- **gcTime: 10 минут** - Неиспользуемые кешированные данные хранятся в памяти 10 минут перед удалением.

- **retry: 1** - При ошибке query будет повторён один раз. Подходит для сетевых ошибок.

- **refetchOnWindowFocus: false** - Не обновляем профиль когда пользователь вернулся в браузер. Профиль медленно меняется, это минимизирует запросы.

- **refetchOnMount: true** - Загружаем профиль при монтировании компонента. Обеспечивает актуальные данные.

- **refetchOnReconnect: true** - Загружаем профиль при восстановлении интернета.

### Кастомизация конфигурации (если нужно):

Если вам нужны другие параметры, создайте вариант hook'а:

```tsx
// useProfile.ts - добавить новый hook
export const useProfileWithCustomConfig = (config?: UseQueryOptions) => {
  // ...использовать конфиг
};

// Использование
const { profileData } = useProfileWithCustomConfig({
  staleTime: 1000 * 60, // 1 минута вместо 5
  refetchOnWindowFocus: true, // Обновлять при фокусе
});
```

## Обработка ошибок API

### 401 Unauthorized (Не авторизован)
- **Что происходит:** Токен истёк или пользователь вышел
- **Обработка:** Hook автоматически очищает кеш и перенаправляет на `/auth`
- **В компоненте:** Проверьте `error?.message.includes('Сессия истекла')`

### 404 Not Found (Профиль не найден)
- **Что происходит:** Профиль удалён или не существует
- **Обработка:** Hook возвращает error с сообщением
- **В компоненте:** Проверьте `error?.message.includes('не найден')`

### Network Error (Ошибка сети)
- **Что происходит:** Сервер недоступен
- **Обработка:** Query повторится 1 раз автоматически
- **В компоненте:** Покажите сообщение об ошибке сети

## TypeScript типы

```tsx
import { useProfile, ProfileResponse } from '@/hooks/useProfile';
import { User } from '@/integrations/api/unifiedClient';

// ProfileResponse
interface ProfileResponse {
  user: User;
  profile?: Record<string, any>;
}

// User
interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'student' | 'teacher' | 'parent' | 'tutor';
  role_display: string;
  phone: string;
  avatar?: string;
  is_verified: boolean;
  is_staff?: boolean;
  date_joined: string;
  full_name: string;
}

// Return type useProfile
{
  profileData: ProfileResponse | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<...>;
  isError: boolean;
  user: User | undefined;
}
```

## Лучшие практики

1. **Кешируйте на уровне Query** - Не создавайте дополнительное состояние в компоненте для данных профиля
2. **Используйте refetch для обновления** - После изменения профиля вызовите `refetch()`
3. **Проверяйте состояние загрузки** - Всегда показывайте spinner при `isLoading`
4. **Обрабатывайте ошибки gracefully** - Покажите пользователю понятное сообщение об ошибке
5. **Не запрашивайте профиль часто** - staleTime: 5 минут достаточно для большинства сценариев
6. **Используйте useProfileUser для простых случаев** - Если вам нужны только данные пользователя

## Производительность

- **Запросы:** 1 запрос при монтировании, потом максимум каждые 5 минут
- **Кеширование:** Автоматическое кеширование на 10 минут
- **Оптимизация:** Перенаправление на /auth обрабатывается автоматически при 401
- **Размер бандла:** Минимальный - только использует встроенные react-query
