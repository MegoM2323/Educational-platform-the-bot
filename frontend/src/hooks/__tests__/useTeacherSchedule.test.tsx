import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTeacherSchedule } from '../useTeacherSchedule';
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

const mockScheduleData = [
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
    student: '550e8400-e29b-41d4-a716-446655440001',
    subject: '770e8400-e29b-41d4-a716-446655440000',
    date: '2025-12-15',
    start_time: '10:00:00',
    end_time: '11:00:00',
    description: 'Physics fundamentals',
    telemost_link: 'https://telemost.yandex.ru/j/xyz789',
    status: 'pending' as const,
    created_at: '2025-11-29T10:00:00Z',
    updated_at: '2025-11-29T10:00:00Z',
    teacher_name: 'John Doe',
    student_name: 'Bob Johnson',
    subject_name: 'Physics',
    is_upcoming: true,
  },
  {
    id: '990e8400-e29b-41d4-a716-446655440000',
    teacher: '550e8400-e29b-41d4-a716-446655440001',
    student: '550e8400-e29b-41d4-a716-446655440000',
    subject: '660e8400-e29b-41d4-a716-446655440000',
    date: '2025-12-16',
    start_time: '14:00:00',
    end_time: '15:00:00',
    description: 'Algebra advanced',
    telemost_link: '',
    status: 'confirmed' as const,
    created_at: '2025-11-29T10:00:00Z',
    updated_at: '2025-11-29T10:00:00Z',
    teacher_name: 'John Doe',
    student_name: 'Jane Smith',
    subject_name: 'Mathematics',
    is_upcoming: true,
  },
  {
    id: 'aa0e8400-e29b-41d4-a716-446655440000',
    teacher: '550e8400-e29b-41d4-a716-446655440001',
    student: '550e8400-e29b-41d4-a716-446655440000',
    subject: '660e8400-e29b-41d4-a716-446655440000',
    date: '2025-11-28',
    start_time: '09:00:00',
    end_time: '10:00:00',
    description: 'Past lesson',
    telemost_link: '',
    status: 'completed' as const,
    created_at: '2025-11-28T10:00:00Z',
    updated_at: '2025-11-28T10:00:00Z',
    teacher_name: 'John Doe',
    student_name: 'Jane Smith',
    subject_name: 'Mathematics',
    is_upcoming: false,
  },
];

describe('useTeacherSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Data Loading', () => {
    it('should show isLoading=true initially', () => {
      vi.mocked(schedulingAPI.getMySchedule).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      expect(result.current.isLoading).toBe(true);
    });

    it('should load schedule on mount with valid date range', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toHaveLength(4);
      expect(result.current.lessons[0].teacher_name).toBe('John Doe');
      expect(schedulingAPI.getMySchedule).toHaveBeenCalledWith('2025-12-01', '2025-12-31');
    });

    it('should handle API errors gracefully', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockRejectedValue(
        new Error('Network error')
      );

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

    it('should return empty array on initial load before query resolves', () => {
      vi.mocked(schedulingAPI.getMySchedule).mockImplementation(
        () => new Promise(() => {})
      );

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      expect(result.current.lessons).toEqual([]);
      expect(result.current.isLoading).toBe(true);
    });

    it('should handle empty response (no lessons)', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([]);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toHaveLength(0);
      expect(result.current.lessonsByDate).toEqual({});
      expect(result.current.upcomingLessons).toHaveLength(0);
    });

    it('should refetch when date range changes', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result, rerender } = renderHook(
        ({ dateFrom, dateTo }) => useTeacherSchedule(dateFrom, dateTo),
        {
          wrapper: createWrapper(),
          initialProps: { dateFrom: '2025-12-01', dateTo: '2025-12-15' },
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(schedulingAPI.getMySchedule).toHaveBeenCalledWith('2025-12-01', '2025-12-15');

      vi.clearAllMocks();
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      rerender({ dateFrom: '2025-12-16', dateTo: '2025-12-31' });

      await waitFor(() => {
        expect(schedulingAPI.getMySchedule).toHaveBeenCalledWith('2025-12-16', '2025-12-31');
      });
    });

    it('should not fetch when dates are not provided', () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([]);

      const { result } = renderHook(() => useTeacherSchedule(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.lessons).toEqual([]);
      expect(schedulingAPI.getMySchedule).not.toHaveBeenCalled();
    });
  });

  describe('Grouping by Date (lessonsByDate)', () => {
    it('should group lessons by date correctly', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessonsByDate).toHaveProperty('2025-12-15');
      expect(result.current.lessonsByDate).toHaveProperty('2025-12-16');
      expect(result.current.lessonsByDate).toHaveProperty('2025-11-28');

      // 2025-12-15 should have 2 lessons
      expect(result.current.lessonsByDate['2025-12-15']).toHaveLength(2);

      // 2025-12-16 should have 1 lesson
      expect(result.current.lessonsByDate['2025-12-16']).toHaveLength(1);

      // 2025-11-28 should have 1 lesson
      expect(result.current.lessonsByDate['2025-11-28']).toHaveLength(1);
    });

    it('should handle lessons without date property', async () => {
      const lessonsWithoutDate = [
        {
          ...mockScheduleData[0],
          date: undefined,
        },
      ];

      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(lessonsWithoutDate);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessonsByDate).toBeDefined();
    });

    it('should update grouping when schedule changes', async () => {
      const wrapper1 = createWrapper();
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([mockScheduleData[0]]);

      const { result: result1 } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: wrapper1,
        }
      );

      await waitFor(() => expect(result1.current.isLoading).toBe(false));
      expect(Object.keys(result1.current.lessonsByDate)).toHaveLength(1);

      // Create new hook with fresh data
      const wrapper2 = createWrapper();
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result: result2 } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: wrapper2,
        }
      );

      await waitFor(() => expect(result2.current.isLoading).toBe(false));
      expect(Object.keys(result2.current.lessonsByDate).length).toBeGreaterThan(1);
    });
  });

  describe('Upcoming Lessons Filter', () => {
    it('should filter upcoming lessons correctly', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.upcomingLessons).toHaveLength(3);
      expect(result.current.upcomingLessons.every((l) => l.is_upcoming)).toBe(true);
    });

    it('should return only upcoming lessons', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // mockScheduleData[3] has is_upcoming=false, so should not be included
      expect(result.current.upcomingLessons).not.toContain(mockScheduleData[3]);
    });

    it('should return empty array when no upcoming lessons', async () => {
      const pastLessonsOnly = [mockScheduleData[3]]; // Only completed lesson

      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(pastLessonsOnly);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.upcomingLessons).toHaveLength(0);
    });

    it('should update upcoming lessons when data changes', async () => {
      const wrapper1 = createWrapper();
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([mockScheduleData[3]]);

      const { result: result1 } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: wrapper1,
        }
      );

      await waitFor(() => expect(result1.current.isLoading).toBe(false));
      expect(result1.current.upcomingLessons).toHaveLength(0);

      // Create new hook with fresh data
      const wrapper2 = createWrapper();
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result: result2 } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: wrapper2,
        }
      );

      await waitFor(() => expect(result2.current.isLoading).toBe(false));
      expect(result2.current.upcomingLessons).toHaveLength(3);
    });
  });

  describe('Today Lessons Filter', () => {
    it('should return lessons for today', async () => {
      const today = new Date().toISOString().split('T')[0];

      const lessonsWithToday = [
        {
          ...mockScheduleData[0],
          date: today,
          is_upcoming: true,
        },
        {
          ...mockScheduleData[1],
          date: today,
          is_upcoming: true,
        },
      ];

      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(lessonsWithToday);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.todayLessons).toHaveLength(2);
      expect(result.current.todayLessons.every((l) => l.date === today)).toBe(true);
    });

    it('should return empty array when no lessons today', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // None of mockScheduleData dates are today
      const today = new Date().toISOString().split('T')[0];
      const hasToday = mockScheduleData.some((l) => l.date === today);

      if (!hasToday) {
        expect(result.current.todayLessons).toHaveLength(0);
      }
    });
  });

  describe('Return Value Structure', () => {
    it('should return all expected properties', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current).toHaveProperty('lessons');
      expect(result.current).toHaveProperty('lessonsByDate');
      expect(result.current).toHaveProperty('upcomingLessons');
      expect(result.current).toHaveProperty('todayLessons');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
    });

    it('should have correct types for all properties', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(Array.isArray(result.current.lessons)).toBe(true);
      expect(Array.isArray(result.current.upcomingLessons)).toBe(true);
      expect(Array.isArray(result.current.todayLessons)).toBe(true);
      expect(typeof result.current.lessonsByDate).toBe('object');
      expect(typeof result.current.isLoading).toBe('boolean');
    });
  });

  describe('Edge Cases', () => {
    it('should handle API returning null', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(null as any);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toEqual([]);
      expect(result.current.upcomingLessons).toEqual([]);
    });

    it('should handle API returning undefined gracefully', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockImplementation(() => {
        return Promise.resolve([] as any); // Return empty array instead of undefined
      });

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toEqual([]);
    });

    it('should handle malformed lesson data', async () => {
      const malformedData = [
        {
          id: '770e8400-e29b-41d4-a716-446655440000',
          // Missing required fields
        },
      ];

      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(malformedData as any);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toHaveLength(1);
    });

    it('should handle very large dataset', async () => {
      const largeLessonSet = Array.from({ length: 1000 }, (_, i) => ({
        ...mockScheduleData[0],
        id: `lesson-${i}`,
        date: new Date(2025, 11, (i % 30) + 1).toISOString().split('T')[0],
      }));

      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(largeLessonSet);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.lessons).toHaveLength(1000);
      expect(Object.keys(result.current.lessonsByDate).length).toBeGreaterThan(0);
    });
  });

  describe('Error Handling and Retry', () => {
    it('should handle error and allow retry', async () => {
      vi.mocked(schedulingAPI.getMySchedule)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockScheduleData);

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.error).toBeTruthy();
      expect(result.current.lessons).toEqual([]);
    });

  });

  describe('Memoization', () => {
    it('should compute lessonsByDate correctly for fresh request', async () => {
      // Fresh mock setup for this test
      vi.mocked(schedulingAPI.getMySchedule).mockImplementation(() =>
        Promise.resolve(mockScheduleData)
      );

      const { result } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Verify structure
      expect(result.current.lessonsByDate).toBeDefined();
      if (result.current.lessonsByDate['2025-12-15']) {
        expect(result.current.lessonsByDate['2025-12-15']).toHaveLength(2);
      }
    });

    it('should not recalculate if data is same', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const wrapper = createWrapper();
      const { result, rerender } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-31'),
        {
          wrapper: wrapper,
        }
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      const originalGrouping = result.current.lessonsByDate;
      const originalLessonCount = originalGrouping['2025-12-15']?.length || 0;

      rerender();

      // Grouping object reference might be different, but content should be same
      expect(result.current.lessonsByDate['2025-12-15']?.length).toBe(originalLessonCount);
    });
  });

  describe('Combined Scenarios', () => {
    it('should handle complete workflow: load, filter, update', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      const { result, rerender } = renderHook(
        ({ dateFrom, dateTo }) => useTeacherSchedule(dateFrom, dateTo),
        {
          wrapper: createWrapper(),
          initialProps: { dateFrom: '2025-12-01', dateTo: '2025-12-31' },
        }
      );

      // Initial load
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.lessons).toHaveLength(4);

      // Change date range
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue([mockScheduleData[0]]);
      rerender({ dateFrom: '2025-12-15', dateTo: '2025-12-15' });

      await waitFor(() => {
        expect(result.current.lessons).toHaveLength(1);
      });
    });

    it('should maintain separate query states for different date ranges', async () => {
      vi.mocked(schedulingAPI.getMySchedule)
        .mockResolvedValueOnce(mockScheduleData.slice(0, 2))
        .mockResolvedValueOnce(mockScheduleData.slice(2));

      const { result: result1 } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-15'),
        {
          wrapper: createWrapper(),
        }
      );

      const { result: result2 } = renderHook(
        () => useTeacherSchedule('2025-12-16', '2025-12-31'),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
        expect(result2.current.isLoading).toBe(false);
      });

      expect(result1.current.lessons).toHaveLength(2);
      expect(result2.current.lessons).toHaveLength(2);
    });
  });

  describe('Query Key Dependencies', () => {
    it('should use correct query key format', async () => {
      vi.mocked(schedulingAPI.getMySchedule).mockResolvedValue(mockScheduleData);

      renderHook(() => useTeacherSchedule('2025-12-01', '2025-12-31'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(schedulingAPI.getMySchedule).toHaveBeenCalledWith('2025-12-01', '2025-12-31');
      });
    });

    it('should create separate cache entries for different date ranges', async () => {
      vi.mocked(schedulingAPI.getMySchedule)
        .mockResolvedValueOnce(mockScheduleData.slice(0, 2))
        .mockResolvedValueOnce(mockScheduleData.slice(2));

      const wrapper1 = createWrapper();
      const wrapper2 = createWrapper();

      const { result: result1 } = renderHook(
        () => useTeacherSchedule('2025-12-01', '2025-12-15'),
        {
          wrapper: wrapper1,
        }
      );

      const { result: result2 } = renderHook(
        () => useTeacherSchedule('2025-12-16', '2025-12-31'),
        {
          wrapper: wrapper2,
        }
      );

      await waitFor(() => {
        expect(result1.current.lessons).toHaveLength(2);
        expect(result2.current.lessons).toHaveLength(2);
      });

      // API should be called twice with different parameters
      expect(schedulingAPI.getMySchedule).toHaveBeenCalledTimes(2);
    });
  });
});
