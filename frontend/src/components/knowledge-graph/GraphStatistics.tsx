/**
 * GraphStatistics Component
 * Отображение общей статистики прогресса над графом знаний
 * T703: Progress Visualization Integration
 */
import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Clock, CheckCircle2, PlayCircle, Lock, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { calculateOverallProgress, type ProgressData } from './progressUtils';

export interface GraphStatisticsProps {
  /** Данные прогресса для расчета статистики */
  progressData?: ProgressData;
  /** Общее время, потраченное на изучение (в минутах) */
  totalTimeSpent?: number;
  /** Дата последней активности (ISO string) */
  lastActivity?: string;
  /** CSS класс */
  className?: string;
  /** Компактный вид */
  compact?: boolean;
}

/**
 * Форматировать время в часы и минуты
 */
const formatTime = (minutes: number): string => {
  if (minutes < 60) {
    return `${minutes} мин`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours} ч ${mins} мин` : `${hours} ч`;
};

/**
 * Форматировать относительное время
 */
const formatRelativeTime = (isoDate: string): string => {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'только что';
  if (diffMins < 60) return `${diffMins} мин назад`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} ч назад`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'вчера';
  if (diffDays < 7) return `${diffDays} дн назад`;

  return date.toLocaleDateString('ru-RU');
};

/**
 * Компонент статистики прогресса
 */
export const GraphStatistics: React.FC<GraphStatisticsProps> = ({
  progressData,
  totalTimeSpent,
  lastActivity,
  className = '',
  compact = false,
}) => {
  // Если нет данных, не показываем компонент
  if (!progressData) {
    return null;
  }

  const stats = calculateOverallProgress(progressData);
  const completionPercentage = Math.round(stats.averageCompletion);

  if (compact) {
    return (
      <Card className={cn('p-3', className)}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium">Прогресс</span>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-xs">
              {stats.completedLessons} / {stats.totalLessons}
            </Badge>
            <div className="w-16">
              <Progress value={completionPercentage} className="h-2" />
            </div>
            <span className="text-sm font-semibold text-gray-700 min-w-[40px]">
              {completionPercentage}%
            </span>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-4', className)}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Общая статистика</h3>
        <Badge variant="outline" className="text-sm">
          {completionPercentage}% завершено
        </Badge>
      </div>

      {/* Прогресс-бар */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Общее завершение</span>
          <span className="text-sm font-semibold text-gray-900">
            {completionPercentage}%
          </span>
        </div>
        <Progress value={completionPercentage} className="h-3" />
      </div>

      {/* Карточки со статистикой */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Завершено уроков */}
        <div className="flex flex-col gap-1 p-3 bg-green-50 rounded-lg border border-green-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="text-xs text-green-700 font-medium">Завершено</span>
          </div>
          <div className="text-2xl font-bold text-green-900">
            {stats.completedLessons}
          </div>
          <div className="text-xs text-green-600">
            из {stats.totalLessons} уроков
          </div>
        </div>

        {/* В процессе */}
        <div className="flex flex-col gap-1 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2">
            <PlayCircle className="h-4 w-4 text-blue-600" />
            <span className="text-xs text-blue-700 font-medium">В процессе</span>
          </div>
          <div className="text-2xl font-bold text-blue-900">
            {stats.inProgressLessons}
          </div>
          <div className="text-xs text-blue-600">
            {stats.inProgressLessons === 1 ? 'урок' : 'уроков'}
          </div>
        </div>

        {/* Не начато */}
        <div className="flex flex-col gap-1 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-slate-600" />
            <span className="text-xs text-slate-700 font-medium">Не начато</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats.notStartedLessons}
          </div>
          <div className="text-xs text-slate-600">
            {stats.notStartedLessons === 1 ? 'урок' : 'уроков'}
          </div>
        </div>

        {/* Время или последняя активность */}
        <div className="flex flex-col gap-1 p-3 bg-amber-50 rounded-lg border border-amber-200">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-amber-600" />
            <span className="text-xs text-amber-700 font-medium">
              {totalTimeSpent !== undefined ? 'Время' : 'Активность'}
            </span>
          </div>
          <div className="text-2xl font-bold text-amber-900">
            {totalTimeSpent !== undefined
              ? formatTime(totalTimeSpent).split(' ')[0]
              : '—'}
          </div>
          <div className="text-xs text-amber-600">
            {totalTimeSpent !== undefined
              ? formatTime(totalTimeSpent).split(' ').slice(1).join(' ')
              : lastActivity
              ? formatRelativeTime(lastActivity)
              : 'нет данных'}
          </div>
        </div>
      </div>

      {/* Дополнительная информация */}
      {lastActivity && totalTimeSpent !== undefined && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Последняя активность:</span>
            <span className="font-medium">{formatRelativeTime(lastActivity)}</span>
          </div>
        </div>
      )}
    </Card>
  );
};

/**
 * Компактная версия статистики (одна строка)
 */
export const GraphStatisticsCompact: React.FC<
  Omit<GraphStatisticsProps, 'compact'>
> = (props) => {
  return <GraphStatistics {...props} compact={true} />;
};

export default GraphStatistics;
