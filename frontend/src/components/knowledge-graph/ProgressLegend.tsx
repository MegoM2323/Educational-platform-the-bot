/**
 * ProgressLegend Component
 * Легенда для отображения статусов прогресса в графе знаний
 * T703: Progress Visualization Integration
 */
import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  PROGRESS_COLORS,
  getStatusText,
  type ProgressStatus,
  calculateOverallProgress,
  type ProgressData,
} from './progressUtils';

export interface ProgressLegendProps {
  /** Данные прогресса для расчета статистики */
  progressData?: ProgressData;
  /** Показывать ли легенду */
  visible?: boolean;
  /** Callback при изменении видимости */
  onVisibilityChange?: (visible: boolean) => void;
  /** Позиция легенды */
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  /** Показывать ли статистику */
  showStats?: boolean;
  /** Разрешить сворачивание */
  collapsible?: boolean;
  /** CSS класс */
  className?: string;
}

/**
 * Компонент легенды прогресса
 */
export const ProgressLegend: React.FC<ProgressLegendProps> = ({
  progressData,
  visible = true,
  onVisibilityChange,
  position = 'bottom-left',
  showStats = true,
  collapsible = false,
  className = '',
}) => {
  const [isCollapsed, setIsCollapsed] = React.useState(false);

  if (!visible) return null;

  const statuses: ProgressStatus[] = ['not_started', 'in_progress', 'completed', 'locked'];

  // Расчет статистики если есть данные
  const stats = progressData ? calculateOverallProgress(progressData) : null;

  const positionClasses: Record<typeof position, string> = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4',
  };

  const handleClose = () => {
    onVisibilityChange?.(false);
  };

  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  return (
    <Card
      className={cn(
        'absolute z-10 bg-white/95 backdrop-blur-sm shadow-lg rounded-lg p-3 min-w-[200px]',
        positionClasses[position],
        className
      )}
    >
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-semibold text-gray-700">
          {showStats && stats ? 'Прогресс' : 'Статусы уроков'}
        </div>
        <div className="flex items-center gap-1">
          {collapsible && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0"
              onClick={handleToggleCollapse}
              title={isCollapsed ? 'Развернуть' : 'Свернуть'}
            >
              {isCollapsed ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
              )}
            </Button>
          )}
          {onVisibilityChange && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0"
              onClick={handleClose}
              title="Скрыть легенду"
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Статистика (если включена и есть данные) */}
          {showStats && stats && (
            <div className="mb-3 pb-2 border-b border-gray-200">
              <div className="text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Всего уроков:</span>
                  <Badge variant="outline" className="text-xs font-medium">
                    {stats.totalLessons}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Завершено:</span>
                  <Badge
                    variant="outline"
                    className="text-xs font-medium bg-green-50 text-green-700 border-green-200"
                  >
                    {stats.completedLessons}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">В процессе:</span>
                  <Badge
                    variant="outline"
                    className="text-xs font-medium bg-blue-50 text-blue-700 border-blue-200"
                  >
                    {stats.inProgressLessons}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Средний прогресс:</span>
                  <Badge variant="outline" className="text-xs font-medium">
                    {Math.round(stats.averageCompletion)}%
                  </Badge>
                </div>
              </div>
            </div>
          )}

          {/* Легенда статусов */}
          <div className="space-y-1.5">
            <div className="text-xs font-medium text-gray-600 mb-1">Статусы:</div>
            {statuses.map((status) => (
              <div key={status} className="flex items-center gap-2 text-xs">
                <div
                  className={cn(
                    'w-3 h-3 rounded-full flex-shrink-0',
                    status === 'locked' && 'opacity-50'
                  )}
                  style={{ backgroundColor: PROGRESS_COLORS[status] }}
                  aria-label={`Цвет статуса: ${getStatusText(status)}`}
                />
                <span className="text-gray-700">{getStatusText(status)}</span>
              </div>
            ))}
          </div>

          {/* Дополнительная информация */}
          <div className="mt-3 pt-2 border-t border-gray-200">
            <div className="text-xs text-gray-500 space-y-0.5">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span>Текущий урок</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-1">
                Кликните по узлу для деталей
              </div>
            </div>
          </div>
        </>
      )}
    </Card>
  );
};

/**
 * Компактная версия легенды (только цвета, без статистики)
 */
export const ProgressLegendCompact: React.FC<
  Omit<ProgressLegendProps, 'showStats' | 'collapsible'>
> = (props) => {
  return <ProgressLegend {...props} showStats={false} collapsible={false} />;
};

/**
 * Мобильная версия легенды (адаптивная позиция)
 */
export const ProgressLegendMobile: React.FC<
  Omit<ProgressLegendProps, 'position'>
> = (props) => {
  return (
    <div className="block sm:hidden">
      <ProgressLegend {...props} position="bottom-left" />
    </div>
  );
};

/**
 * Десктопная версия легенды
 */
export const ProgressLegendDesktop: React.FC<
  Omit<ProgressLegendProps, 'position'>
> = (props) => {
  return (
    <div className="hidden sm:block">
      <ProgressLegend {...props} position="bottom-right" />
    </div>
  );
};

export default ProgressLegend;
