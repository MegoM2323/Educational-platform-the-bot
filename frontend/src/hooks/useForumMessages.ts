import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumMessage, SendForumMessageRequest } from '../integrations/api/forumAPI';
import { toast } from 'sonner';

export const useForumMessages = (chatId: number | null, limit: number = 50, offset: number = 0) => {
  return useQuery({
    queryKey: ['forum-messages', chatId, limit, offset],
    queryFn: () => {
      if (!chatId) throw new Error('Chat ID is required');
      return forumAPI.getForumMessages(chatId, limit, offset);
    },
    enabled: !!chatId,
    staleTime: Infinity, // Rely on WebSocket for real-time updates, no polling
    retry: 2,
  });
};

export const useSendForumMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, data }: { chatId: number; data: SendForumMessageRequest }) =>
      forumAPI.sendForumMessage(chatId, data),
    onSuccess: (message, variables) => {
      queryClient.invalidateQueries({ queryKey: ['forum-messages', variables.chatId] });
      queryClient.invalidateQueries({ queryKey: ['forum-chats'] });
      toast.success('Сообщение отправлено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки сообщения: ${error.message}`);
    },
  });
};

export const usePaginatedForumMessages = (chatId: number | null) => {
  const [limit, setLimit] = [50, () => {}];
  const [offset, setOffset] = [0, () => {}];

  const query = useForumMessages(chatId, limit, offset);

  return {
    ...query,
    offset,
    setOffset,
    loadMore: () => setOffset((prev: number) => prev + limit),
    loadBefore: () => setOffset((prev: number) => Math.max(0, prev - limit)),
  };
};
