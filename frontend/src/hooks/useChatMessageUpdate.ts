import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI, ChatMessage } from '../integrations/api/chatAPI';
import { toast } from 'sonner';

interface UseChatMessageUpdateOptions {
  chatId: number;
  onSuccess?: (message: ChatMessage) => void;
  onError?: (error: Error) => void;
}

export const useChatMessageUpdate = ({ chatId, onSuccess, onError }: UseChatMessageUpdateOptions) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, data }: { messageId: number; data: { content: string } }) =>
      chatAPI.editMessage(chatId, messageId, data.content),

    onMutate: async ({ messageId, data }) => {
      await queryClient.cancelQueries({ queryKey: ['chat-messages', chatId] });

      const previousQueries = queryClient.getQueriesData<ChatMessage[]>({
        queryKey: ['chat-messages', chatId],
      });

      queryClient.setQueriesData<ChatMessage[]>(
        { queryKey: ['chat-messages', chatId], exact: false },
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
      queryClient.invalidateQueries({ queryKey: ['chat-messages', chatId] });

      queryClient.invalidateQueries({ queryKey: ['chat', 'chats'] });
    },
  });
};
