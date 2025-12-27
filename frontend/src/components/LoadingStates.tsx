import React from 'react';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Loader2, AlertCircle, RefreshCw, FileText, Users, BookOpen, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface LoadingSkeletonProps {
  className?: string;
  lines?: number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ 
  className, 
  lines = 3 
}) => {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
};

interface DashboardSkeletonProps {
  className?: string;
}

export const DashboardSkeleton: React.FC<DashboardSkeletonProps> = ({ 
  className 
}) => {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Header skeleton */}
      <Card className="p-6">
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-4 w-48" />
      </Card>
      
      {/* Progress section skeleton */}
      <Card className="p-6 gradient-primary text-primary-foreground shadow-glow">
        <div className="flex items-center gap-4 mb-4">
          <Skeleton className="w-12 h-12 rounded-full bg-primary-foreground/20" />
          <div className="flex-1">
            <Skeleton className="h-6 w-32 mb-2 bg-primary-foreground/20" />
            <Skeleton className="h-4 w-48 bg-primary-foreground/20" />
          </div>
        </div>
        <Skeleton className="h-3 w-full bg-primary-foreground/20 mb-2" />
        <div className="grid grid-cols-3 gap-4 mt-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="text-center">
              <Skeleton className="h-8 w-16 mx-auto mb-2 bg-primary-foreground/20" />
              <Skeleton className="h-4 w-20 mx-auto bg-primary-foreground/20" />
            </div>
          ))}
        </div>
      </Card>

      {/* Cards skeleton */}
      <div className="grid md:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <Card key={i} className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <Skeleton className="w-5 h-5" />
              <Skeleton className="h-6 w-32" />
            </div>
            <div className="space-y-3">
              {[1, 2, 3].map((j) => (
                <div key={j} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex-1">
                    <Skeleton className="h-4 w-3/4 mb-1" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                  <Skeleton className="h-6 w-16" />
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* Quick actions skeleton */}
      <Card className="p-6">
        <Skeleton className="h-6 w-32 mb-4" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-muted rounded-lg flex flex-col items-center justify-center gap-2">
              <Skeleton className="w-6 h-6" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

interface ChatSkeletonProps {
  className?: string;
}

export const ChatSkeleton: React.FC<ChatSkeletonProps> = ({ className }) => {
  return (
    <div className={cn('flex h-[calc(100vh-200px)] gap-4', className)}>
      {/* Threads list skeleton */}
      <Card className="w-80 p-4 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="p-3 rounded-lg border">
              <div className="flex items-start gap-3">
                <Skeleton className="w-10 h-10 rounded-full" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-3/4 mb-1" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Messages area skeleton */}
      <Card className="flex-1 flex flex-col">
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            <Skeleton className="w-10 h-10 rounded-full" />
            <div>
              <Skeleton className="h-6 w-32 mb-1" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>
        </div>
        <div className="flex-1 p-4 space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="w-8 h-8 rounded-full" />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-3 w-12" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4 mt-1" />
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Skeleton className="flex-1 h-10" />
            <Skeleton className="w-10 h-10" />
          </div>
        </div>
      </Card>
    </div>
  );
};

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  text?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  className,
  text 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  return (
    <div className={cn('flex items-center justify-center gap-2', className)}>
      <Loader2 className={cn('animate-spin', sizeClasses[size])} />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  );
};

interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
  className?: string;
  showRetry?: boolean;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ 
  error, 
  onRetry, 
  className,
  showRetry = true 
}) => {
  return (
    <Card className={cn('p-6 text-center', className)}>
      <div className="flex flex-col items-center space-y-4">
        <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center">
          <AlertCircle className="w-8 h-8 text-destructive" />
        </div>
        
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Произошла ошибка</h3>
          <p className="text-muted-foreground">{error}</p>
        </div>

        {showRetry && onRetry && (
          <Button type="button" onClick={onRetry} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Попробовать снова
          </Button>
        )}
      </div>
    </Card>
  );
};

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ 
  title, 
  description, 
  icon,
  action,
  className 
}) => {
  return (
    <Card className={cn('p-8 text-center', className)}>
      <div className="flex flex-col items-center space-y-4">
        {icon && (
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center">
            {icon}
          </div>
        )}
        
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="text-muted-foreground">{description}</p>
        </div>

        {action && action}
      </div>
    </Card>
  );
};

interface LoadingOverlayProps {
  isLoading: boolean;
  children: React.ReactNode;
  className?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ 
  isLoading, 
  children, 
  className 
}) => {
  return (
    <div className={cn('relative', className)}>
      {children}
      {isLoading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
          <LoadingSpinner size="lg" text="Загрузка..." />
        </div>
      )}
    </div>
  );
};

// Enhanced skeleton components for different content types
interface MaterialSkeletonProps {
  className?: string;
  count?: number;
}

export const MaterialSkeleton: React.FC<MaterialSkeletonProps> = ({ 
  className, 
  count = 3 
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="p-4">
          <div className="flex items-start gap-3">
            <Skeleton className="w-12 h-12 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <div className="flex gap-2">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-6 w-20" />
              </div>
            </div>
            <Skeleton className="w-8 h-8" />
          </div>
        </Card>
      ))}
    </div>
  );
};

interface ChatMessageSkeletonProps {
  className?: string;
  count?: number;
}

export const ChatMessageSkeleton: React.FC<ChatMessageSkeletonProps> = ({ 
  className, 
  count = 5 
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <Skeleton className="w-8 h-8 rounded-full" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
};

interface UserListSkeletonProps {
  className?: string;
  count?: number;
}

export const UserListSkeleton: React.FC<UserListSkeletonProps> = ({ 
  className, 
  count = 4 
}) => {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-2">
          <Skeleton className="w-10 h-10 rounded-full" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="w-6 h-6" />
        </div>
      ))}
    </div>
  );
};

interface ReportSkeletonProps {
  className?: string;
  count?: number;
}

export const ReportSkeleton: React.FC<ReportSkeletonProps> = ({ 
  className, 
  count = 2 
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="p-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-6 w-16" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};

// Progress indicator with steps
interface ProgressStepsProps {
  steps: string[];
  currentStep: number;
  className?: string;
}

export const ProgressSteps: React.FC<ProgressStepsProps> = ({ 
  steps, 
  currentStep, 
  className 
}) => {
  return (
    <div className={cn('flex items-center space-x-4', className)}>
      {steps.map((step, index) => (
        <div key={index} className="flex items-center">
          <div className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
            index < currentStep 
              ? 'bg-primary text-primary-foreground' 
              : index === currentStep
              ? 'bg-primary/20 text-primary border-2 border-primary'
              : 'bg-muted text-muted-foreground'
          )}>
            {index < currentStep ? '✓' : index + 1}
          </div>
          <span className={cn(
            'ml-2 text-sm',
            index <= currentStep ? 'text-foreground' : 'text-muted-foreground'
          )}>
            {step}
          </span>
          {index < steps.length - 1 && (
            <div className={cn(
              'w-8 h-0.5 mx-4',
              index < currentStep ? 'bg-primary' : 'bg-muted'
            )} />
          )}
        </div>
      ))}
    </div>
  );
};

// Loading state with retry functionality
interface LoadingWithRetryProps {
  isLoading: boolean;
  error?: string | null;
  onRetry?: () => void;
  children: React.ReactNode;
  className?: string;
}

export const LoadingWithRetry: React.FC<LoadingWithRetryProps> = ({
  isLoading,
  error,
  onRetry,
  children,
  className
}) => {
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <LoadingSpinner size="lg" text="Загрузка..." />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState 
        error={error} 
        onRetry={onRetry}
        className={className}
      />
    );
  }

  return <>{children}</>;
};
