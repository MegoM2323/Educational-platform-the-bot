import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatService, ChatMessage, ChatThread, ChatRoom, SendMessageRequest, CreateThreadRequest } from '@/integrations/api/chatService';
import { toast } from 'sonner';

// Получить общий чат
export const useGeneralChat = () => {
  return useQuery({
    queryKey: ['general-chat'],
    queryFn: () => chatService.getGeneralChat(),
    staleTime: 300000, // 5 минут
    retry: 2,
  });
};

// Получить сообщения общего чата
export const useGeneralChatMessages = (limit: number = 50, offset: number = 0) => {
  return useQuery({
    queryKey: ['general-chat-messages', limit, offset],
    queryFn: () => chatService.getGeneralChatMessages(limit, offset),
    staleTime: 30000, // 30 секунд
    retry: 2,
  });
};

// Отправить сообщение в общий чат
export const useSendGeneralMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SendMessageRequest) =>
      chatService.sendGeneralMessage(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-messages'] });
      toast.success('Сообщение отправлено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки сообщения: ${error.message}`);
    },
  });
};

// Получить треды общего чата
export const useGeneralChatThreads = (limit: number = 20, offset: number = 0) => {
  return useQuery({
    queryKey: ['general-chat-threads', limit, offset],
    queryFn: () => chatService.getGeneralChatThreads(limit, offset),
    staleTime: 60000, // 1 минута
    retry: 2,
  });
};

// Создать новый тред
export const useCreateThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateThreadRequest) =>
      chatService.createThread(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред создан');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка создания треда: ${error.message}`);
    },
  });
};

// Получить сообщения треда
export const useThreadMessages = (threadId: number, limit: number = 50, offset: number = 0) => {
  return useQuery({
    queryKey: ['thread-messages', threadId, limit, offset],
    queryFn: () => chatService.getThreadMessages(threadId, limit, offset),
    enabled: !!threadId,
    staleTime: 30000, // 30 секунд
    retry: 2,
  });
};

// Отправить сообщение в тред
export const useSendThreadMessage = (threadId: number) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SendMessageRequest) =>
      chatService.sendThreadMessage(threadId, data),
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

// Закрепить тред
export const usePinThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) =>
      chatService.pinThread(threadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред закреплен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка закрепления треда: ${error.message}`);
    },
  });
};

// Открепить тред
export const useUnpinThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) =>
      chatService.unpinThread(threadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред откреплен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка открепления треда: ${error.message}`);
    },
  });
};

// Заблокировать тред
export const useLockThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) =>
      chatService.lockThread(threadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред заблокирован');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка блокировки треда: ${error.message}`);
    },
  });
};

// Разблокировать тред
export const useUnlockThread = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: number) =>
      chatService.unlockThread(threadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-chat-threads'] });
      toast.success('Тред разблокирован');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка разблокировки треда: ${error.message}`);
    },
  });
};
