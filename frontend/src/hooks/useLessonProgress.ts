/**
 * Custom hook for managing lesson progress
 * Handles lesson viewing, element navigation, and answer submission
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { lessonService } from '@/services/lessonService';
import type {
  Lesson,
  LessonProgress,
  PrerequisiteCheck,
  SubmitAnswerRequest,
} from '@/services/lessonService';
import { logger } from '@/utils/logger';
import { toast } from 'sonner';

interface UseLessonProgressProps {
  lessonId: string;
  studentId: string;
  graphId?: string;
  onComplete?: () => void;
}

export const useLessonProgress = ({
  lessonId,
  studentId,
  graphId,
  onComplete,
}: UseLessonProgressProps) => {
  const queryClient = useQueryClient();

  // Получить урок со всеми элементами
  const {
    data: lesson,
    isLoading: isLessonLoading,
    error: lessonError,
  } = useQuery<Lesson, Error>({
    queryKey: ['lesson', lessonId],
    queryFn: () => lessonService.getLesson(lessonId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  // Получить прогресс студента по уроку
  const {
    data: progress,
    isLoading: isProgressLoading,
    error: progressError,
  } = useQuery<LessonProgress, Error>({
    queryKey: ['lesson-progress', lessonId, studentId],
    queryFn: () => lessonService.getLessonProgress(lessonId, studentId),
    staleTime: 30 * 1000, // 30 seconds
    retry: 2,
    refetchOnMount: true,
  });

  // Проверить пререквизиты (если передан graphId)
  const {
    data: prerequisiteCheck,
    isLoading: isPrerequisiteLoading,
  } = useQuery<PrerequisiteCheck, Error>({
    queryKey: ['prerequisites', graphId, lessonId],
    queryFn: () => lessonService.checkPrerequisites(graphId!, lessonId),
    enabled: !!graphId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  // Mutation для отправки ответа на элемент
  const submitAnswerMutation = useMutation({
    mutationFn: ({
      elementId,
      data,
    }: {
      elementId: string;
      data: SubmitAnswerRequest;
    }) => lessonService.submitElementAnswer(elementId, data),
    onSuccess: (data) => {
      // Показать результат
      if (data.score !== null && data.score !== undefined) {
        toast.success(`Ответ принят! Получено баллов: ${data.score}/${data.max_score}`);
      } else {
        toast.success('Ответ принят!');
      }

      // Обновить прогресс урока
      queryClient.invalidateQueries({
        queryKey: ['lesson-progress', lessonId, studentId],
      });

      // Обновить прогресс элемента
      queryClient.invalidateQueries({
        queryKey: ['element-progress'],
      });

      logger.info('[useLessonProgress] Answer submitted, queries invalidated');
    },
    onError: (error: Error) => {
      logger.error('[useLessonProgress] Submit answer error:', error);
      toast.error(`Ошибка отправки ответа: ${error.message}`);
    },
  });

  // Mutation для завершения урока
  const completeLessonMutation = useMutation({
    mutationFn: () => lessonService.completeLessonStatus(lessonId, studentId),
    onSuccess: () => {
      logger.info('[useLessonProgress] Lesson completed');
      toast.success('Урок завершен! Поздравляем!');

      // Обновить прогресс
      queryClient.invalidateQueries({
        queryKey: ['lesson-progress', lessonId, studentId],
      });

      // Вызвать callback если передан
      if (onComplete) {
        onComplete();
      }
    },
    onError: (error: Error) => {
      logger.error('[useLessonProgress] Complete lesson error:', error);
      toast.error(`Ошибка завершения урока: ${error.message}`);
    },
  });

  // Вычисляемые свойства
  const isLoading = isLessonLoading || isProgressLoading || isPrerequisiteLoading;
  const error = lessonError || progressError;

  // Проверка доступности урока
  const isUnlocked = !prerequisiteCheck || prerequisiteCheck.can_start;
  const missingPrerequisites = prerequisiteCheck?.missing_prerequisites || [];

  // Элементы урока с прогрессом
  const elementsWithProgress =
    lesson?.elements.map((element) => {
      const elementProgress = progress?.element_progress.find(
        (p) => p.element.id === element.id
      );
      return {
        ...element,
        progress: elementProgress,
      };
    }) || [];

  // Текущий индекс элемента (первый незавершенный или первый)
  const getCurrentElementIndex = (): number => {
    if (!elementsWithProgress.length) return 0;

    const firstIncomplete = elementsWithProgress.findIndex(
      (el) => !el.progress || el.progress.status !== 'completed'
    );

    return firstIncomplete !== -1 ? firstIncomplete : 0;
  };

  // Проверка завершения всех элементов
  const allElementsCompleted = (): boolean => {
    if (!elementsWithProgress.length) return false;

    return elementsWithProgress.every(
      (el) => el.progress && el.progress.status === 'completed'
    );
  };

  // Получить прогресс в процентах
  const getProgressPercent = (): number => {
    if (!progress) return 0;
    return Math.round(
      (progress.completed_elements_count / progress.total_elements_count) * 100
    );
  };

  return {
    // Данные
    lesson,
    progress,
    prerequisiteCheck,
    elementsWithProgress,

    // Состояния загрузки
    isLoading,
    isLessonLoading,
    isProgressLoading,
    isPrerequisiteLoading,
    error,

    // Доступность
    isUnlocked,
    missingPrerequisites,

    // Mutations
    submitAnswer: submitAnswerMutation.mutate,
    isSubmitting: submitAnswerMutation.isPending,
    completeLesson: completeLessonMutation.mutate,
    isCompletingLesson: completeLessonMutation.isPending,

    // Вспомогательные методы
    getCurrentElementIndex,
    allElementsCompleted,
    getProgressPercent,
  };
};
