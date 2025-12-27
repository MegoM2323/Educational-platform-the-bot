/**
 * useNetworkStatus - Hook для отслеживания статуса интернета
 *
 * Функции:
 * - Слушание событий online/offline
 * - Проверка соединения через HEAD запрос
 * - Состояние с задержкой (debounced)
 * - Callback при изменении статуса
 */

import { useCallback, useEffect, useRef, useState } from "react";

export interface UseNetworkStatusResult {
  /** Is the browser online */
  isOnline: boolean;

  /** Is checking connection status */
  isChecking: boolean;

  /** Last time status was checked */
  lastChecked: Date | null;
}

/**
 * Hook for tracking network status
 *
 * Usage:
 * ```tsx
 * const { isOnline, isChecking } = useNetworkStatus();
 *
 * if (!isOnline) {
 *   return <OfflineMessage />;
 * }
 * ```
 */
export function useNetworkStatus(
  onOnline?: () => void,
  onOffline?: () => void,
): UseNetworkStatusResult {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const [isChecking, setIsChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const checkTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const prevStatusRef = useRef<boolean>(isOnline);

  /**
   * Check connection by making a HEAD request
   */
  const checkConnection = useCallback(async (): Promise<boolean> => {
    setIsChecking(true);
    try {
      const response = await fetch("/api/system/health/", {
        method: "HEAD",
        cache: "no-store",
      });
      setLastChecked(new Date());
      return response.ok;
    } catch {
      setLastChecked(new Date());
      return false;
    } finally {
      setIsChecking(false);
    }
  }, []);

  /**
   * Handle online event
   */
  const handleOnline = useCallback(() => {
    setIsOnline(true);

    // Verify connection with HEAD request
    checkTimeoutRef.current = setTimeout(() => {
      checkConnection();
    }, 500);

    if (onOnline) {
      onOnline();
    }
  }, [checkConnection, onOnline]);

  /**
   * Handle offline event
   */
  const handleOffline = useCallback(() => {
    setIsOnline(false);

    if (onOffline) {
      onOffline();
    }
  }, [onOffline]);

  /**
   * Set up event listeners
   */
  useEffect(() => {
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);

      if (checkTimeoutRef.current) {
        clearTimeout(checkTimeoutRef.current);
      }
    };
  }, [handleOnline, handleOffline]);

  /**
   * Call callbacks when status changes
   */
  useEffect(() => {
    if (isOnline !== prevStatusRef.current) {
      prevStatusRef.current = isOnline;

      if (isOnline && onOnline) {
        onOnline();
      } else if (!isOnline && onOffline) {
        onOffline();
      }
    }
  }, [isOnline, onOnline, onOffline]);

  return {
    isOnline,
    isChecking,
    lastChecked,
  };
}
