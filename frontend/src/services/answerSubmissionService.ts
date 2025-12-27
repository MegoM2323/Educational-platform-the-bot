/**
 * Answer Submission Service
 * Handles answer submission with offline support, retry logic, and error handling
 */

import { lessonService, type SubmitAnswerRequest, type SubmitAnswerResponse } from './lessonService';
import { offlineStorage } from '@/utils/offlineStorage';
import { logger } from '@/utils/logger';

// Типы
export interface SubmissionResult {
  success: boolean;
  data?: SubmitAnswerResponse;
  error?: string;
  cached?: boolean;
}

export interface NetworkStatus {
  isOnline: boolean;
  effectiveType?: string;
  downlink?: number;
}

class AnswerSubmissionService {
  private networkStatus: NetworkStatus = { isOnline: navigator.onLine };
  private syncInProgress = false;
  private listeners: Array<(status: NetworkStatus) => void> = [];

  constructor() {
    this.initNetworkListeners();
  }

  /**
   * Инициализация слушателей сети
   */
  private initNetworkListeners(): void {
    if (typeof window === 'undefined') return;

    window.addEventListener('online', () => {
      this.updateNetworkStatus(true);
      this.autoSyncPendingAnswers();
    });

    window.addEventListener('offline', () => {
      this.updateNetworkStatus(false);
    });

    // Проверка качества соединения (если поддерживается)
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      connection.addEventListener('change', () => {
        this.updateNetworkStatus(navigator.onLine);
      });
    }
  }

  /**
   * Обновить статус сети
   */
  private updateNetworkStatus(isOnline: boolean): void {
    const connection = (navigator as any).connection;

    this.networkStatus = {
      isOnline,
      effectiveType: connection?.effectiveType,
      downlink: connection?.downlink,
    };

    logger.info('[AnswerSubmissionService] Network status updated:', this.networkStatus);

    // Уведомить слушателей
    this.listeners.forEach((listener) => listener(this.networkStatus));
  }

  /**
   * Подписаться на изменения статуса сети
   */
  onNetworkStatusChange(callback: (status: NetworkStatus) => void): () => void {
    this.listeners.push(callback);

    // Вернуть функцию отписки
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  /**
   * Проверить доступность сети (реальная проверка)
   */
  private async checkNetworkConnectivity(): Promise<boolean> {
    try {
      // Пробуем сделать HEAD запрос к бэкенду
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch('/api/health/', {
        method: 'HEAD',
        signal: controller.signal,
        cache: 'no-cache',
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      logger.warn('[AnswerSubmissionService] Network check failed:', error);
      return false;
    }
  }

  /**
   * Отправить ответ на элемент
   * Автоматически кэширует при отсутствии сети
   */
  async submitAnswer(params: {
    elementId: string;
    answer: any;
    lessonId: string;
    graphId?: string;
    graphLessonId: string;
  }): Promise<SubmissionResult> {
    logger.info('[AnswerSubmissionService] Submitting answer:', {
      elementId: params.elementId,
      lessonId: params.lessonId,
    });

    // Проверить сеть
    const isOnline = await this.checkNetworkConnectivity();

    if (!isOnline) {
      // Сохранить в offline storage
      offlineStorage.saveAnswer(params);

      logger.info('[AnswerSubmissionService] Answer cached for later submission');

      return {
        success: true,
        cached: true,
        error: undefined,
      };
    }

    // Попробовать отправить
    try {
      const requestData: SubmitAnswerRequest = {
        answer: params.answer,
        graph_lesson_id: params.graphLessonId,
      };

      const result = await lessonService.submitElementAnswer(params.elementId, requestData);

      logger.info('[AnswerSubmissionService] Answer submitted successfully');

      // Удалить из кэша если был
      offlineStorage.removeAnswer(params.elementId, params.lessonId);

      return {
        success: true,
        data: result,
        cached: false,
      };
    } catch (error) {
      logger.error('[AnswerSubmissionService] Submit failed:', error);

      // Сохранить в offline storage для повтора
      offlineStorage.saveAnswer(params);
      offlineStorage.updateAnswerStatus(params.elementId, params.lessonId, 'failed', String(error));

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        cached: true,
      };
    }
  }

  /**
   * Повторить отправку неудачных ответов
   */
  async retryFailedSubmissions(): Promise<number> {
    const pending = offlineStorage.getPendingAnswers();

    if (pending.length === 0) {
      logger.info('[AnswerSubmissionService] No pending answers to retry');
      return 0;
    }

    logger.info('[AnswerSubmissionService] Retrying failed submissions:', {
      count: pending.length,
    });

    let successCount = 0;

    for (const cached of pending) {
      try {
        const requestData: SubmitAnswerRequest = {
          answer: cached.answer,
          graph_lesson_id: cached.graph_lesson_id,
        };

        await lessonService.submitElementAnswer(cached.element_id, requestData);

        offlineStorage.updateAnswerStatus(cached.element_id, cached.lesson_id, 'submitted');
        successCount++;

        logger.info('[AnswerSubmissionService] Retry successful:', {
          elementId: cached.element_id,
        });
      } catch (error) {
        logger.error('[AnswerSubmissionService] Retry failed:', error);
        offlineStorage.updateAnswerStatus(
          cached.element_id,
          cached.lesson_id,
          'failed',
          String(error)
        );
      }
    }

    logger.info('[AnswerSubmissionService] Retry complete:', {
      total: pending.length,
      success: successCount,
      failed: pending.length - successCount,
    });

    return successCount;
  }

  /**
   * Автоматическая синхронизация при восстановлении сети
   */
  private async autoSyncPendingAnswers(): Promise<void> {
    if (this.syncInProgress) {
      logger.info('[AnswerSubmissionService] Sync already in progress, skipping');
      return;
    }

    if (!offlineStorage.needsSync()) {
      logger.info('[AnswerSubmissionService] No pending answers to sync');
      return;
    }

    this.syncInProgress = true;

    try {
      logger.info('[AnswerSubmissionService] Auto-sync started');
      await this.retryFailedSubmissions();
      logger.info('[AnswerSubmissionService] Auto-sync completed');
    } catch (error) {
      logger.error('[AnswerSubmissionService] Auto-sync failed:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  /**
   * Получить кэшированные ответы
   */
  getCachedAnswers() {
    return offlineStorage.getPendingAnswers();
  }

  /**
   * Получить количество ожидающих ответов
   */
  getPendingCount(): number {
    return offlineStorage.getPendingCount();
  }

  /**
   * Очистить весь кэш
   */
  clearCache(): void {
    offlineStorage.clearAll();
  }

  /**
   * Получить текущий статус сети
   */
  getNetworkStatus(): NetworkStatus {
    return { ...this.networkStatus };
  }

  /**
   * Проверить, есть ли кэшированный ответ для элемента
   */
  hasCachedAnswer(elementId: string, lessonId: string): boolean {
    return offlineStorage.getAnswer(elementId, lessonId) !== null;
  }
}

// Export singleton instance
export const answerSubmissionService = new AnswerSubmissionService();
