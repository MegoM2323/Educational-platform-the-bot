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
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId, 50, 0] });

      // Snapshot previous value
      const previousMessages = queryClient.getQueryData<ForumMessage[]>(['forum-messages', chatId, 50, 0]);

      // Optimistically remove message
      queryClient.setQueryData<ForumMessage[]>(['forum-messages', chatId, 50, 0], (old) =>
        old?.filter((msg) => msg.id !== messageId)
      );

      return { previousMessages };
    },

    onError: (error, messageId, context) => {
      // Rollback on error
      if (context?.previousMessages) {
        queryClient.setQueryData(['forum-messages', chatId, 50, 0], context.previousMessages);
      }
      toast.error('Не удалось удалить сообщение');
      onError?.(error as Error);
    },

    onSuccess: () => {
      toast.success('Сообщение успешно удалено');
      onSuccess?.();
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId, 50, 0] });
    },
  });
};
