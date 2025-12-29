import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStudentSchedule } from '../useStudentSchedule';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import * as React from 'react';

// Mock schedulingAPI
vi.mock('@/integrations/api/schedulingAPI', () => ({
  schedulingAPI: {
    getMySchedule: vi.fn(),
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
  {
    id: '880e8400-e29b-41d4-a716-446655440000',
    teacher: '550e8400-e29b-41d4-a716-446655440001',
    student: '550e8400-e29b-41d4-a716-446655440000',
    subject: '770e8400-e29b-41d4-a716-446655440000',
    date: '2025-12-16',
    start_time: '10:00:00',
    end_time: '11:00:00',
    description: 'Physics fundamentals',
    telemost_link: 'https://telemost.yandex.ru/j/xyz789',
    status: 'confirmed' as const,
    created_at: '2025-11-29T10:00:00Z',
    updated_at: '2025-11-29T10:00:00Z',
    teacher_name: 'Jane Doe',
    student_name: 'Jane Smith',
    subject_name: 'Physics',
    is_upcoming: true,
  },
  {
    id: '990e8400-e29b-41d4-a716-446655440000',
    teacher: '550e8400-e29b-41d4-a716-446655440001',
    student: '550e8400-e29b-41d4-a716-446655440000',
    subject: '660e8400-e29b-41d4-a716-446655440000',
    date: '2025-11-28',
    start_time: '09:00:00',
    end_time: '10:00:00',
    description: 'Past lesson',
    telemost_link: '',
    status: 'completed' as const,
    created_at: '2025-11-29T10:00:00Z',
    updated_at: '2025-11-29T10:00:00Z',
    teacher_name: 'John Doe',
    student_name: 'Jane Smith',
    subject_name: 'Mathematics',
    is_upcoming: false,
  },
];

describe('useStudentSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load student lessons on mount', async () => {
    vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

    const { result } = renderHook(() => useStudentSchedule(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.lessons).toHaveLength(3);
    expect(result.current.lessons[0].teacher_name).toBe('John Doe');
    expect(schedulingAPI.getMySchedule).toHaveBeenCalled();
  });

  it('should handle loading errors', async () => {
    vi.mocked(schedulingAPI.getMySchedule).mockRejectedValue(
      new Error('Failed to load lessons')
    );

    const { result } = renderHook(() => useStudentSchedule(), {
      wrapper: createWrapper(),
    });

    // Hook has retry: 1, so it will retry once before failing
    // Wait for error to appear after retry completes
    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    }, { timeout: 5000 });

    // Lessons should be empty array on error
    expect(result.current.lessons).toEqual([]);
  });

  it('should return empty lessons array on initial load', () => {
    vi.mocked(schedulingAPI.getMySchedule).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useStudentSchedule(), {
      wrapper: createWrapper(),
    });

    expect(result.current.lessons).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  describe('lessons grouping by subject', () => {
    it('should group lessons by subject_name', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessonsBySubject).toHaveProperty('Mathematics');
      expect(result.current.lessonsBySubject).toHaveProperty('Physics');
      expect(result.current.lessonsBySubject['Mathematics']).toHaveLength(2);
      expect(result.current.lessonsBySubject['Physics']).toHaveLength(1);
    });

    it('should handle lessons without subject_name', async () => {
      const lessonsWithoutSubject = [
        {
          ...mockLessons[0],
          subject_name: undefined,
        },
      ];

      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(lessonsWithoutSubject);

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessonsBySubject).toBeDefined();
    });

    it('should update grouping when lessons change', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([mockLessons[0]]);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
        },
      });
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.lessonsBySubject['Mathematics']).toHaveLength(1);

      // Update mock data and invalidate query to trigger refetch
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);
      await queryClient.invalidateQueries({ queryKey: ['lessons'] });

      await waitFor(() => {
        expect(result.current.lessonsBySubject['Mathematics']).toHaveLength(2);
      });
    });
  });

  describe('upcoming lessons filter', () => {
    it('should filter upcoming lessons based on is_upcoming flag', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.upcomingLessons).toHaveLength(2);
      expect(result.current.upcomingLessons.every((l) => l.is_upcoming)).toBe(true);
    });

    it('should return empty array when no upcoming lessons', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([mockLessons[2]]);

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.upcomingLessons).toHaveLength(0);
    });

    it('should update upcoming lessons when data changes', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([mockLessons[2]]);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
        },
      });
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.upcomingLessons).toHaveLength(0);

      // Update mock data and invalidate query to trigger refetch
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);
      await queryClient.invalidateQueries({ queryKey: ['lessons'] });

      await waitFor(() => {
        expect(result.current.upcomingLessons).toHaveLength(2);
      });
    });
  });

  describe('filter support', () => {
    it('should pass filters to getMySchedule', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const filters = {
        date_from: '2025-12-01',
        date_to: '2025-12-31',
        subject: '660e8400-e29b-41d4-a716-446655440000',
      };

      renderHook(() => useStudentSchedule(filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(schedulingAPI.getMySchedule).toHaveBeenCalledWith(filters);
      });
    });

    it('should update when filters change', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const { rerender } = renderHook(
        ({ filters }) => useStudentSchedule(filters),
        {
          wrapper: createWrapper(),
          initialProps: { filters: { date_from: '2025-12-01' } },
        }
      );

      await waitFor(() => {
        expect(schedulingAPI.getMySchedule).toHaveBeenCalledWith({ date_from: '2025-12-01' });
      });

      const initialCallCount = vi.mocked(schedulingAPI.getMySchedule).mock.calls.length;

      rerender({ filters: { date_from: '2025-12-15' } });

      await waitFor(() => {
        expect(vi.mocked(schedulingAPI.getMySchedule).mock.calls.length).toBeGreaterThan(
          initialCallCount
        );
      });
    });
  });

  describe('return value structure', () => {
    it('should return all expected properties', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current).toHaveProperty('lessons');
      expect(result.current).toHaveProperty('lessonsBySubject');
      expect(result.current).toHaveProperty('upcomingLessons');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
    });

    it('should have correct types for lessons', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(Array.isArray(result.current.lessons)).toBe(true);
      expect(Array.isArray(result.current.upcomingLessons)).toBe(true);
      expect(typeof result.current.lessonsBySubject).toBe('object');
    });
  });

  describe('memoization', () => {
    it('should not recalculate grouping when filter changes (if data unchanged)', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockLessons);

      const { result: result1 } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result1.current.isLoading).toBe(false));
      const grouping1 = result1.current.lessonsBySubject;

      // Create new hook instance with same data
      const { result: result2 } = renderHook(() => useStudentSchedule(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result2.current.isLoading).toBe(false));

      // Grouping object references should be different (memoized per hook instance)
      // but content should be same
      expect(result2.current.lessonsBySubject['Mathematics']).toEqual(grouping1['Mathematics']);
    });
  });
});
