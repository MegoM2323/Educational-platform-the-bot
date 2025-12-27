import React, { useMemo } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// SPINNER COMPONENT
// ============================================================================

interface SpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  ariaLabel?: string;
}

const sizeMap = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-10 h-10',
};

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  className,
  ariaLabel = 'Loading...'
}) => {
  return (
    <div
      role="status"
      aria-label={ariaLabel}
      aria-live="polite"
      className="flex items-center justify-center"
    >
      <Loader2
        className={cn('animate-spin', sizeMap[size], className)}
        aria-hidden="true"
      />
    </div>
  );
};

// ============================================================================
// LOADING STATE COMPONENT
// ============================================================================

interface LoadingStateProps {
  isLoading: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  text?: string;
  fullHeight?: boolean;
  className?: string;
  ariaLabel?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  isLoading,
  size = 'md',
  text,
  fullHeight = false,
  className,
  ariaLabel = 'Loading content...'
}) => {
  if (!isLoading) return null;

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3',
        fullHeight && 'h-screen',
        className
      )}
      role="status"
      aria-label={ariaLabel}
      aria-live="polite"
    >
      <Spinner size={size} ariaLabel={ariaLabel} />
      {text && <p className="text-sm text-muted-foreground">{text}</p>}
    </div>
  );
};

// ============================================================================
// SKELETON LOADER COMPONENTS
// ============================================================================

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  animated?: boolean;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  animated = true,
  ...props
}) => {
  return (
    <div
      className={cn(
        'rounded-md bg-muted',
        animated && 'animate-pulse',
        className
      )}
      aria-hidden="true"
      {...props}
    />
  );
};

// ============================================================================
// SKELETON LOADERS FOR DIFFERENT CONTENT TYPES
// ============================================================================

interface SkeletonLoaderProps {
  className?: string;
}

/**
 * TextLineSkeleton - Shows loading for a single text line
 * Used for headings, labels, or short text content
 */
export const TextLineSkeleton: React.FC<SkeletonLoaderProps> = ({ className }) => {
  return (
    <Skeleton
      className={cn('h-4 w-full', className)}
      role="status"
      aria-label="Loading text..."
    />
  );
};

/**
 * ParagraphSkeleton - Shows loading for multiple text lines (paragraph)
 */
interface ParagraphSkeletonProps extends SkeletonLoaderProps {
  lines?: number;
  lastLineWidth?: 'full' | '3/4' | '2/3' | '1/2';
}

export const ParagraphSkeleton: React.FC<ParagraphSkeletonProps> = ({
  className,
  lines = 3,
  lastLineWidth = '2/3'
}) => {
  const widthMap = {
    full: 'w-full',
    '3/4': 'w-3/4',
    '2/3': 'w-2/3',
    '1/2': 'w-1/2',
  };

  return (
    <div
      className={cn('space-y-2', className)}
      role="status"
      aria-label="Loading paragraph..."
    >
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 ? widthMap[lastLineWidth] : 'w-full'
          )}
        />
      ))}
    </div>
  );
};

/**
 * CardSkeleton - Shows loading for a card component
 */
interface CardSkeletonProps extends SkeletonLoaderProps {
  hasHeader?: boolean;
  hasImage?: boolean;
}

export const CardSkeleton: React.FC<CardSkeletonProps> = ({
  className,
  hasHeader = false,
  hasImage = false
}) => {
  return (
    <div
      className={cn('rounded-lg border border-border p-4', className)}
      role="status"
      aria-label="Loading card..."
    >
      {hasImage && (
        <Skeleton className="h-40 w-full rounded-lg mb-4" />
      )}
      {hasHeader && (
        <Skeleton className="h-6 w-2/3 mb-4" />
      )}
      <ParagraphSkeleton lines={2} />
    </div>
  );
};

/**
 * TableSkeleton - Shows loading for a table with rows and columns
 */
interface TableSkeletonProps extends SkeletonLoaderProps {
  rows?: number;
  columns?: number;
}

export const TableSkeleton: React.FC<TableSkeletonProps> = ({
  className,
  rows = 5,
  columns = 4
}) => {
  return (
    <div
      className={cn('w-full', className)}
      role="status"
      aria-label="Loading table..."
    >
      {/* Table header */}
      <div className="flex gap-3 p-4 border-b">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton
            key={`header-${i}`}
            className="h-4 flex-1"
          />
        ))}
      </div>

      {/* Table rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={`row-${rowIdx}`} className="flex gap-3 p-4 border-b">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton
              key={`cell-${rowIdx}-${colIdx}`}
              className="h-4 flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  );
};

/**
 * ListSkeleton - Shows loading for a list of items
 */
interface ListSkeletonProps extends SkeletonLoaderProps {
  count?: number;
  hasAvatar?: boolean;
}

export const ListSkeleton: React.FC<ListSkeletonProps> = ({
  className,
  count = 4,
  hasAvatar = false
}) => {
  return (
    <div
      className={cn('space-y-3', className)}
      role="status"
      aria-label="Loading list..."
    >
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex gap-3 p-3 rounded-lg border">
          {hasAvatar && (
            <Skeleton className="w-10 h-10 rounded-full flex-shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
};

/**
 * FormSkeleton - Shows loading for a form with input fields
 */
interface FormSkeletonProps extends SkeletonLoaderProps {
  fields?: number;
}

export const FormSkeleton: React.FC<FormSkeletonProps> = ({
  className,
  fields = 3
}) => {
  return (
    <div
      className={cn('space-y-4', className)}
      role="status"
      aria-label="Loading form..."
    >
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i}>
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-10 w-full rounded-md" />
        </div>
      ))}
    </div>
  );
};

/**
 * GridSkeleton - Shows loading for a grid of items
 */
interface GridSkeletonProps extends SkeletonLoaderProps {
  count?: number;
  columns?: number;
  aspectRatio?: 'square' | 'video' | '3/4';
}

export const GridSkeleton: React.FC<GridSkeletonProps> = ({
  className,
  count = 6,
  columns = 3,
  aspectRatio = 'square'
}) => {
  const aspectMap = {
    square: 'aspect-square',
    video: 'aspect-video',
    '3/4': 'aspect-[3/4]',
  };

  return (
    <div
      className={cn(
        `grid grid-cols-${columns} gap-4`,
        className
      )}
      role="status"
      aria-label="Loading grid..."
    >
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className={cn('w-full rounded-lg', aspectMap[aspectRatio])} />
          <Skeleton className="h-4 w-3/4" />
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// PROGRESS BAR COMPONENT
// ============================================================================

interface ProgressBarProps {
  progress: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  animated?: boolean;
  className?: string;
  ariaLabel?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  max = 100,
  size = 'md',
  showLabel = false,
  animated = true,
  className,
  ariaLabel = 'Progress',
}) => {
  const percentage = useMemo(() => {
    return Math.min(Math.max((progress / max) * 100, 0), 100);
  }, [progress, max]);

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div
      className={cn('w-full', className)}
      role="progressbar"
      aria-valuenow={Math.round(percentage)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={ariaLabel}
    >
      <div className={cn('w-full bg-muted rounded-full overflow-hidden', sizeClasses[size])}>
        <div
          className={cn(
            'bg-gradient-to-r from-primary to-primary/80 h-full',
            animated && 'transition-all duration-500 ease-out'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-muted-foreground mt-1">
          {Math.round(percentage)}%
        </p>
      )}
    </div>
  );
};

// ============================================================================
// LOADING OVERLAY COMPONENT
// ============================================================================

interface LoadingOverlayProps {
  isLoading: boolean;
  children: React.ReactNode;
  message?: string;
  blur?: boolean;
  className?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isLoading,
  children,
  message,
  blur = true,
  className,
}) => {
  return (
    <div className={cn('relative', className)}>
      {children}
      {isLoading && (
        <div
          className={cn(
            'absolute inset-0 flex items-center justify-center z-50',
            blur && 'bg-background/50 backdrop-blur-sm',
            !blur && 'bg-background/40'
          )}
          role="status"
          aria-label="Loading..."
          aria-live="polite"
        >
          <div className="flex flex-col items-center gap-3">
            <Spinner size="lg" />
            {message && (
              <p className="text-sm text-muted-foreground">{message}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// SHIMMER EFFECT SKELETON (ADVANCED)
// ============================================================================

interface ShimmerSkeletonProps extends SkeletonLoaderProps {
  children?: React.ReactNode;
}

export const ShimmerSkeleton: React.FC<ShimmerSkeletonProps> = ({
  className,
  children
}) => {
  // Create a keyframe animation for shimmer effect
  const shimmerStyle = `
    @keyframes shimmer {
      0% {
        background-position: -1000px 0;
      }
      100% {
        background-position: 1000px 0;
      }
    }
  `;

  return (
    <>
      <style>{shimmerStyle}</style>
      <div
        className={cn(
          'relative overflow-hidden rounded-md bg-muted',
          className
        )}
        style={{
          backgroundImage: 'linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%)',
          backgroundSize: '1000px 100%',
          animation: 'shimmer 2s infinite',
        }}
        role="status"
        aria-label="Loading with shimmer effect..."
      >
        {children}
      </div>
    </>
  );
};

// ============================================================================
// PULSE SKELETON (ANIMATED)
// ============================================================================

interface PulseSkeletonProps extends SkeletonLoaderProps {
  children?: React.ReactNode;
}

export const PulseSkeleton: React.FC<PulseSkeletonProps> = ({
  className,
  children
}) => {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
      role="status"
      aria-label="Loading content..."
    >
      {children}
    </div>
  );
};

// ============================================================================
// SKELETON WRAPPER (CONDITIONAL LOADING)
// ============================================================================

interface SkeletonWrapperProps {
  isLoading: boolean;
  skeleton: React.ReactNode;
  children: React.ReactNode;
}

export const SkeletonWrapper: React.FC<SkeletonWrapperProps> = ({
  isLoading,
  skeleton,
  children,
}) => {
  return <>{isLoading ? skeleton : children}</>;
};
