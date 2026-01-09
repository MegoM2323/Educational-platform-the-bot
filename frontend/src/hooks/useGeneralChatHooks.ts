import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI, ChatMessage, Chat } from '@/integrations/api/chatAPI';
import { toast } from 'sonner';

export const useGeneralChat = () => {
  return useQuery({
    queryKey: ['general-chat'],
    queryFn: async () => {
      const response = await chatAPI.getChatList();

      console.log('[useGeneralChat] API Response:', response);

      // If no chats found, return null
      if (!response?.results || response.results.length === 0) {
        console.warn('[useGeneralChat] No chats available for user');
        return null;
      }

      console.log('[useGeneralChat] Available chats:', response.results.map((c: Chat) => ({
        id: c.id,
        name: c.name,
        is_group: c.is_group,
        participant_count: c.participant_count
      })));

      // Try to find a group chat first, then use first chat as fallback
      const groupChat = response.results.find((chat: Chat) => chat.is_group === true);
      const generalChat = groupChat || response.results[0] || null;

      if (generalChat) {
        console.log(`[useGeneralChat] Selected chat ${generalChat.id}: ${generalChat.name} (is_group: ${generalChat.is_group})`);
      } else {
        console.warn('[useGeneralChat] Could not select any chat from results');
      }

      return generalChat;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  });
};

export const useGeneralChatMessages = (limit: number = 50, offset: number = 0) => {
  const { data: generalChat } = useGeneralChat();

  return useQuery({
    queryKey: ['general-chat-messages', limit, offset],
    queryFn: async () => {
      if (!generalChat?.id) {
        throw new Error('General chat not found');
      }
      const page = Math.floor(offset / limit) + 1;
      const response = await chatAPI.getChatMessages(generalChat.id, page, limit);
      return response.results;
    },
    enabled: !!generalChat?.id,
    staleTime: 30000,
    retry: 2,
  });
};

export const useSendGeneralMessage = () => {
  const queryClient = useQueryClient();
  const { data: generalChat } = useGeneralChat();

  return useMutation({
    mutationFn: (data: { content: string }) => {
      if (!generalChat?.id) {
        throw new Error('General chat not found');
      }
      return chatAPI.sendMessage(generalChat.id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-messages'] });
      toast.success('Сообщение отправлено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки сообщения: ${error.message}`);
    },
  });
};

export const useGeneralChatThreads = (limit: number = 20, offset: number = 0) => {
  return useQuery({
    queryKey: ['general-chat-threads', limit, offset],
    queryFn: async () => {
      return [];
    },
    staleTime: 60000,
    retry: 2,
  });
};

export const useCreateThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { title: string; content: string }) => {
      throw new Error('Thread creation not implemented in new chat API');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред создан');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка создания треда: ${error.message}`);
    },
  });
};

export const useThreadMessages = (threadId: number, limit: number = 50, offset: number = 0) => {
  return useQuery({
    queryKey: ['thread-messages', threadId, limit, offset],
    queryFn: async () => {
      return [];
    },
    enabled: !!threadId,
    staleTime: 30000,
    retry: 2,
  });
};

export const useSendThreadMessage = (threadId: number) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { content: string }) => {
      throw new Error('Thread messages not implemented in new chat API');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thread-messages', threadId] });
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Сообщение отправлено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки сообщения: ${error.message}`);
    },
  });
};

export const usePinThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) => {
      throw new Error('Thread pinning not implemented in new chat API');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред закреплен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка закрепления треда: ${error.message}`);
    },
  });
};

export const useUnpinThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) => {
      throw new Error('Thread unpinning not implemented in new chat API');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред откреплен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка открепления треда: ${error.message}`);
    },
  });
};

export const useLockThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) => {
      throw new Error('Thread locking not implemented in new chat API');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред заблокирован');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка блокировки треда: ${error.message}`);
    },
  });
};

export const useUnlockThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) => {
      throw new Error('Thread unlocking not implemented in new chat API');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред разблокирован');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка разблокировки треда: ${error.message}`);
    },
  });
};
