import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI, ChatMessage } from '../integrations/api/chatAPI';
import { toast } from 'sonner';

interface UseChatMessageDeleteOptions {
  chatId: number;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useChatMessageDelete = ({ chatId, onSuccess, onError }: UseChatMessageDeleteOptions) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: number) => chatAPI.deleteMessage(chatId, messageId),

    onMutate: async (messageId) => {
      await queryClient.cancelQueries({ queryKey: ['chat-messages', chatId] });

      const previousQueries = queryClient.getQueriesData<ChatMessage[]>({
        queryKey: ['chat-messages', chatId],
      });

      queryClient.setQueriesData<ChatMessage[]>(
        { queryKey: ['chat-messages', chatId], exact: false },
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
      queryClient.invalidateQueries({ queryKey: ['chat-messages', chatId] });

      queryClient.invalidateQueries({ queryKey: ['chat', 'chats'] });
    },
  });
};
