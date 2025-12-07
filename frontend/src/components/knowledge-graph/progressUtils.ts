/**
 * Утилиты для визуализации прогресса в графе знаний
 * T703: Progress Visualization Integration
 */

export type ProgressStatus = 'not_started' | 'in_progress' | 'completed' | 'locked';

export interface ProgressData {
  [lessonId: string]: {
    status: ProgressStatus;
    percentage: number;
    completedAt?: string;
  };
}

/**
 * Цветовая схема для статусов прогресса
 */
export const PROGRESS_COLORS = {
  not_started: '#94a3b8',  // slate-400
  in_progress: '#3b82f6',  // blue-500
  completed: '#22c55e',    // green-500
  locked: '#ef4444',       // red-500
} as const;

/**
 * Яркие цвета для hover состояния
 */
export const PROGRESS_HOVER_COLORS = {
  not_started: '#cbd5e1',  // slate-300
  in_progress: '#60a5fa',  // blue-400
  completed: '#4ade80',    // green-400
  locked: '#f87171',       // red-400
} as const;

/**
 * Получить цвет узла на основе статуса прогресса
 */
export const getNodeColorByStatus = (
  status: ProgressStatus,
  progress: number,
  isHovered: boolean = false
): string => {
  const colorMap = isHovered ? PROGRESS_HOVER_COLORS : PROGRESS_COLORS;
  return colorMap[status];
};

/**
 * Получить opacity для заблокированного урока
 */
export const getNodeOpacity = (isLocked: boolean): number => {
  return isLocked ? 0.5 : 1.0;
};

/**
 * Форматировать процент прогресса для отображения
 */
export const formatProgressLabel = (percentage: number): string => {
  return `${Math.round(percentage)}%`;
};

/**
 * Рассчитать размер узла на основе сложности урока
 * @param difficulty - уровень сложности (1-3 или 'easy'/'medium'/'hard')
 * @returns радиус узла в пикселях
 */
export const getNodeSize = (difficulty: number | string): number => {
  const baseRadius = 30;

  if (typeof difficulty === 'string') {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return baseRadius * 0.8;  // 24px
      case 'medium':
        return baseRadius;         // 30px
      case 'hard':
        return baseRadius * 1.2;  // 36px
      default:
        return baseRadius;
    }
  }

  // Если difficulty - число (1-3)
  switch (difficulty) {
    case 1:
      return baseRadius * 0.8;  // 24px
    case 2:
      return baseRadius;         // 30px
    case 3:
      return baseRadius * 1.2;  // 36px
    default:
      return baseRadius;
  }
};

/**
 * Параметры анимации перехода прогресса
 */
export interface ProgressTransition {
  duration: number;      // миллисекунды
  timing: string;        // CSS timing function
  delay: number;         // миллисекунды
}

/**
 * Получить параметры анимации для перехода статуса
 */
export const animateProgressTransition = (
  from: ProgressStatus,
  to: ProgressStatus
): ProgressTransition => {
  // Завершение урока - более заметная анимация
  if (to === 'completed') {
    return {
      duration: 800,
      timing: 'cubic-bezier(0.34, 1.56, 0.64, 1)', // bounce
      delay: 0,
    };
  }

  // Разблокировка - средняя анимация
  if (from === 'locked' && to !== 'locked') {
    return {
      duration: 600,
      timing: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)', // back
      delay: 0,
    };
  }

  // Обычный переход - плавная анимация
  return {
    duration: 500,
    timing: 'ease-in-out',
    delay: 0,
  };
};

/**
 * Получить конфигурацию эффекта свечения для текущего урока
 */
export const getCurrentLessonGlow = (): {
  color: string;
  blur: number;
  spread: number;
  animation: string;
} => {
  return {
    color: '#fbbf24', // amber-400 (gold)
    blur: 8,
    spread: 2,
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  };
};

/**
 * Рассчитать общий прогресс графа
 */
export const calculateOverallProgress = (progressData: ProgressData): {
  totalLessons: number;
  completedLessons: number;
  inProgressLessons: number;
  notStartedLessons: number;
  averageCompletion: number;
} => {
  const lessons = Object.values(progressData);
  const totalLessons = lessons.length;

  if (totalLessons === 0) {
    return {
      totalLessons: 0,
      completedLessons: 0,
      inProgressLessons: 0,
      notStartedLessons: 0,
      averageCompletion: 0,
    };
  }

  const completedLessons = lessons.filter(l => l.status === 'completed').length;
  const inProgressLessons = lessons.filter(l => l.status === 'in_progress').length;
  const notStartedLessons = lessons.filter(l => l.status === 'not_started').length;

  const totalPercentage = lessons.reduce((sum, lesson) => sum + lesson.percentage, 0);
  const averageCompletion = totalPercentage / totalLessons;

  return {
    totalLessons,
    completedLessons,
    inProgressLessons,
    notStartedLessons,
    averageCompletion,
  };
};

/**
 * Получить текст статуса на русском языке
 */
export const getStatusText = (status: ProgressStatus): string => {
  switch (status) {
    case 'not_started':
      return 'Не начат';
    case 'in_progress':
      return 'В процессе';
    case 'completed':
      return 'Завершен';
    case 'locked':
      return 'Заблокирован';
    default:
      return 'Неизвестно';
  }
};

/**
 * Проверить, должен ли узел пульсировать (анимация для разблокированных уроков)
 */
export const shouldPulse = (
  status: ProgressStatus,
  previousStatus?: ProgressStatus
): boolean => {
  // Пульсация при разблокировке
  if (previousStatus === 'locked' && status !== 'locked') {
    return true;
  }

  return false;
};

/**
 * Получить CSS-класс для анимации узла
 */
export const getNodeAnimationClass = (
  status: ProgressStatus,
  previousStatus?: ProgressStatus,
  isCurrent: boolean = false
): string => {
  const classes: string[] = [];

  // Текущий урок - постоянное свечение
  if (isCurrent) {
    classes.push('animate-pulse-slow');
  }

  // Только что завершенный - анимация завершения
  if (previousStatus !== 'completed' && status === 'completed') {
    classes.push('animate-completion');
  }

  // Только что разблокированный - пульсация
  if (shouldPulse(status, previousStatus)) {
    classes.push('animate-unlock-pulse');
  }

  return classes.join(' ');
};

/**
 * Экспорт всех утилит для удобного импорта
 */
export default {
  PROGRESS_COLORS,
  PROGRESS_HOVER_COLORS,
  getNodeColorByStatus,
  getNodeOpacity,
  formatProgressLabel,
  getNodeSize,
  animateProgressTransition,
  getCurrentLessonGlow,
  calculateOverallProgress,
  getStatusText,
  shouldPulse,
  getNodeAnimationClass,
};
