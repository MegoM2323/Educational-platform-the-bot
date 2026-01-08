import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI, ChatMessage } from '../integrations/api/chatAPI';
import { toast } from 'sonner';

interface UseForumMessageDeleteOptions {
  chatId: number;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useForumMessageDelete = ({ chatId, onSuccess, onError }: UseForumMessageDeleteOptions) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: number) => chatAPI.deleteMessage(chatId, messageId),

    onMutate: async (messageId) => {
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      const previousQueries = queryClient.getQueriesData<ChatMessage[]>({
        queryKey: ['forum-messages', chatId],
      });

      queryClient.setQueriesData<ChatMessage[]>(
        { queryKey: ['forum-messages', chatId], exact: false },
        (old) => old?.filter((msg) => msg.id !== messageId)
      );

      return { previousQueries };
    },

    onError: (error, messageId, context) => {
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
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId] });

      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
    },
  });
};
