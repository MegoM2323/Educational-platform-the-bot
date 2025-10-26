// Network Status Handler Component
// Handles offline detection, network status changes, and connection recovery

import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Wifi, WifiOff, RefreshCw, AlertTriangle } from 'lucide-react';
import { useNotifications } from '@/components/NotificationSystem';
import { errorHandlingService } from '@/services/errorHandlingService';

interface NetworkStatus {
  isOnline: boolean;
  connectionType?: string;
  effectiveType?: string;
  downlink?: number;
  rtt?: number;
  lastSeen?: Date;
  retryCount: number;
}

interface NetworkStatusHandlerProps {
  children: React.ReactNode;
  showStatusIndicator?: boolean;
  autoRetry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

export const NetworkStatusHandler: React.FC<NetworkStatusHandlerProps> = ({
  children,
  showStatusIndicator = true,
  autoRetry = true,
  maxRetries = 3,
  retryDelay = 2000,
}) => {
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>({
    isOnline: navigator.onLine,
    retryCount: 0,
  });
  
  const [isRetrying, setIsRetrying] = useState(false);
  const [showOfflineBanner, setShowOfflineBanner] = useState(false);
  
  const { showError, showSuccess, showWarning, showInfo } = useNotifications();

  // Check network connectivity
  const checkConnectivity = useCallback(async (): Promise<boolean> => {
    try {
      // Try to fetch a small resource to verify connectivity
      const response = await fetch('/api/health/', {
        method: 'HEAD',
        cache: 'no-cache',
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  }, []);

  // Update network status
  const updateNetworkStatus = useCallback(async () => {
    const isOnline = navigator.onLine;
    const connection = (navigator as any).connection;
    
    setNetworkStatus(prevStatus => {
      const newStatus: NetworkStatus = {
        isOnline,
        connectionType: connection?.type,
        effectiveType: connection?.effectiveType,
        downlink: connection?.downlink,
        rtt: connection?.rtt,
        lastSeen: isOnline ? new Date() : prevStatus.lastSeen,
        retryCount: isOnline ? 0 : prevStatus.retryCount,
      };

      if (!isOnline && !prevStatus.isOnline) {
        // Already offline, no need to show warning again
        return newStatus;
      }

      if (!isOnline && prevStatus.isOnline) {
        // Just went offline
        setShowOfflineBanner(true);
        showWarning('Отсутствует подключение к интернету', {
          description: 'Проверьте подключение к интернету',
          duration: 0, // Don't auto-dismiss
        });
      } else if (isOnline && showOfflineBanner) {
        // Just came back online
        setShowOfflineBanner(false);
        showSuccess('Подключение восстановлено');
      }

      return newStatus;
    });
  }, [showOfflineBanner, showWarning, showSuccess]);

  // Retry connection
  const retryConnection = useCallback(async () => {
    if (isRetrying) return;
    
    setIsRetrying(true);
    
    try {
      const isConnected = await checkConnectivity();
      
      if (isConnected) {
        setNetworkStatus(prev => ({
          ...prev,
          isOnline: true,
          retryCount: 0,
          lastSeen: new Date(),
        }));
        setShowOfflineBanner(false);
        showSuccess('Подключение восстановлено');
      } else {
        setNetworkStatus(prev => {
          const newRetryCount = prev.retryCount + 1;
          
          if (newRetryCount >= maxRetries) {
            showError('Не удается восстановить подключение', {
              description: 'Попробуйте позже или обратитесь в поддержку',
              action: {
                label: 'Повторить',
                onClick: () => {
                  setNetworkStatus(prev => ({ ...prev, retryCount: 0 }));
                  retryConnection();
                },
              },
            });
          } else {
            showWarning(`Попытка ${newRetryCount} из ${maxRetries} не удалась`, {
              description: 'Повторяем через несколько секунд...',
            });
            
            // Auto-retry after delay
            if (autoRetry) {
              setTimeout(() => {
                retryConnection();
              }, retryDelay * newRetryCount); // Exponential backoff
            }
          }
          
          return {
            ...prev,
            retryCount: newRetryCount,
          };
        });
      }
    } catch (error) {
      errorHandlingService.handleNetworkError(error as Error, retryConnection);
    } finally {
      setIsRetrying(false);
    }
  }, [
    isRetrying,
    checkConnectivity,
    maxRetries,
    autoRetry,
    retryDelay,
    showSuccess,
    showError,
    showWarning,
  ]);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      updateNetworkStatus();
    };

    const handleOffline = () => {
      updateNetworkStatus();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Check connectivity on mount
    updateNetworkStatus();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [updateNetworkStatus]);

  // Monitor connection quality
  useEffect(() => {
    const connection = (navigator as any).connection;
    if (!connection) return;

    const handleConnectionChange = () => {
      updateNetworkStatus();
      
      // Show warning for slow connections
      if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
        showInfo('Медленное подключение', {
          description: 'Соединение может работать медленно',
        });
      }
    };

    connection.addEventListener('change', handleConnectionChange);

    return () => {
      connection.removeEventListener('change', handleConnectionChange);
    };
  }, [updateNetworkStatus, showInfo]);

  // Get connection status badge
  const getStatusBadge = () => {
    if (!showStatusIndicator) return null;

    if (!networkStatus.isOnline) {
      return (
        <Badge variant="destructive" className="flex items-center gap-1">
          <WifiOff className="w-3 h-3" />
          Офлайн
        </Badge>
      );
    }

    if (networkStatus.effectiveType === 'slow-2g' || networkStatus.effectiveType === '2g') {
      return (
        <Badge variant="secondary" className="flex items-center gap-1">
          <Wifi className="w-3 h-3" />
          Медленно
        </Badge>
      );
    }

    return (
      <Badge variant="default" className="flex items-center gap-1">
        <Wifi className="w-3 h-3" />
        Онлайн
      </Badge>
    );
  };

  return (
    <>
      {children}
      
      {/* Status Indicator */}
      {getStatusBadge()}
      
      {/* Offline Banner */}
      {showOfflineBanner && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-destructive text-destructive-foreground">
          <Card className="m-4 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <WifiOff className="w-5 h-5" />
                <div>
                  <h3 className="font-semibold">Отсутствует подключение к интернету</h3>
                  <p className="text-sm opacity-90">
                    Проверьте подключение к интернету. Некоторые функции могут быть недоступны.
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {networkStatus.retryCount > 0 && (
                  <span className="text-sm opacity-75">
                    Попытка {networkStatus.retryCount} из {maxRetries}
                  </span>
                )}
                
                <Button
                  size="sm"
                  variant="outline"
                  onClick={retryConnection}
                  disabled={isRetrying}
                  className="bg-background text-foreground hover:bg-muted"
                >
                  {isRetrying ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  Повторить
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
      
      {/* Connection Quality Warning */}
      {networkStatus.isOnline && networkStatus.effectiveType === 'slow-2g' && (
        <div className="fixed bottom-4 right-4 z-40">
          <Card className="p-3 border-warning">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-warning-foreground" />
              <span className="text-sm text-warning-foreground">
                Медленное подключение
              </span>
            </div>
          </Card>
        </div>
      )}
    </>
  );
};

// Hook for using network status
export const useNetworkStatus = () => {
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>({
    isOnline: navigator.onLine,
    retryCount: 0,
  });

  useEffect(() => {
    const handleOnline = () => {
      setNetworkStatus(prev => ({
        ...prev,
        isOnline: true,
        retryCount: 0,
        lastSeen: new Date(),
      }));
    };

    const handleOffline = () => {
      setNetworkStatus(prev => ({
        ...prev,
        isOnline: false,
      }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return networkStatus;
};

export default NetworkStatusHandler;

