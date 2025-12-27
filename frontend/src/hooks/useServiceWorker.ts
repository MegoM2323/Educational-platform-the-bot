/**
 * useServiceWorker Hook
 *
 * React hook for managing service worker lifecycle and offline functionality.
 * Handles registration, updates, cache management, and online/offline status.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  registerServiceWorker,
  unregisterServiceWorker,
  onServiceWorkerUpdate,
  checkForServiceWorkerUpdate,
  installServiceWorkerUpdate,
  clearServiceWorkerCache,
  isOnline,
  onOnlineStatusChange,
  syncPendingMessages,
  precacheCriticalAssets,
  getCacheStats,
} from '@/services/serviceWorkerManager';

interface ServiceWorkerState {
  isSupported: boolean;
  isRegistered: boolean;
  isOnline: boolean;
  updateAvailable: boolean;
  isUpdating: boolean;
  cacheSize: number;
  error: Error | null;
}

interface UseServiceWorkerOptions {
  autoRegister?: boolean;
  precacheUrls?: string[];
  onUpdateAvailable?: () => void;
  onOnlineStatusChange?: (online: boolean) => void;
}

/**
 * Hook for managing service worker registration and lifecycle
 */
export function useServiceWorker(options: UseServiceWorkerOptions = {}) {
  const {
    autoRegister = true,
    precacheUrls = [],
    onUpdateAvailable,
    onOnlineStatusChange: onStatusChangeCallback,
  } = options;

  const [state, setState] = useState<ServiceWorkerState>({
    isSupported: typeof navigator !== 'undefined' && 'serviceWorker' in navigator,
    isRegistered: false,
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    updateAvailable: false,
    isUpdating: false,
    cacheSize: 0,
    error: null,
  });

  // Register service worker
  useEffect(() => {
    if (!autoRegister || !state.isSupported) {
      return;
    }

    let isMounted = true;

    async function register() {
      try {
        const success = await registerServiceWorker();

        if (isMounted) {
          setState(prev => ({
            ...prev,
            isRegistered: success,
            error: null,
          }));

          // Precache critical assets if provided
          if (success && precacheUrls.length > 0) {
            await precacheCriticalAssets(precacheUrls);
          }

          // Get initial cache stats
          const stats = await getCacheStats();
          if (isMounted) {
            setState(prev => ({
              ...prev,
              cacheSize: stats.totalSize,
            }));
          }
        }
      } catch (error) {
        if (isMounted) {
          setState(prev => ({
            ...prev,
            error: error instanceof Error ? error : new Error('Unknown error'),
          }));
        }
      }
    }

    register();

    return () => {
      isMounted = false;
    };
  }, [autoRegister, state.isSupported, precacheUrls.length]);

  // Listen for service worker updates
  useEffect(() => {
    if (!state.isSupported) {
      return;
    }

    const unsubscribe = onServiceWorkerUpdate(available => {
      setState(prev => ({ ...prev, updateAvailable: available }));

      if (available && onUpdateAvailable) {
        onUpdateAvailable();
      }
    });

    return () => {
      unsubscribe();
    };
  }, [state.isSupported, onUpdateAvailable]);

  // Listen for online/offline status changes
  useEffect(() => {
    const unsubscribe = onOnlineStatusChange(online => {
      setState(prev => ({ ...prev, isOnline: online }));

      if (onStatusChangeCallback) {
        onStatusChangeCallback(online);
      }

      // Try to sync when coming back online
      if (online) {
        syncPendingMessages().catch(error => {
          console.error('Failed to sync messages:', error);
        });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [onStatusChangeCallback]);

  // Install update
  const installUpdate = useCallback(async () => {
    setState(prev => ({ ...prev, isUpdating: true }));

    try {
      installServiceWorkerUpdate();

      // Wait a bit for the reload to happen
      await new Promise(resolve => setTimeout(resolve, 2000));
    } catch (error) {
      setState(prev => ({
        ...prev,
        isUpdating: false,
        error: error instanceof Error ? error : new Error('Failed to install update'),
      }));
    }
  }, []);

  // Clear cache
  const clearCache = useCallback(async () => {
    try {
      await clearServiceWorkerCache();

      setState(prev => ({
        ...prev,
        cacheSize: 0,
        error: null,
      }));

      return true;
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error : new Error('Failed to clear cache'),
      }));

      return false;
    }
  }, []);

  // Unregister service worker
  const unregister = useCallback(async () => {
    try {
      await clearServiceWorkerCache();
      await unregisterServiceWorker();

      setState(prev => ({
        ...prev,
        isRegistered: false,
        error: null,
      }));

      return true;
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error : new Error('Failed to unregister'),
      }));

      return false;
    }
  }, []);

  // Check for updates
  const checkForUpdates = useCallback(async () => {
    try {
      const result = await checkForServiceWorkerUpdate();

      setState(prev => ({
        ...prev,
        updateAvailable: result.updateAvailable,
        error: null,
      }));

      return result.updateAvailable;
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error : new Error('Failed to check for updates'),
      }));

      return false;
    }
  }, []);

  // Refresh cache stats
  const refreshCacheStats = useCallback(async () => {
    try {
      const stats = await getCacheStats();

      setState(prev => ({
        ...prev,
        cacheSize: stats.totalSize,
        error: null,
      }));

      return stats;
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error : new Error('Failed to get cache stats'),
      }));

      return null;
    }
  }, []);

  return {
    // State
    ...state,

    // Actions
    installUpdate,
    clearCache,
    unregister,
    checkForUpdates,
    refreshCacheStats,
  };
}

/**
 * Hook for simple online/offline status
 */
export function useOnlineStatus(): boolean {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

/**
 * Hook for notifying about service worker updates
 */
export function useServiceWorkerUpdate() {
  const [showUpdatePrompt, setShowUpdatePrompt] = useState(false);

  const { updateAvailable, installUpdate } = useServiceWorker({
    onUpdateAvailable: () => {
      setShowUpdatePrompt(true);
    },
  });

  const handleUpdate = useCallback(async () => {
    setShowUpdatePrompt(false);
    await installUpdate();
  }, [installUpdate]);

  const handleDismiss = useCallback(() => {
    setShowUpdatePrompt(false);
  }, []);

  return {
    showUpdatePrompt,
    updateAvailable,
    handleUpdate,
    handleDismiss,
  };
}
