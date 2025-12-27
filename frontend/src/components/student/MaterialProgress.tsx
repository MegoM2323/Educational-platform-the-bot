/**
 * MaterialProgress - Компонент отслеживания прогресса материала
 * Отображает прогресс, статус, время изучения и оценки учащегося
 *
 * Features:
 * - Progress bar (0-100%) с цветовой кодировкой
 * - Status indicators: Not Started, In Progress, Completed
 * - Time spent tracking
 * - Last accessed timestamp
 * - Score/grade display
 * - Next milestone highlight
 * - Responsive design (mobile, tablet, desktop)
 * - ARIA labels for accessibility
 * - Keyboard navigation support
 * - Loading state with skeleton
 * - Error handling with retry
 */

import React, { useState, useCallback, useMemo } from "react";
import { Clock, CheckCircle2, AlertCircle, RotateCcw } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type ProgressStatus = "not_started" | "in_progress" | "completed";

export interface MaterialProgressProps {
  /** Информация о материале */
  material: {
    id: number | string;
    title: string;
    description?: string;
  };

  /** Процент прогресса (0-100) */
  progress: number;

  /** Статус выполнения */
  status: ProgressStatus;

  /** Время, потраченное на материал (в минутах) */
  timeSpent?: number;

  /** Последний доступ (ISO string или Date) */
  lastAccessed?: string | Date;

  /** Оценка (0-100) */
  score?: number;

  /** Максимальная оценка */
  maxScore?: number;

  /** Следующая веха прогресса (%) */
  nextMilestone?: number;

  /** Состояние загрузки */
  isLoading?: boolean;

  /** Состояние ошибки */
  error?: string | null;

  /** Callback для повторной загрузки */
  onRetry?: () => void;

  /** Дополнительные CSS классы */
  className?: string;

  /** Обработчик клика на компонент */
  onClick?: () => void;

  /** Aria-label для доступности */
  ariaLabel?: string;
}

/**
 * Форматирует время в человеческий формат
 * @example "2 hours ago", "5 minutes ago"
 */
function formatTimeAgo(dateString: string | Date | undefined): string {
  if (!dateString) return "Never";

  const date = typeof dateString === "string" ? new Date(dateString) : dateString;
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
  return date.toLocaleDateString();
}

/**
 * Форматирует время, потраченное на материал
 * @example "45 minutes", "2 hours 30 minutes"
 */
function formatTimeSpent(minutes?: number): string {
  if (!minutes || minutes === 0) return "Not started";
  if (minutes < 60) return `${minutes} minute${minutes !== 1 ? "s" : ""}`;

  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (mins === 0) return `${hours} hour${hours !== 1 ? "s" : ""}`;
  return `${hours}h ${mins}m`;
}

/**
 * Получает цвет прогресс-бара в зависимости от процента
 */
function getProgressColor(progress: number): string {
  if (progress === 0) return "bg-gray-300"; // Not started
  if (progress < 50) return "bg-yellow-400"; // In progress (1-50%)
  if (progress < 100) return "bg-green-500"; // Almost done (51-99%)
  return "bg-blue-500"; // Completed
}

/**
 * Получает текст статуса на русском
 */
function getStatusLabel(status: ProgressStatus): string {
  const labels = {
    not_started: "Not Started",
    in_progress: "In Progress",
    completed: "Completed",
  };
  return labels[status];
}

/**
 * Получает иконку для статуса
 */
function StatusIcon({
  status,
  className = "w-5 h-5",
}: {
  status: ProgressStatus;
  className?: string;
}): JSX.Element {
  switch (status) {
    case "not_started":
      return <AlertCircle className={cn("text-gray-400", className)} />;
    case "in_progress":
      return <Clock className={cn("text-blue-500", className)} />;
    case "completed":
      return <CheckCircle2 className={cn("text-green-500", className)} />;
  }
}

/**
 * Skeleton loading component для MaterialProgress
 */
function MaterialProgressSkeleton(): JSX.Element {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-2 w-full" />
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
      <Skeleton className="h-10 w-full" />
    </div>
  );
}

/**
 * MaterialProgress Component
 *
 * Основной компонент для отслеживания прогресса материала
 *
 * Usage:
 * ```tsx
 * <MaterialProgress
 *   material={{ id: 1, title: "Algebra Basics" }}
 *   progress={65}
 *   status="in_progress"
 *   timeSpent={45}
 *   lastAccessed="2024-12-27T10:30:00Z"
 *   score={78}
 *   maxScore={100}
 *   nextMilestone={75}
 * />
 * ```
 */
export const MaterialProgress = React.forwardRef<
  HTMLDivElement,
  MaterialProgressProps
>(
  (
    {
      material,
      progress,
      status,
      timeSpent,
      lastAccessed,
      score,
      maxScore,
      nextMilestone,
      isLoading = false,
      error = null,
      onRetry,
      className,
      onClick,
      ariaLabel,
    },
    ref,
  ) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Memoized calculations
    const displayProgress = useMemo(() => Math.min(Math.max(progress, 0), 100), [progress]);

    const formattedTimeAgo = useMemo(
      () => formatTimeAgo(lastAccessed),
      [lastAccessed],
    );

    const formattedTimeSpent = useMemo(
      () => formatTimeSpent(timeSpent),
      [timeSpent],
    );

    const scorePercentage = useMemo(() => {
      if (!score || !maxScore) return null;
      return Math.round((score / maxScore) * 100);
    }, [score, maxScore]);

    // Progress bar color
    const progressColor = useMemo(
      () => getProgressColor(displayProgress),
      [displayProgress],
    );

    // Determine milestone message
    const milestoneMessage = useMemo(() => {
      if (!nextMilestone) return null;
      const remaining = nextMilestone - displayProgress;
      if (remaining <= 0) return "🎉 Next milestone reached!";
      return `${remaining}% to next milestone`;
    }, [nextMilestone, displayProgress]);

    // Handle retry
    const handleRetry = useCallback(() => {
      if (onRetry) onRetry();
    }, [onRetry]);

    // Loading state
    if (isLoading) {
      return (
        <div
          ref={ref}
          className={cn(
            "rounded-lg border border-border bg-card p-4",
            className,
          )}
          role="status"
          aria-label={ariaLabel || "Loading material progress"}
          aria-busy="true"
        >
          <MaterialProgressSkeleton />
        </div>
      );
    }

    // Error state
    if (error) {
      return (
        <div
          ref={ref}
          className={cn(
            "rounded-lg border-2 border-red-200 bg-red-50 p-4",
            className,
          )}
          role="alert"
          aria-label={ariaLabel || "Error loading material progress"}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-500" />
              <div>
                <p className="font-semibold text-red-900">Error</p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRetry}
                className="flex items-center gap-2"
                aria-label="Retry loading material progress"
              >
                <RotateCcw className="h-4 w-4" />
                Retry
              </Button>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          "group rounded-lg border border-border bg-card transition-colors hover:bg-muted/50",
          isExpanded && "ring-2 ring-primary ring-offset-2",
          className,
        )}
        onClick={onClick}
        role="region"
        aria-label={
          ariaLabel ||
          `${material.title} progress: ${displayProgress}%, status: ${getStatusLabel(status)}`
        }
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        {/* Header: Material Title + Status */}
        <div className="flex items-start justify-between p-4">
          <div className="flex-1">
            <h3 className="font-semibold text-foreground">{material.title}</h3>
            {material.description && (
              <p className="mt-1 text-sm text-muted-foreground">
                {material.description}
              </p>
            )}
          </div>

          {/* Status Icon */}
          <div
            className="ml-3 flex items-center gap-2"
            aria-label={`Status: ${getStatusLabel(status)}`}
          >
            <StatusIcon status={status} />
            <span className="text-xs font-medium text-muted-foreground">
              {getStatusLabel(status)}
            </span>
          </div>
        </div>

        {/* Progress Bar with Percentage */}
        <div className="space-y-2 px-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              Progress
            </span>
            <span
              className="text-sm font-semibold text-foreground"
              aria-label={`${displayProgress} percent progress`}
            >
              {displayProgress}%
            </span>
          </div>

          {/* Custom Progress Bar with Color Coding */}
          <div
            className="relative h-2 w-full overflow-hidden rounded-full bg-secondary"
            role="progressbar"
            aria-valuenow={displayProgress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Progress: ${displayProgress}%`}
          >
            <div
              className={cn("h-full transition-all duration-500", progressColor)}
              style={{ width: `${displayProgress}%` }}
            />

            {/* Next Milestone Indicator */}
            {nextMilestone && nextMilestone > displayProgress && (
              <div
                className="absolute h-full w-0.5 bg-primary opacity-75"
                style={{ left: `${nextMilestone}%` }}
                aria-hidden="true"
                title={`Next milestone: ${nextMilestone}%`}
              />
            )}
          </div>

          {/* Milestone Message */}
          {milestoneMessage && (
            <p
              className={cn(
                "text-xs font-medium",
                displayProgress >= nextMilestone!
                  ? "text-green-600"
                  : "text-amber-600",
              )}
            >
              {milestoneMessage}
            </p>
          )}
        </div>

        {/* Responsive Grid: Time Spent + Last Accessed + Score */}
        <div
          className={cn(
            "grid gap-3 border-t border-border px-4 py-3",
            "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
          )}
        >
          {/* Time Spent */}
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">
              Time Spent
            </p>
            <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Clock className="h-4 w-4 text-blue-500" />
              {formattedTimeSpent}
            </p>
          </div>

          {/* Last Accessed */}
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">
              Last Accessed
            </p>
            <p className="text-sm font-semibold text-foreground">
              {formattedTimeAgo}
            </p>
          </div>

          {/* Score Display (if available) */}
          {score !== undefined && maxScore !== undefined && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Score</p>
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-foreground">
                  {score}/{maxScore}
                </p>
                {scorePercentage !== null && (
                  <span
                    className={cn(
                      "rounded px-2 py-0.5 text-xs font-bold",
                      scorePercentage >= 80 && "bg-green-100 text-green-700",
                      scorePercentage >= 60 &&
                        scorePercentage < 80 &&
                        "bg-yellow-100 text-yellow-700",
                      scorePercentage < 60 && "bg-red-100 text-red-700",
                    )}
                  >
                    {scorePercentage}%
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Expandable Details Section */}
        {isExpanded && (
          <div className="border-t border-border bg-muted/30 px-4 py-3">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Material ID:</span>
                <span className="font-mono text-xs font-medium">
                  {material.id}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Status:</span>
                <span className="font-medium capitalize">{status}</span>
              </div>
            </div>
          </div>
        )}

        {/* Expand Button */}
        <div className="border-t border-border px-4 py-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="w-full py-2 text-center text-xs font-medium text-primary hover:text-primary/80"
            aria-expanded={isExpanded}
            aria-label={`${isExpanded ? "Hide" : "Show"} details`}
          >
            {isExpanded ? "Hide Details" : "Show Details"}
          </button>
        </div>
      </div>
    );
  },
);

MaterialProgress.displayName = "MaterialProgress";

/**
 * MaterialProgressList - Компонент для отображения списка прогресса материалов
 *
 * Usage:
 * ```tsx
 * <MaterialProgressList
 *   materials={[
 *     { material: { id: 1, title: "Algebra" }, progress: 65, status: "in_progress" },
 *     { material: { id: 2, title: "Geometry" }, progress: 100, status: "completed" },
 *   ]}
 * />
 * ```
 */
export interface MaterialProgressListProps {
  /** Array of material progress items */
  materials: MaterialProgressProps[];

  /** Loading state */
  isLoading?: boolean;

  /** Error message */
  error?: string | null;

  /** Callback for retry */
  onRetry?: () => void;

  /** Empty state message */
  emptyMessage?: string;

  /** CSS classname */
  className?: string;
}

export const MaterialProgressList = React.forwardRef<
  HTMLDivElement,
  MaterialProgressListProps
>(
  (
    {
      materials,
      isLoading = false,
      error = null,
      onRetry,
      emptyMessage = "No materials found",
      className,
    },
    ref,
  ) => {
    if (isLoading) {
      return (
        <div className={cn("space-y-4", className)}>
          {Array.from({ length: 3 }).map((_, i) => (
            <MaterialProgressSkeleton key={i} />
          ))}
        </div>
      );
    }

    if (error) {
      return (
        <div
          className={cn(
            "rounded-lg border-2 border-red-200 bg-red-50 p-4",
            className,
          )}
          role="alert"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-500" />
              <div>
                <p className="font-semibold text-red-900">Error</p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="flex items-center gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Retry
              </Button>
            )}
          </div>
        </div>
      );
    }

    if (materials.length === 0) {
      return (
        <div
          className={cn(
            "rounded-lg border border-dashed border-border bg-muted/50 py-12 text-center",
            className,
          )}
        >
          <p className="text-muted-foreground">{emptyMessage}</p>
        </div>
      );
    }

    return (
      <div ref={ref} className={cn("space-y-4", className)}>
        {materials.map((item, index) => (
          <MaterialProgress
            key={`${item.material.id}-${index}`}
            {...item}
          />
        ))}
      </div>
    );
  },
);

MaterialProgressList.displayName = "MaterialProgressList";
