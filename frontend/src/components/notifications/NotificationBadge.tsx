import { useState, useEffect, useRef } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { logger } from '@/utils/logger';
import { useNotificationCenter, type Notification } from '@/hooks/useNotificationCenter';
import { useAuth } from '@/contexts/AuthContext';
import { Bell } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface NotificationBadgeProps {
  className?: string;
  showZero?: boolean;
  showPreview?: boolean;
  previewCount?: number;
  variant?: 'default' | 'icon' | 'compact';
}

/**
 * NotificationBadge Component
 *
 * Displays unread notification count with real-time WebSocket updates.
 * Features:
 * - Animated pulse on new notification
 * - Hover preview of latest notifications
 * - Real-time unread count synchronization
 * - Responsive sizing
 * - Type-based color coding
 * - Offline detection and reconnection
 *
 * @example
 * ```tsx
 * // Simple badge with count
 * <NotificationBadge />
 *
 * // With icon variant
 * <NotificationBadge variant="icon" />
 *
 * // With preview on hover
 * <NotificationBadge showPreview previewCount={3} />
 * ```
 */
export function NotificationBadge({
  className,
  showZero = false,
  showPreview = true,
  previewCount = 3,
  variant = 'default',
}: NotificationBadgeProps) {
  const { user } = useAuth();
  const { unreadCount, notifications, refetch } = useNotificationCenter();
  const [displayCount, setDisplayCount] = useState(unreadCount);
  const [showPulse, setShowPulse] = useState(false);
  const [showPreviewPopover, setShowPreviewPopover] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const pulseTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const wsRef = useRef<WebSocket | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  /**
   * Setup WebSocket connection for real-time notification updates
   */
  useEffect(() => {
    if (!user) return;

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(
          `${protocol}//${window.location.host}/ws/notifications/`
        );

        ws.onopen = () => {
          logger.info('NotificationBadge WebSocket connected');
          setIsOnline(true);
          // Clear any pending reconnection timeout
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'notification_received') {
              // Trigger pulse animation
              setShowPulse(true);
              if (pulseTimeoutRef.current) {
                clearTimeout(pulseTimeoutRef.current);
              }
              pulseTimeoutRef.current = setTimeout(() => {
                setShowPulse(false);
              }, 3000);

              // Update count
              setDisplayCount((prev) => prev + 1);

              logger.info('New notification received in badge', {
                id: data.notification?.id,
              });
            }
          } catch (err) {
            logger.error('Error parsing WebSocket message in badge', { error: err });
          }
        };

        ws.onerror = (error) => {
          logger.error('WebSocket error in badge', { error });
          setIsOnline(false);
        };

        ws.onclose = () => {
          logger.info('WebSocket disconnected from badge');
          setIsOnline(false);
          // Attempt reconnection after 5 seconds
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        };

        wsRef.current = ws;
      } catch (err) {
        logger.error('Error setting up WebSocket in badge', { error: err });
        setIsOnline(false);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    // Handle online/offline events
    const handleOnline = () => {
      setIsOnline(true);
      // Refetch to ensure we have latest data
      refetch();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (pulseTimeoutRef.current) {
        clearTimeout(pulseTimeoutRef.current);
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [user, refetch]);

  /**
   * Sync display count with hook unread count
   */
  useEffect(() => {
    setDisplayCount(unreadCount);
  }, [unreadCount]);

  /**
   * Close preview when clicking outside
   */
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (previewRef.current && !previewRef.current.contains(event.target as Node)) {
        setShowPreviewPopover(false);
      }
    };

    if (showPreviewPopover) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showPreviewPopover]);

  /**
   * Get color based on unread count
   */
  const getColorByCount = () => {
    if (displayCount === 0) return 'bg-gray-400';
    if (displayCount <= 5) return 'bg-blue-500';
    if (displayCount <= 10) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  /**
   * Get color based on notification type
   */
  const getTypeColor = (type: string): string => {
    const colorMap: Record<string, string> = {
      system: 'bg-blue-100 text-blue-800',
      message_new: 'bg-green-100 text-green-800',
      assignment_submitted: 'bg-purple-100 text-purple-800',
      material_feedback: 'bg-indigo-100 text-indigo-800',
      payment_received: 'bg-emerald-100 text-emerald-800',
      invoice_created: 'bg-amber-100 text-amber-800',
    };
    return colorMap[type] || 'bg-gray-100 text-gray-800';
  };

  if (displayCount === 0 && !showZero) {
    return null;
  }

  /**
   * Icon variant - just bell icon with badge
   */
  if (variant === 'icon') {
    return (
      <div className={cn('relative inline-block', className)}>
        <Bell className="w-5 h-5 text-gray-700" />
        {displayCount > 0 && (
          <Badge
            className={cn(
              'absolute -top-2 -right-2 h-5 w-5 min-w-[20px] flex items-center justify-center p-0 text-xs',
              getColorByCount(),
              showPulse && 'animate-pulse'
            )}
          >
            {displayCount > 99 ? '99+' : displayCount}
          </Badge>
        )}
        {!isOnline && (
          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-gray-400 rounded-full border border-white" />
        )}
      </div>
    );
  }

  /**
   * Compact variant - badge only
   */
  if (variant === 'compact') {
    return (
      <Badge
        className={cn(
          'inline-flex items-center justify-center min-w-[24px] h-6 text-xs font-bold',
          getColorByCount(),
          showPulse && 'animate-pulse',
          className
        )}
      >
        {displayCount > 99 ? '99+' : displayCount}
      </Badge>
    );
  }

  /**
   * Default variant with preview
   */
  const previewNotifications = notifications.slice(0, previewCount);
  const unreadPreviewNotifications = previewNotifications.filter((n) => !n.is_read);

  return (
    <div
      ref={previewRef}
      className={cn('relative inline-block', className)}
      onMouseEnter={() => showPreview && displayCount > 0 && setShowPreviewPopover(true)}
      onMouseLeave={() => setShowPreviewPopover(false)}
    >
      <div className="relative inline-flex items-center gap-2 cursor-pointer">
        <span className="text-sm font-medium text-gray-700">Notifications</span>
        <Badge
          className={cn(
            'h-6 min-w-[24px] flex items-center justify-center text-xs font-bold',
            getColorByCount(),
            showPulse && 'animate-pulse shadow-lg shadow-red-500/50'
          )}
        >
          {displayCount > 99 ? '99+' : displayCount}
        </Badge>
        {!isOnline && (
          <div
            className="w-2 h-2 bg-gray-400 rounded-full"
            title="Offline - will reconnect automatically"
          />
        )}
      </div>

      {/* Preview Popover */}
      {showPreviewPopover && showPreview && displayCount > 0 && (
        <Card className="absolute top-full mt-2 right-0 w-80 z-50 shadow-lg border border-gray-200">
          <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
            {/* Preview header */}
            <div className="flex items-center justify-between pb-2 border-b">
              <h3 className="font-semibold text-sm text-gray-900">Latest Notifications</h3>
              {unreadPreviewNotifications.length > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {unreadPreviewNotifications.length} new
                </Badge>
              )}
            </div>

            {/* Preview list */}
            {previewNotifications.length > 0 ? (
              <div className="space-y-2">
                {previewNotifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={cn(
                      'p-3 rounded-md border transition-colors',
                      notification.is_read
                        ? 'bg-gray-50 border-gray-200'
                        : 'bg-blue-50 border-blue-200'
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {notification.title}
                        </p>
                        <p className="text-xs text-gray-600 line-clamp-2 mt-1">
                          {notification.message}
                        </p>
                      </div>
                      {!notification.is_read && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-1" />
                      )}
                    </div>

                    {/* Type badge */}
                    <div className="mt-2 flex flex-wrap gap-1">
                      <span
                        className={cn(
                          'text-xs px-2 py-0.5 rounded',
                          getTypeColor(notification.type)
                        )}
                      >
                        {notification.type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500">No notifications yet</p>
              </div>
            )}

            {/* Footer with count */}
            {displayCount > previewCount && (
              <div className="pt-2 border-t text-center">
                <p className="text-xs text-gray-600">
                  +{displayCount - previewCount} more notification
                  {displayCount - previewCount !== 1 ? 's' : ''}
                </p>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
