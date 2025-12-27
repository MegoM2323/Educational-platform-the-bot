/**
 * CircularProgressIndicator - Компонент круговой шкалы прогресса
 * Отображает прогресс в виде кольца с анимацией
 *
 * Features:
 * - SVG-based circular progress (no libraries)
 * - Color coding based on progress percentage
 * - Animated fill transition
 * - Configurable size
 * - Status indicator (not started, in progress, completed)
 * - Optional percentage text in center
 * - ARIA labels for accessibility
 */

import React, { useMemo } from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, Clock, AlertCircle } from "lucide-react";

export type ProgressStatus = "not_started" | "in_progress" | "completed";

export interface CircularProgressIndicatorProps {
  /** Progress percentage (0-100) */
  progress: number;

  /** Status indicator */
  status: ProgressStatus;

  /** Size in pixels (default: 120) */
  size?: number;

  /** Stroke width in pixels (default: 8) */
  strokeWidth?: number;

  /** Show percentage text in center (default: true) */
  showLabel?: boolean;

  /** Additional CSS classes */
  className?: string;

  /** Aria-label for accessibility */
  ariaLabel?: string;
}

/**
 * Get color based on progress percentage
 */
function getProgressColor(progress: number): string {
  if (progress === 0) return "#e5e7eb"; // Gray for not started
  if (progress < 50) return "#fbbf24"; // Amber for in progress (1-50%)
  if (progress < 100) return "#10b981"; // Green for almost done (51-99%)
  return "#3b82f6"; // Blue for completed
}

/**
 * Get status icon color
 */
function getStatusIconColor(status: ProgressStatus): string {
  switch (status) {
    case "not_started":
      return "text-gray-400";
    case "in_progress":
      return "text-blue-500";
    case "completed":
      return "text-green-500";
  }
}

/**
 * Get status icon
 */
function StatusIcon({
  status,
  size = 24,
}: {
  status: ProgressStatus;
  size?: number;
}): JSX.Element {
  const iconSize = size;
  const color = getStatusIconColor(status);

  switch (status) {
    case "not_started":
      return <AlertCircle size={iconSize} className={color} />;
    case "in_progress":
      return <Clock size={iconSize} className={color} />;
    case "completed":
      return <CheckCircle2 size={iconSize} className={color} />;
  }
}

/**
 * CircularProgressIndicator Component
 *
 * Usage:
 * ```tsx
 * <CircularProgressIndicator
 *   progress={65}
 *   status="in_progress"
 *   size={140}
 *   showLabel={true}
 * />
 * ```
 */
export const CircularProgressIndicator = React.forwardRef<
  SVGSVGElement,
  CircularProgressIndicatorProps
>(
  (
    {
      progress,
      status,
      size = 120,
      strokeWidth = 8,
      showLabel = true,
      className,
      ariaLabel,
    },
    ref,
  ) => {
    // Clamp progress between 0 and 100
    const displayProgress = useMemo(
      () => Math.min(Math.max(progress, 0), 100),
      [progress],
    );

    // Calculate SVG dimensions
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (displayProgress / 100) * circumference;

    // Get progress color
    const progressColor = useMemo(
      () => getProgressColor(displayProgress),
      [displayProgress],
    );

    return (
      <div className={cn("flex flex-col items-center gap-2", className)}>
        {/* SVG Circular Progress */}
        <div className="relative">
          <svg
            ref={ref}
            width={size}
            height={size}
            className="transform -rotate-90"
            role="progressbar"
            aria-valuenow={displayProgress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={
              ariaLabel ||
              `Progress: ${displayProgress}% (${status.replace("_", " ")})`
            }
          >
            {/* Background circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#f3f4f6"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />

            {/* Progress circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={progressColor}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-500 ease-out"
            />
          </svg>

          {/* Center content (percentage or status icon) */}
          <div className="absolute inset-0 flex items-center justify-center">
            {showLabel ? (
              <div className="flex flex-col items-center gap-1">
                <span className="text-lg font-bold text-foreground">
                  {displayProgress}%
                </span>
                <span className="text-xs text-muted-foreground">
                  {displayProgress === 100 ? "Done" : "Progress"}
                </span>
              </div>
            ) : (
              <StatusIcon status={status} size={size * 0.4} />
            )}
          </div>
        </div>

        {/* Status indicator below circle */}
        <div className="flex items-center gap-1.5">
          <StatusIcon status={status} size={16} />
          <span className="text-xs font-medium text-muted-foreground capitalize">
            {status.replace("_", " ")}
          </span>
        </div>
      </div>
    );
  },
);

CircularProgressIndicator.displayName = "CircularProgressIndicator";

/**
 * CompactCircularProgress - Smaller version for list items
 */
export const CompactCircularProgress = React.forwardRef<
  SVGSVGElement,
  Omit<CircularProgressIndicatorProps, "size" | "strokeWidth">
>(({ progress, status, showLabel = false, className, ariaLabel }, ref) => {
  return (
    <CircularProgressIndicator
      ref={ref}
      progress={progress}
      status={status}
      size={60}
      strokeWidth={4}
      showLabel={showLabel}
      className={cn("", className)}
      ariaLabel={ariaLabel}
    />
  );
});

CompactCircularProgress.displayName = "CompactCircularProgress";
