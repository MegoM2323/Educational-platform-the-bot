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
      forumAPI.editForumMessage(messageId, data),

    onMutate: async ({ messageId, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId, 50, 0] });

      // Snapshot previous value
      const previousMessages = queryClient.getQueryData<ForumMessage[]>(['forum-messages', chatId, 50, 0]);

      // Optimistically update
      queryClient.setQueryData<ForumMessage[]>(['forum-messages', chatId, 50, 0], (old) =>
        old?.map((msg) =>
          msg.id === messageId
            ? { ...msg, content: data.content, is_edited: true, updated_at: new Date().toISOString() }
            : msg
        )
      );

      return { previousMessages };
    },

    onError: (error, variables, context) => {
      // Rollback on error
      if (context?.previousMessages) {
        queryClient.setQueryData(['forum-messages', chatId, 50, 0], context.previousMessages);
      }
      toast.error('Не удалось отредактировать сообщение');
      onError?.(error as Error);
    },

    onSuccess: (data) => {
      toast.success('Сообщение отредактировано');
      onSuccess?.(data);
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId, 50, 0] });
    },
  });
};
