/**
 * ProgressHistoryChart - Компонент истории прогресса
 * Отображает график изменения прогресса во времени
 *
 * Features:
 * - Line chart showing progress over time
 * - Simple SVG-based implementation (no external chart library)
 * - Responsive sizing
 * - Hover tooltips
 * - Time-based X-axis
 * - Loading state
 * - Empty state
 * - Responsive design
 */

import React, { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { AlertCircle, Loader2 } from "lucide-react";

export interface ProgressHistoryEntry {
  /** Timestamp (ISO string or Date) */
  timestamp: string | Date;

  /** Progress percentage (0-100) */
  progress: number;

  /** Optional: time spent in minutes */
  timeSpent?: number;

  /** Optional: notes/milestone */
  note?: string;
}

export interface ProgressHistoryChartProps {
  /** Array of progress history entries */
  data: ProgressHistoryEntry[];

  /** Loading state */
  isLoading?: boolean;

  /** Error message */
  error?: string | null;

  /** Callback for retry */
  onRetry?: () => void;

  /** Chart height in pixels (default: 300) */
  height?: number;

  /** Show tooltip (default: true) */
  showTooltip?: boolean;

  /** Show grid (default: true) */
  showGrid?: boolean;

  /** Additional CSS classes */
  className?: string;

  /** Empty state message */
  emptyMessage?: string;
}

/**
 * Format date for display
 */
function formatDateShort(dateString: string | Date): string {
  const date = typeof dateString === "string" ? new Date(dateString) : dateString;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * Custom tooltip component
 */
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload;
    return (
      <div className="rounded-lg border border-border bg-card p-3 shadow-lg">
        <p className="text-sm font-medium text-foreground">
          Progress: {data.progress}%
        </p>
        <p className="text-xs text-muted-foreground">
          {formatDateShort(data.timestamp)}
        </p>
        {data.timeSpent && (
          <p className="text-xs text-muted-foreground">
            Time: {Math.floor(data.timeSpent / 60)}h {data.timeSpent % 60}m
          </p>
        )}
        {data.note && (
          <p className="text-xs text-muted-foreground">{data.note}</p>
        )}
      </div>
    );
  }
  return null;
};

/**
 * ProgressHistoryChart Component
 *
 * Usage:
 * ```tsx
 * <ProgressHistoryChart
 *   data={[
 *     { timestamp: "2024-12-25T10:00:00Z", progress: 25 },
 *     { timestamp: "2024-12-26T14:30:00Z", progress: 50 },
 *     { timestamp: "2024-12-27T16:45:00Z", progress: 75 },
 *   ]}
 *   height={300}
 * />
 * ```
 */
export const ProgressHistoryChart = React.forwardRef<
  HTMLDivElement,
  ProgressHistoryChartProps
>(
  (
    {
      data,
      isLoading = false,
      error = null,
      onRetry,
      height = 300,
      showTooltip = true,
      showGrid = true,
      className,
      emptyMessage = "No progress history yet",
    },
    ref,
  ) => {
    // Sort data by timestamp
    const sortedData = useMemo(() => {
      return [...data].sort((a, b) => {
        const dateA = new Date(a.timestamp).getTime();
        const dateB = new Date(b.timestamp).getTime();
        return dateA - dateB;
      });
    }, [data]);

    // Format data for recharts
    const chartData = useMemo(() => {
      return sortedData.map((entry) => ({
        timestamp: entry.timestamp,
        progress: entry.progress,
        timeSpent: entry.timeSpent || 0,
        note: entry.note,
        displayDate: formatDateShort(entry.timestamp),
      }));
    }, [sortedData]);

    // Loading state
    if (isLoading) {
      return (
        <div
          ref={ref}
          className={cn(
            "flex items-center justify-center rounded-lg border border-border bg-card p-8",
            className,
          )}
          style={{ height: `${height}px` }}
          role="status"
          aria-label="Loading progress history"
        >
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading history...</p>
          </div>
        </div>
      );
    }

    // Error state
    if (error) {
      return (
        <div
          ref={ref}
          className={cn(
            "flex items-center justify-between rounded-lg border-2 border-red-200 bg-red-50 p-4",
            className,
          )}
          role="alert"
        >
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <div>
              <p className="font-semibold text-red-900">Error</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="rounded bg-red-600 px-3 py-1 text-sm font-medium text-white hover:bg-red-700"
              aria-label="Retry loading progress history"
            >
              Retry
            </button>
          )}
        </div>
      );
    }

    // Empty state
    if (chartData.length === 0) {
      return (
        <div
          ref={ref}
          className={cn(
            "flex items-center justify-center rounded-lg border border-dashed border-border bg-muted/50 p-8",
            className,
          )}
          style={{ height: `${height}px` }}
          aria-label="Empty progress history"
        >
          <p className="text-muted-foreground">{emptyMessage}</p>
        </div>
      );
    }

    return (
      <div ref={ref} className={cn("rounded-lg border border-border bg-card p-4", className)}>
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-foreground">Progress History</h3>
          <p className="text-xs text-muted-foreground">
            {chartData.length} check-in{chartData.length !== 1 ? "s" : ""}
          </p>
        </div>

        <ResponsiveContainer width="100%" height={height}>
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 10, left: 0, bottom: 25 }}
          >
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}

            <XAxis
              dataKey="displayDate"
              stroke="#9ca3af"
              style={{ fontSize: "12px" }}
              tick={{ fill: "#6b7280" }}
            />

            <YAxis
              domain={[0, 100]}
              stroke="#9ca3af"
              style={{ fontSize: "12px" }}
              tick={{ fill: "#6b7280" }}
              label={{ value: "Progress (%)", angle: -90, position: "insideLeft" }}
            />

            {showTooltip && <Tooltip content={<CustomTooltip />} />}

            <Line
              type="monotone"
              dataKey="progress"
              stroke="#3b82f6"
              dot={{ fill: "#3b82f6", r: 4 }}
              activeDot={{ r: 6, fill: "#1e40af" }}
              strokeWidth={2}
              isAnimationActive={true}
              animationDuration={600}
              name="Progress"
            />
          </LineChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="mt-4 flex items-center gap-4 border-t border-border pt-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-blue-500"></div>
            <span className="text-muted-foreground">Progress over time</span>
          </div>
        </div>
      </div>
    );
  },
);

ProgressHistoryChart.displayName = "ProgressHistoryChart";
