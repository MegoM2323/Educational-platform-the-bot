import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import TutorDashboard from '../TutorDashboard';
import * as useTutorHook from '@/hooks/useTutor';

// Mock модулей
vi.mock('@/hooks/useTutor');

// Mock UI компонентов
vi.mock('@/components/ui/sidebar', () => ({
  SidebarProvider: ({ children }: any) => <div data-testid="sidebar-provider">{children}</div>,
  SidebarInset: ({ children }: any) => <div data-testid="sidebar-inset">{children}</div>,
  SidebarTrigger: () => <button data-testid="sidebar-trigger">Toggle</button>,
}));
vi.mock('@/components/layout/TutorSidebar', () => ({
  TutorSidebar: () => <div data-testid="tutor-sidebar">Sidebar</div>,
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

const mockStudents = [
  {
    id: 1,
    full_name: 'Alice Student',
    first_name: 'Alice',
    last_name: 'Student',
    grade: '10A',
    goal: 'University preparation',
    subjects: [
      {
        id: 1,
        name: 'Mathematics',
        teacher_name: 'John Teacher',
        enrollment_id: 101,
      },
    ],
  },
  {
    id: 2,
    full_name: 'Bob Student',
    first_name: 'Bob',
    last_name: 'Student',
    grade: '9B',
    goal: 'General education',
    subjects: [],
  },
  {
    id: 3,
    full_name: 'Charlie Student',
    first_name: 'Charlie',
    last_name: 'Student',
    grade: '11A',
    subjects: [],
  },
];

describe('TutorDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render dashboard with loading state', () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    expect(screen.getByText(/Загрузка…/)).toBeInTheDocument();
  });

  it('should render dashboard with student data', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: mockStudents,
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Личный кабинет тьютора/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Ученики: 3/)).toBeInTheDocument();
  });

  it('should display correct student count', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: mockStudents,
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument(); // student count
    });
  });

  it('should display student list', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: mockStudents,
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Alice Student')).toBeInTheDocument();
      expect(screen.getByText('Bob Student')).toBeInTheDocument();
      expect(screen.getByText('Charlie Student')).toBeInTheDocument();
    });
  });

  it('should display student grades', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: mockStudents,
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/10A класс/)).toBeInTheDocument();
      expect(screen.getByText(/9B класс/)).toBeInTheDocument();
      expect(screen.getByText(/11A класс/)).toBeInTheDocument();
    });
  });

  it('should display student goals when available', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: mockStudents,
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Цель: University preparation/)).toBeInTheDocument();
      expect(screen.getByText(/Цель: General education/)).toBeInTheDocument();
    });
  });

  it('should render quick actions buttons', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: mockStudents,
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Мои ученики')).toBeInTheDocument();
      expect(screen.getByText('Отчёты')).toBeInTheDocument();
      expect(screen.getByText('Общий чат')).toBeInTheDocument();
    });
  });

  it('should handle empty student list', async () => {
    vi.mocked(useTutorHook.useTutorStudents).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);

    render(<TutorDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Ученики: 0/)).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument(); // count in card
    });
  });
});
