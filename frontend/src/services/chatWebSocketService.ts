/**
 * Chat WebSocket Service - специализированный сервис для чата
 * Обеспечивает real-time обмен сообщениями, индикаторы печати и уведомления
 */

import { websocketService, WebSocketMessage, getWebSocketBaseUrl } from './websocketService';
import { tokenStorage } from './tokenStorage';
import { logger } from '../utils/logger';

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
  onError?: (error: string, code?: string) => void;
  onConnect?: () => void;
  onMessageDelivered?: (messageId: number) => void;
  onMessagePinned?: (data: { message_id: number; is_pinned: boolean; thread_id?: number }) => void;
  onChatLocked?: (data: { chat_id: number; is_active: boolean }) => void;
  onUserMuted?: (data: { user_id: number; is_muted: boolean }) => void;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'auth_error' | 'error';

export class ChatWebSocketService {
  private subscriptions = new Map<string, string>();
  private typingTimeouts = new Map<number, NodeJS.Timeout>();
  private eventHandlers: ChatEventHandlers = {};
  private connectionStatus: ConnectionStatus = 'disconnected';
  private connectionStatusCallbacks: ((status: ConnectionStatus) => void)[] = [];
  private connectionUnsubscribe: (() => void) | null = null;
  private authErrorUnsubscribe: (() => void) | null = null;
  private activeSubscriptions = new Map<number, string>();

  constructor() {
    // Подписываемся на системные события WebSocket
    this.connectionUnsubscribe = websocketService.onConnectionChange((connected) => {
      if (connected) {
        this.setConnectionStatus('connected');
        this.resubscribeAll();
        // Уведомляем обработчик onConnect
        if (this.eventHandlers.onConnect) {
          this.eventHandlers.onConnect();
        }
      } else {
        this.setConnectionStatus('disconnected');
      }
    });

    // Подписываемся на ошибки аутентификации
    this.authErrorUnsubscribe = websocketService.onAuthError((code, reason) => {
      logger.error('[ChatWebSocket] Auth error received:', { code, reason });
      this.handleAuthError(code, reason);
    });
  }


  /**
   * Обработка ошибок аутентификации
   * Вызывается при получении close codes 4001 (auth error) или 4002 (access denied)
   */
  private handleAuthError(code: number, reason: string): void {
    // Устанавливаем статус auth_error
    this.setConnectionStatus('auth_error');

    // Формируем сообщение об ошибке
    let errorMessage = reason;
    if (code === 4001) {
      errorMessage = 'Authentication failed. Please log in again.';
    } else if (code === 4002) {
      errorMessage = 'Access denied. You do not have permission to access this resource.';
    }

    // Вызываем обработчик ошибки если есть
    if (this.eventHandlers.onError) {
      this.eventHandlers.onError(errorMessage, code.toString());
    }

    // Опционально: редирект на страницу логина для 4001
    if (code === 4001 && typeof window !== 'undefined') {
      logger.info('[ChatWebSocket] Redirecting to login due to auth error');
      // Очищаем токены
      tokenStorage.clearTokens();
      // Редирект на страницу логина (опционально, можно убрать если не нужно)
      // window.location.href = '/login';
    }
  }
  /**
   * Установка статуса подключения и уведомление подписчиков
   */
  private setConnectionStatus(status: ConnectionStatus): void {
    if (this.connectionStatus !== status) {
      this.connectionStatus = status;
      this.connectionStatusCallbacks.forEach(callback => callback(status));
    }
  }

  /**
   * Подписка на изменения статуса подключения
   */
  onConnectionStatusChange(callback: (status: ConnectionStatus) => void): () => void {
    this.connectionStatusCallbacks.push(callback);
    return () => {
      this.connectionStatusCallbacks = this.connectionStatusCallbacks.filter(cb => cb !== callback);
    };
  }

  /**
   * Получение текущего статуса подключения
   */
  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * Получение токена авторизации из нескольких источников
   */
  private getAuthToken(): string | null {
    // Попытка получить токен из tokenStorage
    const { accessToken } = tokenStorage.getTokens();
    if (accessToken) {
      logger.debug('[ChatWebSocket] Using token from tokenStorage');
      return accessToken;
    }

    // Fallback: прямой доступ к localStorage
    const localStorageToken = localStorage.getItem('auth_token');
    if (localStorageToken) {
      logger.debug('[ChatWebSocket] Using token from localStorage (fallback)');
      return localStorageToken;
    }

    logger.error('[ChatWebSocket] No authentication token found in any storage');
    return null;
  }

  /**
   * Подключение к общему чату
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
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

      // Получаем токен через централизованный метод
      const token = this.getAuthToken();

      if (!token) {
        const errorMsg = 'Authentication token not found. Please log in again.';
        logger.error('[ChatWebSocket] ' + errorMsg);
        this.setConnectionStatus('auth_error');
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError(errorMsg);
        }
        return;
      }

      // Устанавливаем статус "подключение"
      this.setConnectionStatus('connecting');

      // Формируем URL для WebSocket подключения
      const tokenParam = `?token=${token}`;
      const fullUrl = `${baseUrl}/chat/general/${tokenParam}`;

      logger.info('[ChatWebSocket] Connecting to general chat:', {
        hasToken: !!token,
        tokenLength: token.length,
        fullUrl
      });

      websocketService.connect(fullUrl);
    }
  }

  /**
   * Подключение к конкретной чат-комнате
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
   * @returns Promise<boolean> - true если подключение установлено, false при ошибке
   */
  async connectToRoom(roomId: number, handlers: ChatEventHandlers): Promise<boolean> {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const channel = `chat_${roomId}`;

    // Получаем токен через централизованный метод
    const token = this.getAuthToken();

    if (!token) {
      const errorMsg = 'Authentication token not found. Please log in again.';
      logger.error('[ChatWebSocket] ' + errorMsg);
      this.setConnectionStatus('auth_error');
      if (handlers.onError) {
        handlers.onError(errorMsg);
      }
      return Promise.reject(new Error(errorMsg));
    }

    // Устанавливаем статус "подключение"
    this.setConnectionStatus('connecting');

    const subscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
      this.handleChatMessage(message);
    });

    this.subscriptions.set(channel, subscriptionId);
    this.activeSubscriptions.set(roomId, subscriptionId);

    // Формируем URL для WebSocket подключения
    const baseUrl = getWebSocketBaseUrl();
    const tokenParam = `?token=${token}`;
    const fullUrl = `${baseUrl}/chat/${roomId}/${tokenParam}`;

    logger.info('[ChatWebSocket] Connecting to room:', {
      roomId,
      hasToken: !!token,
      tokenLength: token.length,
      fullUrl
    });

    return new Promise((resolve, reject) => {
      let unsubscribe: (() => void) | null = null;

      const timeout = setTimeout(() => {
        if (unsubscribe) unsubscribe();
        logger.warn('[ChatWebSocket] Connection timeout');
        this.setConnectionStatus('error');
        reject(new Error('Connection timeout'));
      }, 5000);

      const checkConnection = () => {
        const status = this.getConnectionStatus();
        if (status === 'connected') {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          resolve(true);
        } else if (status === 'error' || status === 'auth_error') {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          reject(new Error(`Connection failed with status: ${status}`));
        }
      };

      // Subscribe to status changes
      unsubscribe = this.onConnectionStatusChange((status) => {
        if (status === 'connected') {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          resolve(true);
        } else if (status === 'error' || status === 'auth_error') {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          reject(new Error(`Connection failed with status: ${status}`));
        }
      });

      try {
        websocketService.connect(fullUrl);
        // Check if already connected (synchronous connect)
        checkConnection();
      } catch (error) {
        clearTimeout(timeout);
        if (unsubscribe) unsubscribe();
        logger.error('[ChatWebSocket] Failed to connect:', error);
        this.setConnectionStatus('error');
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        if (handlers.onError) {
          handlers.onError(errorMsg);
        }
        reject(new Error(errorMsg));
      }
    });
  }

  /**
   * Отключение от конкретной комнаты
   */
  disconnectFromRoom(roomId: number): void {
    if (!this.activeSubscriptions.has(roomId)) {
      logger.warn('[ChatWebSocket] Already disconnected from room', roomId);
      return;
    }

    const channel = `chat_${roomId}`;
    const subscriptionId = this.subscriptions.get(channel);

    if (subscriptionId) {
      websocketService.unsubscribe(subscriptionId);
      this.subscriptions.delete(channel);
    }

    this.activeSubscriptions.delete(roomId);

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
   * Полное отключение от WebSocket сервиса
   * Очищает все подписки, таймеры и закрывает соединение
   */
  disconnect(): void {
    // Очищаем все таймеры печати перед отключением
    this.clearAllTypingTimeouts();

    // Отписываемся от всех каналов
    this.subscriptions.forEach((subscriptionId) => {
      websocketService.unsubscribe(subscriptionId);
    });
    this.subscriptions.clear();
    this.activeSubscriptions.clear();

    // Отписываемся от системных событий
    if (this.connectionUnsubscribe) {
      this.connectionUnsubscribe();
      this.connectionUnsubscribe = null;
    }

    if (this.authErrorUnsubscribe) {
      this.authErrorUnsubscribe();
      this.authErrorUnsubscribe = null;
    }

    // Очищаем обработчики событий
    this.eventHandlers = {};

    // Отключаемся от WebSocket
    websocketService.disconnect();

    // Сбрасываем статус
    this.setConnectionStatus('disconnected');
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
   * Закрепить/открепить сообщение
   */
  sendPinMessage(roomId: number, messageId: number): void {
    websocketService.send({
      type: 'pin_message',
      room_id: roomId,
      message_id: messageId,
    });
  }

  /**
   * Заблокировать/разблокировать чат
   */
  sendLockChat(roomId: number): void {
    websocketService.send({
      type: 'lock_chat',
      room_id: roomId,
    });
  }

  /**
   * Замутить/размутить пользователя
   */
  sendMuteUser(roomId: number, userId: number): void {
    websocketService.send({
      type: 'mute_user',
      room_id: roomId,
      user_id: userId,
    });
  }

  /**
   * Валидация структуры входящего сообщения
   */
  private validateMessage(message: WebSocketMessage): { valid: boolean; error?: string } {
    if (!message || typeof message !== 'object') {
      return { valid: false, error: 'Message is not an object' };
    }

    if (!message.type || typeof message.type !== 'string') {
      return { valid: false, error: 'Message type is missing or invalid' };
    }

    // Валидация специфичных типов сообщений
    switch (message.type) {
      case 'chat_message':
        if (!message.message || typeof message.message !== 'object') {
          return { valid: false, error: 'chat_message must contain message object' };
        }
        if (!message.message.id || !message.message.content) {
          return { valid: false, error: 'chat_message.message must have id and content' };
        }
        break;

      case 'typing':
      case 'typing_stop':
      case 'user_joined':
      case 'user_left':
        if (!message.user || typeof message.user !== 'object') {
          return { valid: false, error: `${message.type} must contain user object` };
        }
        break;

      case 'room_history':
        if (!Array.isArray(message.messages)) {
          return { valid: false, error: 'room_history must contain messages array' };
        }
        break;

      case 'error':
        if (!message.error || typeof message.error !== 'string') {
          return { valid: false, error: 'error message must contain error string' };
        }
        break;

      case 'message_sent':
        if (typeof message.message_id !== 'number') {
          return { valid: false, error: 'message_sent must contain numeric message_id' };
        }
        if (message.status !== 'delivered') {
          return { valid: false, error: 'message_sent must have status "delivered"' };
        }
        break;
    }

    return { valid: true };
  }

  /**
   * Обработка входящих сообщений чата
   */
  private handleChatMessage(message: WebSocketMessage): void {
    logger.debug('[ChatWebSocketService] Received message:', {
      type: message.type,
      hasMessage: !!message.message,
      messageId: message.message?.id,
      hasHandler: !!this.eventHandlers.onMessage
    });

    // Валидация структуры сообщения
    const validation = this.validateMessage(message);
    if (!validation.valid) {
      logger.error('[ChatWebSocketService] Invalid message structure:', {
        error: validation.error,
        message
      });
      if (this.eventHandlers.onError) {
        this.eventHandlers.onError(
          `Invalid message: ${validation.error}`,
          'validation_error'
        );
      }
      return;
    }

    switch (message.type) {
      case 'chat_message':
        if (message.message && this.eventHandlers.onMessage) {
          logger.debug('[ChatWebSocketService] Calling onMessage handler for message ID:', message.message.id);
          this.eventHandlers.onMessage(message.message);
        } else {
          logger.warn('[ChatWebSocketService] chat_message received but no handler or message data:', {
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
        logger.error('[ChatWebSocketService] Server error received:', {
          error: message.error,
          code: message.code
        });
        if (message.error && this.eventHandlers.onError) {
          this.eventHandlers.onError(message.error, message.code);
        }

        // Специальная обработка ошибок авторизации
        if (message.code === 'auth_error' || message.code === 'access_denied') {
          this.setConnectionStatus('auth_error');
        }
        break;

      case 'message_sent':
        logger.debug('[ChatWebSocketService] Message delivery confirmation:', {
          messageId: message.message_id,
          status: message.status
        });
        if (message.message_id && this.eventHandlers.onMessageDelivered) {
          this.eventHandlers.onMessageDelivered(message.message_id);
        }
        break;

      case 'message_pinned':
        logger.debug('[ChatWebSocketService] Message pinned event:', {
          messageId: message.data?.message_id,
          isPinned: message.data?.is_pinned,
          threadId: message.data?.thread_id
        });
        if (message.data && this.eventHandlers.onMessagePinned) {
          this.eventHandlers.onMessagePinned(message.data);
        }
        break;

      case 'chat_locked':
        logger.debug('[ChatWebSocketService] Chat locked event:', {
          chatId: message.data?.chat_id,
          isActive: message.data?.is_active
        });
        if (message.data && this.eventHandlers.onChatLocked) {
          this.eventHandlers.onChatLocked(message.data);
        }
        break;

      case 'user_muted':
        logger.debug('[ChatWebSocketService] User muted event:', {
          userId: message.data?.user_id,
          isMuted: message.data?.is_muted
        });
        if (message.data && this.eventHandlers.onUserMuted) {
          this.eventHandlers.onUserMuted(message.data);
        }
        break;

      default:
        logger.warn('[ChatWebSocketService] Unknown message type:', message.type);
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError(
            `Unknown message type: ${message.type}`,
            'unknown_type'
          );
        }
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

  /**
   * Получение информации о переподключении
   */
  getReconnectionInfo(): {
    isReconnecting: boolean;
    attempt: number;
    maxAttempts: number;
    nextRetryDelay: number;
  } {
    return websocketService.getReconnectionInfo();
  }

  /**
   * Ручная повторная попытка подключения
   */
  retryConnection(): void {
    logger.info('[ChatWebSocket] Manual retry connection requested');
    websocketService.retryConnection();
  }
}

// Создаем глобальный экземпляр сервиса чата
export const chatWebSocketService = new ChatWebSocketService();

// Экспортируем типы
export type { ChatMessage, TypingUser, ChatEventHandlers };
