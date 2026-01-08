import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI, ChatMessage } from '../integrations/api/chatAPI';
import { toast } from 'sonner';

interface UseForumMessageUpdateOptions {
  chatId: number;
  onSuccess?: (message: ChatMessage) => void;
  onError?: (error: Error) => void;
}

export const useForumMessageUpdate = ({ chatId, onSuccess, onError }: UseForumMessageUpdateOptions) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, data }: { messageId: number; data: { content: string } }) =>
      chatAPI.editMessage(chatId, messageId, data.content),

    onMutate: async ({ messageId, data }) => {
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      const previousQueries = queryClient.getQueriesData<ChatMessage[]>({
        queryKey: ['forum-messages', chatId],
      });

      queryClient.setQueriesData<ChatMessage[]>(
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
      queryClient.invalidateQueries({ queryKey: ['forum-messages', chatId] });

      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
    },
  });
};
