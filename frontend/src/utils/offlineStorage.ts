/**
 * Offline Storage Utility
 * Manages local caching of answer submissions when offline
 * Handles auto-sync when network is restored
 */

import { logger } from './logger';

// Типы
export interface CachedAnswer {
  element_id: string;
  answer: any;
  lesson_id: string;
  graph_id?: string;
  graph_lesson_id: string;
  timestamp: string;
  attempts: number;
  status: 'pending' | 'failed' | 'submitted';
  error?: string;
}

interface OfflineStorageData {
  answers: Record<string, CachedAnswer>;
  lastSync: string | null;
}

const STORAGE_KEY = 'kg_offline_answers';
const MAX_RETRY_ATTEMPTS = 5;

class OfflineStorage {
  private data: OfflineStorageData;

  constructor() {
    this.data = this.loadFromStorage();
  }

  /**
   * Загрузить данные из localStorage
   */
  private loadFromStorage(): OfflineStorageData {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        return { answers: {}, lastSync: null };
      }

      const parsed = JSON.parse(stored);
      logger.info('[OfflineStorage] Loaded data:', {
        answerCount: Object.keys(parsed.answers || {}).length,
      });

      return parsed;
    } catch (error) {
      logger.error('[OfflineStorage] Failed to load from localStorage:', error);
      return { answers: {}, lastSync: null };
    }
  }

  /**
   * Сохранить данные в localStorage
   */
  private saveToStorage(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
      logger.info('[OfflineStorage] Data saved to localStorage');
    } catch (error) {
      logger.error('[OfflineStorage] Failed to save to localStorage:', error);
    }
  }

  /**
   * Создать ключ для ответа на элемент
   */
  private getAnswerKey(elementId: string, lessonId: string): string {
    return `${lessonId}_${elementId}`;
  }

  /**
   * Сохранить ответ в кэш
   */
  saveAnswer(params: {
    elementId: string;
    answer: any;
    lessonId: string;
    graphId?: string;
    graphLessonId: string;
  }): void {
    const key = this.getAnswerKey(params.elementId, params.lessonId);

    const cached: CachedAnswer = {
      element_id: params.elementId,
      answer: params.answer,
      lesson_id: params.lessonId,
      graph_id: params.graphId,
      graph_lesson_id: params.graphLessonId,
      timestamp: new Date().toISOString(),
      attempts: 0,
      status: 'pending',
    };

    this.data.answers[key] = cached;
    this.saveToStorage();

    logger.info('[OfflineStorage] Answer saved to cache:', {
      elementId: params.elementId,
      lessonId: params.lessonId,
    });
  }

  /**
   * Получить кэшированный ответ
   */
  getAnswer(elementId: string, lessonId: string): CachedAnswer | null {
    const key = this.getAnswerKey(elementId, lessonId);
    return this.data.answers[key] || null;
  }

  /**
   * Удалить ответ из кэша
   */
  removeAnswer(elementId: string, lessonId: string): void {
    const key = this.getAnswerKey(elementId, lessonId);
    delete this.data.answers[key];
    this.saveToStorage();

    logger.info('[OfflineStorage] Answer removed from cache:', {
      elementId,
      lessonId,
    });
  }

  /**
   * Получить все ожидающие синхронизации ответы
   */
  getPendingAnswers(): CachedAnswer[] {
    return Object.values(this.data.answers).filter(
      (answer) => answer.status === 'pending' || answer.status === 'failed'
    );
  }

  /**
   * Обновить статус ответа
   */
  updateAnswerStatus(
    elementId: string,
    lessonId: string,
    status: CachedAnswer['status'],
    error?: string
  ): void {
    const key = this.getAnswerKey(elementId, lessonId);
    const answer = this.data.answers[key];

    if (!answer) {
      logger.warn('[OfflineStorage] Answer not found for status update:', {
        elementId,
        lessonId,
      });
      return;
    }

    answer.status = status;
    answer.attempts += 1;
    if (error) {
      answer.error = error;
    }

    // Удалить после успешной отправки
    if (status === 'submitted') {
      delete this.data.answers[key];
      this.data.lastSync = new Date().toISOString();
    }

    // Удалить после превышения лимита попыток
    if (answer.attempts >= MAX_RETRY_ATTEMPTS) {
      logger.error('[OfflineStorage] Max retry attempts reached, removing answer:', {
        elementId,
        lessonId,
        attempts: answer.attempts,
      });
      delete this.data.answers[key];
    }

    this.saveToStorage();
  }

  /**
   * Получить количество ожидающих ответов
   */
  getPendingCount(): number {
    return this.getPendingAnswers().length;
  }

  /**
   * Очистить весь кэш
   */
  clearAll(): void {
    this.data = { answers: {}, lastSync: null };
    this.saveToStorage();
    logger.info('[OfflineStorage] All cached answers cleared');
  }

  /**
   * Получить время последней синхронизации
   */
  getLastSyncTime(): string | null {
    return this.data.lastSync;
  }

  /**
   * Проверить, нужна ли синхронизация
   */
  needsSync(): boolean {
    return this.getPendingCount() > 0;
  }
}

// Export singleton instance
export const offlineStorage = new OfflineStorage();
