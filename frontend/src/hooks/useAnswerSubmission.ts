/**
 * Custom hook for answer submission
 * Provides stateful answer submission with offline support, retry, and network status
 */

import { useState, useEffect, useCallback } from 'react';
import { answerSubmissionService, type SubmissionResult, type NetworkStatus } from '@/services/answerSubmissionService';
import { logger } from '@/utils/logger';
import { toast } from 'sonner';

export interface SubmitAnswerParams {
  elementId: string;
  answer: any;
  lessonId: string;
  graphId?: string;
  graphLessonId: string;
}

export type SubmissionStatus = 'idle' | 'loading' | 'success' | 'error' | 'offline';

interface UseAnswerSubmissionReturn {
  submitAnswer: (params: SubmitAnswerParams) => Promise<void>;
  retry: () => Promise<void>;
  isLoading: boolean;
  status: SubmissionStatus;
  error: string | undefined;
  isCached: boolean;
  pendingCount: number;
  isNetworkOnline: boolean;
  lastSubmissionResult: SubmissionResult | null;
}

export const useAnswerSubmission = (): UseAnswerSubmissionReturn => {
  const [status, setStatus] = useState<SubmissionStatus>('idle');
  const [error, setError] = useState<string | undefined>(undefined);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>(
    answerSubmissionService.getNetworkStatus()
  );
  const [lastSubmissionParams, setLastSubmissionParams] = useState<SubmitAnswerParams | null>(null);
  const [lastSubmissionResult, setLastSubmissionResult] = useState<SubmissionResult | null>(null);

  // Обновить количество ожидающих ответов
  const updatePendingCount = useCallback(() => {
    const count = answerSubmissionService.getPendingCount();
    setPendingCount(count);
  }, []);

  // Подписаться на изменения статуса сети
  useEffect(() => {
    const unsubscribe = answerSubmissionService.onNetworkStatusChange((status) => {
      setNetworkStatus(status);

      if (status.isOnline && pendingCount > 0) {
        toast.info('Соединение восстановлено. Синхронизация ответов...');
      }
    });

    // Начальное обновление
    updatePendingCount();

    return unsubscribe;
  }, [pendingCount, updatePendingCount]);

  /**
   * Отправить ответ
   */
  const submitAnswer = useCallback(async (params: SubmitAnswerParams): Promise<void> => {
    logger.info('[useAnswerSubmission] Submit answer called:', {
      elementId: params.elementId,
    });

    setStatus('loading');
    setError(undefined);
    setLastSubmissionParams(params);

    try {
      const result = await answerSubmissionService.submitAnswer(params);
      setLastSubmissionResult(result);

      if (result.cached) {
        // Ответ сохранен в кэш
        setStatus('offline');
        toast.info('Вы офлайн. Ответ будет отправлен при подключении к сети.', {
          duration: 4000,
        });
      } else if (result.success) {
        // Успешная отправка
        setStatus('success');

        // Короткое уведомление об успехе (уже показано в lessonService)
        // Здесь только меняем статус

        // Сбросить статус через 2 секунды
        setTimeout(() => {
          setStatus('idle');
        }, 2000);
      } else {
        // Ошибка отправки
        setStatus('error');
        setError(result.error || 'Неизвестная ошибка');
        toast.error(result.error || 'Ошибка отправки ответа', {
          duration: 5000,
        });
      }

      // Обновить количество ожидающих
      updatePendingCount();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка';

      setStatus('error');
      setError(errorMessage);
      setLastSubmissionResult({ success: false, error: errorMessage });

      logger.error('[useAnswerSubmission] Submit error:', err);
      toast.error(`Ошибка: ${errorMessage}`, { duration: 5000 });

      updatePendingCount();
    }
  }, [updatePendingCount]);

  /**
   * Повторить последнюю отправку
   */
  const retry = useCallback(async (): Promise<void> => {
    if (!lastSubmissionParams) {
      logger.warn('[useAnswerSubmission] No last submission to retry');
      toast.warning('Нет ответа для повторной отправки');
      return;
    }

    logger.info('[useAnswerSubmission] Retrying last submission');
    await submitAnswer(lastSubmissionParams);
  }, [lastSubmissionParams, submitAnswer]);

  return {
    submitAnswer,
    retry,
    isLoading: status === 'loading',
    status,
    error,
    isCached: status === 'offline',
    pendingCount,
    isNetworkOnline: networkStatus.isOnline,
    lastSubmissionResult,
  };
};

/**
 * Hook для проверки кэшированных ответов конкретного элемента
 */
export const useIsCachedAnswer = (elementId: string, lessonId: string): boolean => {
  const [isCached, setIsCached] = useState<boolean>(false);

  useEffect(() => {
    const cached = answerSubmissionService.hasCachedAnswer(elementId, lessonId);
    setIsCached(cached);
  }, [elementId, lessonId]);

  return isCached;
};
