import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumMessage, SendForumMessageRequest, EditMessageRequest } from '../integrations/api/forumAPI';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

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
  const { user } = useAuth();

  return useMutation({
    mutationFn: ({ chatId, data, file }: { chatId: number; data: SendForumMessageRequest; file?: File }) =>
      forumAPI.sendForumMessage(chatId, { ...data, file }),
    onMutate: async ({ chatId, data, file }) => {
      // Cancel outgoing refetches to avoid overwriting our optimistic update
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      // Snapshot previous value for rollback
      const previousMessages = queryClient.getQueryData<ForumMessage[]>(['forum-messages', chatId]);

      // Optimistic update: IMMEDIATELY add temporary message to cache
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages', chatId], exact: false },
        (oldData) => {
          if (!oldData) return oldData;

          // Create temporary optimistic message with REAL current user data
          const optimisticMessage: ForumMessage = {
            id: Date.now(), // Temporary ID
            content: data.content,
            sender: {
              id: user?.id || 0, // REAL current user ID - determines message side (left/right)
              full_name: user?.first_name && user?.last_name
                ? `${user.first_name} ${user.last_name}`.trim()
                : user?.email || 'Вы',
              role: user?.role || '',
            },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            is_read: false,
            is_edited: false,
            message_type: file ? 'file' : 'text',
            file_name: file?.name,
            file_type: file?.type,
            is_image: file ? file.type.startsWith('image/') : false,
          };

          // Add optimistic message to the end
          return [...oldData, optimisticMessage];
        }
      );

      return { previousMessages };
    },
    onSuccess: (message, variables) => {
      // Replace optimistic message with real server response
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages', variables.chatId], exact: false },
        (oldData) => {
          if (!oldData) return [message];

          // Remove temporary optimistic message (has temporary timestamp-based ID)
          // Keep only messages with real server IDs (< Date.now() threshold)
          const now = Date.now();
          const withoutOptimistic = oldData.filter((msg) =>
            msg.id < now - 60000 // Real message IDs are much smaller than timestamps
          );

          // Check if real message already exists (from WebSocket)
          const exists = withoutOptimistic.some((msg) => msg.id === message.id);
          if (exists) return withoutOptimistic;

          // Add real message
          return [...withoutOptimistic, message];
        }
      );

      // Update forum chats to show last_message
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
      toast.success('Сообщение отправлено');
    },
    onError: (error: Error, variables, context) => {
      // Rollback optimistic update on error
      if (context?.previousMessages) {
        queryClient.setQueryData(['forum-messages', variables.chatId], context.previousMessages);
      }
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

export const useEditForumMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ messageId, data }: { messageId: number; data: EditMessageRequest }) =>
      forumAPI.editForumMessage(messageId, data),
    onSuccess: (updatedMessage, variables) => {
      // Update the message in all cached queries
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages'] },
        (oldData) => {
          if (!oldData) return oldData;
          return oldData.map((msg) =>
            msg.id === updatedMessage.id ? updatedMessage : msg
          );
        }
      );

      toast.success('Сообщение отредактировано');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка редактирования: ${error.message}`);
    },
  });
};

export const useDeleteForumMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: number) => forumAPI.deleteForumMessage(messageId),
    onSuccess: (_, messageId) => {
      // Remove the message from all cached queries
      queryClient.setQueriesData<ForumMessage[]>(
        { queryKey: ['forum-messages'] },
        (oldData) => {
          if (!oldData) return oldData;
          return oldData.filter((msg) => msg.id !== messageId);
        }
      );

      toast.success('Сообщение удалено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления: ${error.message}`);
    },
  });
};
