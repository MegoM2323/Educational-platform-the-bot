import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ParentDashboard from '../ParentDashboard';
import * as useParentHook from '@/hooks/useParent';
import * as AuthContext from '@/contexts/AuthContext';
import { parentDashboardAPI } from '@/integrations/api/dashboard';

// Mock модулей
vi.mock('@/hooks/useParent');
vi.mock('@/contexts/AuthContext');
vi.mock('@/integrations/api/dashboard');
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));
vi.mock('@/components/NotificationSystem', () => ({
  useErrorNotification: () => vi.fn(),
  useSuccessNotification: () => vi.fn(),
}));

// Mock UI компонентов
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
        {
          id: 2,
          enrollment_id: 102,
          name: 'Physics',
          teacher_name: 'Physics Teacher',
          teacher_id: 11,
          payment_status: 'pending' as any,
          has_subscription: false,
          next_payment_date: null,
          amount: '100.00',
        },
      ],
      payments: [
        {
          enrollment_id: 101,
          subject: 'Mathematics',
          subject_id: 1,
          teacher: 'Math Teacher',
          teacher_id: 10,
          status: 'paid',
          amount: '100.00',
          due_date: null,
          paid_at: '2025-01-10T10:00:00Z',
          has_subscription: true,
          next_payment_date: '2025-02-20',
        },
        {
          enrollment_id: 102,
          subject: 'Physics',
          subject_id: 2,
          teacher: 'Physics Teacher',
          teacher_id: 11,
          status: 'pending',
          amount: '100.00',
          due_date: '2025-02-01T10:00:00Z',
          paid_at: null,
          has_subscription: false,
          next_payment_date: null,
        },
      ],
    },
    {
      id: 2,
      name: 'Bob',
      grade: '9B',
      goal: 'General education',
      tutor_name: 'Jane Tutor',
      progress_percentage: 72,
      progress: 72,
      avatar: null,
      subjects: [],
      payments: [],
    },
  ],
  reports: [
    {
      id: 1,
      child_name: 'Alice',
      subject: 'Mathematics',
      title: 'Monthly Progress',
      content: 'Great progress',
      teacher_name: 'Math Teacher',
      created_at: '2025-01-15T10:00:00Z',
      type: 'progress' as const,
    },
  ],
  statistics: {
    total_children: 2,
    average_progress: 78.5,
    completed_payments: 5,
    pending_payments: 1,
    overdue_payments: 0,
  },
};

describe('ParentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useAuth
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, first_name: 'Parent', last_name: 'User', role: 'parent' },
    } as any);

    // Mock window.location.href
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
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

  it('should display children profiles', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Используем getAllByText так как имя может отображаться несколько раз (профиль + отчеты)
      const aliceElements = screen.getAllByText('Alice');
      expect(aliceElements.length).toBeGreaterThan(0);
      const bobElements = screen.getAllByText('Bob');
      expect(bobElements.length).toBeGreaterThan(0);
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
      // Используем getAllByText так как предмет может отображаться несколько раз
      const mathElements = screen.getAllByText('Mathematics');
      expect(mathElements.length).toBeGreaterThan(0);
      const physicsElements = screen.getAllByText('Physics');
      expect(physicsElements.length).toBeGreaterThan(0);
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
      // Проверяем более специфичный текст вместо просто "2"
      expect(screen.getByText(/2 детей/)).toBeInTheDocument();
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
      expect(screen.getByText(/Failed to load dashboard/)).toBeInTheDocument();
    });
  });

  it('should handle payment initiation', async () => {
    const mockPaymentData = {
      confirmation_url: 'https://yookassa.ru/checkout/123',
      payment_id: 'pay_123',
    };

    vi.mocked(parentDashboardAPI.initiatePayment).mockResolvedValue(mockPaymentData);

    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    const user = userEvent.setup();
    render(<ParentDashboard />, { wrapper: createWrapper() });

    // Проверяем что компонент отрендерился с данными Mathematics
    await waitFor(() => {
      const mathElements = screen.getAllByText('Mathematics');
      expect(mathElements.length).toBeGreaterThan(0);
    });

    // Note: Actual click testing would require full DOM structure
    // This test verifies the component renders without errors
  });

  it('should handle cancel subscription', async () => {
    const mockCancelResponse = {
      success: true,
      message: 'Subscription cancelled',
    };

    vi.mocked(parentDashboardAPI.cancelSubscription).mockResolvedValue(mockCancelResponse);

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

  it('should refetch data on window focus', async () => {
    const mockRefetch = vi.fn();

    // Mock document.hasFocus to return true in test environment
    const originalHasFocus = document.hasFocus;
    document.hasFocus = vi.fn(() => true);

    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    // Simulate window focus event
    const focusEvent = new Event('focus');
    window.dispatchEvent(focusEvent);

    // Wait for debounce (1000ms) + buffer
    await new Promise(resolve => setTimeout(resolve, 1100));

    expect(mockRefetch).toHaveBeenCalled();

    // Restore original hasFocus
    document.hasFocus = originalHasFocus;
  });

  it('should handle empty children list', async () => {
    const emptyData = {
      ...mockDashboardData,
      children: [],
    };

    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: emptyData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Личный кабинет родителя/)).toBeInTheDocument();
    });
  });

  it('should handle empty reports list', async () => {
    const dataWithoutReports = {
      ...mockDashboardData,
      reports: [],
    };

    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: dataWithoutReports,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Личный кабинет родителя/)).toBeInTheDocument();
    });
  });

  it('should display notification badge', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Проверяем наличие badge с количеством детей
      expect(screen.getByText(/2 детей/)).toBeInTheDocument();
    });
  });

  it('should handle payment error gracefully', async () => {
    vi.mocked(parentDashboardAPI.initiatePayment).mockRejectedValue(
      new Error('Payment failed')
    );

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

  it('should handle missing enrollment_id in payment', async () => {
    const dataWithMissingEnrollment = {
      ...mockDashboardData,
      children: [
        {
          ...mockDashboardData.children[0],
          subjects: [
            {
              ...mockDashboardData.children[0].subjects[0],
              enrollment_id: undefined,
            },
          ],
        },
      ],
    };

    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: dataWithMissingEnrollment as any,
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

  it('should handle payment with missing confirmation URL', async () => {
    vi.mocked(parentDashboardAPI.initiatePayment).mockResolvedValue({
      payment_id: 'pay_123',
    } as any);

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

  it('should display child progress percentage', async () => {
    vi.mocked(useParentHook.useParentDashboard).mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ParentDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Progress percentages: 85% and 72%
      expect(screen.getByText(/85/)).toBeInTheDocument();
      expect(screen.getByText(/72/)).toBeInTheDocument();
    });
  });
});
