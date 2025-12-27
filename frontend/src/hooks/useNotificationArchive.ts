import { useState, useCallback, useEffect } from 'react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  type: string;
  priority: string;
  recipient_id?: number;
  created_at: string;
  archived_at: string;
  is_read: boolean;
  data?: Record<string, any>;
}

interface ArchiveFilters {
  search?: string;
  type?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: NotificationItem[];
}

/**
 * Custom hook for managing notification archive operations
 *
 * Handles:
 * - Fetching archived notifications with pagination
 * - Filtering and searching
 * - Restoring individual notifications
 * - Restoring multiple notifications in bulk
 * - Permanently deleting notifications
 * - Managing loading and error states
 *
 * @example
 * ```tsx
 * const { notifications, isLoading, restoreNotification } = useNotificationArchive();
 * ```
 */
export const useNotificationArchive = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);
  const [filters, setFilters] = useState<ArchiveFilters>({});

  /**
   * Fetch archived notifications from API
   */
  const fetchArchiveNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Build query parameters
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('limit', pageSize.toString());

      if (filters.search) {
        params.append('search', filters.search);
      }
      if (filters.type) {
        params.append('type', filters.type);
      }
      if (filters.status) {
        params.append('status', filters.status);
      }
      if (filters.date_from) {
        params.append('date_from', filters.date_from);
      }
      if (filters.date_to) {
        params.append('date_to', filters.date_to);
      }

      const response = await unifiedAPI.get<PaginatedResponse>(
        `/api/notifications/archive/?${params.toString()}`
      );

      setNotifications(response.results);
      setTotalCount(response.count);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch archived notifications';
      setError(errorMessage);
      logger.error('Error fetching archive notifications', { error: err });
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, filters]);

  /**
   * Fetch notifications on mount and when filters change
   */
  useEffect(() => {
    fetchArchiveNotifications();
  }, [fetchArchiveNotifications]);

  /**
   * Restore a single archived notification
   */
  const restoreNotification = useCallback(
    async (notificationId: number) => {
      try {
        const response = await unifiedAPI.patch<NotificationItem>(
          `/api/notifications/${notificationId}/restore/`,
          {}
        );

        // Remove from archive list
        setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
        setTotalCount((prev) => Math.max(0, prev - 1));

        logger.info('Notification restored', { id: notificationId });
        return response;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to restore notification';
        logger.error('Error restoring notification', { error: err, id: notificationId });
        throw new Error(errorMessage);
      }
    },
    []
  );

  /**
   * Restore multiple archived notifications in bulk
   */
  const bulkRestore = useCallback(
    async (notificationIds: number[]) => {
      try {
        const response = await unifiedAPI.post<{
          restored_count: number;
          not_found: number;
          errors: string[];
        }>('/api/notifications/bulk-restore/', {
          notification_ids: notificationIds,
        });

        // Remove restored notifications from list
        if (response.restored_count > 0) {
          setNotifications((prev) =>
            prev.filter((n) => !notificationIds.includes(n.id))
          );
          setTotalCount((prev) => Math.max(0, prev - response.restored_count));
        }

        logger.info('Bulk restore completed', { restored: response.restored_count });
        return response;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to bulk restore notifications';
        logger.error('Error in bulk restore', { error: err });
        throw new Error(errorMessage);
      }
    },
    []
  );

  /**
   * Delete a single archived notification permanently
   */
  const deleteNotification = useCallback(
    async (notificationId: number) => {
      try {
        await unifiedAPI.delete(`/api/notifications/${notificationId}/`);

        // Remove from archive list
        setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
        setTotalCount((prev) => Math.max(0, prev - 1));

        logger.info('Notification deleted', { id: notificationId });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to delete notification';
        logger.error('Error deleting notification', { error: err, id: notificationId });
        throw new Error(errorMessage);
      }
    },
    []
  );

  /**
   * Delete multiple archived notifications permanently
   */
  const bulkDelete = useCallback(
    async (notificationIds: number[]) => {
      try {
        // Delete each notification
        await Promise.all(
          notificationIds.map((id) =>
            unifiedAPI.delete(`/api/notifications/${id}/`)
          )
        );

        // Remove from archive list
        setNotifications((prev) =>
          prev.filter((n) => !notificationIds.includes(n.id))
        );
        setTotalCount((prev) => Math.max(0, prev - notificationIds.length));

        logger.info('Bulk delete completed', { count: notificationIds.length });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to delete notifications';
        logger.error('Error in bulk delete', { error: err });
        throw new Error(errorMessage);
      }
    },
    []
  );

  return {
    notifications,
    isLoading,
    error,
    page,
    setPage,
    pageSize,
    totalCount,
    filters,
    setFilters,
    restoreNotification,
    bulkRestore,
    deleteNotification,
    bulkDelete,
    refetch: fetchArchiveNotifications,
  };
};
