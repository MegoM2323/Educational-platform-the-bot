import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Info, X, AlertTriangle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastProps {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: ToastAction;
  onClose: (id: string) => void;
  autoClose?: boolean;
}

/**
 * Standalone Toast component for displaying notifications
 *
 * @example
 * ```tsx
 * <Toast
 *   id="toast-1"
 *   type="success"
 *   title="Success"
 *   description="Your changes have been saved"
 *   onClose={handleClose}
 * />
 * ```
 */
export const Toast: React.FC<ToastProps> = ({
  id,
  type,
  title,
  description,
  duration = 3000,
  action,
  onClose,
  autoClose = true,
}) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (!autoClose || type === 'loading') return;

    const timer = setTimeout(() => {
      setIsVisible(false);
      // Allow animation time before removing
      setTimeout(() => onClose(id), 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [id, duration, autoClose, type, onClose]);

  const handleClose = () => {
    setIsVisible(false);
    // Allow animation time before removing
    setTimeout(() => onClose(id), 300);
  };

  // Get styles based on type
  const typeStyles: Record<ToastType, { bg: string; border: string; icon: React.ReactNode }> = {
    success: {
      bg: 'bg-green-50 dark:bg-green-950',
      border: 'border-green-200 dark:border-green-800',
      icon: <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />,
    },
    error: {
      bg: 'bg-red-50 dark:bg-red-950',
      border: 'border-red-200 dark:border-red-800',
      icon: <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />,
    },
    warning: {
      bg: 'bg-yellow-50 dark:bg-yellow-950',
      border: 'border-yellow-200 dark:border-yellow-800',
      icon: <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />,
    },
    info: {
      bg: 'bg-blue-50 dark:bg-blue-950',
      border: 'border-blue-200 dark:border-blue-800',
      icon: <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />,
    },
    loading: {
      bg: 'bg-gray-50 dark:bg-gray-950',
      border: 'border-gray-200 dark:border-gray-800',
      icon: <Loader2 className="h-5 w-5 text-gray-600 dark:text-gray-400 animate-spin" />,
    },
  };

  const style = typeStyles[type];

  return (
    <div
      className={cn(
        'rounded-lg border p-4 shadow-md transition-all duration-300 ease-in-out',
        style.bg,
        style.border,
        isVisible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
      )}
      role="alert"
      aria-live={type === 'error' ? 'assertive' : 'polite'}
      aria-atomic="true"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 pt-0.5">{style.icon}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-50">
            {title}
          </h3>
          {description && (
            <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
              {description}
            </p>
          )}

          {/* Action Button */}
          {action && (
            <button
              onClick={action.onClick}
              className={cn(
                'mt-2 inline-flex items-center text-sm font-medium underline',
                type === 'success' && 'text-green-700 dark:text-green-300 hover:text-green-900 dark:hover:text-green-100',
                type === 'error' && 'text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100',
                type === 'warning' && 'text-yellow-700 dark:text-yellow-300 hover:text-yellow-900 dark:hover:text-yellow-100',
                type === 'info' && 'text-blue-700 dark:text-blue-300 hover:text-blue-900 dark:hover:text-blue-100',
                type === 'loading' && 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              )}
            >
              {action.label}
            </button>
          )}
        </div>

        {/* Close Button */}
        <button
          onClick={handleClose}
          className={cn(
            'flex-shrink-0 p-1 rounded-md transition-colors',
            type === 'success' && 'hover:bg-green-100 dark:hover:bg-green-900/30 text-green-600 dark:text-green-400',
            type === 'error' && 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400',
            type === 'warning' && 'hover:bg-yellow-100 dark:hover:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
            type === 'info' && 'hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400',
            type === 'loading' && 'hover:bg-gray-100 dark:hover:bg-gray-900/30 text-gray-600 dark:text-gray-400'
          )}
          aria-label="Close notification"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

Toast.displayName = 'Toast';
