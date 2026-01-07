import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ParentDashboard from '../ParentDashboard';
import * as useParentHook from '@/hooks/useParent';
import * as useProfileHook from '@/hooks/useProfile';
import * as AuthContext from '@/contexts/AuthContext';
import { parentDashboardAPI } from '@/integrations/api/dashboard';

vi.mock('@/hooks/useParent');
vi.mock('@/hooks/useProfile');
vi.mock('@/contexts/AuthContext');
vi.mock('@/integrations/api/dashboard');
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));
vi.mock('@/components/NotificationSystem', () => ({
  useErrorNotification: () => vi.fn(),
  useSuccessNotification: () => vi.fn(),
}));

vi.mock('@/components/ui/sidebar', () => ({
  SidebarProvider: ({ children }: any) => <div data-testid="sidebar-provider">{children}</div>,
  SidebarInset: ({ children }: any) => <div data-testid="sidebar-inset">{children}</div>,
  SidebarTrigger: () => <button data-testid="sidebar-trigger">Toggle</button>,
}));
vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>,
}));
vi.mock('@/components/LoadingStates', () => ({
  DashboardSkeleton: () => <div data-testid="dashboard-skeleton">Loading...</div>,
  ErrorState: ({ error, onRetry }: any) => (
    <div data-testid="error-state">
      <div>{error}</div>
      <button onClick={onRetry}>Retry</button>
    </div>
  ),
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));
vi.mock('@/components/PaymentStatusBadge', () => ({
  PaymentStatusBadge: ({ status }: any) => <span data-testid="payment-badge">{status}</span>,
}));
vi.mock('@/components/ProfileCard', () => ({
  ProfileCard: ({ userName, userEmail, profileData }: any) => (
    <div data-testid="profile-card">
      <div>{userName}</div>
      <div>{userEmail}</div>
      <div>{profileData.childrenCount} детей</div>
    </div>
  ),
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

const mockProfileData = {
  user: {
    id: 1,
    email: 'parent@example.com',
    full_name: 'Parent User',
    avatar_url: null,
    role: 'parent',
  },
  profile: {},
};

const mockDashboardData = {
  children: [
    {
      id: 1,
      name: 'Alice',
      grade: '10A',
      goal: 'University preparation',
      tutor_name: 'John Tutor',
      progress_percentage: 85,
      progress: 85,
      avatar: null,
      subjects: [
        {
          id: 1,
          enrollment_id: 101,
          name: 'Mathematics',
          teacher_name: 'Math Teacher',
          teacher_id: 10,
          payment_status: 'paid' as any,
          next_payment_date: '2025-02-20',
          has_subscription: true,
          amount: '100.00',
        },
      ],
      payments: [],
    },
  ],
  reports: [
    {
      id: 1,
      student_name: 'Alice',
      title: 'Monthly Progress',
      tutor_name: 'John',
      status: 'sent',
      created_at: '2025-01-15T10:00:00Z',
      week_start: '2025-01-08',
      week_end: '2025-01-15',
    },
  ],
  statistics: {
    total_children: 1,
    average_progress: 85,
    completed_payments: 5,
    pending_payments: 1,
    overdue_payments: 0,
  },
};

describe('ParentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, first_name: 'Parent', last_name: 'User', role: 'parent' },
    } as any);

    vi.mocked(useProfileHook.useProfile).mockReturnValue({
      profileData: mockProfileData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isError: false,
      user: mockProfileData.user,
    } as any);

    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    });
  });

  it('should render dashboard with data', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Личный кабинет родителя/)).toBeInTheDocument();
    });
  });

  it('should render dashboard with loading state', () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    expect(screen.getByTestId('dashboard-skeleton')).toBeInTheDocument();
  });

  it('should display children profiles', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      const aliceElements = screen.getAllByText('Alice');
      expect(aliceElements.length).toBeGreaterThan(0);
    });
  });

  it('should display children subjects', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      const mathElements = screen.getAllByText('Mathematics');
      expect(mathElements.length).toBeGreaterThan(0);
    });
  });

  it('should display payment status badges', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('payment-badge');
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it('should display statistics', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('profile-card')).toBeInTheDocument();
      expect(screen.getByText('Monthly Progress')).toBeInTheDocument();
    });
  });

  it('should display reports section', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Monthly Progress')).toBeInTheDocument();
    });
  });

  it('should show error state when data fetch fails', async () => {
    const mockError = new Error('Failed to load dashboard');

    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: mockError,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeInTheDocument();
    });
  });
})
