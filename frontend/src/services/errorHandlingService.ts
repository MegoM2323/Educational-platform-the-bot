// Enhanced Error Handling Service
// Provides user-friendly error messages and recovery options

import { errorLoggingService } from './errorLoggingService';
import { useNotifications } from '@/components/NotificationSystem';

export interface ErrorRecoveryOption {
  label: string;
  action: () => void;
  type: 'retry' | 'redirect' | 'refresh' | 'contact' | 'dismiss';
}

export interface UserFriendlyError {
  title: string;
  message: string;
  recoveryOptions: ErrorRecoveryOption[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'network' | 'auth' | 'validation' | 'server' | 'client' | 'websocket';
  canRetry: boolean;
  shouldReport: boolean;
}

class ErrorHandlingService {
  private notificationService: any = null;

  constructor() {
    // Initialize notification service when available
    this.initializeNotificationService();
  }

  private initializeNotificationService(): void {
    try {
      // This will be set when the notification context is available
      this.notificationService = null;
    } catch (error) {
      console.warn('Notification service not available:', error);
    }
  }

  setNotificationService(notificationService: any): void {
    this.notificationService = notificationService;
  }

  // Main error handling method
  handleError(
    error: Error | any,
    context?: {
      operation?: string;
      component?: string;
      userId?: string;
      retryAction?: () => void;
      customMessage?: string;
    }
  ): UserFriendlyError {
    const errorId = this.logError(error, context);
    const userFriendlyError = this.createUserFriendlyError(error, context);
    
    // Show notification if service is available
    if (this.notificationService) {
      this.showErrorNotification(userFriendlyError, context?.retryAction);
    }

    return userFriendlyError;
  }

  private logError(error: Error | any, context?: any): string {
    const errorMessage = error?.message || 'Unknown error occurred';
    const errorStack = error?.stack;
    
    let category: 'network' | 'auth' | 'validation' | 'server' | 'client' | 'websocket' = 'client';
    let level: 'error' | 'warning' | 'info' | 'debug' = 'error';

    // Determine category and level based on error type
    if (errorMessage.includes('Network') || errorMessage.includes('fetch')) {
      category = 'network';
    } else if (errorMessage.includes('Auth') || errorMessage.includes('token') || errorMessage.includes('401')) {
      category = 'auth';
    } else if (errorMessage.includes('Validation') || errorMessage.includes('400')) {
      category = 'validation';
      level = 'warning';
    } else if (errorMessage.includes('Server') || errorMessage.includes('500')) {
      category = 'server';
    } else if (errorMessage.includes('WebSocket')) {
      category = 'websocket';
    }

    return errorLoggingService.logError({
      level,
      category,
      message: errorMessage,
      stack: errorStack,
      context: {
        ...context,
        errorType: error?.constructor?.name || 'Unknown',
      },
    });
  }

  private createUserFriendlyError(
    error: Error | any,
    context?: any
  ): UserFriendlyError {
    const errorMessage = error?.message || 'Произошла неизвестная ошибка';
    
    // Network errors
    if (errorMessage.includes('Network') || errorMessage.includes('fetch')) {
      return {
        title: 'Проблема с подключением',
        message: 'Не удается подключиться к серверу. Проверьте подключение к интернету.',
        recoveryOptions: [
          {
            label: 'Повторить попытку',
            action: context?.retryAction || (() => window.location.reload()),
            type: 'retry',
          },
          {
            label: 'Обновить страницу',
            action: () => window.location.reload(),
            type: 'refresh',
          },
        ],
        severity: 'high',
        category: 'network',
        canRetry: true,
        shouldReport: false,
      };
    }

    // Authentication errors
    if (errorMessage.includes('Auth') || errorMessage.includes('token') || errorMessage.includes('401')) {
      return {
        title: 'Ошибка авторизации',
        message: 'Ваша сессия истекла или произошла ошибка авторизации. Войдите в систему заново.',
        recoveryOptions: [
          {
            label: 'Войти в систему',
            action: () => window.location.href = '/auth',
            type: 'redirect',
          },
          {
            label: 'Обновить страницу',
            action: () => window.location.reload(),
            type: 'refresh',
          },
        ],
        severity: 'high',
        category: 'auth',
        canRetry: false,
        shouldReport: false,
      };
    }

    // Validation errors
    if (errorMessage.includes('Validation') || errorMessage.includes('400')) {
      return {
        title: 'Ошибка в данных',
        message: 'Проверьте правильность введенных данных и попробуйте снова.',
        recoveryOptions: [
          {
            label: 'Исправить данные',
            action: () => {}, // Will be handled by the component
            type: 'retry',
          },
          {
            label: 'Закрыть',
            action: () => {},
            type: 'dismiss',
          },
        ],
        severity: 'medium',
        category: 'validation',
        canRetry: true,
        shouldReport: false,
      };
    }

    // Server errors
    if (errorMessage.includes('Server') || errorMessage.includes('500')) {
      return {
        title: 'Ошибка сервера',
        message: 'На сервере произошла ошибка. Мы уже работаем над её исправлением.',
        recoveryOptions: [
          {
            label: 'Повторить попытку',
            action: context?.retryAction || (() => window.location.reload()),
            type: 'retry',
          },
          {
            label: 'Связаться с поддержкой',
            action: () => this.contactSupport(),
            type: 'contact',
          },
        ],
        severity: 'critical',
        category: 'server',
        canRetry: true,
        shouldReport: true,
      };
    }

    // WebSocket errors
    if (errorMessage.includes('WebSocket')) {
      return {
        title: 'Проблема с чатом',
        message: 'Не удается подключиться к чату. Проверьте подключение к интернету.',
        recoveryOptions: [
          {
            label: 'Переподключиться',
            action: context?.retryAction || (() => window.location.reload()),
            type: 'retry',
          },
          {
            label: 'Обновить страницу',
            action: () => window.location.reload(),
            type: 'refresh',
          },
        ],
        severity: 'medium',
        category: 'websocket',
        canRetry: true,
        shouldReport: false,
      };
    }

    // Generic client errors
    return {
      title: 'Произошла ошибка',
      message: context?.customMessage || 'Что-то пошло не так. Попробуйте обновить страницу.',
      recoveryOptions: [
        {
          label: 'Обновить страницу',
          action: () => window.location.reload(),
          type: 'refresh',
        },
        {
          label: 'На главную',
          action: () => window.location.href = '/',
          type: 'redirect',
        },
      ],
      severity: 'medium',
      category: 'client',
      canRetry: true,
      shouldReport: true,
    };
  }

  private showErrorNotification(error: UserFriendlyError, retryAction?: () => void): void {
    if (!this.notificationService) return;

    const options = {
      title: error.title,
      description: error.message,
      duration: error.severity === 'critical' ? 10000 : 5000,
      action: error.canRetry && retryAction ? {
        label: 'Повторить',
        onClick: retryAction,
      } : undefined,
    };

    switch (error.severity) {
      case 'critical':
        this.notificationService.showError(error.message, options);
        break;
      case 'high':
        this.notificationService.showError(error.message, options);
        break;
      case 'medium':
        this.notificationService.showWarning(error.message, options);
        break;
      case 'low':
        this.notificationService.showInfo(error.message, options);
        break;
    }
  }

  private contactSupport(): void {
    // Open support contact or create a support ticket
    const supportEmail = 'support@thebot-platform.com';
    const subject = 'Ошибка в приложении';
    const body = `Описание ошибки: ${window.location.href}\n\nПожалуйста, опишите, что вы делали, когда произошла ошибка.`;
    
    window.open(`mailto:${supportEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`);
  }

  // Specific error handlers for different scenarios
  handleNetworkError(error: Error, retryAction?: () => void): UserFriendlyError {
    return this.handleError(error, {
      operation: 'network_request',
      retryAction,
    });
  }

  handleAuthError(error: Error, retryAction?: () => void): UserFriendlyError {
    return this.handleError(error, {
      operation: 'authentication',
      retryAction,
    });
  }

  handleValidationError(error: Error, retryAction?: () => void): UserFriendlyError {
    return this.handleError(error, {
      operation: 'validation',
      retryAction,
    });
  }

  handleServerError(error: Error, retryAction?: () => void): UserFriendlyError {
    return this.handleError(error, {
      operation: 'server_request',
      retryAction,
    });
  }

  handleWebSocketError(error: Error, retryAction?: () => void): UserFriendlyError {
    return this.handleError(error, {
      operation: 'websocket_connection',
      retryAction,
    });
  }

  // Utility methods
  isRetryableError(error: Error | any): boolean {
    const errorMessage = error?.message || '';
    
    return (
      errorMessage.includes('Network') ||
      errorMessage.includes('timeout') ||
      errorMessage.includes('500') ||
      errorMessage.includes('502') ||
      errorMessage.includes('503') ||
      errorMessage.includes('504')
    );
  }

  shouldReportError(error: Error | any): boolean {
    const errorMessage = error?.message || '';
    
    return (
      errorMessage.includes('Server') ||
      errorMessage.includes('500') ||
      errorMessage.includes('Internal Server Error') ||
      !errorMessage.includes('Network') // Don't report network errors
    );
  }

  getErrorSeverity(error: Error | any): 'low' | 'medium' | 'high' | 'critical' {
    const errorMessage = error?.message || '';
    
    if (errorMessage.includes('500') || errorMessage.includes('Server')) {
      return 'critical';
    }
    
    if (errorMessage.includes('Network') || errorMessage.includes('Auth')) {
      return 'high';
    }
    
    if (errorMessage.includes('Validation') || errorMessage.includes('400')) {
      return 'medium';
    }
    
    return 'low';
  }
}

// Export singleton instance
export const errorHandlingService = new ErrorHandlingService();

// Export class for testing
export { ErrorHandlingService };

