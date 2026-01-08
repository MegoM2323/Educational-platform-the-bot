import { useQuery, useInfiniteQuery, useMutation, useQueryClient, InfiniteData } from '@tanstack/react-query';
import { chatAPI, ChatMessage } from '../integrations/api/chatAPI';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export const useForumMessages = (chatId: number | null) => {
  const MESSAGES_PER_PAGE = 50;

  return useInfiniteQuery<ChatMessage[], Error>({
    queryKey: ['forum-messages', chatId],
    queryFn: async ({ pageParam = 1, signal }) => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }

      try {
        const response = await chatAPI.getChatMessages(
          chatId,
          pageParam as number,
          MESSAGES_PER_PAGE
        );

        return response.results;
      } catch (error: any) {
        if (error.name === 'AbortError') {
          throw error;
        }

        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось загрузить сообщения';
        throw new Error(errorMessage);
      }
    },
    getNextPageParam: (lastPage, allPages) => {
      const currentPage = allPages.length;
      const hasMore = lastPage.length === MESSAGES_PER_PAGE;

      return hasMore ? currentPage + 1 : undefined;
    },
    initialPageParam: 1,
    enabled: !!chatId && chatId > 0,
    staleTime: 1000 * 60,
    refetchOnMount: 'stale',
    refetchOnWindowFocus: false,
    retry: (failureCount, error) => {
      if (error.message.includes('401') || error.message.includes('403') ||
          error.message.includes('авторизован') || error.message.includes('доступ')) {
        return false;
      }
      return failureCount < 2;
    },
  });
};

export const useForumMessagesLegacy = (chatId: number | null, limit: number = 50, offset: number = 0) => {
  const query = useQuery<ChatMessage[]>({
    queryKey: ['forum-messages-legacy', chatId, limit, offset],
    queryFn: async ({ signal }) => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }
      const page = Math.floor(offset / limit) + 1;
      const response = await chatAPI.getChatMessages(chatId, page, limit);
      return response.results;
    },
    enabled: !!chatId,
    staleTime: 1000 * 60,
    placeholderData: (previousData) => previousData,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    retry: 2,
  });

  return query;
};

export const useSendForumMessage = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast: toastHook } = useAuth();

  return useMutation({
    mutationFn: async ({ chatId, data, file }: { chatId: number; data: { content: string }; file?: File }) => {
      try {
        return await chatAPI.sendMessage(chatId, data);
      } catch (error: any) {
        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось отправить сообщение';
        throw new Error(errorMessage);
      }
    },
    onMutate: async ({ chatId, data, file }) => {
      await queryClient.cancelQueries({ queryKey: ['forum-messages', chatId] });

      const previousMessages = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(['forum-messages', chatId]);

      const tempId = -Date.now();

      const currentUser = user;

      const optimisticMessage: ChatMessage = {
        id: tempId,
        chat_id: chatId,
        sender_id: currentUser?.id || 0,
        sender_name: currentUser?.first_name && currentUser?.last_name
          ? `${currentUser.first_name} ${currentUser.last_name}`.trim()
          : currentUser?.email || 'Вы',
        sender_avatar: currentUser?.avatar,
        content: data.content,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_edited: false,
        is_deleted: false,
        read_by: [],
      };

      queryClient.setQueryData<InfiniteData<ChatMessage[]>>(
        ['forum-messages', chatId],
        (oldData) => {
          if (!oldData || !oldData.pages || !Array.isArray(oldData.pages)) {
            return { pages: [[optimisticMessage]], pageParams: [1] };
          }

          const newPages = [...oldData.pages];
          const lastPageIndex = newPages.length - 1;
          newPages[lastPageIndex] = [...newPages[lastPageIndex], optimisticMessage];

          return {
            pages: newPages,
            pageParams: oldData.pageParams,
          };
        }
      );

      return { previousMessages, tempId, timestamp: Date.now() };
    },
    onSuccess: (message, variables, context) => {
      queryClient.setQueryData<InfiniteData<ChatMessage[]>>(
        ['forum-messages', variables.chatId],
        (oldData) => {
          if (!oldData || !oldData.pages || !Array.isArray(oldData.pages)) {
            return {
              pages: [[message]],
              pageParams: [1],
            };
          }

          const newPages = oldData.pages.map((page) => {
            const filtered = page.filter((msg) => msg.id !== context?.tempId);

            const hadTempMessage = page.some((msg) => msg.id === context?.tempId);

            const realMessageExists = page.some((msg) => msg.id === message.id);

            return hadTempMessage && !realMessageExists ? [...filtered, message] : filtered;
          });

          return {
            pages: newPages,
            pageParams: oldData.pageParams,
          };
        }
      );

      queryClient.setQueriesData(
        { queryKey: ['forum', 'chats'] },
        (oldChats: any) => {
          if (!oldChats) return oldChats;

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
      chatAPI.deleteMessage(chatId, messageId),
    onSuccess: (_, variables) => {
      queryClient.setQueriesData<InfiniteData<ChatMessage[]>>(
        { queryKey: ['forum-messages'] },
        (oldData) => {
          if (!oldData || !oldData.pages || !Array.isArray(oldData.pages)) {
            return oldData;
          }

          const newPages = oldData.pages.map((page) =>
            page.filter((msg) => msg.id !== variables.messageId)
          );

          return {
            pages: newPages,
            pageParams: oldData.pageParams,
          };
        }
      );

      queryClient.invalidateQueries({ queryKey: ['forum-messages'] });

      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });

      toast.success('Сообщение удалено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления: ${error.message}`);
    },
  });
};
