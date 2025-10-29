// Error Handling Provider
// Integrates all error handling systems and provides them to the app

import React, { createContext, useContext, useEffect, useCallback } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { NetworkStatusHandler } from '@/components/NetworkStatusHandler';
import { NotificationProvider } from '@/components/NotificationSystem';
import { errorHandlingService } from '@/services/errorHandlingService';
import { errorLoggingService } from '@/services/errorLoggingService';
import { retryService } from '@/services/retryService';

interface ErrorHandlingContextType {
  reportError: (error: Error, context?: any) => void;
  getErrorStats: () => any;
  resetErrorStats: () => void;
  isOnline: boolean;
  retryStats: any;
}

const ErrorHandlingContext = createContext<ErrorHandlingContextType | undefined>(undefined);

export const useErrorHandling = () => {
  const context = useContext(ErrorHandlingContext);
  if (!context) {
    throw new Error('useErrorHandling must be used within an ErrorHandlingProvider');
  }
  return context;
};

interface ErrorHandlingProviderProps {
  children: React.ReactNode;
  enableLogging?: boolean;
  enableRetry?: boolean;
  enableNetworkMonitoring?: boolean;
}

export const ErrorHandlingProvider: React.FC<ErrorHandlingProviderProps> = ({
  children,
  enableLogging = true,
  enableRetry = true,
  enableNetworkMonitoring = true,
}) => {
  const [isOnline, setIsOnline] = React.useState(navigator.onLine);

  // Initialize error handling services
  useEffect(() => {
    if (enableLogging) {
      // Set up global error handlers
      const handleGlobalError = (event: ErrorEvent) => {
        errorLoggingService.logError({
          level: 'error',
          category: 'client',
          message: event.message,
          stack: event.error?.stack,
          context: {
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
          },
        });
      };

      const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
        errorLoggingService.logError({
          level: 'error',
          category: 'client',
          message: `Unhandled Promise Rejection: ${event.reason}`,
          stack: event.reason?.stack,
          context: {
            reason: event.reason,
          },
        });
      };

      window.addEventListener('error', handleGlobalError);
      window.addEventListener('unhandledrejection', handleUnhandledRejection);

      return () => {
        window.removeEventListener('error', handleGlobalError);
        window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      };
    }
  }, [enableLogging]);

  // Ensure test helper buffer for WS tests exists
  useEffect(() => {
    (window as any).__wsMessages = (window as any).__wsMessages || [];
  }, []);

  // Monitor network status
  useEffect(() => {
    if (!enableNetworkMonitoring) return;

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [enableNetworkMonitoring]);

  // Report error function
  const reportError = useCallback((error: Error, context?: any) => {
    if (enableLogging) {
      errorLoggingService.logError({
        level: 'error',
        category: 'client',
        message: error.message,
        stack: error.stack,
        context,
      });
    }

    // Handle error with user-friendly messages
    errorHandlingService.handleError(error, context);
  }, [enableLogging]);

  // Get error statistics
  const getErrorStats = useCallback(() => {
    const errorStats = enableLogging ? errorLoggingService.getErrorAnalytics() : null;
    const retryStats = enableRetry ? retryService.getStats() : null;

    return {
      errorStats,
      retryStats,
      isOnline,
    };
  }, [enableLogging, enableRetry, isOnline]);

  // Reset error statistics
  const resetErrorStats = useCallback(() => {
    if (enableLogging) {
      errorLoggingService.clearLogs();
    }
    if (enableRetry) {
      retryService.resetCircuitBreaker();
    }
  }, [enableLogging, enableRetry]);

  const contextValue: ErrorHandlingContextType = {
    reportError,
    getErrorStats,
    resetErrorStats,
    isOnline,
    retryStats: enableRetry ? retryService.getStats() : null,
  };

  return (
    <ErrorHandlingContext.Provider value={contextValue}>
      <NotificationProvider>
        <ErrorBoundary>
          {enableNetworkMonitoring ? (
            <NetworkStatusHandler showStatusIndicator={false}>
              {children}
            </NetworkStatusHandler>
          ) : (
            children
          )}
        </ErrorBoundary>
      </NotificationProvider>
    </ErrorHandlingContext.Provider>
  );
};

// Hook for easy error reporting
export const useErrorReporter = () => {
  const { reportError } = useErrorHandling();
  
  return {
    reportError: (error: Error, context?: any) => {
      console.error('Error reported:', error, context);
      reportError(error, context);
    },
    reportNetworkError: (error: Error, context?: any) => {
      errorLoggingService.logNetworkError(error, context);
      errorHandlingService.handleNetworkError(error);
    },
    reportAuthError: (error: Error, context?: any) => {
      errorLoggingService.logAuthError(error, context);
      errorHandlingService.handleAuthError(error);
    },
    reportValidationError: (error: Error, context?: any) => {
      errorLoggingService.logValidationError(error, context);
      errorHandlingService.handleValidationError(error);
    },
    reportServerError: (error: Error, context?: any) => {
      errorLoggingService.logServerError(error, context);
      errorHandlingService.handleServerError(error);
    },
  };
};

// Hook for retry functionality
export const useRetry = () => {
  const retryApiCall = useCallback(
    async <T,>(apiCall: () => Promise<T>, context?: string): Promise<T> => {
      return retryService.retryApiCall(apiCall, context);
    },
    []
  );

  const retryWebSocketConnection = useCallback(
    async (connectionFn: () => WebSocket, context?: string): Promise<WebSocket> => {
      return retryService.retryWebSocketConnection(connectionFn, context);
    },
    []
  );

  const retryFileUpload = useCallback(
    async <T,>(uploadFn: () => Promise<T>, context?: string): Promise<T> => {
      return retryService.retryFileUpload(uploadFn, context);
    },
    []
  );

  return {
    retryApiCall,
    retryWebSocketConnection,
    retryFileUpload,
    getRetryStats: () => retryService.getStats(),
    resetRetryStats: () => retryService.resetCircuitBreaker(),
  };
};

export default ErrorHandlingProvider;

