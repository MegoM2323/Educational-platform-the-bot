import { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  chatAPI,
  ChatRoom,
  ChatMessage,
  SendMessageRequest,
  MessageThread,
  Chat,
  ChatContact,
  ChatListResponse,
  ChatMessagesResponse,
} from '../integrations/api/chat';
import { getChatSocket, initChatSocket, type ChatSocketMessage } from '../integrations/websocket/chatSocket';
import { toast } from 'sonner';
import { logger } from '../utils/logger';

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

// NEW HOOKS FOR CHAT API

export const useChatList = (page: number = 1, pageSize: number = 20) => {
  return useQuery({
    queryKey: ['chat-list', page, pageSize],
    queryFn: () => chatAPI.getChatList(page, pageSize),
    staleTime: 60000,
    retry: 2,
    placeholderData: { count: 0, results: [] },
  });
};

export const useChat = (chatId: number) => {
  return useQuery({
    queryKey: ['chat', chatId],
    queryFn: () => chatAPI.getChatById(chatId),
    enabled: !!chatId,
    staleTime: 180000,
    retry: 2,
  });
};

export const useChatMessages = (chatId: number, page: number = 1, pageSize: number = 50) => {
  return useQuery({
    queryKey: ['chat-messages', chatId, page, pageSize],
    queryFn: () => chatAPI.getChatMessages(chatId, page, pageSize),
    enabled: !!chatId,
    staleTime: 30000,
    retry: 2,
    placeholderData: { count: 0, results: [] },
  });
};

export const useSendChatMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, data }: { chatId: number; data: SendMessageRequest }) =>
      chatAPI.sendMessage(chatId, data),
    onSuccess: (_, { chatId }) => {
      queryClient.invalidateQueries({ queryKey: ['chat-messages', chatId] });
      queryClient.invalidateQueries({ queryKey: ['chat-list'] });
    },
    onError: (error: Error) => {
      toast.error(`Ошибка отправки сообщения: ${error.message}`);
    },
  });
};

export const useDeleteChatMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, messageId }: { chatId: number; messageId: number }) =>
      chatAPI.deleteMessage(chatId, messageId),
    onSuccess: (_, { chatId }) => {
      queryClient.invalidateQueries({ queryKey: ['chat-messages', chatId] });
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления сообщения: ${error.message}`);
    },
  });
};

export const useUpdateMessageStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, messageId }: { chatId: number; messageId: number }) =>
      chatAPI.updateMessageStatus(chatId, messageId, { read_at: new Date().toISOString() }),
    onSuccess: (_, { chatId }) => {
      queryClient.invalidateQueries({ queryKey: ['chat-messages', chatId] });
    },
  });
};

export const useChatContacts = () => {
  return useQuery({
    queryKey: ['chat-contacts'],
    queryFn: () => chatAPI.getContacts(),
    staleTime: 300000,
    retry: 2,
    placeholderData: [],
  });
};

interface CreateChatData {
  participant_ids: number[];
  name?: string;
  description?: string;
}

export const useCreateChat = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateChatData) => chatAPI.createChat(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-list'] });
      toast.success('Чат создан');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка создания чата: ${error.message}`);
    },
  });
};

export const useDeleteChat = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (chatId: number) => chatAPI.deleteChat(chatId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-list'] });
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления чата: ${error.message}`);
    },
  });
};

export const useWebSocketChat = (chatId: number, enabled: boolean = true) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!enabled || !chatId) return;

    const setupSocket = async () => {
      try {
        const socket = initChatSocket();
        socketRef.current = socket;

        socket.onConnectionChange((connected) => {
          setIsConnected(connected);
          if (connected) {
            setError(null);
            logger.info('[useWebSocketChat] Connected to socket');
          }
        });

        if (!socket.isConnected()) {
          await socket.connect();
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Ошибка подключения WebSocket';
        setError(message);
        logger.error('[useWebSocketChat] Setup error:', err);
      }
    };

    setupSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current = null;
      }
    };
  }, [chatId, enabled]);

  const subscribe = useCallback(
    (callback: (msg: ChatSocketMessage) => void) => {
      if (!socketRef.current) return () => {};
      return socketRef.current.subscribeToChat(chatId, callback);
    },
    [chatId]
  );

  const send = useCallback(
    (message: string) => {
      if (!socketRef.current) {
        setError('WebSocket не подключен');
        return;
      }
      socketRef.current.send(chatId, message);
    },
    [chatId]
  );

  return {
    isConnected,
    error,
    subscribe,
    send,
  };
};

export const useTypingIndicator = (chatId: number) => {
  const socketRef = useRef(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    try {
      socketRef.current = getChatSocket();
    } catch (error) {
      logger.warn('[useTypingIndicator] Socket not initialized');
    }

    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  const startTyping = useCallback(() => {
    if (!socketRef.current || !socketRef.current.isConnected()) return;

    if (!isTyping) {
      setIsTyping(true);
      socketRef.current.sendTypingIndicator(chatId, true);
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      socketRef.current?.sendTypingIndicator(chatId, false);
    }, 3000);
  }, [chatId, isTyping]);

  const stopTyping = useCallback(() => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    setIsTyping(false);
    if (socketRef.current?.isConnected()) {
      socketRef.current.sendTypingIndicator(chatId, false);
    }
  }, [chatId]);

  return { startTyping, stopTyping, isTyping };
};

export const useUnreadCount = (chatId?: number) => {
  const { data: chatList } = useChatList();

  const unreadCount = chatId
    ? chatList?.results.find((chat) => chat.id === chatId)?.unread_count || 0
    : chatList?.results.reduce((sum, chat) => sum + chat.unread_count, 0) || 0;

  return unreadCount;
};
