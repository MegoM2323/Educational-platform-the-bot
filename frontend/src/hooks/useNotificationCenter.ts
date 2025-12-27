import { useState, useCallback, useEffect, useRef } from 'react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

export interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  recipient_id?: number;
  created_at: string;
  is_read: boolean;
  is_sent: boolean;
  sent_at?: string;
  read_at?: string;
  data?: Record<string, any>;
}

interface NotificationFilters {
  type?: string;
  priority?: string;
  is_read?: boolean;
  search?: string;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Notification[];
}

/**
 * Custom hook for managing notifications in the notification center
 *
 * Handles:
 * - Fetching active notifications with pagination
 * - Filtering by type, priority, and read status
 * - Searching notifications
 * - Marking notifications as read/unread
 * - Deleting notifications
 * - Real-time WebSocket updates
 * - Unread count tracking
 *
 * @example
 * ```tsx
 * const { notifications, markAsRead, unreadCount } = useNotificationCenter();
 * ```
 */
export const useNotificationCenter = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalCount, setTotalCount] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filters, setFilters] = useState<NotificationFilters>({});
  const wsRef = useRef<WebSocket | null>(null);

  /**
   * Fetch notifications from API
   */
  const fetchNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Build query parameters
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('limit', pageSize.toString());

      if (filters.type) {
        params.append('type', filters.type);
      }
      if (filters.priority) {
        params.append('priority', filters.priority);
      }
      if (filters.is_read !== undefined) {
        params.append('is_read', filters.is_read.toString());
      }
      if (filters.search) {
        params.append('search', filters.search);
      }

      const response = await unifiedAPI.get<PaginatedResponse>(
        `/api/notifications/?${params.toString()}`
      );

      setNotifications(response.results);
      setTotalCount(response.count);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch notifications';
      setError(errorMessage);
      logger.error('Error fetching notifications', { error: err });
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, filters]);

  /**
   * Fetch unread count
   */
  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await unifiedAPI.get<{ unread_count: number }>(
        '/api/notifications/unread_count/'
      );
      setUnreadCount(response.unread_count);
    } catch (err) {
      logger.error('Error fetching unread count', { error: err });
    }
  }, []);

  /**
   * Fetch notifications on mount and when filters/page change
   */
  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  /**
   * Fetch unread count on mount
   */
  useEffect(() => {
    fetchUnreadCount();
  }, [fetchUnreadCount]);

  /**
   * Mark a single notification as read
   */
  const markAsRead = useCallback(
    async (notificationId: number) => {
      try {
        await unifiedAPI.post(`/api/notifications/${notificationId}/mark_read/`, {});

        // Update local state
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
          )
        );

        // Decrease unread count
        setUnreadCount((prev) => Math.max(0, prev - 1));

        logger.info('Notification marked as read', { id: notificationId });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to mark as read';
        logger.error('Error marking notification as read', { error: err, id: notificationId });
        throw new Error(errorMessage);
      }
    },
    []
  );

  /**
   * Mark multiple notifications as read
   */
  const markMultipleAsRead = useCallback(
    async (notificationIds: number[], markAll: boolean = false) => {
      try {
        const response = await unifiedAPI.post<{ message: string }>(
          '/api/notifications/mark_multiple_read/',
          {
            mark_all: markAll,
            notification_ids: markAll ? [] : notificationIds,
          }
        );

        if (markAll) {
          // Mark all as read
          setNotifications((prev) =>
            prev.map((n) => ({
              ...n,
              is_read: true,
              read_at: new Date().toISOString(),
            }))
          );
          setUnreadCount(0);
        } else {
          // Mark specific ones as read
          setNotifications((prev) =>
            prev.map((n) =>
              notificationIds.includes(n.id)
                ? { ...n, is_read: true, read_at: new Date().toISOString() }
                : n
            )
          );
          setUnreadCount((prev) =>
            Math.max(0, prev - notificationIds.filter((id) => {
              const notification = notifications.find((n) => n.id === id);
              return notification && !notification.is_read;
            }).length)
          );
        }

        logger.info('Multiple notifications marked as read', { count: notificationIds.length });
        return response;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to mark as read';
        logger.error('Error marking multiple as read', { error: err });
        throw new Error(errorMessage);
      }
    },
    [notifications]
  );

  /**
   * Delete a single notification
   */
  const deleteNotification = useCallback(
    async (notificationId: number) => {
      try {
        await unifiedAPI.delete(`/api/notifications/${notificationId}/`);

        const notification = notifications.find((n) => n.id === notificationId);
        if (notification && !notification.is_read) {
          setUnreadCount((prev) => Math.max(0, prev - 1));
        }

        setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
        setTotalCount((prev) => Math.max(0, prev - 1));

        logger.info('Notification deleted', { id: notificationId });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to delete notification';
        logger.error('Error deleting notification', { error: err, id: notificationId });
        throw new Error(errorMessage);
      }
    },
    [notifications]
  );

  /**
   * Delete multiple notifications
   */
  const deleteMultiple = useCallback(
    async (notificationIds: number[]) => {
      try {
        await Promise.all(
          notificationIds.map((id) => unifiedAPI.delete(`/api/notifications/${id}/`))
        );

        const deletedUnread = notificationIds.filter((id) => {
          const notification = notifications.find((n) => n.id === id);
          return notification && !notification.is_read;
        }).length;

        setUnreadCount((prev) => Math.max(0, prev - deletedUnread));
        setNotifications((prev) => prev.filter((n) => !notificationIds.includes(n.id)));
        setTotalCount((prev) => Math.max(0, prev - notificationIds.length));

        logger.info('Multiple notifications deleted', { count: notificationIds.length });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to delete notifications';
        logger.error('Error deleting multiple notifications', { error: err });
        throw new Error(errorMessage);
      }
    },
    [notifications]
  );

  /**
   * Setup WebSocket connection for real-time notifications
   */
  const setupWebSocket = useCallback(() => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/ws/notifications/`
      );

      ws.onopen = () => {
        logger.info('WebSocket connected for notifications');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'notification_received') {
            // New notification received
            const newNotification = data.notification as Notification;
            setNotifications((prev) => [newNotification, ...prev]);
            setUnreadCount((prev) => prev + 1);
            setTotalCount((prev) => prev + 1);
            logger.info('New notification received', { id: newNotification.id });
          }
        } catch (err) {
          logger.error('Error parsing WebSocket message', { error: err });
        }
      };

      ws.onerror = (error) => {
        logger.error('WebSocket error', { error });
      };

      ws.onclose = () => {
        logger.info('WebSocket disconnected');
        // Attempt reconnection after 5 seconds
        setTimeout(setupWebSocket, 5000);
      };

      wsRef.current = ws;
    } catch (err) {
      logger.error('Error setting up WebSocket', { error: err });
    }
  }, []);

  /**
   * Cleanup WebSocket on unmount
   */
  useEffect(() => {
    setupWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [setupWebSocket]);

  return {
    notifications,
    isLoading,
    error,
    page,
    setPage,
    pageSize,
    totalCount,
    unreadCount,
    filters,
    setFilters,
    markAsRead,
    markMultipleAsRead,
    deleteNotification,
    deleteMultiple,
    refetch: fetchNotifications,
  };
};
