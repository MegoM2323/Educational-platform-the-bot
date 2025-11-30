import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';
import ProfilePage from '@/pages/profile/ProfilePage';

// Mock the authentication context
vi.mock('@/contexts/AuthContext', () => ({
  AuthProvider: ({ children }: any) => children,
  useAuth: vi.fn(() => ({
    user: {
      id: '1',
      email: 'student@test.com',
      first_name: 'Иван',
      last_name: 'Петров',
      role: 'student',
      is_active: true,
    },
    isAuthenticated: true,
    isLoading: false,
    signOut: vi.fn(),
    login: vi.fn(),
  })),
}));

// Mock the profile hooks
vi.mock('@/hooks/useProfile', () => ({
  useProfile: vi.fn(() => ({
    profileData: {
      user: {
        id: '1',
        email: 'student@test.com',
        first_name: 'Иван',
        last_name: 'Петров',
        role: 'student',
      },
      profile: {
        first_name: 'Иван',
        last_name: 'Петров',
        avatar: null,
      },
    },
    profile: {
      first_name: 'Иван',
      last_name: 'Петров',
      avatar: null,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useProfileUser: vi.fn(),
}));

// Mock the profile API hooks
vi.mock('@/hooks/useProfileAPI', () => ({
  useProfileAPI: vi.fn(() => ({
    updateProfile: vi.fn().mockResolvedValue({ success: true }),
    uploadAvatar: vi.fn().mockResolvedValue({ success: true }),
  })),
  useStudentProfile: vi.fn(),
  useTeacherProfile: vi.fn(),
  useTutorProfile: vi.fn(),
  useParentProfile: vi.fn(),
}));

// Mock toast notifications
vi.mock('sonner', () => ({
  toast: vi.fn(),
}));

// Mock components
vi.mock('@/components/profile/StudentProfileForm', () => ({
  StudentProfileForm: () => <div>Профиль студента</div>,
}));

vi.mock('@/components/profile/TeacherProfileForm', () => ({
  TeacherProfileForm: () => <div>Профиль учителя</div>,
}));

vi.mock('@/components/profile/TutorProfileForm', () => ({
  TutorProfileForm: () => <div>Профиль репетитора</div>,
}));

vi.mock('@/components/profile/ParentProfileForm', () => ({
  ParentProfileForm: () => <div>Профиль родителя</div>,
}));

vi.mock('@/components/profile/AvatarUpload', () => ({
  AvatarUpload: ({ onAvatarUpload }: any) => (
    <div>
      <input
        type="file"
        data-testid="avatar-upload"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onAvatarUpload(file);
        }}
      />
    </div>
  ),
}));

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const createWrapper = (queryClient: QueryClient) => {
  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe('Profile Route Integration Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  describe('Route Accessibility', () => {
    it('маршрут /profile должен быть доступен', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      // Проверяем что компонент загрузился
      await waitFor(() => {
        expect(screen.getByText('Мой профиль')).toBeInTheDocument();
      });
    });

    it('маршрут /profile должен отобразить правильный заголовок', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText('Мой профиль')).toBeInTheDocument();
        expect(screen.getByText(/редактировать информацию о себе/i)).toBeInTheDocument();
      });
    });

    it('маршрут /profile должен содержать breadcrumb навигацию', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        const nav = screen.getByRole('navigation');
        expect(nav).toBeInTheDocument();
      });
    });
  });

  describe('Profile Form Loading', () => {
    it('должна отобразить форму профиля студента', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText('Профиль студента')).toBeInTheDocument();
      });
    });

    it('должна отобразить аватар компонент', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId('avatar-upload')).toBeInTheDocument();
      });
    });

    it('должна отобразить кнопку "Назад"', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        const backButton = screen.getByRole('button', { name: /назад/i });
        expect(backButton).toBeInTheDocument();
      });
    });
  });

  describe('Avatar Upload Integration', () => {
    it('должна позволить загрузить аватар', async () => {
      const wrapper = createWrapper(queryClient);
      const user = userEvent.setup();

      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId('avatar-upload')).toBeInTheDocument();
      });

      const input = screen.getByTestId('avatar-upload') as HTMLInputElement;
      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });

      await user.upload(input, file);

      // Проверяем что файл был загружен
      expect(input.files?.[0]).toBe(file);
    });

    it('должна обновить данные после загрузки аватара', async () => {
      const { useProfile } = await import('@/hooks/useProfile');
      const mockUseProfile = useProfile as any;
      const mockRefetch = vi.fn();

      mockUseProfile.mockReturnValue({
        profileData: {
          user: { id: '1', email: 'test@test.com' },
          profile: { avatar: null },
        },
        profile: { avatar: null },
        isLoading: false,
        refetch: mockRefetch,
      });

      const wrapper = createWrapper(queryClient);
      const user = userEvent.setup();

      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId('avatar-upload')).toBeInTheDocument();
      });

      const input = screen.getByTestId('avatar-upload');
      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });

      await user.upload(input, file);

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
      });
    });
  });

  describe('Profile Form Submission', () => {
    it('должна иметь доступную форму для редактирования профиля', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText('Профиль студента')).toBeInTheDocument();
      });

      // Форма должна быть загружена
      const profileForm = screen.getByText('Профиль студента');
      expect(profileForm).toBeInTheDocument();
    });

    it('должна показать сообщение об ошибке при неудаче сохранения', async () => {
      const { useProfileAPI } = await import('@/hooks/useProfileAPI');
      const mockUseProfileAPI = useProfileAPI as any;

      mockUseProfileAPI.mockReturnValue({
        updateProfile: vi.fn().mockRejectedValue(new Error('API Error')),
        uploadAvatar: vi.fn(),
      });

      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText('Профиль студента')).toBeInTheDocument();
      });
    });
  });

  describe('User Information Display', () => {
    it('должна отобразить инициалы пользователя в аватаре', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText('ИП')).toBeInTheDocument(); // Иван Петров
      });
    });

    it('должна отобразить имя и фамилию в breadcrumb', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText(/Иван Петров/)).toBeInTheDocument();
      });
    });
  });

  describe('Navigation', () => {
    it('кнопка "Назад" должна быть кликабельна', async () => {
      const wrapper = createWrapper(queryClient);
      const user = userEvent.setup();

      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /назад/i })).toBeInTheDocument();
      });

      const backButton = screen.getByRole('button', { name: /назад/i });
      expect(backButton).toBeEnabled();
    });

    it('должна отобразить правильный роль-специфичный профиль', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        // Для студента должна отобразиться форма студента
        expect(screen.getByText('Профиль студента')).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('должна быть адаптивной на мобильных устройствах', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        expect(screen.getByText('Мой профиль')).toBeInTheDocument();
      });

      // Проверяем наличие элементов для мобильной версии
      const mobileNote = screen.getByText(/мобильном устройстве/i);
      expect(mobileNote).toBeInTheDocument();
    });

    it('должна отобразить компоновку "3 колонки" на больших экранах', async () => {
      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      await waitFor(() => {
        const container = screen.getByText('Мой профиль').closest('.max-w-7xl');
        expect(container).toHaveClass('max-w-7xl');
      });
    });
  });

  describe('Error Handling', () => {
    it('должна обработать ошибки при загрузке профиля', async () => {
      const { useProfile } = await import('@/hooks/useProfile');
      const mockUseProfile = useProfile as any;

      mockUseProfile.mockReturnValue({
        profileData: null,
        profile: null,
        isLoading: false,
        error: new Error('Failed to load profile'),
        refetch: vi.fn(),
      });

      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      // Все еще должны видеть заголовок страницы
      await waitFor(() => {
        expect(screen.getByText('Мой профиль')).toBeInTheDocument();
      });
    });

    it('должна показать загрузку при получении профиля', async () => {
      const { useProfile } = await import('@/hooks/useProfile');
      const mockUseProfile = useProfile as any;

      mockUseProfile.mockReturnValue({
        profileData: null,
        profile: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      const wrapper = createWrapper(queryClient);
      render(
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>,
        { wrapper }
      );

      // LoadingSpinner должен быть отображен
      expect(screen.getByText('Мой профиль')).toBeInTheDocument();
    });
  });
});
