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
        throw new Error(response.error);
      }
      return response.data!;
    },
    refetchInterval: 30 * 1000, // Обновлять каждые 30 секунд
    staleTime: 10 * 1000, // 10 секунд
  });
}

// Хук для получения количества непрочитанных сообщений в конкретном чате
export function useChatUnreadCount(chatId: number) {
  return useQuery({
    queryKey: ['chat', 'unread', chatId],
    queryFn: async (): Promise<number> => {
      const response = await apiClient.request<{ unread_count: number }>(`/chat/rooms/${chatId}/unread-count/`);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!.unread_count;
    },
    refetchInterval: 30 * 1000,
    staleTime: 10 * 1000,
  });
}
