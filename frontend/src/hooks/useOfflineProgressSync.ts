/**
 * useOfflineProgressSync - Hook для синхронизации прогресса в офлайн режиме
 *
 * Функции:
 * - Сохранение прогресса локально при отсутствии интернета
 * - Синхронизация при восстановлении соединения
 * - Получение статуса синхронизации
 * - Ручная синхронизация
 * - Очистка локального хранилища
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNetworkStatus } from "./useNetworkStatus";
import { api } from "@/utils/api";
import { toast } from "sonner";

export interface OfflineProgressUpdate {
  materialId: string | number;
  progress: number;
  timeSpent: number;
  timestamp: string;
  synced: boolean;
}

const STORAGE_KEY = "offline_progress_updates";

/**
 * Parse offline updates from localStorage
 */
function getOfflineUpdates(): OfflineProgressUpdate[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error("Failed to parse offline updates:", error);
    return [];
  }
}

/**
 * Save offline update to localStorage
 */
function saveOfflineUpdate(update: OfflineProgressUpdate): void {
  try {
    const updates = getOfflineUpdates();
    // Remove existing update for this material
    const filtered = updates.filter((u) => u.materialId !== update.materialId);
    // Add new update
    filtered.push(update);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error("Failed to save offline update:", error);
  }
}

/**
 * Remove offline update from localStorage
 */
function removeOfflineUpdate(materialId: string | number): void {
  try {
    const updates = getOfflineUpdates();
    const filtered = updates.filter((u) => u.materialId !== materialId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error("Failed to remove offline update:", error);
  }
}

/**
 * Clear all offline updates
 */
function clearOfflineUpdates(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error("Failed to clear offline updates:", error);
  }
}

export interface UseOfflineProgressSyncResult {
  /** Pending offline updates */
  pendingUpdates: OfflineProgressUpdate[];

  /** Is syncing in progress */
  isSyncing: boolean;

  /** Last sync error */
  syncError: string | null;

  /** Save progress locally (for offline use) */
  saveProgressOffline: (
    materialId: string | number,
    progress: number,
    timeSpent: number,
  ) => void;

  /** Manually trigger sync */
  syncNow: () => Promise<void>;

  /** Clear all offline updates */
  clearPending: () => void;

  /** Is online */
  isOnline: boolean;
}

/**
 * Hook for managing offline progress synchronization
 *
 * Usage:
 * ```tsx
 * const {
 *   pendingUpdates,
 *   isSyncing,
 *   saveProgressOffline,
 *   syncNow,
 *   isOnline,
 * } = useOfflineProgressSync();
 *
 * // Save progress locally if offline
 * if (!isOnline) {
 *   saveProgressOffline(materialId, 75, 120);
 * }
 * ```
 */
export function useOfflineProgressSync(): UseOfflineProgressSyncResult {
  const [pendingUpdates, setPendingUpdates] = useState<OfflineProgressUpdate[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const { isOnline } = useNetworkStatus();
  const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load pending updates on mount
  useEffect(() => {
    setPendingUpdates(getOfflineUpdates());
  }, []);

  // Attempt to sync when online
  useEffect(() => {
    if (isOnline && pendingUpdates.length > 0) {
      // Debounce sync attempt
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
      }

      syncTimeoutRef.current = setTimeout(() => {
        syncPendingUpdates();
      }, 1000); // Wait 1 second after coming online
    }

    return () => {
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
      }
    };
  }, [isOnline, pendingUpdates.length]);

  /**
   * Sync all pending updates with the backend
   */
  const syncPendingUpdates = useCallback(async () => {
    if (isSyncing || !isOnline || pendingUpdates.length === 0) {
      return;
    }

    setIsSyncing(true);
    setSyncError(null);

    try {
      const updates = getOfflineUpdates();

      for (const update of updates) {
        try {
          await api.patch(
            `/materials/${update.materialId}/progress/`,
            {
              progress_percentage: update.progress,
              time_spent: update.timeSpent,
            },
          );

          // Remove from pending after successful sync
          removeOfflineUpdate(update.materialId);
          setPendingUpdates((prev) =>
            prev.filter((u) => u.materialId !== update.materialId),
          );
        } catch (error) {
          // Continue with next update if one fails
          console.error(
            `Failed to sync progress for material ${update.materialId}:`,
            error,
          );
        }
      }

      // Show success message if some updates synced
      if (updates.length > 0) {
        toast.success("Progress synced successfully");
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to sync progress";
      setSyncError(errorMessage);
      toast.error(`Sync failed: ${errorMessage}`);
    } finally {
      setIsSyncing(false);
    }
  }, [isSyncing, isOnline, pendingUpdates.length]);

  /**
   * Save progress locally (for offline use)
   */
  const saveProgressOffline = useCallback(
    (
      materialId: string | number,
      progress: number,
      timeSpent: number,
    ) => {
      const update: OfflineProgressUpdate = {
        materialId,
        progress: Math.min(Math.max(progress, 0), 100),
        timeSpent: Math.max(timeSpent, 0),
        timestamp: new Date().toISOString(),
        synced: false,
      };

      saveOfflineUpdate(update);
      setPendingUpdates((prev) => {
        const filtered = prev.filter((u) => u.materialId !== materialId);
        return [...filtered, update];
      });

      // If online, try to sync immediately
      if (isOnline) {
        syncPendingUpdates();
      } else {
        toast.info("Progress saved locally. Will sync when online.");
      }
    },
    [isOnline, syncPendingUpdates],
  );

  /**
   * Manually trigger sync
   */
  const syncNow = useCallback(async () => {
    if (!isOnline) {
      toast.error("Cannot sync while offline");
      return;
    }

    await syncPendingUpdates();
  }, [isOnline, syncPendingUpdates]);

  /**
   * Clear all pending updates
   */
  const clearPending = useCallback(() => {
    clearOfflineUpdates();
    setPendingUpdates([]);
    toast.info("Pending progress updates cleared");
  }, []);

  return {
    pendingUpdates,
    isSyncing,
    syncError,
    saveProgressOffline,
    syncNow,
    clearPending,
    isOnline,
  };
}
