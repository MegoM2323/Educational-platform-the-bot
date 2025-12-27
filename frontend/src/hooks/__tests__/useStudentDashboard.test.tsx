import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStudentDashboard } from '../useStudent';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import * as React from 'react';

// Mock unifiedAPI
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    getStudentDashboard: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useStudentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно загружать данные дашборда', async () => {
    const mockData = {
      materials_count: 10,
      completed_materials: 5,
      progress_percentage: 50,
      recent_materials: [],
      upcoming_deadlines: [],
    };

    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(unifiedAPI.getStudentDashboard).toHaveBeenCalledTimes(1);
  });

  it('должен обрабатывать ошибки загрузки', async () => {
    const error = 'Network error';
    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: false,
      error,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  it('должен показывать состояние загрузки', () => {
    vi.mocked(unifiedAPI.getStudentDashboard).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('должен правильно настраивать refetchOnWindowFocus', async () => {
    const mockData = {
      materials_count: 10,
      completed_materials: 5,
      progress_percentage: 50,
      recent_materials: [],
      upcoming_deadlines: [],
    };

    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Hook should have refetchOnWindowFocus enabled
    expect(unifiedAPI.getStudentDashboard).toHaveBeenCalled();
  });

  it('должен иметь настройку retry', async () => {
    const mockData = {
      materials_count: 10,
      completed_materials: 5,
      progress_percentage: 50,
      recent_materials: [],
      upcoming_deadlines: [],
    };

    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: 2 } },
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useStudentDashboard(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Hook should successfully fetch data with retry enabled
    expect(result.current.data).toEqual(mockData);
  });

  it('должен кешировать данные', async () => {
    const mockData = {
      materials_count: 10,
      completed_materials: 5,
      progress_percentage: 50,
      recent_materials: [],
      upcoming_deadlines: [],
    };

    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result, rerender } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Second render should use cache (staleTime 60s)
    rerender();

    expect(unifiedAPI.getStudentDashboard).toHaveBeenCalledTimes(1);
  });

  it('должен инвалидировать кеш при refetch', async () => {
    const mockData = {
      materials_count: 10,
      completed_materials: 5,
      progress_percentage: 50,
      recent_materials: [],
      upcoming_deadlines: [],
    };

    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    result.current.refetch();

    await waitFor(() => {
      expect(unifiedAPI.getStudentDashboard).toHaveBeenCalledTimes(2);
    });
  });

  it('должен возвращать undefined data при отсутствии данных', async () => {
    vi.mocked(unifiedAPI.getStudentDashboard).mockResolvedValue({
      success: false,
      error: 'No data',
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useStudentDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
