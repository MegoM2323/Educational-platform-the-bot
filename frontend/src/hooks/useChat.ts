// Chat React Query Hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  chatAPI,
  ChatRoom,
  ChatMessage,
  SendMessageRequest,
  MessageThread,
} from '../integrations/api/chat';
import { toast } from 'sonner';

// Get general chat room
export const useGeneralChat = () => {
  return useQuery({
    queryKey: ['general-chat'],
    queryFn: () => chatAPI.getGeneralChat(),
    staleTime: 300000, // 5 minutes - chat room info doesn't change often
    retry: 2,
  });
};

// Get general chat messages with pagination
export const useGeneralMessages = (page: number = 1, pageSize: number = 50) => {
  return useQuery({
    queryKey: ['general-messages', page, pageSize],
    queryFn: () => chatAPI.getGeneralMessages(page, pageSize),
    staleTime: 30000, // 30 seconds - messages update frequently
    retry: 2,
    refetchInterval: 10000, // Refetch every 10 seconds for new messages
  });
};

// Send message
export const useSendMessage = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: SendMessageRequest) =>
      chatAPI.sendMessage(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-messages'] });
      toast.success('Сообщение отправлено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки сообщения: ${error.message}`);
    },
  });
};

// Create thread (reply to message)
export const useCreateThread = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ messageId, data }: { messageId: number; data: SendMessageRequest }) =>
      chatAPI.createThread(messageId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-messages'] });
      queryClient.invalidateQueries({ queryKey: ['threads'] });
      toast.success('Ответ отправлен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки ответа: ${error.message}`);
    },
  });
};

// Get threads for a message
export const useThreads = (parentMessageId: number) => {
  return useQuery({
    queryKey: ['threads', parentMessageId],
    queryFn: () => chatAPI.getThreads(parentMessageId),
    enabled: !!parentMessageId,
    staleTime: 60000,
    retry: 2,
  });
};

// Get thread messages
export const useThreadMessages = (threadId: number) => {
  return useQuery({
    queryKey: ['thread-messages', threadId],
    queryFn: () => chatAPI.getThreadMessages(threadId),
    enabled: !!threadId,
    staleTime: 30000,
    retry: 2,
    refetchInterval: 10000, // Refetch every 10 seconds for new messages
  });
};

// Update message
export const useUpdateMessage = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ messageId, content }: { messageId: number; content: string }) =>
      chatAPI.updateMessage(messageId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-messages'] });
      queryClient.invalidateQueries({ queryKey: ['thread-messages'] });
      toast.success('Сообщение обновлено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка обновления сообщения: ${error.message}`);
    },
  });
};

// Delete message
export const useDeleteMessage = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (messageId: number) =>
      chatAPI.deleteMessage(messageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['general-messages'] });
      queryClient.invalidateQueries({ queryKey: ['thread-messages'] });
      toast.success('Сообщение удалено');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления сообщения: ${error.message}`);
    },
  });
};

// Get all chat rooms
export const useChatRooms = () => {
  return useQuery({
    queryKey: ['chat-rooms'],
    queryFn: () => chatAPI.getChatRooms(),
    staleTime: 300000,
    retry: 2,
  });
};

// Get room messages
export const useRoomMessages = (roomId: number) => {
  return useQuery({
    queryKey: ['room-messages', roomId],
    queryFn: () => chatAPI.getRoomMessages(roomId),
    enabled: !!roomId,
    staleTime: 30000,
    retry: 2,
    refetchInterval: 10000,
  });
};
