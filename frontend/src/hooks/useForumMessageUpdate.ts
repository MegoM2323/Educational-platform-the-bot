import { useMutation, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumMessage, EditMessageRequest } from '../integrations/api/forumAPI';
import { toast } from 'sonner';

interface UseForumMessageUpdateOptions {
  chatId: number;
  onSuccess?: (message: ForumMessage) => void;
  onError?: (error: Error) => void;
}

export const useForumMessageUpdate = ({ chatId, onSuccess, onError }: UseForumMessageUpdateOptions) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, data }: { messageId: number; data: EditMessageRequest }) =>
      forumAPI.editForumMessage(chatId, messageId, data),

    onMutate: async ({ messageId, data }) => {
      // Cancel outgoing refetches for all queries matching this chatId
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      // Snapshot previous value - get ALL matching queries using pattern matching
      const previousQueries = queryClient.getQueriesData<ForumMessage[]>({
        queryKey: ['forum-messages', chatId],
      });

      // Optimistically update ALL queries for this chat
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages', chatId], exact: false },
        (old) =>
          old?.map((msg) =>
            msg.id === messageId
              ? { ...msg, content: data.content, is_edited: true, updated_at: new Date().toISOString() }
              : msg
          )
      );

      return { previousQueries };
    },

    onError: (error, variables, context) => {
      // Rollback on error - restore ALL previous queries
      if (context?.previousQueries) {
        context.previousQueries.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      toast.error('Не удалось отредактировать сообщение');
      onError?.(error as Error);
    },

    onSuccess: (data) => {
      toast.success('Сообщение отредактировано');
      onSuccess?.(data);
    },

    onSettled: () => {
      // Invalidate messages cache to ensure fresh data
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId] });

      // Update forum chats to show edited last_message if needed
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
    },
  });
};
