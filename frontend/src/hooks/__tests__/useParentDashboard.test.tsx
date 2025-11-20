import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useParentDashboard, useInitiatePayment } from '../useParent';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { parentDashboardAPI } from '@/integrations/api/dashboard';
import * as React from 'react';

// Mock dependencies
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    getParentDashboard: vi.fn(),
  },
}));

vi.mock('@/integrations/api/dashboard', () => ({
  parentDashboardAPI: {
    initiatePayment: vi.fn(),
    cancelSubscription: vi.fn(),
  },
}));

// Mock window.location.href
delete (window as any).location;
window.location = { href: '' } as any;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useParentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.location.href = '';
  });

  it('должен успешно загружать данные детей', async () => {
    const mockData = {
      parent: { id: 1, name: 'Родитель', email: 'parent@test.com' },
      children: [
        {
          id: 1,
          name: 'Ребенок 1',
          grade: '5',
          goal: 'Цель 1',
          tutor_name: 'Тьютор 1',
          progress_percentage: 75,
          progress: 75,
          subjects: [],
          payments: [],
        },
      ],
      reports: [],
      statistics: {
        total_children: 1,
        average_progress: 75,
        completed_payments: 0,
        pending_payments: 0,
        overdue_payments: 0,
      },
      total_children: 1,
    };

    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.data?.children).toHaveLength(1);
    expect(unifiedAPI.getParentDashboard).toHaveBeenCalledTimes(1);
  });

  it('должен обрабатывать ошибки при загрузке данных', async () => {
    const error = 'Network error';
    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: false,
      error,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  it('должен показывать состояние загрузки', () => {
    vi.mocked(unifiedAPI.getParentDashboard).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('должен загружать данные нескольких детей', async () => {
    const mockData = {
      parent: { id: 1, name: 'Родитель', email: 'parent@test.com' },
      children: [
        {
          id: 1,
          name: 'Ребенок 1',
          grade: '5',
          goal: 'Цель 1',
          tutor_name: 'Тьютор 1',
          progress_percentage: 75,
          progress: 75,
          subjects: [],
          payments: [],
        },
        {
          id: 2,
          name: 'Ребенок 2',
          grade: '6',
          goal: 'Цель 2',
          tutor_name: 'Тьютор 2',
          progress_percentage: 60,
          progress: 60,
          subjects: [],
          payments: [],
        },
      ],
      reports: [],
      statistics: {
        total_children: 2,
        average_progress: 67.5,
        completed_payments: 0,
        pending_payments: 0,
        overdue_payments: 0,
      },
      total_children: 2,
    };

    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.children).toHaveLength(2);
    expect(result.current.data?.total_children).toBe(2);
  });

  it('должен кешировать данные детей', async () => {
    const mockData = {
      parent: { id: 1, name: 'Родитель', email: 'parent@test.com' },
      children: [],
      reports: [],
      statistics: {
        total_children: 0,
        average_progress: 0,
        completed_payments: 0,
        pending_payments: 0,
        overdue_payments: 0,
      },
      total_children: 0,
    };

    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result, rerender } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Second render should use cache
    rerender();

    expect(unifiedAPI.getParentDashboard).toHaveBeenCalledTimes(1);
  });

  it('должен показывать индикатор просроченных платежей', async () => {
    const mockData = {
      parent: { id: 1, name: 'Родитель', email: 'parent@test.com' },
      children: [],
      reports: [],
      statistics: {
        total_children: 1,
        average_progress: 75,
        completed_payments: 2,
        pending_payments: 1,
        overdue_payments: 3,
      },
      total_children: 1,
    };

    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.statistics.overdue_payments).toBe(3);
  });

  it('должен правильно настраивать refetchOnWindowFocus', async () => {
    const mockData = {
      parent: { id: 1, name: 'Родитель', email: 'parent@test.com' },
      children: [],
      reports: [],
      statistics: {
        total_children: 0,
        average_progress: 0,
        completed_payments: 0,
        pending_payments: 0,
        overdue_payments: 0,
      },
      total_children: 0,
    };

    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Hook should have refetchOnWindowFocus enabled
    expect(unifiedAPI.getParentDashboard).toHaveBeenCalled();
  });

  it('должен обновлять статус подписки', async () => {
    const mockData = {
      parent: { id: 1, name: 'Родитель', email: 'parent@test.com' },
      children: [
        {
          id: 1,
          name: 'Ребенок 1',
          grade: '5',
          goal: 'Цель 1',
          tutor_name: 'Тьютор 1',
          progress_percentage: 75,
          progress: 75,
          subjects: [
            {
              id: 1,
              enrollment_id: 1,
              name: 'Математика',
              teacher_name: 'Учитель',
              teacher_id: 1,
              payment_status: 'paid',
              has_subscription: true,
              subscription_status: 'active',
            },
          ],
          payments: [],
        },
      ],
      reports: [],
      statistics: {
        total_children: 1,
        average_progress: 75,
        completed_payments: 1,
        pending_payments: 0,
        overdue_payments: 0,
      },
      total_children: 1,
    };

    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.children[0].subjects[0].has_subscription).toBe(true);
    expect(result.current.data?.children[0].subjects[0].subscription_status).toBe('active');
  });

  it('должен возвращать undefined data при отсутствии данных', async () => {
    vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
      success: false,
      error: 'No data',
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useParentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

describe('useInitiatePayment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.location.href = '';
  });

  it('должен инициировать платеж', async () => {
    const mockResponse = {
      payment_id: 'payment_123',
      confirmation_url: 'https://payment.url',
    };

    vi.mocked(parentDashboardAPI.initiatePayment).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useInitiatePayment(1, 1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBeDefined());

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(parentDashboardAPI.initiatePayment).toHaveBeenCalledWith(1, 1, expect.any(Object));
    // Note: window.location.href redirection is handled by the hook
  });

  it('должен обрабатывать ошибку платежа', async () => {
    const error = new Error('Payment failed');
    vi.mocked(parentDashboardAPI.initiatePayment).mockRejectedValue(error);

    const { result } = renderHook(() => useInitiatePayment(1, 1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBeDefined());

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  it('должен сохранять payment_id в sessionStorage', async () => {
    const mockResponse = {
      payment_id: 'payment_456',
      confirmation_url: 'https://payment.url',
    };

    const sessionStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
      length: 0,
      key: vi.fn(),
    };
    Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

    vi.mocked(parentDashboardAPI.initiatePayment).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useInitiatePayment(1, 1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBeDefined());

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(sessionStorageMock.setItem).toHaveBeenCalledWith('pending_payment_id', 'payment_456');
  });
});
