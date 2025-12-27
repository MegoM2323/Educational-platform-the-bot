/**
 * MaterialProgressCard - Enhanced component with circular progress, history, and animations
 * Combines MaterialProgress, CircularProgressIndicator, and ProgressHistoryChart
 *
 * Features:
 * - Circular progress indicator
 * - Progress history chart
 * - Offline progress sync
 * - Completion animation
 * - Responsive layout
 * - Tab-based view switching
 */

import React, { useState, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { CircularProgressIndicator } from "./CircularProgressIndicator";
import { ProgressHistoryChart } from "./ProgressHistoryChart";
import { MaterialProgress, type MaterialProgressProps } from "./MaterialProgress";
import { useOfflineProgressSync } from "@/hooks/useOfflineProgressSync";
import { cn } from "@/lib/utils";
import { WifiOff, Cloud, CheckCircle2, RefreshCw } from "lucide-react";

export interface MaterialProgressCardProps extends MaterialProgressProps {
  /** Progress history data */
  historyData?: Array<{
    timestamp: string | Date;
    progress: number;
    timeSpent?: number;
    note?: string;
  }>;

  /** Show completion animation */
  showCompletionAnimation?: boolean;

  /** Callback when progress is updated */
  onProgressUpdated?: (progress: number) => void;

  /** Enable offline sync */
  enableOfflineSync?: boolean;

  /** Additional CSS classes */
  className?: string;
}

/**
 * Completion animation component
 */
const CompletionAnimation = ({ show }: { show: boolean }): JSX.Element | null => {
  if (!show) return null;

  return (
    <div className="pointer-events-none fixed inset-0 flex items-center justify-center">
      <div className="animate-bounce">
        <CheckCircle2 className="h-24 w-24 text-green-500" />
      </div>

      {/* Confetti effect simulation */}
      <div className="absolute inset-0 flex items-center justify-center">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="absolute h-2 w-2 rounded-full bg-green-400"
            style={{
              animation: `float ${2 + Math.random()}s ease-out forwards`,
              left: "50%",
              top: "50%",
              marginLeft: "-4px",
              marginTop: "-4px",
              transform: `rotate(${i * 30}deg) translateY(-100px)`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes float {
          0% {
            opacity: 1;
            transform: translateY(0) rotate(0deg);
          }
          100% {
            opacity: 0;
            transform: translateY(-100px) rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
};

/**
 * MaterialProgressCard Component
 *
 * Usage:
 * ```tsx
 * <MaterialProgressCard
 *   material={{ id: 1, title: "Algebra Basics" }}
 *   progress={75}
 *   status="in_progress"
 *   timeSpent={120}
 *   historyData={[
 *     { timestamp: "2024-12-25T10:00:00Z", progress: 25 },
 *     { timestamp: "2024-12-26T14:30:00Z", progress: 50 },
 *     { timestamp: "2024-12-27T16:45:00Z", progress: 75 },
 *   ]}
 *   enableOfflineSync={true}
 * />
 * ```
 */
export const MaterialProgressCard = React.forwardRef<
  HTMLDivElement,
  MaterialProgressCardProps
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
      onClick,
      className,
      historyData = [],
      showCompletionAnimation = true,
      onProgressUpdated,
      enableOfflineSync = true,
      ariaLabel,
    },
    ref,
  ) => {
    const [showAnimation, setShowAnimation] = useState(false);
    const { pendingUpdates, isOnline, isSyncing, syncError, syncNow } =
      useOfflineProgressSync();

    // Check if this is a completion (progress just reached 100%)
    React.useEffect(() => {
      if (showCompletionAnimation && progress === 100 && status === "completed") {
        setShowAnimation(true);
        const timer = setTimeout(() => setShowAnimation(false), 3000);
        return () => clearTimeout(timer);
      }
    }, [progress, status, showCompletionAnimation]);

    // Check for pending updates
    const hasPendingUpdates = useMemo(
      () => pendingUpdates.some((u) => u.materialId === material.id),
      [pendingUpdates, material.id],
    );

    const SyncButton = () => (
      <Button
        variant="outline"
        size="sm"
        onClick={syncNow}
        disabled={isSyncing || isOnline}
        className="flex items-center gap-2"
        aria-label="Sync offline progress"
      >
        {isOnline ? (
          <>
            <Cloud className="h-4 w-4 text-green-500" />
            Synced
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-amber-500" />
            {isSyncing ? "Syncing..." : "Sync"}
          </>
        )}
      </Button>
    );

    return (
      <div
        ref={ref}
        className={cn(
          "space-y-6 rounded-lg border border-border bg-card p-6",
          className,
        )}
        role="region"
        aria-label={ariaLabel || `${material.title} progress details`}
      >
        {/* Completion Animation */}
        <CompletionAnimation show={showAnimation} />

        {/* Offline Status + Sync Button */}
        {enableOfflineSync && !isOnline && (
          <div className="flex items-center justify-between rounded-lg bg-amber-50 p-3">
            <div className="flex items-center gap-2">
              <WifiOff className="h-4 w-4 text-amber-600" />
              <p className="text-sm text-amber-800">
                You're offline. Changes will sync when online.
              </p>
            </div>
            <SyncButton />
          </div>
        )}

        {/* Pending Updates Indicator */}
        {enableOfflineSync && hasPendingUpdates && isOnline && (
          <div className="flex items-center justify-between rounded-lg bg-blue-50 p-3">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
              <p className="text-sm text-blue-800">
                Syncing offline changes...
              </p>
            </div>
            {syncError && (
              <p className="text-xs text-red-600">{syncError}</p>
            )}
          </div>
        )}

        {/* Two-column layout: Circular Progress + Material Progress */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Left: Circular Progress */}
          <div className="flex justify-center">
            <CircularProgressIndicator
              progress={progress}
              status={status}
              size={160}
              strokeWidth={10}
              showLabel={true}
              ariaLabel={`Progress: ${progress}%, Status: ${status.replace("_", " ")}`}
            />
          </div>

          {/* Right: Material Progress Details */}
          <div>
            <MaterialProgress
              material={material}
              progress={progress}
              status={status}
              timeSpent={timeSpent}
              lastAccessed={lastAccessed}
              score={score}
              maxScore={maxScore}
              nextMilestone={nextMilestone}
              isLoading={isLoading}
              error={error}
              onRetry={onRetry}
              onClick={onClick}
            />
          </div>
        </div>

        {/* Tabs: Details and History */}
        <Tabs defaultValue="details" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="history">
              History {historyData.length > 0 && `(${historyData.length})`}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              {/* Progress Summary */}
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <h4 className="text-sm font-semibold text-foreground">Progress</h4>
                <p className="mt-2 text-2xl font-bold text-primary">
                  {progress}%
                </p>
                <p className="text-xs text-muted-foreground">
                  {status === "completed"
                    ? "Completed"
                    : `${100 - progress}% remaining`}
                </p>
              </div>

              {/* Time Spent Summary */}
              {timeSpent !== undefined && (
                <div className="rounded-lg border border-border bg-muted/50 p-4">
                  <h4 className="text-sm font-semibold text-foreground">Time Spent</h4>
                  <p className="mt-2 text-2xl font-bold text-primary">
                    {Math.floor(timeSpent / 60)}h {timeSpent % 60}m
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {timeSpent} minutes total
                  </p>
                </div>
              )}

              {/* Score Summary */}
              {score !== undefined && maxScore !== undefined && (
                <div className="rounded-lg border border-border bg-muted/50 p-4">
                  <h4 className="text-sm font-semibold text-foreground">Score</h4>
                  <p className="mt-2 text-2xl font-bold text-primary">
                    {score}/{maxScore}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {Math.round((score / maxScore) * 100)}%
                  </p>
                </div>
              )}

              {/* Last Accessed Summary */}
              {lastAccessed && (
                <div className="rounded-lg border border-border bg-muted/50 p-4">
                  <h4 className="text-sm font-semibold text-foreground">
                    Last Accessed
                  </h4>
                  <p className="mt-2 text-sm font-medium text-primary">
                    {new Date(lastAccessed).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(lastAccessed).toLocaleTimeString()}
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="history">
            <ProgressHistoryChart
              data={historyData}
              isLoading={isLoading}
              error={error}
              onRetry={onRetry}
              height={300}
              emptyMessage="No progress history yet. Keep learning!"
            />
          </TabsContent>
        </Tabs>

        {/* Offline Sync Status */}
        {enableOfflineSync && (
          <div className="border-t border-border pt-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                {isOnline ? (
                  <span className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-green-500"></div>
                    Online
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500"></div>
                    Offline Mode
                  </span>
                )}
              </div>
              {!isOnline && hasPendingUpdates && (
                <SyncButton />
              )}
            </div>
          </div>
        )}
      </div>
    );
  },
);

MaterialProgressCard.displayName = "MaterialProgressCard";
