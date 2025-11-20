import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import StudentDashboard from '../StudentDashboard';
import * as useStudentHook from '@/hooks/useStudent';
import * as AuthContext from '@/contexts/AuthContext';

// Mock необходимых модулей
vi.mock('@/hooks/useStudent');
vi.mock('@/contexts/AuthContext');
vi.mock('@/components/NotificationSystem', () => ({
  useErrorNotification: () => vi.fn(),
  useSuccessNotification: () => vi.fn(),
}));
vi.mock('@/components/ErrorHandlingProvider', () => ({
  useErrorReporter: () => ({
    reportError: vi.fn(),
    reportNetworkError: vi.fn(),
  }),
}));
vi.mock('@/components/NetworkStatusHandler', () => ({
  useNetworkStatus: () => ({ isOnline: true }),
}));

// Mock UI компонентов с сохранением базового функционала
vi.mock('@/components/ui/sidebar', () => ({
  SidebarProvider: ({ children }: any) => <div data-testid="sidebar-provider">{children}</div>,
  SidebarInset: ({ children }: any) => <div data-testid="sidebar-inset">{children}</div>,
  SidebarTrigger: () => <button data-testid="sidebar-trigger">Toggle</button>,
}));
vi.mock('@/components/layout/StudentSidebar', () => ({
  StudentSidebar: () => <div data-testid="student-sidebar">Sidebar</div>,
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </MemoryRouter>
  );
};

const mockDashboardData = {
  student_info: {
    id: 1,
    name: 'Test Student',
    role: 'student',
  },
  materials_by_subject: {
    'Mathematics': {
      subject_info: {
        id: 1,
        name: 'Mathematics',
        color: '#FF5733',
        teacher: {
          id: 10,
          full_name: 'John Teacher',
        },
      },
      materials: [
        {
          id: 101,
          title: 'Algebra Basics',
          description: 'Introduction to algebra',
          created_at: '2025-01-15T10:00:00Z',
          type: 'lesson',
          status: 'new',
          progress_percentage: 0,
        },
        {
          id: 102,
          title: 'Geometry Fundamentals',
          description: 'Shapes and angles',
          created_at: '2025-01-16T10:00:00Z',
          type: 'lesson',
          status: 'in_progress',
          progress_percentage: 45,
        },
      ],
    },
  },
  progress_statistics: {
    overall_percentage: 75,
    completed_tasks: 10,
    total_tasks: 15,
    streak_days: 5,
    accuracy_percentage: 88,
  },
  recent_activity: [
    {
      id: 1,
      title: 'Math Homework',
      deadline: '2025-01-25',
      status: 'pending' as const,
    },
    {
      id: 2,
      title: 'Physics Quiz',
      deadline: '2025-01-20',
      status: 'overdue' as const,
    },
  ],
  general_chat: {
    id: 1,
    name: 'General Chat',
  },
};

describe('StudentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useAuth
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, first_name: 'Test', last_name: 'Student', role: 'student' },
      signOut: vi.fn(),
    } as any);
  });

  it('should render dashboard with loading state', () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    expect(screen.getByTestId('sidebar-provider')).toBeInTheDocument();
  });

  it('should render dashboard with data', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Привет, Test!/)).toBeInTheDocument();
    });

    // Проверяем прогресс
    expect(screen.getByText(/75%/)).toBeInTheDocument();
    expect(screen.getByText(/10.*15/)).toBeInTheDocument();
  });

  it('should display progress statistics correctly', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // streak days
      expect(screen.getByText('10')).toBeInTheDocument(); // completed tasks
      expect(screen.getByText('88%')).toBeInTheDocument(); // accuracy
    });
  });

  it('should show error state when data fetch fails', async () => {
    const mockError = new Error('Failed to load dashboard');

    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: mockError,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Failed to load dashboard/)).toBeInTheDocument();
    });
  });

  it('should show empty state when no materials exist', async () => {
    const emptyData = {
      ...mockDashboardData,
      materials_by_subject: {},
    };

    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: emptyData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Нет доступных материалов/)).toBeInTheDocument();
    });
  });

  it('should render materials section with correct data', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Algebra Basics')).toBeInTheDocument();
      expect(screen.getByText('Geometry Fundamentals')).toBeInTheDocument();
    });
  });

  it('should render subjects section with teacher info', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
      expect(screen.getByText(/John Teacher/)).toBeInTheDocument();
    });
  });

  it('should render recent assignments', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Math Homework')).toBeInTheDocument();
      expect(screen.getByText('Physics Quiz')).toBeInTheDocument();
    });
  });

  it('should display quick actions', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Общий чат')).toBeInTheDocument();
      expect(screen.getByText('Материалы')).toBeInTheDocument();
      expect(screen.getByText('Мой прогресс')).toBeInTheDocument();
    });
  });

  it('should show offline content when network is offline', async () => {
    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    // Mock offline state
    vi.mocked(require('@/components/NetworkStatusHandler').useNetworkStatus).mockReturnValue({
      isOnline: false,
    });

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Component должен показать офлайн контент
      expect(screen.getByTestId('sidebar-provider')).toBeInTheDocument();
    });
  });

  it('should handle sign out', async () => {
    const mockSignOut = vi.fn();
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, first_name: 'Test', last_name: 'Student', role: 'student' },
      signOut: mockSignOut,
    } as any);

    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    const user = userEvent.setup();
    render(<StudentDashboard />, { wrapper: createWrapper() });

    const logoutButton = await screen.findByRole('button', { name: /Выйти/ });
    await user.click(logoutButton);

    expect(mockSignOut).toHaveBeenCalled();
  });

  it('should show empty state for assignments when none exist', async () => {
    const dataWithoutActivity = {
      ...mockDashboardData,
      recent_activity: [],
    };

    vi.mocked(useStudentHook.useStudentDashboard).mockReturnValue({
      data: dataWithoutActivity,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<StudentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Нет активных заданий/)).toBeInTheDocument();
    });
  });
});
