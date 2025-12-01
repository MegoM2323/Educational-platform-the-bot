import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumMessage, SendForumMessageRequest } from '../integrations/api/forumAPI';
import { toast } from 'sonner';

export const useForumMessages = (chatId: number | null, limit: number = 50, offset: number = 0) => {
  const query = useQuery<ForumMessage[]>({
    queryKey: ['forum-messages', chatId, limit, offset],
    queryFn: async () => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }
      const messages = await forumAPI.getForumMessages(chatId, limit, offset);
      return messages;
    },
    enabled: !!chatId,
    staleTime: 1000 * 60, // Consider data stale after 1 minute, allow refetching
    refetchOnMount: true, // Refetch when component mounts
    refetchOnWindowFocus: false, // Don't refetch on window focus to reduce server load
    retry: 2,
  });

  return query;
};

export const useSendForumMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, data }: { chatId: number; data: SendForumMessageRequest }) =>
      forumAPI.sendForumMessage(chatId, data),
    onSuccess: (message, variables) => {
      // Optimistic update: immediately add the message to the cache
      queryClient.setQueryData<ForumMessage[]>(
        ['forum-messages', variables.chatId, 50, 0],
        (oldData) => {
          if (!oldData) return [message];

          // Check if message already exists (avoid duplicates)
          const exists = oldData.some((msg) => msg.id === message.id);
          if (exists) return oldData;

          // Add new message to the end (chronological order)
          return [...oldData, message];
        }
      );

      // Also invalidate to refetch latest data from server
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
