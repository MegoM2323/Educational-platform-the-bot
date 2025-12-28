import { useQuery, useInfiniteQuery, useMutation, useQueryClient, InfiniteData } from '@tanstack/react-query';
import { forumAPI, ForumMessage, SendForumMessageRequest } from '../integrations/api/forumAPI';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Hook для загрузки сообщений форума с infinite scroll поддержкой
 * Использует useInfiniteQuery для эффективного управления пагинацией и кешем
 */
export const useForumMessages = (chatId: number | null) => {
  const MESSAGES_PER_PAGE = 50;

  return useInfiniteQuery<ForumMessage[], Error>({
    queryKey: ['forum-messages', chatId],
    queryFn: async ({ pageParam = 0 }) => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }

      try {
        // Fetch messages from API with pagination
        const messages = await forumAPI.getForumMessages(
          chatId,
          MESSAGES_PER_PAGE,
          pageParam as number
        );

        return messages;
      } catch (error: any) {
        // Provide user-friendly error messages
        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось загрузить сообщения';
        throw new Error(errorMessage);
      }
    },
    getNextPageParam: (lastPage, allPages) => {
      // If last page has fewer messages than requested, no more pages
      if (lastPage.length < MESSAGES_PER_PAGE) {
        return undefined;
      }

      // Calculate total fetched messages for next offset
      const totalFetched = allPages.reduce((sum, page) => sum + page.length, 0);

      // Return offset for the next batch of OLDER messages
      // Backend returns messages in chronological order (oldest first)
      // When scrolling up, we need to fetch earlier messages
      return totalFetched;
    },
    initialPageParam: 0,
    enabled: !!chatId,
    staleTime: 1000 * 60, // Consider data stale after 1 minute
    refetchOnMount: true, // Refetch when component mounts
    refetchOnWindowFocus: false, // Don't refetch on window focus to reduce server load
    retry: (failureCount, error) => {
      // Don't retry on authentication errors (401, 403)
      if (error.message.includes('401') || error.message.includes('403') ||
          error.message.includes('авторизован') || error.message.includes('доступ')) {
        return false;
      }
      // Retry up to 2 times for other errors
      return failureCount < 2;
    },
  });
};

/**
 * Legacy hook для обратной совместимости с существующим кодом
 * @deprecated Используйте useForumMessages вместо этого
 */
export const useForumMessagesLegacy = (chatId: number | null, limit: number = 50, offset: number = 0) => {
  const query = useQuery<ForumMessage[]>({
    queryKey: ['forum-messages-legacy', chatId, limit, offset],
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
  const { toast: toastHook } = useAuth(); // Get toast from context if available

  return useMutation({
    mutationFn: async ({ chatId, data, file }: { chatId: number; data: SendForumMessageRequest; file?: File }) => {
      try {
        return await forumAPI.sendForumMessage(chatId, { ...data, file });
      } catch (error: any) {
        // Provide user-friendly error messages
        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось отправить сообщение';
        throw new Error(errorMessage);
      }
    },
    onMutate: async ({ chatId, data, file }) => {
      // Cancel outgoing refetches to avoid overwriting our optimistic update
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      // Snapshot previous value for rollback (InfiniteData structure)
      const previousMessages = queryClient.getQueryData<InfiniteData<ForumMessage[]>>(['forum-messages', chatId]);

      // Create temporary optimistic message with REAL current user data
      const optimisticMessage: ForumMessage = {
        id: `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}` as any, // Temporary ID with collision prevention
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

      // Optimistic update: IMMEDIATELY add temporary message to InfiniteData cache
      queryClient.setQueryData<InfiniteData<ForumMessage[]>>(
        ['forum-messages', chatId],
        (oldData) => {
          if (!oldData) return oldData;

          // Add optimistic message to the last page
          const newPages = [...oldData.pages];
          const lastPageIndex = newPages.length - 1;
          newPages[lastPageIndex] = [...newPages[lastPageIndex], optimisticMessage];

          return {
            ...oldData,
            pages: newPages,
          };
        }
      );

      return { previousMessages };
    },
    onSuccess: (message, variables) => {
      // Replace optimistic message with real server response in InfiniteData structure
      queryClient.setQueryData<InfiniteData<ForumMessage[]>>(
        ['forum-messages', variables.chatId],
        (oldData) => {
          if (!oldData) {
            return {
              pages: [[message]],
              pageParams: [0],
            };
          }

          // Update all pages: remove temp message, check for duplicates, add real message
          const newPages = oldData.pages.map((page, index) => {
            // Remove temporary optimistic messages (string IDs starting with 'temp-')
            const withoutOptimistic = page.filter((msg) => typeof msg.id === 'number');

            // Add real message only to the last page
            if (index === oldData.pages.length - 1) {
              // Check if real message already exists (from WebSocket)
              const exists = withoutOptimistic.some((msg) => msg.id === message.id);
              if (!exists) {
                return [...withoutOptimistic, message];
              }
            }

            return withoutOptimistic;
          });

          return {
            ...oldData,
            pages: newPages,
          };
        }
      );

      // Invalidate messages cache to ensure all queries are fresh
      queryClient.invalidateQueries({ queryKey: ['forum-messages', variables.chatId] });

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


export const useDeleteForumMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: number) => forumAPI.deleteForumMessage(messageId),
    onSuccess: (_, messageId) => {
      // Remove the message from all cached InfiniteData queries
      queryClient.setQueriesData<InfiniteData<ForumMessage[]>>(
        { queryKey: ['forum-messages'] },
        (oldData) => {
          if (!oldData) return oldData;

          // Filter out deleted message from all pages
          const newPages = oldData.pages.map((page) =>
            page.filter((msg) => msg.id !== messageId)
          );

          return {
            ...oldData,
            pages: newPages,
          };
        }
      );

      // Invalidate messages cache to ensure fresh data
      queryClient.invalidateQueries({ queryKey: ['forum-messages'] });

      // Update forum chats to show updated last_message after deletion
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });

      toast.success('Сообщение удалено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления: ${error.message}`);
    },
  });
};
