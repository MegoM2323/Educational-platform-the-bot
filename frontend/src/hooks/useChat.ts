import { useState, useEffect, useCallback, useRef } from "react";
import {
  chatAPI,
  Chat,
  ChatMessage,
  ChatContact,
} from "../integrations/api/chatAPI";
import {
  chatWebSocketService,
  ConnectionStatus,
} from "../services/chatWebSocketService";
import { logger } from "../utils/logger";

export type ChatRoom = Chat;

export interface UseChatOptions {
  roomId?: number;
  enableWebSocket?: boolean;
  onNewMessage?: (message: ChatMessage) => void;
  onMessageEdited?: (data: { message_id: number; content: string }) => void;
  onMessageDeleted?: (data: { message_id: number }) => void;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  connectionStatus: ConnectionStatus;

  sendMessage: (content: string) => Promise<void>;
  editMessage: (messageId: number, content: string) => Promise<void>;
  deleteMessage: (messageId: number) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  markAsRead: () => Promise<void>;
  sendTyping: () => void;

  connect: () => Promise<void>;
  disconnect: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const {
    roomId,
    enableWebSocket = true,
    onNewMessage,
    onMessageEdited,
    onMessageDeleted,
  } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [currentPage, setCurrentPage] = useState(1);

  const isConnectedRef = useRef(false);
  const unsubscribeStatusRef = useRef<(() => void) | null>(null);
  const isInitialLoadRef = useRef(true);

  const loadMessages = useCallback(async () => {
    if (!roomId) {
      logger.warn("[useChat] Cannot load messages: roomId is not provided");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await chatAPI.getChatMessages(roomId, 1, 50);

      const newMessages = response.results.map((msg) => ({
        id: msg.id,
        chat_id: msg.chat_id,
        sender_id: msg.sender_id,
        sender_name: msg.sender_name,
        sender_avatar: msg.sender_avatar,
        content: msg.content,
        created_at: msg.created_at,
        updated_at: msg.updated_at,
        is_edited: msg.is_edited,
        is_deleted: msg.is_deleted,
        read_by: msg.read_by,
      }));

      setMessages(newMessages);
      setHasMore(!!response.next);
      setCurrentPage(1);

      logger.info("[useChat] Messages loaded successfully", {
        roomId,
        count: newMessages.length,
        hasMore: !!response.next,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Ошибка загрузки сообщений";
      setError(errorMessage);
      logger.error("[useChat] Failed to load messages:", err);
    } finally {
      setIsLoading(false);
    }
  }, [roomId]);

  const loadMoreMessages = useCallback(async () => {
    if (!roomId || isLoadingMore || !hasMore) {
      return;
    }

    setIsLoadingMore(true);
    setError(null);

    try {
      const nextPage = currentPage + 1;
      const response = await chatAPI.getChatMessages(roomId, nextPage, 50);

      const newMessages = response.results.map((msg) => ({
        id: msg.id,
        chat_id: msg.chat_id,
        sender_id: msg.sender_id,
        sender_name: msg.sender_name,
        sender_avatar: msg.sender_avatar,
        content: msg.content,
        created_at: msg.created_at,
        updated_at: msg.updated_at,
        is_edited: msg.is_edited,
        is_deleted: msg.is_deleted,
        read_by: msg.read_by,
      }));

      setMessages((prev) => [...prev, ...newMessages]);
      setHasMore(!!response.next);
      setCurrentPage(nextPage);

      logger.info("[useChat] More messages loaded", {
        roomId,
        page: nextPage,
        count: newMessages.length,
        hasMore: !!response.next,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Ошибка загрузки сообщений";
      setError(errorMessage);
      logger.error("[useChat] Failed to load more messages:", err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [roomId, currentPage, hasMore, isLoadingMore]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!roomId) {
        const errorMsg = "Cannot send message: roomId is not provided";
        logger.error("[useChat]", errorMsg);
        setError(errorMsg);
        return;
      }

      if (!content.trim()) {
        logger.warn("[useChat] Attempt to send empty message");
        return;
      }

      try {
        if (enableWebSocket && chatWebSocketService.isConnected()) {
          chatWebSocketService.sendRoomMessage(roomId, content);
          logger.debug("[useChat] Message sent via WebSocket", {
            roomId,
            contentLength: content.length,
          });
        } else {
          const message = await chatAPI.sendMessage(roomId, { content });

          setMessages((prev) => {
            const exists = prev.some((m) => m.id === message.id);
            if (exists) return prev;
            return [message, ...prev];
          });

          logger.debug("[useChat] Message sent via REST API", {
            roomId,
            messageId: message.id,
          });
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Ошибка отправки сообщения";
        setError(errorMessage);
        logger.error("[useChat] Failed to send message:", err);
        throw err;
      }
    },
    [roomId, enableWebSocket],
  );

  const editMessage = useCallback(
    async (messageId: number, content: string) => {
      if (!roomId) {
        const errorMsg = "Cannot edit message: roomId is not provided";
        logger.error("[useChat]", errorMsg);
        setError(errorMsg);
        return;
      }

      try {
        const updatedMessage = await chatAPI.editMessage(
          roomId,
          messageId,
          content,
        );

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId
              ? {
                  ...msg,
                  content,
                  is_edited: true,
                  updated_at: updatedMessage.updated_at,
                }
              : msg,
          ),
        );

        logger.debug("[useChat] Message edited", { roomId, messageId });
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Ошибка редактирования сообщения";
        setError(errorMessage);
        logger.error("[useChat] Failed to edit message:", err);
        throw err;
      }
    },
    [roomId],
  );

  const deleteMessage = useCallback(
    async (messageId: number) => {
      if (!roomId) {
        const errorMsg = "Cannot delete message: roomId is not provided";
        logger.error("[useChat]", errorMsg);
        setError(errorMsg);
        return;
      }

      try {
        await chatAPI.deleteMessage(roomId, messageId);

        setMessages((prev) => prev.filter((msg) => msg.id !== messageId));

        logger.debug("[useChat] Message deleted", { roomId, messageId });
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Ошибка удаления сообщения";
        setError(errorMessage);
        logger.error("[useChat] Failed to delete message:", err);
        throw err;
      }
    },
    [roomId],
  );

  const markAsRead = useCallback(async () => {
    if (!roomId) {
      logger.warn("[useChat] Cannot mark as read: roomId is not provided");
      return;
    }

    try {
      await chatAPI.markAsRead(roomId);
      logger.debug("[useChat] Chat marked as read", { roomId });
    } catch (err) {
      logger.error("[useChat] Failed to mark as read:", err);
    }
  }, [roomId]);

  const sendTyping = useCallback(() => {
    if (!roomId || !enableWebSocket || !chatWebSocketService.isConnected()) {
      return;
    }

    chatWebSocketService.sendTyping(roomId);
    chatWebSocketService.startTypingTimer(roomId);
  }, [roomId, enableWebSocket]);

  const connect = useCallback(async () => {
    if (!roomId || !enableWebSocket) {
      logger.warn(
        "[useChat] Cannot connect: roomId not provided or WebSocket disabled",
      );
      return;
    }

    if (isConnectedRef.current) {
      logger.debug("[useChat] Already connected to room", { roomId });
      return;
    }

    try {
      await chatWebSocketService.connectToRoom(roomId, {
        onMessage: (message) => {
          logger.debug("[useChat] WebSocket message received", {
            messageId: message.id,
            roomId,
          });

          setMessages((prev) => {
            const exists = prev.some((m) => m.id === message.id);
            if (exists) {
              logger.debug("[useChat] Duplicate message ignored", {
                messageId: message.id,
              });
              return prev;
            }

            // Преобразование WebSocket ChatMessage (room, sender object)
            // в REST API ChatMessage (chat_id, flat fields)
            const chatMessage: ChatMessage = {
              id: message.id,
              chat_id: message.room, // WebSocket использует 'room', REST API использует 'chat_id'
              sender_id: message.sender.id,
              sender_name:
                `${message.sender.first_name} ${message.sender.last_name}`.trim() ||
                message.sender.username,
              sender_avatar: message.sender.avatar,
              content: message.content,
              created_at: message.created_at,
              updated_at: message.updated_at,
              is_edited: message.is_edited ?? false, // Защита от undefined
              is_deleted: false, // Новые сообщения через WS никогда не deleted
              read_by: [], // read_by обновляется через отдельный механизм mark_as_read
            };

            if (onNewMessage) {
              onNewMessage(chatMessage);
            }

            return [chatMessage, ...prev];
          });
        },
        onMessageEdited: (data) => {
          logger.debug("[useChat] WebSocket message edited", data);

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === data.message_id
                ? { ...msg, content: data.content, is_edited: true }
                : msg,
            ),
          );

          if (onMessageEdited) {
            onMessageEdited(data);
          }
        },
        onMessageDeleted: (data) => {
          logger.debug("[useChat] WebSocket message deleted", data);

          setMessages((prev) =>
            prev.filter((msg) => msg.id !== data.message_id),
          );

          if (onMessageDeleted) {
            onMessageDeleted(data);
          }
        },
        onError: (errorMsg, code) => {
          logger.error("[useChat] WebSocket error:", {
            errorMsg,
            code,
            roomId,
          });
          setError(errorMsg);
        },
        onConnect: () => {
          logger.info("[useChat] WebSocket connected", { roomId });
          isConnectedRef.current = true;
        },
      });

      logger.info("[useChat] Successfully initiated connection", { roomId });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Ошибка подключения WebSocket";
      setError(errorMessage);
      logger.error("[useChat] Failed to connect:", err);
      throw err;
    }
  }, [
    roomId,
    enableWebSocket,
    onNewMessage,
    onMessageEdited,
    onMessageDeleted,
  ]);

  const disconnect = useCallback(() => {
    if (!roomId) {
      return;
    }

    if (unsubscribeStatusRef.current) {
      unsubscribeStatusRef.current();
      unsubscribeStatusRef.current = null;
    }

    if (isConnectedRef.current) {
      chatWebSocketService.disconnectFromRoom(roomId);
      isConnectedRef.current = false;
      logger.info("[useChat] Disconnected from room", { roomId });
    }
  }, [roomId]);

  useEffect(() => {
    if (!roomId) {
      return;
    }

    const unsubscribe = chatWebSocketService.onConnectionStatusChange(
      (status) => {
        setConnectionStatus(status);

        if (status === "connected" && !isConnectedRef.current) {
          isConnectedRef.current = true;
        } else if (
          status === "disconnected" ||
          status === "error" ||
          status === "auth_error"
        ) {
          isConnectedRef.current = false;
        }
      },
    );

    unsubscribeStatusRef.current = unsubscribe;

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, [roomId]);

  useEffect(() => {
    if (!roomId) {
      return;
    }

    if (isInitialLoadRef.current) {
      loadMessages();
      isInitialLoadRef.current = false;
    }

    if (enableWebSocket) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [roomId, enableWebSocket]);

  return {
    messages,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    connectionStatus,

    sendMessage,
    editMessage,
    deleteMessage,
    loadMoreMessages,
    markAsRead,
    sendTyping,

    connect,
    disconnect,
  };
}

export { Chat, ChatMessage, ChatContact };
