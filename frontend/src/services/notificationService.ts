/**
 * Notification Service (T702)
 * Централизованная система уведомлений с toast notifications
 */

import { toast } from '@/hooks/use-toast';

// ============================================
// Types
// ============================================

export type NotificationType = 'success' | 'info' | 'warning' | 'error';

export interface NotificationOptions {
  title: string;
  description?: string;
  type?: NotificationType;
  duration?: number; // milliseconds, по умолчанию 5000
  dismissible?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// ============================================
// Notification Service
// ============================================

export const notificationService = {
  /**
   * Показать уведомление
   */
  show: (options: NotificationOptions) => {
    const {
      title,
      description,
      type = 'info',
      duration = 5000,
      dismissible = true,
      action,
    } = options;

    // Определить variant для toast
    const variant = type === 'error' ? 'destructive' : 'default';

    const toastInstance = toast({
      title,
      description,
      variant,
      duration,
      action: action
        ? {
            altText: action.label,
            onClick: action.onClick,
          }
        : undefined,
    });

    // Авто-dismiss через duration
    if (dismissible && duration > 0) {
      setTimeout(() => {
        toastInstance.dismiss();
      }, duration);
    }

    return toastInstance;
  },

  /**
   * Успех
   */
  success: (title: string, description?: string, duration = 5000) => {
    return notificationService.show({
      title,
      description,
      type: 'success',
      duration,
    });
  },

  /**
   * Информация
   */
  info: (title: string, description?: string, duration = 5000) => {
    return notificationService.show({
      title,
      description,
      type: 'info',
      duration,
    });
  },

  /**
   * Предупреждение
   */
  warning: (title: string, description?: string, duration = 5000) => {
    return notificationService.show({
      title,
      description,
      type: 'warning',
      duration,
    });
  },

  /**
   * Ошибка
   */
  error: (title: string, description?: string, duration = 7000) => {
    return notificationService.show({
      title,
      description,
      type: 'error',
      duration,
    });
  },

  // ============================================
  // Специфичные уведомления для Knowledge Graph
  // ============================================

  /**
   * Урок завершен
   */
  lessonCompleted: (lessonTitle: string, stats: { completedLessons: number; totalLessons: number }) => {
    return notificationService.success(
      'Урок завершен!',
      `${lessonTitle} • Пройдено ${stats.completedLessons}/${stats.totalLessons} уроков`,
      6000
    );
  },

  /**
   * Новые уроки разблокированы
   */
  lessonsUnlocked: (count: number, lessonTitles?: string[]) => {
    const description = lessonTitles?.length
      ? lessonTitles.slice(0, 3).join(', ') + (lessonTitles.length > 3 ? '...' : '')
      : undefined;

    return notificationService.info(
      `${count} ${count === 1 ? 'новый урок' : 'новых урока(ов)'} разблокирован${count === 1 ? '' : 'о'}!`,
      description,
      6000
    );
  },

  /**
   * Элемент завершен
   */
  elementCompleted: (elementTitle: string, score?: number, maxScore?: number) => {
    const scoreText = score !== undefined && maxScore !== undefined ? ` • ${score}/${maxScore} баллов` : '';

    return notificationService.success('Элемент выполнен', `${elementTitle}${scoreText}`, 3000);
  },

  /**
   * Ошибка при сохранении прогресса
   */
  progressSaveError: (retryAction?: () => void) => {
    return notificationService.show({
      title: 'Не удалось сохранить прогресс',
      description: 'Попробуйте еще раз',
      type: 'error',
      duration: 7000,
      action: retryAction
        ? {
            label: 'Повторить',
            onClick: retryAction,
          }
        : undefined,
    });
  },

  /**
   * Ошибка при завершении урока
   */
  lessonCompletionError: (retryAction?: () => void) => {
    return notificationService.show({
      title: 'Не удалось завершить урок',
      description: 'Попробуйте позже',
      type: 'error',
      duration: 7000,
      action: retryAction
        ? {
            label: 'Повторить',
            onClick: retryAction,
          }
        : undefined,
    });
  },

  /**
   * Ошибка при разблокировке уроков
   */
  unlockError: () => {
    return notificationService.warning(
      'Некоторые уроки могут быть не разблокированы',
      'Обновите страницу чтобы увидеть актуальное состояние',
      7000
    );
  },

  /**
   * Ошибка синхронизации прогресса
   */
  syncError: (retryAction?: () => void) => {
    return notificationService.show({
      title: 'Не удалось синхронизировать прогресс',
      description: 'Обновите страницу',
      type: 'error',
      duration: 7000,
      action: retryAction
        ? {
            label: 'Обновить',
            onClick: retryAction,
          }
        : undefined,
    });
  },

  /**
   * Прогресс урока (для мотивации)
   */
  lessonProgress: (completionPercent: number) => {
    if (completionPercent >= 80 && completionPercent < 100) {
      return notificationService.info(
        `${completionPercent}% выполнено!`,
        'Продолжайте в том же духе',
        4000
      );
    }
    return null;
  },

  /**
   * Урок уже завершен (предотвращение дублирования)
   */
  lessonAlreadyCompleted: (lessonTitle: string) => {
    return notificationService.info('Урок уже завершен', lessonTitle, 3000);
  },

  /**
   * Prerequisite не выполнены
   */
  prerequisitesNotMet: (missingLessons: string[]) => {
    const description =
      missingLessons.length > 0
        ? `Сначала завершите: ${missingLessons.slice(0, 2).join(', ')}`
        : 'Сначала завершите предыдущие уроки';

    return notificationService.warning('Prerequisite не выполнены', description, 6000);
  },
};
