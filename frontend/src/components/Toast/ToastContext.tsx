import React, { createContext, useContext, useCallback, useState, useRef } from 'react';
import { ToastItem, ToastContainer } from './ToastContainer';
import { ToastType } from './Toast';

interface ShowToastOptions {
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextType {
  showToast: (type: ToastType, title: string, options?: ShowToastOptions) => string;
  showSuccess: (title: string, options?: ShowToastOptions) => string;
  showError: (title: string, options?: ShowToastOptions) => string;
  showWarning: (title: string, options?: ShowToastOptions) => string;
  showInfo: (title: string, options?: ShowToastOptions) => string;
  showLoading: (title: string, options?: ShowToastOptions) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

interface ToastProviderProps {
  children: React.ReactNode;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  maxToasts?: number;
}

/**
 * Provider for global toast notifications
 *
 * @example
 * ```tsx
 * <ToastProvider position="top-right" maxToasts={3}>
 *   <App />
 * </ToastProvider>
 * ```
 */
export const ToastProvider: React.FC<ToastProviderProps> = ({
  children,
  position = 'top-right',
  maxToasts = 5,
}) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastIdRef = useRef(0);

  const generateId = useCallback(() => {
    toastIdRef.current += 1;
    return `toast-${toastIdRef.current}-${Date.now()}`;
  }, []);

  const showToast = useCallback(
    (type: ToastType, title: string, options: ShowToastOptions = {}): string => {
      const id = generateId();

      // Default durations by type
      const defaultDurations: Record<ToastType, number> = {
        success: 3000,
        error: 5000,
        warning: 4000,
        info: 3000,
        loading: 0, // Loading toasts don't auto-dismiss
      };

      const newToast: ToastItem = {
        id,
        type,
        title,
        description: options.description,
        duration: options.duration ?? defaultDurations[type],
        action: options.action,
      };

      setToasts((prev) => [...prev, newToast]);

      return id;
    },
    [generateId]
  );

  const showSuccess = useCallback(
    (title: string, options?: ShowToastOptions): string => {
      return showToast('success', title, options);
    },
    [showToast]
  );

  const showError = useCallback(
    (title: string, options?: ShowToastOptions): string => {
      return showToast('error', title, options);
    },
    [showToast]
  );

  const showWarning = useCallback(
    (title: string, options?: ShowToastOptions): string => {
      return showToast('warning', title, options);
    },
    [showToast]
  );

  const showInfo = useCallback(
    (title: string, options?: ShowToastOptions): string => {
      return showToast('info', title, options);
    },
    [showToast]
  );

  const showLoading = useCallback(
    (title: string, options?: ShowToastOptions): string => {
      return showToast('loading', title, options);
    },
    [showToast]
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  const value: ToastContextType = {
    showToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showLoading,
    removeToast,
    clearAll,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} position={position} maxToasts={maxToasts} />
    </ToastContext.Provider>
  );
};

ToastProvider.displayName = 'ToastProvider';
