/**
 * useProgressSync Hook (T702)
 * Hook для синхронизации прогресса и управления состоянием завершения уроков
 */

import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { progressSyncService, type ProgressSyncResult, type LessonCompletionResult } from '@/services/progressSyncService';
import { notificationService } from '@/services/notificationService';

export interface UseProgressSyncOptions {
  graphId: number;
  lessonId: number;
  graphLessonId: number;
  studentId: number;
  onLessonComplete?: (result: LessonCompletionResult) => void;
  onUnlock?: (lessonIds: number[]) => void;
  onError?: (error: Error) => void;
}

export interface UseProgressSyncReturn {
  // Основные методы
  completeLesson: () => Promise<LessonCompletionResult | null>;
  syncProgress: () => Promise<ProgressSyncResult>;
  checkCompletion: () => Promise<boolean>;

  // Состояние
  isLoading: boolean;
  isCompleting: boolean;
  error: Error | null;

  // Данные
  unlockedLessons: number[];
  lastSyncResult: ProgressSyncResult | null;
}

export const useProgressSync = (options: UseProgressSyncOptions): UseProgressSyncReturn => {
  const { graphId, lessonId, graphLessonId, studentId, onLessonComplete, onUnlock, onError } = options;

  const queryClient = useQueryClient();
  const [unlockedLessons, setUnlockedLessons] = useState<number[]>([]);
  const [lastSyncResult, setLastSyncResult] = useState<ProgressSyncResult | null>(null);

  // Мутация для завершения урока
  const completionMutation = useMutation({
    mutationFn: async () => {
      return await progressSyncService.completeLessonIfReady(graphId, lessonId, graphLessonId, studentId);
    },
    onSuccess: (result) => {
      if (result) {
        // Урок завершен
        const unlockedIds = result.unlocked_lessons.map((ul) => ul.lesson_id);
        setUnlockedLessons(unlockedIds);

        // Инвалидировать кеш
        progressSyncService.invalidateProgressCache(graphId, studentId, lessonId);

        // Callbacks
        onLessonComplete?.(result);
        if (unlockedIds.length > 0) {
          onUnlock?.(unlockedIds);
        }

        // Уведомления
        notificationService.lessonCompleted(result.lesson_id.toString(), {
          completedLessons: 0, // Будет обновлено из графа
          totalLessons: 0,
        });

        if (result.unlocked_lessons.length > 0) {
          notificationService.lessonsUnlocked(
            result.unlocked_lessons.length,
            result.unlocked_lessons.map((ul) => ul.lesson_title)
          );
        }
      }
    },
    onError: (error: Error) => {
      console.error('[useProgressSync] Error completing lesson:', error);
      notificationService.lessonCompletionError(() => completionMutation.mutate());
      onError?.(error);
    },
  });

  // Мутация для полной синхронизации
  const syncMutation = useMutation({
    mutationFn: async () => {
      return await progressSyncService.syncAfterElementCompletion(graphId, lessonId, graphLessonId, studentId);
    },
    onSuccess: (result) => {
      setLastSyncResult(result);

      if (result.completed) {
        const unlockedIds = result.unlocked_lessons.map((ul) => ul.lesson_id);
        setUnlockedLessons(unlockedIds);

        if (unlockedIds.length > 0) {
          onUnlock?.(unlockedIds);
        }
      }

      // Обновить кеш
      queryClient.invalidateQueries({ queryKey: ['graphProgress', graphId] });
      queryClient.invalidateQueries({ queryKey: ['lessonProgress', lessonId] });
    },
    onError: (error: Error) => {
      console.error('[useProgressSync] Error syncing progress:', error);
      notificationService.syncError(() => syncMutation.mutate());
      onError?.(error);
    },
  });

  // Проверка завершения урока
  const checkCompletion = useCallback(async (): Promise<boolean> => {
    try {
      const result = await progressSyncService.checkLessonCompletion(lessonId, graphLessonId, studentId);
      return result.is_ready;
    } catch (error) {
      console.error('[useProgressSync] Error checking completion:', error);
      return false;
    }
  }, [lessonId, graphLessonId, studentId]);

  return {
    // Методы
    completeLesson: async () => {
      const result = await completionMutation.mutateAsync();
      return result;
    },
    syncProgress: async () => {
      const result = await syncMutation.mutateAsync();
      return result;
    },
    checkCompletion,

    // Состояние
    isLoading: completionMutation.isPending || syncMutation.isPending,
    isCompleting: completionMutation.isPending,
    error: (completionMutation.error || syncMutation.error) as Error | null,

    // Данные
    unlockedLessons,
    lastSyncResult,
  };
};
