/**
 * Tests for useAnswerSubmission hook
 * Covers offline support, retry logic, and error handling
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useAnswerSubmission } from '../useAnswerSubmission';
import { answerSubmissionService } from '@/services/answerSubmissionService';
import { offlineStorage } from '@/utils/offlineStorage';

// Mock services
vi.mock('@/services/answerSubmissionService');
vi.mock('@/utils/offlineStorage');
vi.mock('sonner', () => ({
  toast: {
    info: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

describe('useAnswerSubmission', () => {
  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Mock network status
    vi.spyOn(answerSubmissionService, 'getNetworkStatus').mockReturnValue({
      isOnline: true,
    });

    vi.spyOn(answerSubmissionService, 'getPendingCount').mockReturnValue(0);

    // Mock network status subscription
    vi.spyOn(answerSubmissionService, 'onNetworkStatusChange').mockReturnValue(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should initialize with idle status', () => {
    const { result } = renderHook(() => useAnswerSubmission());

    expect(result.current.status).toBe('idle');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeUndefined();
    expect(result.current.isCached).toBe(false);
  });

  it('should submit answer successfully', async () => {
    vi.spyOn(answerSubmissionService, 'submitAnswer').mockResolvedValue({
      success: true,
      cached: false,
      data: {
        id: 'prog_123',
        score: 10,
        max_score: 10,
        status: 'completed',
      },
    });

    const { result } = renderHook(() => useAnswerSubmission());

    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });

    expect(answerSubmissionService.submitAnswer).toHaveBeenCalledWith({
      elementId: 'elem_123',
      answer: 'Test answer',
      lessonId: 'lesson_456',
      graphLessonId: 'gl_789',
    });
  });

  it('should cache answer when offline', async () => {
    vi.spyOn(answerSubmissionService, 'submitAnswer').mockResolvedValue({
      success: true,
      cached: true,
    });

    const { result } = renderHook(() => useAnswerSubmission());

    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('offline');
      expect(result.current.isCached).toBe(true);
    });
  });

  it('should handle submission error', async () => {
    const errorMessage = 'Network error';
    vi.spyOn(answerSubmissionService, 'submitAnswer').mockResolvedValue({
      success: false,
      error: errorMessage,
      cached: true,
    });

    const { result } = renderHook(() => useAnswerSubmission());

    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('error');
      expect(result.current.error).toBe(errorMessage);
    });
  });

  it('should update pending count', async () => {
    vi.spyOn(answerSubmissionService, 'getPendingCount')
      .mockReturnValueOnce(0)
      .mockReturnValueOnce(1);

    const { result, rerender } = renderHook(() => useAnswerSubmission());

    expect(result.current.pendingCount).toBe(0);

    vi.spyOn(answerSubmissionService, 'submitAnswer').mockResolvedValue({
      success: true,
      cached: true,
    });

    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    rerender();

    await waitFor(() => {
      expect(result.current.pendingCount).toBe(1);
    });
  });

  it('should retry last submission', async () => {
    vi.spyOn(answerSubmissionService, 'submitAnswer')
      .mockResolvedValueOnce({
        success: false,
        error: 'Network error',
        cached: true,
      })
      .mockResolvedValueOnce({
        success: true,
        cached: false,
        data: {
          id: 'prog_123',
          score: 10,
          max_score: 10,
          status: 'completed',
        },
      });

    const { result } = renderHook(() => useAnswerSubmission());

    // First submission fails
    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('error');
    });

    // Retry succeeds
    await act(async () => {
      await result.current.retry();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });

    expect(answerSubmissionService.submitAnswer).toHaveBeenCalledTimes(2);
  });

  it('should track network status', () => {
    vi.spyOn(answerSubmissionService, 'getNetworkStatus').mockReturnValue({
      isOnline: false,
      effectiveType: '4g',
    });

    const { result } = renderHook(() => useAnswerSubmission());

    expect(result.current.isNetworkOnline).toBe(false);
  });

  it('should set loading state during submission', async () => {
    let resolveSubmission: (value: any) => void;
    const submissionPromise = new Promise((resolve) => {
      resolveSubmission = resolve;
    });

    vi.spyOn(answerSubmissionService, 'submitAnswer').mockReturnValue(submissionPromise as any);

    const { result } = renderHook(() => useAnswerSubmission());

    act(() => {
      result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    // Check loading state
    await waitFor(() => {
      expect(result.current.status).toBe('loading');
      expect(result.current.isLoading).toBe(true);
    });

    // Resolve submission
    act(() => {
      resolveSubmission!({
        success: true,
        cached: false,
        data: { id: 'prog_123', score: 10, max_score: 10, status: 'completed' },
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('success');
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should reset status to idle after success', async () => {
    vi.useFakeTimers();

    vi.spyOn(answerSubmissionService, 'submitAnswer').mockResolvedValue({
      success: true,
      cached: false,
      data: {
        id: 'prog_123',
        score: 10,
        max_score: 10,
        status: 'completed',
      },
    });

    const { result } = renderHook(() => useAnswerSubmission());

    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });

    // Fast-forward 2 seconds
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    await waitFor(() => {
      expect(result.current.status).toBe('idle');
    });

    vi.useRealTimers();
  });

  it('should handle exception during submission', async () => {
    const error = new Error('Unexpected error');
    vi.spyOn(answerSubmissionService, 'submitAnswer').mockRejectedValue(error);

    const { result } = renderHook(() => useAnswerSubmission());

    await act(async () => {
      await result.current.submitAnswer({
        elementId: 'elem_123',
        answer: 'Test answer',
        lessonId: 'lesson_456',
        graphLessonId: 'gl_789',
      });
    });

    await waitFor(() => {
      expect(result.current.status).toBe('error');
      expect(result.current.error).toBe('Unexpected error');
    });
  });
});
