import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import TeacherDashboard from '../TeacherDashboard';
import * as useTeacherHook from '@/hooks/useTeacher';
import * as AuthContext from '@/contexts/AuthContext';

// Mock модулей
vi.mock('@/hooks/useTeacher');
vi.mock('@/contexts/AuthContext');
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

// Mock UI компонентов
vi.mock('@/components/ui/sidebar', () => ({
  SidebarProvider: ({ children }: any) => <div data-testid="sidebar-provider">{children}</div>,
  SidebarInset: ({ children }: any) => <div data-testid="sidebar-inset">{children}</div>,
  SidebarTrigger: () => <button data-testid="sidebar-trigger">Toggle</button>,
}));
vi.mock('@/components/layout/TeacherSidebar', () => ({
  TeacherSidebar: () => <div data-testid="teacher-sidebar">Sidebar</div>,
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
  materials: [
    {
      id: 1,
      title: 'Algebra Introduction',
      description: 'Basic algebra concepts',
      subject: { id: 1, name: 'Mathematics', color: '#FF5733' },
      status: 'active' as const,
      assigned_count: 15,
      created_at: '2025-01-10T10:00:00Z',
    },
    {
      id: 2,
      title: 'Physics Laws',
      description: 'Newton laws',
      subject: { id: 2, name: 'Physics', color: '#33FF57' },
      status: 'draft' as const,
      assigned_count: 8,
      created_at: '2025-01-12T10:00:00Z',
    },
  ],
  students: [
    {
      id: 1,
      name: 'Alice Student',
      profile: { grade: '10A', progress_percentage: 85 },
      subjects: [],
    },
    {
      id: 2,
      name: 'Bob Student',
      profile: { grade: '10B', progress_percentage: 72 },
      subjects: [],
    },
  ],
  reports: [
    {
      id: 1,
      title: 'Monthly Progress',
      student_name: 'Alice Student',
      subject: 'Mathematics',
      created_at: '2025-01-15T10:00:00Z',
      status: 'sent' as const,
    },
  ],
  progress_overview: {
    total_students: 25,
    total_materials: 12,
    total_assignments: 45,
    completed_assignments: 30,
  },
};

const mockPendingSubmissions = [
  {
    id: 1,
    material_id: 101,
    material_title: 'Algebra Homework',
    student_id: 1,
    student_name: 'Alice Student',
    submitted_at: '2025-01-20T10:00:00Z',
    status: 'pending' as const,
  },
  {
    id: 2,
    material_id: 102,
    material_title: 'Physics Quiz',
    student_id: 2,
    student_name: 'Bob Student',
    submitted_at: '2025-01-19T14:30:00Z',
    status: 'pending' as const,
  },
];

describe('TeacherDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useAuth
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, first_name: 'John', last_name: 'Teacher', role: 'teacher' },
    } as any);
  });

  it('should render dashboard with loading state', () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: true,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    expect(screen.getByTestId('sidebar-provider')).toBeInTheDocument();
  });

  it('should render dashboard with data', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: mockPendingSubmissions,
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Личный кабинет преподавателя/)).toBeInTheDocument();
    });

    expect(screen.getByText(/John.*25 учеников/)).toBeInTheDocument();
  });

  it('should display statistics correctly', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: mockPendingSubmissions,
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument(); // total students
      expect(screen.getByText('12')).toBeInTheDocument(); // total materials
    });
  });

  it('should show error state when data fetch fails', async () => {
    const mockError = new Error('Failed to load dashboard');

    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: mockError,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Failed to load dashboard/)).toBeInTheDocument();
    });
  });

  it('should render materials section', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Algebra Introduction')).toBeInTheDocument();
      expect(screen.getByText('Physics Laws')).toBeInTheDocument();
    });
  });

  it('should render students section', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Alice Student')).toBeInTheDocument();
      expect(screen.getByText('Bob Student')).toBeInTheDocument();
    });
  });

  it('should render pending submissions', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: mockPendingSubmissions,
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Algebra Homework')).toBeInTheDocument();
      expect(screen.getByText('Physics Quiz')).toBeInTheDocument();
    });
  });

  it('should render reports section', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Monthly Progress')).toBeInTheDocument();
    });
  });

  it('should display create material button', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Создать материал')).toBeInTheDocument();
    });
  });

  it('should show notification badge', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: mockPendingSubmissions,
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // notification badge
    });
  });

  it('should handle empty materials list', async () => {
    const emptyData = {
      ...mockDashboardData,
      materials: [],
    };

    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: emptyData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-provider')).toBeInTheDocument();
    });
  });

  it('should handle empty students list', async () => {
    const emptyData = {
      ...mockDashboardData,
      students: [],
    };

    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: emptyData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-provider')).toBeInTheDocument();
    });
  });

  it('should handle empty pending submissions', async () => {
    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Личный кабинет преподавателя/)).toBeInTheDocument();
    });
  });

  it('should display user name from auth context', async () => {
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, first_name: 'Jane', last_name: 'Smith', role: 'teacher' },
    } as any);

    vi.mocked(useTeacherHook.useTeacherDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useTeacherHook.usePendingSubmissions).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TeacherDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Jane/)).toBeInTheDocument();
    });
  });
});
