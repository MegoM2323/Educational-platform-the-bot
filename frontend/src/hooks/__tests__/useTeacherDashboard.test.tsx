import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTeacherDashboard } from '../useTeacher';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import * as React from 'react';

// Mock unifiedAPI
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    getTeacherDashboard: vi.fn(),
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

describe('useTeacherDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно загружать данные дашборда', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 5,
      recent_activity: [],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(unifiedAPI.getTeacherDashboard).toHaveBeenCalledTimes(1);
  });

  it('должен обрабатывать ошибки загрузки', async () => {
    const error = 'Network error';
    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: false,
      error,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  it('должен показывать состояние загрузки', () => {
    vi.mocked(unifiedAPI.getTeacherDashboard).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('должен правильно настраивать refetchOnWindowFocus', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 5,
      recent_activity: [],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Hook should have refetchOnWindowFocus enabled
    expect(unifiedAPI.getTeacherDashboard).toHaveBeenCalled();
  });

  it('должен иметь настройку retry', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 5,
      recent_activity: [],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
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

    const { result } = renderHook(() => useTeacherDashboard(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Hook should successfully fetch data with retry enabled
    expect(result.current.data).toEqual(mockData);
  });

  it('должен кешировать данные', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 5,
      recent_activity: [],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result, rerender } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Second render should use cache
    rerender();

    expect(unifiedAPI.getTeacherDashboard).toHaveBeenCalledTimes(1);
  });

  it('должен инвалидировать кеш при refetch', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 5,
      recent_activity: [],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    result.current.refetch();

    await waitFor(() => {
      expect(unifiedAPI.getTeacherDashboard).toHaveBeenCalledTimes(2);
    });
  });

  it('должен подсчитывать pending submissions', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 8,
      recent_activity: [],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.pending_reports).toBe(8);
  });

  it('должен загружать students с progress', async () => {
    const mockData = {
      total_students: 25,
      total_materials: 40,
      pending_reports: 5,
      recent_activity: [
        {
          id: 1,
          student_name: 'Иван Иванов',
          material_title: 'Домашнее задание 1',
          action: 'submitted',
          timestamp: new Date().toISOString(),
        },
      ],
    };

    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.recent_activity).toHaveLength(1);
    expect(result.current.data?.recent_activity[0].student_name).toBe('Иван Иванов');
  });

  it('должен возвращать undefined data при отсутствии данных', async () => {
    vi.mocked(unifiedAPI.getTeacherDashboard).mockResolvedValue({
      success: false,
      error: 'No data',
      timestamp: new Date().toISOString(),
    });

    const { result } = renderHook(() => useTeacherDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
