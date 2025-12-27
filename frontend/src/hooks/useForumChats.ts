import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumChat, Contact, InitiateChatResponse } from '../integrations/api/forumAPI';

export const useForumChats = () => {
  console.log('[useForumChats] Hook called');
  const queryClient = useQueryClient();

  // Основной запрос для списка чатов
  const chatsQuery = useQuery({
    queryKey: ['forum', 'chats'],
    queryFn: () => {
      console.log('[useForumChats] queryFn executing for chats');
      return forumAPI.getForumChats();
    },
    staleTime: 60000, // 1 minute (reduced from 5 minutes for more frequent updates)
    retry: 2,
    refetchOnMount: true, // Explicitly enable refetch on component mount
    refetchOnWindowFocus: false,
  });

  // Запрос для доступных контактов
  const contactsQuery = useQuery({
    queryKey: ['forum', 'available-contacts'],
    queryFn: () => {
      console.log('[useForumChats] queryFn executing for contacts');
      return forumAPI.getAvailableContacts();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  // Мутация для создания/инициации чата
  const initiateChatMutation = useMutation({
    mutationFn: ({ contactUserId, subjectId }: { contactUserId: number; subjectId?: number }) =>
      forumAPI.initiateChat(contactUserId, subjectId),
    onSuccess: () => {
      // Обновить список чатов после успешной инициации
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
      // Обновить список доступных контактов (статус has_active_chat мог измениться)
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
    // Chats
    chats: chatsQuery.data || [],
    isLoadingChats: chatsQuery.isLoading,
    chatsError: chatsQuery.error,

    // Available Contacts
    availableContacts: contactsQuery.data || [],
    isLoadingContacts: contactsQuery.isLoading,
    contactsError: contactsQuery.error,

    // Initiate Chat
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
