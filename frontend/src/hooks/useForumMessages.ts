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
    queryFn: async ({ pageParam = 0, signal }) => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }

      try {
        // T032: Pass AbortSignal to API for request cancellation
        const messages = await forumAPI.getForumMessages(
          chatId,
          MESSAGES_PER_PAGE,
          pageParam as number,
          signal
        );

        return messages;
      } catch (error: any) {
        // T032: Handle AbortError gracefully (don't show as user error)
        if (error.name === 'AbortError') {
          throw error; // Let React Query handle it silently
        }

        // Provide user-friendly error messages
        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось загрузить сообщения';
        throw new Error(errorMessage);
      }
    },
    getNextPageParam: (lastPage, allPages) => {
      // T029: Fix race condition by using stable calculation
      // Calculate offset based on actual page count, not reducing allPages
      const currentOffset = allPages.flat().length;
      const hasMore = lastPage.length === MESSAGES_PER_PAGE;

      return hasMore ? currentOffset : undefined;
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
    queryFn: async ({ signal }) => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }
      // T033: Add AbortController support
      const messages = await forumAPI.getForumMessages(chatId, limit, offset, signal);
      return messages;
    },
    enabled: !!chatId,
    staleTime: 1000 * 60, // Consider data stale after 1 minute, allow refetching
    // T033: Use placeholderData for smooth transitions on offset changes
    placeholderData: (previousData) => previousData,
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
      // T037: Cancel outgoing refetches to avoid race between mutation and background refetch
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      // T030: Snapshot previous value for rollback (InfiniteData structure)
      const previousMessages = queryClient.getQueryData<InfiniteData<ForumMessage[]>>(['forum-messages', chatId]);

      // T038: Create unique temporary ID using negative timestamp
      const tempId = -Date.now();

      // T036: Access fresh user data from context at mutation time (not closure time)
      // user variable is from useAuth() hook, accessed each time mutation runs
      const currentUser = user;

      // Create temporary optimistic message with REAL current user data
      const optimisticMessage: ForumMessage = {
        id: tempId, // Temporary negative number ID
        content: data.content,
        sender: {
          id: currentUser?.id || 0, // REAL current user ID - determines message side (left/right)
          full_name: currentUser?.first_name && currentUser?.last_name
            ? `${currentUser.first_name} ${currentUser.last_name}`.trim()
            : currentUser?.email || 'Вы',
          role: currentUser?.role || '',
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

      // T037: Use setQueryData for immediate update (prevents race with invalidateQueries)
      queryClient.setQueryData<InfiniteData<ForumMessage[]>>(
        ['forum-messages', chatId],
        (oldData) => {
          // T030: Type guard - ensure proper structure
          if (!oldData || !oldData.pages || !Array.isArray(oldData.pages)) {
            return { pages: [[optimisticMessage]], pageParams: [0] };
          }

          // Add optimistic message to the last page
          const newPages = [...oldData.pages];
          const lastPageIndex = newPages.length - 1;
          newPages[lastPageIndex] = [...newPages[lastPageIndex], optimisticMessage];

          // T030: Preserve pageParams to maintain InfiniteData integrity
          return {
            pages: newPages,
            pageParams: oldData.pageParams,
          };
        }
      );

      // T038: Track timestamp for cleanup
      return { previousMessages, tempId, timestamp: Date.now() };
    },
    onSuccess: (message, variables, context) => {
      // T038: Replace optimistic message with real server response
      // Filter out temp message and add real one to prevent memory leak
      queryClient.setQueryData<InfiniteData<ForumMessage[]>>(
        ['forum-messages', variables.chatId],
        (oldData) => {
          // T030: Type guard - ensure we have proper InfiniteData structure
          if (!oldData || !oldData.pages || !Array.isArray(oldData.pages)) {
            return {
              pages: [[message]],
              pageParams: [0],
            };
          }

          // T031: Fix infinite loop risk - check if message already exists
          const messageExists = oldData.pages.some((page) =>
            page.some((msg) => msg.id === message.id)
          );

          if (messageExists) {
            // Message already updated (possibly via WebSocket), skip update
            return oldData;
          }

          // T038: Remove optimistic message and add real one to prevent memory leak
          const newPages = oldData.pages.map((page) => {
            // Filter out the temporary optimistic message
            const filtered = page.filter((msg) => msg.id !== context?.tempId);

            // If this page had the temp message, add real message here
            const hadTempMessage = page.some((msg) => msg.id === context?.tempId);

            return hadTempMessage ? [...filtered, message] : filtered;
          });

          // T030: Return proper InfiniteData structure
          return {
            pages: newPages,
            pageParams: oldData.pageParams,
          };
        }
      );

      // T037: Use setQueriesData instead of invalidateQueries to prevent race condition
      queryClient.setQueriesData(
        { queryKey: ['forum', 'chats'] },
        (oldChats: any) => {
          if (!oldChats) return oldChats;

          // Update last_message for the chat
          if (Array.isArray(oldChats)) {
            return oldChats.map((chat: any) =>
              chat.id === variables.chatId
                ? { ...chat, last_message: message }
                : chat
            );
          }
          return oldChats;
        }
      );

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
    mutationFn: ({ chatId, messageId }: { chatId: number; messageId: number }) =>
      forumAPI.deleteForumMessage(chatId, messageId),
    onSuccess: (_, variables) => {
      // T030: Remove the message from cache with proper InfiniteData structure
      queryClient.setQueriesData<InfiniteData<ForumMessage[]>>(
        { queryKey: ['forum-messages'] },
        (oldData) => {
          // T030: Type guard - ensure proper InfiniteData structure
          if (!oldData || !oldData.pages || !Array.isArray(oldData.pages)) {
            return oldData;
          }

          // Filter out deleted message from all pages
          const newPages = oldData.pages.map((page) =>
            page.filter((msg) => msg.id !== variables.messageId)
          );

          // T030: Preserve pageParams to maintain InfiniteData integrity
          return {
            pages: newPages,
            pageParams: oldData.pageParams,
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
