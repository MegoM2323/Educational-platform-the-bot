import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTutorStudentSchedule } from '../useTutorStudentSchedule';
import { schedulingAPI } from '@/integrations/api/schedulingAPI';
import * as React from 'react';

// Mock schedulingAPI
vi.mock('@/integrations/api/schedulingAPI', () => ({
  schedulingAPI: {
    getStudentSchedule: vi.fn(),
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
    teacher: '550e8400-e29b-41d4-a716-446655440002',
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
];

describe('useTutorStudentSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load student schedule when studentId is provided', async () => {
    const studentId = '550e8400-e29b-41d4-a716-446655440000';
    vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

    const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.lessons).toHaveLength(2);
    expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, undefined);
  });

  it('should not fetch when studentId is null', async () => {
    vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

    const { result } = renderHook(() => useTutorStudentSchedule(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.lessons).toEqual([]);
    expect(schedulingAPI.getStudentSchedule).not.toHaveBeenCalled();
  });

  it('should disable query when studentId is undefined', async () => {
    vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

    const { result } = renderHook(() => useTutorStudentSchedule(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.lessons).toEqual([]);
    expect(schedulingAPI.getStudentSchedule).not.toHaveBeenCalled();
  });

  it('should fetch when studentId changes from null to valid ID', async () => {
    vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

    const { result, rerender } = renderHook(
      ({ studentId }) => useTutorStudentSchedule(studentId),
      {
        wrapper: createWrapper(),
        initialProps: { studentId: null as string | null },
      }
    );

    expect(result.current.isLoading).toBe(false);
    expect(schedulingAPI.getStudentSchedule).not.toHaveBeenCalled();

    const studentId = '550e8400-e29b-41d4-a716-446655440000';
    rerender({ studentId });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, undefined);
    expect(result.current.lessons).toHaveLength(2);
  });

  it('should handle loading errors gracefully', async () => {
    const studentId = '550e8400-e29b-41d4-a716-446655440000';
    vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
      new Error('Access denied')
    );

    const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBeTruthy();
    expect(result.current.lessons).toEqual([]);
  });

  it('should return empty array on initial load', () => {
    const studentId = '550e8400-e29b-41d4-a716-446655440000';
    vi.mocked(schedulingAPI.getStudentSchedule).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
      wrapper: createWrapper(),
    });

    expect(result.current.lessons).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  describe('filter support', () => {
    it('should pass filters to getStudentSchedule', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const filters = {
        date_from: '2025-12-01',
        status: 'confirmed',
      };

      renderHook(() => useTutorStudentSchedule(studentId, filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, filters);
      });
    });

    it('should update when filters change', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { rerender } = renderHook(
        ({ filters }) => useTutorStudentSchedule(studentId, filters),
        {
          wrapper: createWrapper(),
          initialProps: { filters: { date_from: '2025-12-01' } },
        }
      );

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, {
          date_from: '2025-12-01',
        });
      });

      const initialCallCount = vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length;

      rerender({ filters: { date_from: '2025-12-15' } });

      await waitFor(() => {
        expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBeGreaterThan(
          initialCallCount
        );
      });
    });
  });

  describe('return value structure', () => {
    it('should return all expected properties', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current).toHaveProperty('lessons');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
    });

    it('should have correct types for lessons', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(Array.isArray(result.current.lessons)).toBe(true);
      expect(result.current.lessons[0]).toHaveProperty('id');
      expect(result.current.lessons[0]).toHaveProperty('teacher_name');
      expect(result.current.lessons[0]).toHaveProperty('subject_name');
    });
  });

  describe('query key generation', () => {
    it('should use studentId in query key', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalled();
      });

      // Query should be called with studentId
      expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls[0][0]).toBe(studentId);
    });

    it('should refetch when studentId changes', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId1, undefined);
      });

      rerender({ studentId: studentId2 });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId2, undefined);
      });

      expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBe(2);
    });
  });

  describe('permission/authorization simulation', () => {
    it('should handle access denied error', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Tutor can only access their own students')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

    it('should handle invalid student ID', async () => {
      const invalidStudentId = 'invalid-uuid';
      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Invalid student ID')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(invalidStudentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
    });
  });

  describe('Extended - Student Selection', () => {
    it('should return empty array when no student selected', () => {
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.lessons).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(schedulingAPI.getStudentSchedule).not.toHaveBeenCalled();
    });

    it('should load lessons for selected student', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toEqual(mockLessons);
      expect(result.current.lessons).toHaveLength(2);
    });

    it('should reload lessons when switching between students', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';

      const lessonsStudent1 = [mockLessons[0]];
      const lessonsStudent2 = [mockLessons[1]];

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(lessonsStudent1)
        .mockResolvedValueOnce(lessonsStudent2);

      const { result, rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.lessons).toEqual(lessonsStudent1);
      expect(result.current.lessons).toHaveLength(1);

      rerender({ studentId: studentId2 });

      await waitFor(() => {
        expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBe(2);
      });

      expect(result.current.lessons).toEqual(lessonsStudent2);
      expect(result.current.lessons).toHaveLength(1);
    });

    it('should handle invalid student ID gracefully', async () => {
      const invalidStudentId = 'not-a-uuid-format';
      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Invalid student ID format')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(invalidStudentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

    it('should return empty array when student ID is explicitly null', () => {
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.lessons).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });

    it('should return empty array when student ID is undefined', () => {
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(undefined), {
        wrapper: createWrapper(),
      });

      expect(result.current.lessons).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Extended - Data Loading States', () => {
    it('should be in loading state during fetch', () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.lessons).toEqual([]);
    });

    it('should exit loading state after successful fetch', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.isLoading).toBe(false);
      expect(result.current.lessons).toEqual(mockLessons);
    });

    it('should populate lessons array correctly', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toHaveLength(2);
      expect(result.current.lessons[0]).toHaveProperty('id');
      expect(result.current.lessons[0]).toHaveProperty('teacher_name');
      expect(result.current.lessons[0]).toHaveProperty('subject_name');
    });

    it('should set error state on API failure', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const apiError = new Error('Network error');
      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(apiError);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

    it('should return empty array when no lessons for student', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue([]);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toEqual([]);
      expect(result.current.lessons).toHaveLength(0);
      expect(result.current.error).toBeFalsy();
    });
  });

  describe('Extended - Filtering', () => {
    it('should apply date_from filter', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const filters = { date_from: '2025-12-15' };

      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue([mockLessons[0]]);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId, filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, filters);
      expect(result.current.lessons).toEqual([mockLessons[0]]);
    });

    it('should apply date_to filter', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const filters = { date_to: '2025-12-20' };

      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId, filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, filters);
    });

    it('should apply subject filter', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const subjectId = '660e8400-e29b-41d4-a716-446655440000';
      const filters = { subject: subjectId };

      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue([mockLessons[0]]);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId, filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, filters);
    });

    it('should apply status filter', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const filters = { status: 'confirmed' };

      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId, filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, filters);
      expect(result.current.lessons.every(l => l.status === 'confirmed')).toBe(true);
    });

    it('should apply multiple filters combined', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const filters = {
        date_from: '2025-12-01',
        date_to: '2025-12-31',
        subject: '660e8400-e29b-41d4-a716-446655440000',
        status: 'confirmed',
      };

      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue([mockLessons[0]]);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId, filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, filters);
    });

    it('should reload lessons when filters change', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(mockLessons)
        .mockResolvedValueOnce([mockLessons[0]]);

      const { rerender } = renderHook(
        ({ filters }) => useTutorStudentSchedule(studentId, filters),
        {
          wrapper: createWrapper(),
          initialProps: { filters: {} },
        }
      );

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledTimes(1);
      });

      rerender({ filters: { date_from: '2025-12-15' } });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledTimes(2);
      });

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(
        studentId,
        { date_from: '2025-12-15' }
      );
    });

    it('should apply filters only when student is selected', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const filters = { date_from: '2025-12-15' };

      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      const { result, rerender } = renderHook(
        ({ studentId, filters }) => useTutorStudentSchedule(studentId, filters),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: null, filters },
        }
      );

      expect(result.current.lessons).toEqual([]);
      expect(schedulingAPI.getStudentSchedule).not.toHaveBeenCalled();

      rerender({ studentId, filters });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getStudentSchedule).toHaveBeenCalled();
    });

    it('should clear filters by passing empty object', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce([mockLessons[0]])
        .mockResolvedValueOnce(mockLessons);

      const { result, rerender } = renderHook(
        ({ filters }) => useTutorStudentSchedule(studentId, filters),
        {
          wrapper: createWrapper(),
          initialProps: { filters: { date_from: '2025-12-15' } },
        }
      );

      await waitFor(() => expect(result.current.lessons).toHaveLength(1));

      rerender({ filters: {} });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, {});
      });

      expect(result.current.lessons).toHaveLength(2);
    });
  });

  describe('Extended - Caching', () => {
    it('should invalidate cache when student changes', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(mockLessons)
        .mockResolvedValueOnce([mockLessons[1]]);

      const { rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId1, undefined);
      });

      rerender({ studentId: studentId2 });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId2, undefined);
      });

      expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBe(2);
    });

    it('should invalidate cache when filters change', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(mockLessons)
        .mockResolvedValueOnce([mockLessons[0]]);

      const { rerender } = renderHook(
        ({ filters }) => useTutorStudentSchedule(studentId, filters),
        {
          wrapper: createWrapper(),
          initialProps: { filters: { date_from: '2025-12-01' } },
        }
      );

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalled();
      });

      const firstCallCount = vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length;

      rerender({ filters: { date_from: '2025-12-15' } });

      await waitFor(() => {
        expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBeGreaterThan(firstCallCount);
      });
    });

    it('should refetch on component mount', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      vi.mocked(schedulingAPI.getStudentSchedule).mockResolvedValue(mockLessons);

      renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(schedulingAPI.getStudentSchedule).toHaveBeenCalledWith(studentId, undefined);
      });
    });
  });

  describe('Extended - Multi-Student Support', () => {
    it('should store different students data separately', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';

      const lessonsStudent1 = [mockLessons[0]];
      const lessonsStudent2 = [mockLessons[1]];

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(lessonsStudent1)
        .mockResolvedValueOnce(lessonsStudent2);

      const { result, rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      // Load first student's lessons
      await waitFor(() => expect(result.current.lessons).toHaveLength(1));

      // Switch to second student
      rerender({ studentId: studentId2 });

      // Verify data changed
      await waitFor(() => {
        expect(result.current.lessons).toHaveLength(1);
      });

      // Verify API was called for both students
      expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBe(2);
    });

    it('should switch students and show correct data', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';

      const lessonsStudent1 = [mockLessons[0]];
      const lessonsStudent2 = [mockLessons[1]];

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(lessonsStudent1)
        .mockResolvedValueOnce(lessonsStudent2);

      const { result, rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      // Verify first student's data loaded
      await waitFor(() => expect(result.current.lessons).toHaveLength(1));
      const firstLessonTeacher = result.current.lessons[0].teacher_name;

      // Switch student
      rerender({ studentId: studentId2 });

      // Verify second student's data loaded (different teacher)
      await waitFor(() => {
        expect(result.current.lessons[0].teacher_name).not.toBe(firstLessonTeacher);
      });
    });

    it('should not mix data between students', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';

      const lessonsForStudent1 = mockLessons;
      const lessonsForStudent2 = [mockLessons[0]];

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(lessonsForStudent1)
        .mockResolvedValueOnce(lessonsForStudent2);

      const { result, rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      // Verify first student's lessons loaded
      await waitFor(() => expect(result.current.lessons).toHaveLength(2));
      const firstCallsLength = vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length;
      expect(firstCallsLength).toBe(1);

      // Switch to second student
      rerender({ studentId: studentId2 });

      // Verify second student's lessons loaded
      await waitFor(() => expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBe(2));
      expect(result.current.lessons).toHaveLength(1);
    });

    it('should maintain separate cache per student', async () => {
      const studentId1 = '550e8400-e29b-41d4-a716-446655440000';
      const studentId2 = '550e8400-e29b-41d4-a716-446655440001';

      vi.mocked(schedulingAPI.getStudentSchedule)
        .mockResolvedValueOnce(mockLessons)
        .mockResolvedValueOnce([mockLessons[1]]);

      const { result, rerender } = renderHook(
        ({ studentId }) => useTutorStudentSchedule(studentId),
        {
          wrapper: createWrapper(),
          initialProps: { studentId: studentId1 },
        }
      );

      await waitFor(() => expect(result.current.lessons).toHaveLength(2));

      rerender({ studentId: studentId2 });

      await waitFor(() => expect(result.current.lessons).toHaveLength(1));

      // Verify we made multiple calls
      expect(vi.mocked(schedulingAPI.getStudentSchedule).mock.calls.length).toBe(2);
    });
  });

  describe('Extended - Error Handling', () => {
    it('should show error state on API failure', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const apiError = new Error('Failed to fetch schedule');

      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(apiError);

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Error is present in the query after failure
      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

    it('should handle access denied error', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Tutor does not have access to this student')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Error should be present
      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

    it('should handle network errors', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Network timeout')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Error should be captured
      expect(result.current.error).toBeTruthy();
    });

    it('should handle 404 not found error', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Student not found')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
    });

    it('should handle 500 server error', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(schedulingAPI.getStudentSchedule).mockRejectedValue(
        new Error('Internal server error')
      );

      const { result } = renderHook(() => useTutorStudentSchedule(studentId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
    });
  });
});
