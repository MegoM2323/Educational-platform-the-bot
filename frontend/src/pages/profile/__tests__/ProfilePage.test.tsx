import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfilePage } from '../ProfilePage';

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: any) => children,
}));

vi.mock('@/hooks/useProfileAPI', () => ({
  useStudentProfile: vi.fn(),
  useUpdateStudentProfile: vi.fn(),
  useUploadStudentAvatar: vi.fn(),
  useTeacherProfile: vi.fn(),
  useUpdateTeacherProfile: vi.fn(),
  useUploadTeacherAvatar: vi.fn(),
  useTutorProfile: vi.fn(),
  useUpdateTutorProfile: vi.fn(),
  useUploadTutorAvatar: vi.fn(),
  useParentProfile: vi.fn(),
  useUpdateParentProfile: vi.fn(),
  useUploadParentAvatar: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: vi.fn(() => vi.fn()),
  };
});

import { useAuth } from '@/contexts/AuthContext';
import * as profileHooks from '@/hooks/useProfileAPI';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe('ProfilePage', () => {
  const mockUseAuth = useAuth as any;

  const defaultUser = {
    id: '1',
    email: 'student@test.com',
    first_name: 'Иван',
    last_name: 'Петров',
    role: 'student' as const,
    avatar_url: null,
  };

  const defaultProfileData = {
    user: defaultUser,
    profile: {
      grade: 10,
      goal: 'Improve math skills',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuth.mockReturnValue({
      user: defaultUser,
      isAuthenticated: true,
      isLoading: false,
    });

    (profileHooks.useStudentProfile as any).mockReturnValue({
      data: defaultProfileData,
      isLoading: false,
    });

    (profileHooks.useUpdateStudentProfile as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useUploadStudentAvatar as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useTeacherProfile as any).mockReturnValue({
      data: defaultProfileData,
      isLoading: false,
    });

    (profileHooks.useUpdateTeacherProfile as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useUploadTeacherAvatar as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useTutorProfile as any).mockReturnValue({
      data: defaultProfileData,
      isLoading: false,
    });

    (profileHooks.useUpdateTutorProfile as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useUploadTutorAvatar as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useParentProfile as any).mockReturnValue({
      data: defaultProfileData,
      isLoading: false,
    });

    (profileHooks.useUpdateParentProfile as any).mockReturnValue({
      mutate: vi.fn(),
    });

    (profileHooks.useUploadParentAvatar as any).mockReturnValue({
      mutate: vi.fn(),
    });
  });

  it('должна отобразить форму для студента', () => {
    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('Профиль студента')).toBeInTheDocument();
  });

  it('должна отобразить форму для учителя', () => {
    mockUseAuth.mockReturnValue({
      user: { ...defaultUser, role: 'teacher' },
      isAuthenticated: true,
      isLoading: false,
    });

    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('Профиль учителя')).toBeInTheDocument();
  });

  it('должна отобразить форму для репетитора', () => {
    mockUseAuth.mockReturnValue({
      user: { ...defaultUser, role: 'tutor' },
      isAuthenticated: true,
      isLoading: false,
    });

    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('Профиль репетитора')).toBeInTheDocument();
  });

  it('должна отобразить форму для родителя', () => {
    mockUseAuth.mockReturnValue({
      user: { ...defaultUser, role: 'parent' },
      isAuthenticated: true,
      isLoading: false,
    });

    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('Профиль родителя')).toBeInTheDocument();
  });

  it('должна отобразить заголовок страницы', () => {
    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('Мой профиль')).toBeInTheDocument();
  });

  it('должна отобразить инициалы в аватаре', () => {
    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('ИП')).toBeInTheDocument();
  });

  it('должна иметь правильный breadcrumb', () => {
    render(<ProfilePage />, { wrapper: createWrapper() });
    const breadcrumb = screen.getByText('Профиль').closest('nav');
    expect(breadcrumb).toBeInTheDocument();
  });

  it('должна отобразить текст профиля', () => {
    render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText(/редактировать информацию о себе/i)).toBeInTheDocument();
  });

  it('должна отобразить формы профиля для разных ролей', () => {
    const { rerender } = render(<ProfilePage />, { wrapper: createWrapper() });
    expect(screen.getByText('Профиль студента')).toBeInTheDocument();

    mockUseAuth.mockReturnValue({
      user: { ...defaultUser, role: 'teacher' },
      isAuthenticated: true,
      isLoading: false,
    });

    rerender(<ProfilePage />);
    expect(screen.getByText('Профиль учителя')).toBeInTheDocument();
  });
});
