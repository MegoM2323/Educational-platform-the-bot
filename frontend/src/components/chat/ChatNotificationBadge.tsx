import { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { useChatNotifications } from '@/hooks/useChatNotifications';
import { notificationWebSocketService, Notification } from '@/services/notificationWebSocketService';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

interface ChatNotificationBadgeProps {
  className?: string;
  showZero?: boolean;
}

export function ChatNotificationBadge({ className, showZero = false }: ChatNotificationBadgeProps) {
  const { user } = useAuth();
  const { data: notifications, isLoading } = useChatNotifications();
  const [realTimeUnreadCount, setRealTimeUnreadCount] = useState(0);

  // Подключение к WebSocket уведомлениям
  useEffect(() => {
    if (user) {
      notificationWebSocketService.connectToNotifications(user.id, {
        onNotification: (notification: Notification) => {
          if (!notification.is_read) {
            setRealTimeUnreadCount(prev => prev + 1);
          }
        },
        onError: (error) => {
          console.error('WebSocket notification error:', error);
        }
      });

      return () => {
        notificationWebSocketService.disconnectFromNotifications();
      };
    }
  }, [user]);

  if (isLoading) {
    return null;
  }

  const apiUnread = (notifications?.unread_messages || 0) + (notifications?.unread_threads || 0);
  const totalUnread = apiUnread + realTimeUnreadCount;

  if (totalUnread === 0 && !showZero) {
    return null;
  }

  return (
    <Badge 
      variant="destructive" 
      className={cn(
        'ml-auto h-5 min-w-[20px] flex items-center justify-center text-xs animate-pulse',
        className
      )}
    >
      {totalUnread > 99 ? '99+' : totalUnread}
    </Badge>
  );
}
