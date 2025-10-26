import React, { createContext, useContext, useCallback } from 'react';
import { toast } from 'sonner';
import { CheckCircle, AlertCircle, Info, XCircle, Loader2 } from 'lucide-react';

export type NotificationType = 'success' | 'error' | 'warning' | 'info' | 'loading';

interface NotificationOptions {
  title?: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  onDismiss?: () => void;
}

interface NotificationContextType {
  showNotification: (type: NotificationType, message: string, options?: NotificationOptions) => void;
  showSuccess: (message: string, options?: NotificationOptions) => void;
  showError: (message: string, options?: NotificationOptions) => void;
  showWarning: (message: string, options?: NotificationOptions) => void;
  showInfo: (message: string, options?: NotificationOptions) => void;
  showLoading: (message: string, options?: NotificationOptions) => void;
  dismiss: (id: string | number) => void;
  dismissAll: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const showNotification = useCallback((
    type: NotificationType, 
    message: string, 
    options: NotificationOptions = {}
  ) => {
    const { title, description, duration, action, onDismiss } = options;

    const toastOptions = {
      duration: duration || (type === 'error' ? 5000 : 3000),
      action: action ? {
        label: action.label,
        onClick: action.onClick,
      } : undefined,
      onDismiss,
    };

    switch (type) {
      case 'success':
        toast.success(message, {
          ...toastOptions,
          description: title || description,
        });
        break;
      case 'error':
        toast.error(message, {
          ...toastOptions,
          description: title || description,
        });
        break;
      case 'warning':
        toast.warning(message, {
          ...toastOptions,
          description: title || description,
        });
        break;
      case 'info':
        toast.info(message, {
          ...toastOptions,
          description: title || description,
        });
        break;
      case 'loading':
        toast.loading(message, {
          ...toastOptions,
          description: title || description,
        });
        break;
    }
  }, []);

  const showSuccess = useCallback((message: string, options?: NotificationOptions) => {
    showNotification('success', message, options);
  }, [showNotification]);

  const showError = useCallback((message: string, options?: NotificationOptions) => {
    showNotification('error', message, options);
  }, [showNotification]);

  const showWarning = useCallback((message: string, options?: NotificationOptions) => {
    showNotification('warning', message, options);
  }, [showNotification]);

  const showInfo = useCallback((message: string, options?: NotificationOptions) => {
    showNotification('info', message, options);
  }, [showNotification]);

  const showLoading = useCallback((message: string, options?: NotificationOptions) => {
    showNotification('loading', message, options);
  }, [showNotification]);

  const dismiss = useCallback((id: string | number) => {
    toast.dismiss(id);
  }, []);

  const dismissAll = useCallback(() => {
    toast.dismiss();
  }, []);

  const value: NotificationContextType = {
    showNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showLoading,
    dismiss,
    dismissAll,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

// Специализированные хуки для разных типов уведомлений
export const useSuccessNotification = () => {
  const { showSuccess } = useNotifications();
  return showSuccess;
};

export const useErrorNotification = () => {
  const { showError } = useNotifications();
  return showError;
};

export const useWarningNotification = () => {
  const { showWarning } = useNotifications();
  return showWarning;
};

export const useInfoNotification = () => {
  const { showInfo } = useNotifications();
  return showInfo;
};

export const useLoadingNotification = () => {
  const { showLoading } = useNotifications();
  return showLoading;
};

// Компонент для отображения уведомлений о состоянии загрузки
interface LoadingNotificationProps {
  message: string;
  isVisible: boolean;
  onComplete?: () => void;
}

export const LoadingNotification: React.FC<LoadingNotificationProps> = ({
  message,
  isVisible,
  onComplete
}) => {
  const { showLoading, dismiss } = useNotifications();

  React.useEffect(() => {
    if (isVisible) {
      const id = showLoading(message);
      return () => dismiss(id);
    }
  }, [isVisible, message, showLoading, dismiss]);

  React.useEffect(() => {
    if (!isVisible && onComplete) {
      onComplete();
    }
  }, [isVisible, onComplete]);

  return null;
};

// Компонент для отображения прогресса операции
interface ProgressNotificationProps {
  message: string;
  progress: number;
  isVisible: boolean;
  onComplete?: () => void;
}

export const ProgressNotification: React.FC<ProgressNotificationProps> = ({
  message,
  progress,
  isVisible,
  onComplete
}) => {
  const { showLoading, dismiss } = useNotifications();

  React.useEffect(() => {
    if (isVisible) {
      const id = showLoading(`${message} (${Math.round(progress)}%)`);
      return () => dismiss(id);
    }
  }, [isVisible, message, progress, showLoading, dismiss]);

  React.useEffect(() => {
    if (progress >= 100 && onComplete) {
      onComplete();
    }
  }, [progress, onComplete]);

  return null;
};

// Утилиты для работы с уведомлениями
export const notificationUtils = {
  // Показать уведомление об успешной отправке заявки
  showApplicationSubmitted: (trackingToken: string) => {
    toast.success('Заявка успешно отправлена!', {
      description: `Номер заявки: ${trackingToken}`,
      duration: 5000,
      action: {
        label: 'Отследить статус',
        onClick: () => {
          window.open(`/application-status/${trackingToken}`, '_blank');
        },
      },
    });
  },

  // Показать уведомление об ошибке Telegram интеграции
  showTelegramError: (retryAction?: () => void) => {
    toast.error('Ошибка отправки в Telegram', {
      description: 'Не удалось отправить уведомление. Попробуйте позже.',
      duration: 7000,
      action: retryAction ? {
        label: 'Повторить',
        onClick: retryAction,
      } : undefined,
    });
  },

  // Показать уведомление об успешной оплате
  showPaymentSuccess: (amount: number, subject: string) => {
    toast.success('Оплата прошла успешно!', {
      description: `Оплачено ${amount} руб. за предмет "${subject}"`,
      duration: 5000,
    });
  },

  // Показать уведомление об ошибке оплаты
  showPaymentError: (retryAction?: () => void) => {
    toast.error('Ошибка оплаты', {
      description: 'Не удалось обработать платеж. Проверьте данные и попробуйте снова.',
      duration: 7000,
      action: retryAction ? {
        label: 'Повторить',
        onClick: retryAction,
      } : undefined,
    });
  },

  // Показать уведомление о создании отчета
  showReportCreated: (studentName: string) => {
    toast.success('Отчет создан', {
      description: `Отчет для ${studentName} успешно отправлен родителям`,
      duration: 4000,
    });
  },

  // Показать уведомление об ошибке создания отчета
  showReportError: (retryAction?: () => void) => {
    toast.error('Ошибка создания отчета', {
      description: 'Не удалось создать отчет. Попробуйте снова.',
      duration: 5000,
      action: retryAction ? {
        label: 'Повторить',
        onClick: retryAction,
      } : undefined,
    });
  },

  // Показать уведомление о новом сообщении в чате
  showNewMessage: (senderName: string, threadTitle?: string) => {
    toast.info('Новое сообщение', {
      description: `${senderName} написал в ${threadTitle || 'общем чате'}`,
      duration: 3000,
    });
  },

  // Показать уведомление об ошибке загрузки данных
  showDataLoadError: (retryAction?: () => void) => {
    toast.error('Ошибка загрузки данных', {
      description: 'Не удалось загрузить данные. Проверьте подключение к интернету.',
      duration: 5000,
      action: retryAction ? {
        label: 'Обновить',
        onClick: retryAction,
      } : undefined,
    });
  },
};
