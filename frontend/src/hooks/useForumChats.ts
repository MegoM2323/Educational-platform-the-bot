import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI, Chat, ChatContact } from '../integrations/api/chatAPI';

export const useForumChats = () => {
  console.log('[useForumChats] Hook called');
  const queryClient = useQueryClient();

  const chatsQuery = useQuery({
    queryKey: ['forum', 'chats'],
    queryFn: async () => {
      console.log('[useForumChats] queryFn executing for chats');
      try {
        const response = await chatAPI.getChatList();
        return response.results;
      } catch (error: any) {
        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось загрузить список чатов';
        throw new Error(errorMessage);
      }
    },
    staleTime: 60000,
    retry: (failureCount, error) => {
      if (error.message.includes('401') || error.message.includes('403') ||
          error.message.includes('авторизован') || error.message.includes('доступ')) {
        return false;
      }
      return failureCount < 2;
    },
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  const contactsQuery = useQuery({
    queryKey: ['forum', 'available-contacts'],
    queryFn: async () => {
      console.log('[useForumChats] queryFn executing for contacts');
      try {
        return await chatAPI.getContacts();
      } catch (error: any) {
        const errorMessage = error?.response?.data?.detail ||
                            error?.message ||
                            'Не удалось загрузить контакты';
        throw new Error(errorMessage);
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error) => {
      if (error.message.includes('401') || error.message.includes('403')) {
        return false;
      }
      return failureCount < 2;
    },
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  const initiateChatMutation = useMutation({
    mutationFn: ({ contactUserId, subjectId }: { contactUserId: number; subjectId?: number }) =>
      chatAPI.createOrGetChat(contactUserId, subjectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
      queryClient.invalidateQueries({ queryKey: ['forum', 'available-contacts'] });
    },
  });

  console.log('[useForumChats] Query states:', {
    chats: {
      isLoading: chatsQuery.isLoading,
      isFetching: chatsQuery.isFetching,
      isError: chatsQuery.isError,
      dataLength: Array.isArray(chatsQuery.data) ? chatsQuery.data.length : 'not-array',
      error: chatsQuery.error,
    },
    contacts: {
      isLoading: contactsQuery.isLoading,
      isError: contactsQuery.isError,
      dataLength: Array.isArray(contactsQuery.data) ? contactsQuery.data.length : 'not-array',
      error: contactsQuery.error,
    },
    initiateChat: {
      isPending: initiateChatMutation.isPending,
      isError: initiateChatMutation.isError,
      error: initiateChatMutation.error,
    },
  });

  return {
    chats: chatsQuery.data || [],
    isLoadingChats: chatsQuery.isLoading,
    chatsError: chatsQuery.error,

    availableContacts: contactsQuery.data || [],
    isLoadingContacts: contactsQuery.isLoading,
    contactsError: contactsQuery.error,

    initiateChat: (contactUserId: number, subjectId?: number) =>
      initiateChatMutation.mutateAsync({ contactUserId, subjectId }),
    isInitiatingChat: initiateChatMutation.isPending,
    initiateError: initiateChatMutation.error,
    clearInitiateError: () => initiateChatMutation.reset(),
  };
};

export const useForumChatsWithRefresh = () => {
  const queryClient = useQueryClient();

  const hook = useForumChats();

  const refreshChats = () => {
    queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
  };

  return { ...hook, refreshChats };
};
