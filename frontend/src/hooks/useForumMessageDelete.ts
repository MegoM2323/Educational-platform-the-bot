import { useMutation, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumMessage } from '../integrations/api/forumAPI';
import { toast } from 'sonner';

interface UseForumMessageDeleteOptions {
  chatId: number;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useForumMessageDelete = ({ chatId, onSuccess, onError }: UseForumMessageDeleteOptions) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: number) => forumAPI.deleteForumMessage(chatId, messageId),

    onMutate: async (messageId) => {
      // Cancel outgoing refetches for all queries matching this chatId
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      // Snapshot previous value - get ALL matching queries using pattern matching
      const previousQueries = queryClient.getQueriesData<ForumMessage[]>({
        queryKey: ['forum-messages', chatId],
      });

      // Optimistically remove message from ALL queries for this chat
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages', chatId], exact: false },
        (old) => old?.filter((msg) => msg.id !== messageId)
      );

      return { previousQueries };
    },

    onError: (error, messageId, context) => {
      // Rollback on error - restore ALL previous queries
      if (context?.previousQueries) {
        context.previousQueries.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      toast.error('Не удалось удалить сообщение');
      onError?.(error as Error);
    },

    onSuccess: () => {
      toast.success('Сообщение успешно удалено');
      onSuccess?.();
    },

    onSettled: () => {
      // Invalidate messages cache to ensure fresh data
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId] });

      // Update forum chats to show updated last_message after deletion
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
    },
  });
};
