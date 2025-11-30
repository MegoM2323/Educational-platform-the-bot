# useProfile Hook - Полная документация

## Обзор

`useProfile` - это custom React hook для управления профилем пользователя с полной поддержкой кеширования через TanStack Query. Он обеспечивает надежную загрузку, обновление и управление данными профиля с автоматической обработкой ошибок авторизации.

## Что создано

### 1. Основной Hook: `useProfile.ts`

Три связанных hook'а для различных сценариев:

#### `useProfile()` - Полный hook для работы с профилем

```tsx
const { profileData, isLoading, error, refetch, isError, user } = useProfile();
```

**Возвращает:**
- `profileData: ProfileResponse | undefined` - Полные данные профиля (user + profile)
- `isLoading: boolean` - Загружаются ли данные
- `error: Error | null` - Ошибка если произошла
- `refetch: () => Promise<...>` - Функция для принудительного обновления
- `isError: boolean` - Есть ли ошибка
- `user: User | undefined` - Данные пользователя (сокращенно)

#### `useProfileUser()` - Только данные пользователя

```tsx
const user = useProfileUser();
// user: User | undefined
```

Использует для простых случаев когда нужны только данные пользователя.

#### `useIsAuthenticated()` - Проверка авторизации

```tsx
const { isAuthenticated, isLoading, user, error } = useIsAuthenticated();
```

**Возвращает:**
- `isAuthenticated: boolean` - Авторизован ли пользователь
- `isLoading: boolean` - Загружаются ли данные
- `user: User | undefined` - Данные пользователя если авторизован
- `error: Error | null` - Ошибка если произошла

### 2. Компоненты

#### `ProfileHeader.tsx` - Компонент для Header

Готовый компонент который:
- Показывает имя и роль пользователя
- Отображает аватар если есть
- Кнопка для редактирования профиля
- Кнопка для выхода

```tsx
<header className="bg-white shadow">
  <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
    <h1>THE BOT</h1>
    <ProfileHeader />  {/* Вот так просто! */}
  </div>
</header>
```

#### `ProtectedRoute.tsx` - Защита маршрутов

Три компонента для роутинга:

- **`ProtectedRoute`** - Базовая защита от неавторизованных
- **`RoleBasedRoute`** - Рендер разных компонентов по ролям
- **`useRequireAuth()`** - Hook для проверки внутри компонента

```tsx
<Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />

<Route path="/teacher" element={<ProtectedRoute requiredRole="teacher"><TeacherDashboard /></ProtectedRoute>} />

<Route path="/my-dashboard" element={<RoleBasedRoute
  student={<StudentDashboard />}
  teacher={<TeacherDashboard />}
  parent={<ParentDashboard />}
  tutor={<TutorDashboard />}
/>} />
```

## Конфигурация Query

| Параметр | Значение | Описание |
|----------|---------|-----------|
| `queryKey` | `['profile']` | Уникальный ключ для кеша |
| `staleTime` | 5 минут | Время в течение которого данные считаются свежими |
| `gcTime` | 10 минут | Время кеширования неиспользуемых данных |
| `retry` | 1 | Количество повторов при ошибке |
| `refetchOnWindowFocus` | `false` | Не обновлять при фокусе окна |
| `refetchOnMount` | `true` | Загружать при монтировании компонента |
| `refetchOnReconnect` | `true` | Загружать при восстановлении соединения |
| `throwOnError` | `true` | Выбрасывать ошибку для доступа в компоненте |

## Обработка ошибок

### 401 - Не авторизован

```tsx
if (error?.message.includes('Сессия истекла')) {
  // Пользователь разлогинится автоматически
  // И перенаправится на /auth
}
```

**Что происходит:**
1. Hook очищает весь кеш React Query
2. Очищает токены авторизации
3. Перенаправляет на `/auth`

### 404 - Профиль не найден

```tsx
if (error?.message.includes('не найден')) {
  // Показать страницу ошибки
}
```

### Сетевые ошибки

```tsx
if (error?.message.includes('Unable to connect')) {
  // Показать сообщение о сетевой ошибке
  // Пользователь может нажать "Попробовать снова"
}
```

Hook автоматически повторит запрос 1 раз при сетевой ошибке.

## Примеры использования

### 1. Использование в Header

```tsx
import { ProfileHeader } from '@/components/ProfileHeader';

export const Header = () => {
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
        <h1>THE BOT Platform</h1>
        <ProfileHeader />
      </div>
    </header>
  );
};
```

### 2. Защита маршрутов

```tsx
import { ProtectedRoute, RoleBasedRoute } from '@/components/ProtectedRoute';

function App() {
  return (
    <Routes>
      <Route path="/auth" element={<Auth />} />
      
      <Route path="/student-dashboard" element={
        <ProtectedRoute requiredRole="student">
          <StudentDashboard />
        </ProtectedRoute>
      } />

      <Route path="/dashboard" element={
        <RoleBasedRoute
          student={<StudentDashboard />}
          teacher={<TeacherDashboard />}
          parent={<ParentDashboard />}
          tutor={<TutorDashboard />}
        />
      } />
    </Routes>
  );
}
```

### 3. Полный профиль

```tsx
import { useProfile } from '@/hooks/useProfile';

export const ProfilePage = () => {
  const { profileData, isLoading, error, refetch } = useProfile();

  if (isLoading) return <div>Загружаю...</div>;
  if (error) return <div>Ошибка: {error.message}</div>;

  return (
    <div>
      <h1>{profileData?.user.full_name}</h1>
      <p>{profileData?.user.email}</p>
      <p>Роль: {profileData?.user.role_display}</p>
      
      <button onClick={() => refetch()}>Обновить</button>
    </div>
  );
};
```

### 4. Только пользователь

```tsx
import { useProfileUser } from '@/hooks/useProfile';

export const Navigation = () => {
  const user = useProfileUser();

  return (
    <nav>
      <a href="/dashboard">Главная</a>
      
      {user?.role === 'teacher' && (
        <a href="/teacher/materials">Материалы</a>
      )}
      
      {user?.role === 'tutor' && (
        <a href="/tutor/students">Ученики</a>
      )}
    </nav>
  );
};
```

### 5. Проверка авторизации

```tsx
import { useIsAuthenticated } from '@/hooks/useProfile';

export const Dashboard = () => {
  const { isAuthenticated, isLoading, user } = useIsAuthenticated();

  if (isLoading) return <div>Проверка авторизации...</div>;
  if (!isAuthenticated) return <Navigate to="/auth" />;

  return <div>Добро пожаловать, {user?.first_name}!</div>;
};
```

### 6. Редактирование профиля с refetch

```tsx
import { useProfile } from '@/hooks/useProfile';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

export const EditProfileForm = () => {
  const { profileData, refetch } = useProfile();
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (formData) => {
    setIsSaving(true);
    try {
      const response = await unifiedAPI.updateProfile(formData);
      if (response.success) {
        await refetch(); // Обновляем данные
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      handleSave({...formData});
    }}>
      {/* Form fields */}
      <button type="submit" disabled={isSaving}>
        {isSaving ? 'Сохраняю...' : 'Сохранить'}
      </button>
    </form>
  );
};
```

## TypeScript типы

```tsx
// Тип ответа профиля
interface ProfileResponse {
  user: User;
  profile?: Record<string, any>;
}

// Тип пользователя
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
```

## Логирование

Hook использует встроенный logger для отладки:

```
[useProfile] Fetching profile...
[useProfile] Profile loaded successfully { userId: 123, ... }
[useProfile] Authentication error (401), clearing cache...
[useProfile] Profile not found (404)
[useProfile] Query function error: [error message]
```

Для отладки смотрите `utils/logger.ts`.

## Лучшие практики

1. **Используйте ProtectedRoute для защиты страниц**
   ```tsx
   <ProtectedRoute>
     <SecureComponent />
   </ProtectedRoute>
   ```

2. **Используйте RoleBasedRoute для ролевого доступа**
   ```tsx
   <RoleBasedRoute
     teacher={<TeacherPage />}
     student={<StudentPage />}
   />
   ```

3. **Не дублируйте запросы**
   ```tsx
   // Один раз в компоненте
   const { profileData } = useProfile();
   // Другие компоненты будут использовать кеш
   ```

4. **Обновляйте после изменений**
   ```tsx
   const response = await updateProfile(data);
   if (response.success) {
     await refetch();
   }
   ```

5. **Всегда обрабатывайте состояния**
   ```tsx
   if (isLoading) return <Spinner />;
   if (error) return <ErrorMessage error={error} />;
   return <Content data={profileData} />;
   ```

## Интеграция в существующий проект

Если у вас уже есть компоненты используя другие hooks:

### Было:
```tsx
import { useAuth } from '@/hooks/useAuth';

const { user, loading } = useAuth();
```

### Стало:
```tsx
import { useProfileUser } from '@/hooks/useProfile';

const user = useProfileUser();
```

## Производительность

- **Запросы:** 1 при монтировании + при необходимости (refetch)
- **Кеширование:** 5 минут для свежести, 10 минут хранения
- **Автоматические обновления:** На восстановление соединения
- **Оптимизация:** React Query деденцирует дублирующиеся запросы

## Связанные файлы документации

- **`useProfile.examples.md`** - 8 подробных примеров использования
- **`useProfile.INTEGRATION.md`** - Полное руководство интеграции с реальными компонентами

## Поддержка

Вопросы или проблемы? Проверьте:

1. Загружен ли token в локальное хранилище
2. Верный ли endpoint `/auth/profile/` на бэкенде
3. Есть ли `Authorization: Token <token>` заголовок в запросе
4. Логи в DevTools (Ctrl+Shift+K) для деталей ошибки
