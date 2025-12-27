import React, { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Toast, ToastType } from './Toast';

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContainerProps {
  toasts: ToastItem[];
  onRemove: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  maxToasts?: number;
}

/**
 * Container for managing and displaying multiple toasts
 *
 * @example
 * ```tsx
 * <ToastContainer
 *   toasts={toasts}
 *   onRemove={handleRemoveToast}
 *   position="top-right"
 *   maxToasts={3}
 * />
 * ```
 */
export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onRemove,
  position = 'top-right',
  maxToasts = 5,
}) => {
  // Limit number of visible toasts
  const visibleToasts = useMemo(() => {
    return toasts.slice(0, maxToasts);
  }, [toasts, maxToasts]);

  const positionClasses: Record<string, string> = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  };

  return (
    <div
      className={cn(
        'fixed z-50 flex flex-col gap-2 pointer-events-none',
        positionClasses[position],
        {
          'max-w-sm': position.includes('center'),
          'max-w-md': !position.includes('center'),
        }
      )}
      aria-label="Toast notifications"
      role="region"
    >
      {visibleToasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast
            id={toast.id}
            type={toast.type}
            title={toast.title}
            description={toast.description}
            duration={toast.duration}
            action={toast.action}
            onClose={onRemove}
          />
        </div>
      ))}
    </div>
  );
};

ToastContainer.displayName = 'ToastContainer';
