/**
 * Tests for useLessonProgress hook
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useLessonProgress } from '../useLessonProgress';
import { lessonService } from '@/services/lessonService';

// Mock lessonService
vi.mock('@/services/lessonService', () => ({
  lessonService: {
    getLesson: vi.fn(),
    getLessonProgress: vi.fn(),
    checkPrerequisites: vi.fn(),
    submitElementAnswer: vi.fn(),
    completeLessonStatus: vi.fn(),
  },
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('useLessonProgress', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('должен загружать урок и прогресс', async () => {
    const mockLesson = {
      id: '1',
      title: 'Test Lesson',
      description: 'Test Description',
      subject: { id: 1, name: 'Math' },
      total_duration_minutes: 30,
      total_max_score: 100,
      elements: [
        {
          id: '1',
          title: 'Element 1',
          description: 'First element',
          element_type: 'text_problem' as const,
          element_type_display: 'Текстовая задача',
          content: { problem_text: 'Solve this' },
          difficulty: 5,
          estimated_time_minutes: 10,
          max_score: 50,
          tags: [],
          order: 1,
        },
      ],
      created_at: '2024-01-01',
    };

    const mockProgress = {
      id: '1',
      lesson: { id: '1', title: 'Test Lesson' },
      graph_lesson_id: '123',
      status: 'in_progress' as const,
      started_at: '2024-01-01',
      completed_at: null,
      completed_elements_count: 0,
      total_elements_count: 1,
      total_score: 0,
      max_total_score: 50,
      score_percent: 0,
      element_progress: [],
    };

    vi.mocked(lessonService.getLesson).mockResolvedValue(mockLesson);
    vi.mocked(lessonService.getLessonProgress).mockResolvedValue(mockProgress);

    const { result } = renderHook(
      () =>
        useLessonProgress({
          lessonId: '1',
          studentId: '1',
        }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.lesson).toEqual(mockLesson);
    expect(result.current.progress).toEqual(mockProgress);
    expect(result.current.elementsWithProgress).toHaveLength(1);
  });

  it('должен вычислять процент прогресса', async () => {
    const mockLesson = {
      id: '1',
      title: 'Test Lesson',
      description: 'Test',
      subject: { id: 1, name: 'Math' },
      total_duration_minutes: 30,
      total_max_score: 100,
      elements: [],
      created_at: '2024-01-01',
    };

    const mockProgress = {
      id: '1',
      lesson: { id: '1', title: 'Test Lesson' },
      graph_lesson_id: '123',
      status: 'in_progress' as const,
      started_at: '2024-01-01',
      completed_at: null,
      completed_elements_count: 3,
      total_elements_count: 5,
      total_score: 75,
      max_total_score: 100,
      score_percent: 75,
      element_progress: [],
    };

    vi.mocked(lessonService.getLesson).mockResolvedValue(mockLesson);
    vi.mocked(lessonService.getLessonProgress).mockResolvedValue(mockProgress);

    const { result } = renderHook(
      () =>
        useLessonProgress({
          lessonId: '1',
          studentId: '1',
        }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.getProgressPercent()).toBe(60); // 3/5 = 60%
  });

  it('должен проверять пререквизиты если передан graphId', async () => {
    const mockLesson = {
      id: '1',
      title: 'Test Lesson',
      description: 'Test',
      subject: { id: 1, name: 'Math' },
      total_duration_minutes: 30,
      total_max_score: 100,
      elements: [],
      created_at: '2024-01-01',
    };

    const mockProgress = {
      id: '1',
      lesson: { id: '1', title: 'Test Lesson' },
      graph_lesson_id: '123',
      status: 'in_progress' as const,
      started_at: '2024-01-01',
      completed_at: null,
      completed_elements_count: 0,
      total_elements_count: 1,
      total_score: 0,
      max_total_score: 50,
      score_percent: 0,
      element_progress: [],
    };

    const mockPrerequisites = {
      can_start: false,
      missing_prerequisites: [
        { id: '2', title: 'Prerequisite Lesson' },
      ],
    };

    vi.mocked(lessonService.getLesson).mockResolvedValue(mockLesson);
    vi.mocked(lessonService.getLessonProgress).mockResolvedValue(mockProgress);
    vi.mocked(lessonService.checkPrerequisites).mockResolvedValue(mockPrerequisites);

    const { result } = renderHook(
      () =>
        useLessonProgress({
          lessonId: '1',
          studentId: '1',
          graphId: 'graph-1',
        }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isUnlocked).toBe(false);
    expect(result.current.missingPrerequisites).toHaveLength(1);
    expect(lessonService.checkPrerequisites).toHaveBeenCalledWith('graph-1', '1');
  });

  it('должен определять завершение всех элементов', async () => {
    const mockLesson = {
      id: '1',
      title: 'Test Lesson',
      description: 'Test',
      subject: { id: 1, name: 'Math' },
      total_duration_minutes: 30,
      total_max_score: 100,
      elements: [
        {
          id: '1',
          title: 'Element 1',
          description: 'First',
          element_type: 'text_problem' as const,
          element_type_display: 'Текстовая задача',
          content: {},
          difficulty: 5,
          estimated_time_minutes: 10,
          max_score: 50,
          tags: [],
          order: 1,
        },
        {
          id: '2',
          title: 'Element 2',
          description: 'Second',
          element_type: 'quick_question' as const,
          element_type_display: 'Быстрый вопрос',
          content: {},
          difficulty: 3,
          estimated_time_minutes: 5,
          max_score: 50,
          tags: [],
          order: 2,
        },
      ],
      created_at: '2024-01-01',
    };

    const mockProgress = {
      id: '1',
      lesson: { id: '1', title: 'Test Lesson' },
      graph_lesson_id: '123',
      status: 'in_progress' as const,
      started_at: '2024-01-01',
      completed_at: null,
      completed_elements_count: 2,
      total_elements_count: 2,
      total_score: 100,
      max_total_score: 100,
      score_percent: 100,
      element_progress: [
        {
          id: '1',
          element: { id: '1', title: 'Element 1' },
          answer: { text: 'answer 1' },
          score: 50,
          max_score: 50,
          status: 'completed' as const,
          started_at: '2024-01-01',
          completed_at: '2024-01-01',
          attempts: 1,
        },
        {
          id: '2',
          element: { id: '2', title: 'Element 2' },
          answer: { choice: 0 },
          score: 50,
          max_score: 50,
          status: 'completed' as const,
          started_at: '2024-01-01',
          completed_at: '2024-01-01',
          attempts: 1,
        },
      ],
    };

    vi.mocked(lessonService.getLesson).mockResolvedValue(mockLesson);
    vi.mocked(lessonService.getLessonProgress).mockResolvedValue(mockProgress);

    const { result } = renderHook(
      () =>
        useLessonProgress({
          lessonId: '1',
          studentId: '1',
        }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.allElementsCompleted()).toBe(true);
  });
});
