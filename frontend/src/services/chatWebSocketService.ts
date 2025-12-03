/**
 * Chat WebSocket Service - специализированный сервис для чата
 * Обеспечивает real-time обмен сообщениями, индикаторы печати и уведомления
 */

import { websocketService, WebSocketMessage, getWebSocketBaseUrl } from './websocketService';
import { tokenStorage } from './tokenStorage';

export interface ChatMessage {
  id: number;
  room: number;
  thread?: number;
  thread_title?: string;
  sender: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    role: string;
    avatar?: string;
  };
  content: string;
  message_type: 'text' | 'image' | 'file' | 'system';
  file?: string;
  image?: string;
  is_edited: boolean;
  reply_to?: number;
  created_at: string;
  updated_at: string;
  is_read: boolean;
  replies_count: number;
}

export interface TypingUser {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
}

export interface ChatEventHandlers {
  onMessage?: (message: ChatMessage) => void;
  onTyping?: (user: TypingUser) => void;
  onTypingStop?: (user: TypingUser) => void;
  onUserJoined?: (user: TypingUser) => void;
  onUserLeft?: (user: TypingUser) => void;
  onRoomHistory?: (messages: ChatMessage[]) => void;
  onError?: (error: string) => void;
}

export class ChatWebSocketService {
  private subscriptions = new Map<string, string>();
  private typingTimeouts = new Map<number, NodeJS.Timeout>();
  private eventHandlers: ChatEventHandlers = {};

  constructor() {
    // Подписываемся на системные события WebSocket
    websocketService.onConnectionChange((connected) => {
      if (connected) {
        this.resubscribeAll();
      }
    });
  }

  /**
   * Подключение к общему чату
   */
  connectToGeneralChat(handlers: ChatEventHandlers): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const subscriptionId = websocketService.subscribe('general_chat', (message: WebSocketMessage) => {
      this.handleChatMessage(message);
    });

    this.subscriptions.set('general_chat', subscriptionId);

    // Подключаемся к WebSocket если еще не подключены
    if (!websocketService.isConnected()) {
      const baseUrl = getWebSocketBaseUrl();
      const { accessToken } = tokenStorage.getTokens();
      const tokenParam = accessToken ? `?token=${accessToken}` : '';
      const fullUrl = `${baseUrl}/chat/general/${tokenParam}`;
      console.log('[ChatWebSocket] Connecting to general chat:', fullUrl);
      websocketService.connect(fullUrl);
    }
  }

  /**
   * Подключение к конкретной чат-комнате
   */
  connectToRoom(roomId: number, handlers: ChatEventHandlers): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const channel = `chat_${roomId}`;
    const subscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
      this.handleChatMessage(message);
    });

    this.subscriptions.set(channel, subscriptionId);

    // Подключаемся к WebSocket с room-specific URL
    const baseUrl = getWebSocketBaseUrl();
    const { accessToken } = tokenStorage.getTokens();
    const tokenParam = accessToken ? `?token=${accessToken}` : '';
    const fullUrl = `${baseUrl}/chat/${roomId}/${tokenParam}`;
    console.log('[ChatWebSocket] Connecting to room:', roomId, 'URL:', fullUrl);
    websocketService.connect(fullUrl);
  }

  /**
   * Отключение от конкретной комнаты
   */
  disconnectFromRoom(roomId: number): void {
    const channel = `chat_${roomId}`;
    const subscriptionId = this.subscriptions.get(channel);

    if (subscriptionId) {
      websocketService.unsubscribe(subscriptionId);
      this.subscriptions.delete(channel);
    }

    // Очищаем таймер печати для этой комнаты
    const timeoutKey = roomId;
    const timeout = this.typingTimeouts.get(timeoutKey);
    if (timeout) {
      clearTimeout(timeout);
      this.typingTimeouts.delete(timeoutKey);
    }
  }

  /**
   * Отключение от чата
   */
  disconnectFromChat(): void {
    this.subscriptions.forEach((subscriptionId) => {
      websocketService.unsubscribe(subscriptionId);
    });
    this.subscriptions.clear();
    this.clearAllTypingTimeouts();
  }

  /**
   * Отправка сообщения в общий чат
   */
  sendGeneralMessage(content: string): void {
    websocketService.send({
      type: 'chat_message',
      data: { content }
    });
  }

  /**
   * Отправка сообщения в комнату
   */
  sendRoomMessage(roomId: number, content: string): void {
    websocketService.send({
      type: 'chat_message',
      data: { content }
    });
  }

  /**
   * Отправка индикатора печати
   */
  sendTyping(roomId?: number): void {
    websocketService.send({
      type: 'typing',
      data: { room_id: roomId }
    });
  }

  /**
   * Отправка остановки печати
   */
  sendTypingStop(roomId?: number): void {
    websocketService.send({
      type: 'typing_stop',
      data: { room_id: roomId }
    });
  }

  /**
   * Отметка сообщения как прочитанного
   */
  markMessageAsRead(messageId: number): void {
    websocketService.send({
      type: 'mark_read',
      data: { message_id: messageId }
    });
  }

  /**
   * Обработка входящих сообщений чата
   */
  private handleChatMessage(message: WebSocketMessage): void {
    console.log('[ChatWebSocketService] Received message:', {
      type: message.type,
      hasMessage: !!message.message,
      messageId: message.message?.id,
      hasHandler: !!this.eventHandlers.onMessage
    });

    switch (message.type) {
      case 'chat_message':
        if (message.message && this.eventHandlers.onMessage) {
          console.log('[ChatWebSocketService] Calling onMessage handler for message ID:', message.message.id);
          this.eventHandlers.onMessage(message.message);
        } else {
          console.warn('[ChatWebSocketService] chat_message received but no handler or message data:', {
            hasMessage: !!message.message,
            hasHandler: !!this.eventHandlers.onMessage
          });
        }
        break;

      case 'typing':
        if (message.user && this.eventHandlers.onTyping) {
          this.eventHandlers.onTyping(message.user);
        }
        break;

      case 'typing_stop':
        if (message.user && this.eventHandlers.onTypingStop) {
          this.eventHandlers.onTypingStop(message.user);
        }
        break;

      case 'user_joined':
        if (message.user && this.eventHandlers.onUserJoined) {
          this.eventHandlers.onUserJoined(message.user);
        }
        break;

      case 'user_left':
        if (message.user && this.eventHandlers.onUserLeft) {
          this.eventHandlers.onUserLeft(message.user);
        }
        break;

      case 'room_history':
        if (message.messages && this.eventHandlers.onRoomHistory) {
          this.eventHandlers.onRoomHistory(message.messages);
        }
        break;

      case 'error':
        if (message.error && this.eventHandlers.onError) {
          this.eventHandlers.onError(message.error);
        }
        break;
    }
  }

  /**
   * Переподписка на все каналы после переподключения
   */
  private resubscribeAll(): void {
    this.subscriptions.forEach((subscriptionId, channel) => {
      const newSubscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
        this.handleChatMessage(message);
      });
      this.subscriptions.set(channel, newSubscriptionId);
    });
  }

  /**
   * Очистка всех таймеров печати
   */
  private clearAllTypingTimeouts(): void {
    this.typingTimeouts.forEach((timeout) => {
      clearTimeout(timeout);
    });
    this.typingTimeouts.clear();
  }

  /**
   * Автоматическая отправка остановки печати через 3 секунды
   */
  startTypingTimer(roomId?: number): void {
    // Очищаем предыдущий таймер
    const timeoutKey = roomId || 0;
    const existingTimeout = this.typingTimeouts.get(timeoutKey);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    // Устанавливаем новый таймер
    const timeout = setTimeout(() => {
      this.sendTypingStop(roomId);
      this.typingTimeouts.delete(timeoutKey);
    }, 3000);

    this.typingTimeouts.set(timeoutKey, timeout);
  }

  /**
   * Проверка состояния соединения
   */
  isConnected(): boolean {
    return websocketService.isConnected();
  }

  /**
   * Подписка на изменения состояния соединения
   */
  onConnectionChange(callback: (connected: boolean) => void): void {
    websocketService.onConnectionChange(callback);
  }
}

// Создаем глобальный экземпляр сервиса чата
export const chatWebSocketService = new ChatWebSocketService();

// Экспортируем типы
export type { ChatMessage, TypingUser, ChatEventHandlers };
