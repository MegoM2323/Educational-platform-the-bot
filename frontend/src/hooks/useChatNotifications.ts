// Хук для отслеживания уведомлений чата
import { useQuery } from '@tanstack/react-query';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

interface ChatNotification {
  unread_messages: number;
  unread_threads: number;
  has_new_messages: boolean;
}

export function useChatNotifications() {
  return useQuery({
    queryKey: ['chat', 'notifications'],
    queryFn: async (): Promise<ChatNotification> => {
      const response = await unifiedAPI.request<ChatNotification>('/chat/notifications/');
      if (response.error) {
        // Return default values if endpoint not available or returns error
        console.warn('[useChatNotifications] API error, using defaults:', response.error);
        return {
          unread_messages: 0,
          unread_threads: 0,
          has_new_messages: false
        };
      }
      return response.data!;
    },
    refetchInterval: 30 * 1000, // Обновлять каждые 30 секунд
    staleTime: 10 * 1000, // 10 секунд
    retry: 1, // Retry once before giving up
  });
}

// Хук для получения количества непрочитанных сообщений в конкретном чате
export function useChatUnreadCount(chatId: number) {
  return useQuery({
    queryKey: ['chat', 'unread', chatId],
    queryFn: async (): Promise<number> => {
      const response = await unifiedAPI.request<{ unread_count: number }>(`/chat/rooms/${chatId}/unread-count/`);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!.unread_count;
    },
    refetchInterval: 30 * 1000,
    staleTime: 10 * 1000,
  });
}
