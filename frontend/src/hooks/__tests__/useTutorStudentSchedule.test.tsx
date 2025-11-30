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
});
