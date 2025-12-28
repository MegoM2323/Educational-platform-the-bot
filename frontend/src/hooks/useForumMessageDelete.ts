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
    mutationFn: (messageId: number) => forumAPI.deleteForumMessage(messageId),

    onMutate: async (messageId) => {
      // Cancel outgoing refetches for all queries matching this chatId
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      // Snapshot previous value - get first matching query data
      const previousMessages = queryClient.getQueryData<ForumMessage[]>(['forum-messages', chatId, 50, 0]);

      // Optimistically remove message from ALL queries for this chat
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages', chatId], exact: false },
        (old) => old?.filter((msg) => msg.id !== messageId)
      );

      return { previousMessages };
    },

    onError: (error, messageId, context) => {
      // Rollback on error - restore to all queries
      if (context?.previousMessages) {
        queryClient.setQueriesData(
          { queryKey: ['forum-messages', chatId], exact: false },
          context.previousMessages
        );
      }
      toast.error('Не удалось удалить сообщение');
      onError?.(error as Error);
    },

    onSuccess: () => {
      toast.success('Сообщение успешно удалено');
      onSuccess?.();
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId] });
    },
  });
};
