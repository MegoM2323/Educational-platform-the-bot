import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTeacherLessons } from '../useTeacherLessons';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import * as React from 'react';

// Mock schedulingAPI
vi.mock('@/integrations/api/schedulingAPI', () => ({
  schedulingAPI: {
    getLessons: vi.fn(),
    createLesson: vi.fn(),
    updateLesson: vi.fn(),
    deleteLesson: vi.fn(),
  },
}));

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

const mockLessons = [
  {
    id: '770e8400-e29b-41d4-a716-446655440000',
    teacher: '550e8400-e29b-41d4-a716-446655440001',
    student: '550e8400-e29b-41d4-a716-446655440000',
    subject: '660e8400-e29b-41d4-a716-446655440000',
    date: '2025-12-15',
    start_time: '09:00:00',
    end_time: '10:00:00',
    description: 'Algebra basics',
    telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
    status: 'confirmed' as const,
    created_at: '2025-11-29T10:00:00Z',
    updated_at: '2025-11-29T10:00:00Z',
    teacher_name: 'John Doe',
    student_name: 'Jane Smith',
    subject_name: 'Mathematics',
    is_upcoming: true,
  },
];

describe('useTeacherLessons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load lessons on mount', async () => {
    vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);

    const { result } = renderHook(() => useTeacherLessons(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.lessons).toHaveLength(1);
    expect(result.current.lessons[0].teacher_name).toBe('John Doe');
    expect(schedulingAPI.getLessons).toHaveBeenCalledTimes(1);
  });

  it('should handle loading errors', async () => {
    vi.mocked(schedulingAPI.getLessons).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useTeacherLessons(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBeTruthy();
    expect(result.current.lessons).toEqual([]);
  });

  it('should return empty lessons array on initial load', () => {
    vi.mocked(schedulingAPI.getLessons).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useTeacherLessons(), {
      wrapper: createWrapper(),
    });

    expect(result.current.lessons).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  describe('createLesson mutation', () => {
    it('should create lesson and invalidate query cache', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);

      const newLesson = {
        student: '550e8400-e29b-41d4-a716-446655440000',
        subject: '660e8400-e29b-41d4-a716-446655440000',
        date: '2025-12-20',
        start_time: '10:00:00',
        end_time: '11:00:00',
        description: 'Geometry',
        telemost_link: 'https://telemost.yandex.ru/j/xyz',
      };

      vi.mocked(schedulingAPI.createLesson).mockResolvedValue({
        id: '880e8400-e29b-41d4-a716-446655440000',
        teacher: '550e8400-e29b-41d4-a716-446655440001',
        ...newLesson,
        status: 'pending',
        created_at: '2025-11-29T10:00:00Z',
        updated_at: '2025-11-29T10:00:00Z',
        teacher_name: 'John Doe',
        student_name: 'Jane Smith',
        subject_name: 'Geometry',
        is_upcoming: true,
      });

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.createLesson(newLesson);
      });

      await waitFor(() => expect(result.current.isCreating).toBe(false));

      expect(schedulingAPI.createLesson).toHaveBeenCalledWith(newLesson);
    });

    it('should handle creation error', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.createLesson).mockRejectedValue(
        new Error('Invalid student ID')
      );

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      const newLesson = {
        student: 'invalid-id',
        subject: '660e8400-e29b-41d4-a716-446655440000',
        date: '2025-12-20',
        start_time: '10:00:00',
        end_time: '11:00:00',
      };

      await act(async () => {
        result.current.createLesson(newLesson);
      });

      await waitFor(() => expect(result.current.isCreating).toBe(false));
    });

    it('should expose isPending state', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.createLesson).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.createLesson({
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-20',
          start_time: '10:00:00',
          end_time: '11:00:00',
        });
      });

      expect(result.current.isCreating).toBe(true);
    });
  });

  describe('updateLesson mutation', () => {
    it('should update lesson and invalidate cache', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.updateLesson).mockResolvedValue({
        ...mockLessons[0],
        description: 'Updated description',
      });

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.updateLesson({
          id: '770e8400-e29b-41d4-a716-446655440000',
          payload: { description: 'Updated description' },
        });
      });

      await waitFor(() => expect(result.current.isUpdating).toBe(false));

      expect(schedulingAPI.updateLesson).toHaveBeenCalledWith(
        '770e8400-e29b-41d4-a716-446655440000',
        { description: 'Updated description' }
      );
    });

    it('should handle update error', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.updateLesson).mockRejectedValue(
        new Error('Cannot update lesson within 2 hours')
      );

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.updateLesson({
          id: '770e8400-e29b-41d4-a716-446655440000',
          payload: { description: 'Updated' },
        });
      });

      await waitFor(() => expect(result.current.isUpdating).toBe(false));
    });

    it('should expose isUpdating state', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.updateLesson).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.updateLesson({
          id: '770e8400-e29b-41d4-a716-446655440000',
          payload: { description: 'Updated' },
        });
      });

      expect(result.current.isUpdating).toBe(true);
    });
  });

  describe('deleteLesson mutation', () => {
    it('should delete lesson and invalidate cache', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.deleteLesson).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.deleteLesson('770e8400-e29b-41d4-a716-446655440000');
      });

      await waitFor(() => expect(result.current.isDeleting).toBe(false));

      expect(schedulingAPI.deleteLesson).toHaveBeenCalledWith(
        '770e8400-e29b-41d4-a716-446655440000'
      );
    });

    it('should handle deletion error', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.deleteLesson).mockRejectedValue(
        new Error('Cannot delete lesson within 2 hours')
      );

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.deleteLesson('770e8400-e29b-41d4-a716-446655440000');
      });

      await waitFor(() => expect(result.current.isDeleting).toBe(false));
    });

    it('should expose isDeleting state', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.deleteLesson).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        result.current.deleteLesson('770e8400-e29b-41d4-a716-446655440000');
      });

      expect(result.current.isDeleting).toBe(true);
    });
  });

  describe('cache invalidation', () => {
    it('should invalidate lessons query after successful create', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.createLesson).mockResolvedValue({
        id: '880e8400-e29b-41d4-a716-446655440000',
        teacher: '550e8400-e29b-41d4-a716-446655440001',
        student: '550e8400-e29b-41d4-a716-446655440000',
        subject: '660e8400-e29b-41d4-a716-446655440000',
        date: '2025-12-20',
        start_time: '10:00:00',
        end_time: '11:00:00',
        description: 'New lesson',
        telemost_link: '',
        status: 'pending',
        created_at: '2025-11-29T10:00:00Z',
        updated_at: '2025-11-29T10:00:00Z',
        teacher_name: 'John Doe',
        student_name: 'Jane Smith',
        subject_name: 'Physics',
      });

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      const initialCallCount = vi.mocked(schedulingAPI.getLessons).mock.calls.length;

      await act(async () => {
        result.current.createLesson({
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-20',
          start_time: '10:00:00',
          end_time: '11:00:00',
        });
      });

      await waitFor(() => expect(result.current.isCreating).toBe(false));

      // getLessons should be called again due to cache invalidation
      expect(vi.mocked(schedulingAPI.getLessons).mock.calls.length).toBeGreaterThan(
        initialCallCount
      );
    });

    it('should invalidate lessons query after successful update', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.updateLesson).mockResolvedValue({
        ...mockLessons[0],
        description: 'Updated',
      });

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      const initialCallCount = vi.mocked(schedulingAPI.getLessons).mock.calls.length;

      await act(async () => {
        result.current.updateLesson({
          id: '770e8400-e29b-41d4-a716-446655440000',
          payload: { description: 'Updated' },
        });
      });

      await waitFor(() => expect(result.current.isUpdating).toBe(false));

      expect(vi.mocked(schedulingAPI.getLessons).mock.calls.length).toBeGreaterThan(
        initialCallCount
      );
    });

    it('should invalidate lessons query after successful delete', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(schedulingAPI.deleteLesson).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherLessons(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      const initialCallCount = vi.mocked(schedulingAPI.getLessons).mock.calls.length;

      await act(async () => {
        result.current.deleteLesson('770e8400-e29b-41d4-a716-446655440000');
      });

      await waitFor(() => expect(result.current.isDeleting).toBe(false));

      expect(vi.mocked(schedulingAPI.getLessons).mock.calls.length).toBeGreaterThan(
        initialCallCount
      );
    });
  });

  describe('filter support', () => {
    it('should pass filters to getLessons', async () => {
      vi.mocked(schedulingAPI.getLessons).mockResolvedValue(mockLessons);

      const filters = {
        date_from: '2025-12-01',
        status: 'confirmed',
      };

      renderHook(() => useTeacherLessons(filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(schedulingAPI.getLessons).toHaveBeenCalledWith(filters);
      });
    });
  });
});
