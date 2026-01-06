import { WebSocketService, WebSocketConfig } from '../../services/websocketService';
import { tokenStorage } from '../../services/tokenStorage';
import { logger } from '../../utils/logger';
import type { ChatMessage } from '../api/chatAPI';

export type ChatSocketEvent =
  | 'message_received'
  | 'message_deleted'
  | 'message_updated'
  | 'chat_created'
  | 'user_typing'
  | 'user_online'
  | 'connection_established'
  | 'connection_lost';

export interface ChatSocketMessage {
  type: ChatSocketEvent;
  chat_id?: number;
  message?: ChatMessage;
  message_id?: number;
  user_id?: number;
  user_name?: string;
  is_typing?: boolean;
  is_online?: boolean;
}

export interface ChatSubscription {
  chatId: number;
  callback: (event: ChatSocketMessage) => void;
  unsubscribe: () => void;
}

class ChatSocketService extends WebSocketService {
  private chatSubscriptions = new Map<number, Set<(msg: ChatSocketMessage) => void>>();
  private globalSubscriptions = new Map<ChatSocketEvent, Set<(msg: ChatSocketMessage) => void>>();
  private typingTimeouts = new Map<number, NodeJS.Timeout>();
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private baseReconnectInterval = 1000;
  private maxReconnectInterval = 30000;
  private lastRoomId?: number;
  private lastToken?: string;

  constructor(url: string) {
    super({
      url,
      reconnectInterval: 1000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
    });
  }

  async connect(roomId?: number, token?: string): Promise<void> {
    try {
      const authToken = token || tokenStorage.getAccessToken();

      if (!authToken) {
        logger.warn('[ChatSocket] No auth token available');
        throw new Error('Требуется аутентификация');
      }

      this.lastRoomId = roomId;
      this.lastToken = authToken;

      const wsUrl = roomId
        ? `${this.getCurrentUrl(roomId)}?token=${authToken}`
        : `${this.getCurrentUrl()}?token=${authToken}`;
      logger.info('[ChatSocket] Connecting with token', { roomId });

      await super.connect(wsUrl);
      this.setupEventHandlers();
      this.setupConnectionMonitoring();
    } catch (error) {
      logger.error('[ChatSocket] Connection failed:', error);
      throw error;
    }
  }

  private setupConnectionMonitoring(): void {
    this.onConnectionChange((connected) => {
      if (connected) {
        this.notifyConnectionRestored();
      } else {
        logger.warn('[ChatSocket] Connection lost unexpectedly - attempting reconnect');
        this.attemptReconnect();
      }
    });
  }

  private setupEventHandlers(): void {
    this.subscribe('chat_message', (message) => {
      this.handleChatMessage(message);
    });

    this.subscribe('chat_event', (message) => {
      this.handleChatEvent(message);
    });
  }

  private handleChatMessage(wsMessage: Record<string, unknown>): void {
    if (!wsMessage.data) return;

    const data = wsMessage.data as Record<string, unknown>;
    const msg: ChatSocketMessage = {
      type: 'message_received',
      chat_id: data.chat_id as number,
      message: data.message as ChatMessage,
    };

    this.broadcastChatMessage(msg);
  }

  private handleChatEvent(wsMessage: Record<string, unknown>): void {
    if (!wsMessage.data) return;

    const data = wsMessage.data as Record<string, unknown>;
    const eventType = data.type as string;
    const msg: ChatSocketMessage = {
      type: eventType as ChatSocketEvent,
      chat_id: data.chat_id as number,
      message_id: data.message_id as number,
      user_id: data.user_id as number,
      user_name: data.user_name as string,
      is_typing: data.is_typing as boolean,
      is_online: data.is_online as boolean,
    };

    this.broadcastChatMessage(msg);
  }

  send(chatId: number, message: string): void {
    if (!message.trim()) {
      logger.warn('[ChatSocket] Attempt to send empty message');
      return;
    }

    const payload = {
      type: 'chat_message',
      data: {
        chat_id: chatId,
        content: message,
        timestamp: new Date().toISOString(),
      },
    };

    this.sendMessage(JSON.stringify(payload));
    logger.debug('[ChatSocket] Message sent:', { chatId });
  }

  subscribeToChat(chatId: number, callback: (msg: ChatSocketMessage) => void): () => void {
    if (!this.chatSubscriptions.has(chatId)) {
      this.chatSubscriptions.set(chatId, new Set());
    }

    const callbacks = this.chatSubscriptions.get(chatId)!;
    callbacks.add(callback);

    logger.debug('[ChatSocket] Subscribed to chat:', { chatId, count: callbacks.size });

    return () => {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.chatSubscriptions.delete(chatId);
        logger.debug('[ChatSocket] Unsubscribed from chat:', { chatId });
      }
    };
  }

  subscribeToEvent(event: ChatSocketEvent, callback: (msg: ChatSocketMessage) => void): () => void {
    if (!this.globalSubscriptions.has(event)) {
      this.globalSubscriptions.set(event, new Set());
    }

    const callbacks = this.globalSubscriptions.get(event)!;
    callbacks.add(callback);

    logger.debug('[ChatSocket] Subscribed to event:', { event, count: callbacks.size });

    return () => {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.globalSubscriptions.delete(event);
      }
    };
  }

  private broadcastChatMessage(msg: ChatSocketMessage): void {
    if (msg.chat_id && this.chatSubscriptions.has(msg.chat_id)) {
      const callbacks = this.chatSubscriptions.get(msg.chat_id)!;
      callbacks.forEach((callback) => {
        try {
          callback(msg);
        } catch (error) {
          logger.error('[ChatSocket] Callback error:', error);
        }
      });
    }

    if (this.globalSubscriptions.has(msg.type)) {
      const callbacks = this.globalSubscriptions.get(msg.type)!;
      callbacks.forEach((callback) => {
        try {
          callback(msg);
        } catch (error) {
          logger.error('[ChatSocket] Callback error:', error);
        }
      });
    }
  }

  private broadcastConnectionEvent(event: ChatSocketEvent): void {
    const msg: ChatSocketMessage = { type: event };
    this.connectionCallbacks.forEach((callback) => {
      try {
        callback(event === 'connection_established');
      } catch (error) {
        logger.error('[ChatSocket] Connection callback error:', error);
      }
    });
  }

  private getReconnectDelay(): number {
    const delay = Math.min(
      this.baseReconnectInterval * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectInterval
    );
    return delay;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('[ChatSocket] Max reconnect attempts reached');
      this.notifyConnectionLost();
      return;
    }

    const delay = this.getReconnectDelay();
    logger.info(
      `[ChatSocket] Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts + 1})`
    );

    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect(this.lastRoomId, this.lastToken).catch((error) => {
        logger.error('[ChatSocket] Reconnection failed:', error);
        this.attemptReconnect();
      });
    }, delay);
  }

  private notifyConnectionLost(): void {
    logger.warn('[ChatSocket] Connection permanently lost. Please refresh the page.');
    this.broadcastConnectionEvent('connection_lost');
  }

  private notifyConnectionRestored(): void {
    logger.info('[ChatSocket] Connection restored successfully');
    this.reconnectAttempts = 0;
    this.broadcastConnectionEvent('connection_established');
  }

  onConnectionChange(callback: (connected: boolean) => void): () => void {
    this.connectionCallbacks.push(callback);
    return () => {
      this.connectionCallbacks = this.connectionCallbacks.filter(
        (cb: (arg0: boolean) => void) => cb !== callback
      );
    };
  }

  sendTypingIndicator(chatId: number, isTyping: boolean): void {
    const payload = {
      type: 'user_event',
      data: {
        chat_id: chatId,
        event_type: 'typing',
        is_typing: isTyping,
        timestamp: new Date().toISOString(),
      },
    };

    this.sendMessage(JSON.stringify(payload));
  }

  sendOnlineStatus(isOnline: boolean): void {
    const payload = {
      type: 'user_event',
      data: {
        event_type: 'online_status',
        is_online: isOnline,
        timestamp: new Date().toISOString(),
      },
    };

    this.sendMessage(JSON.stringify(payload));
  }

  isConnected(): boolean {
    return super.isConnected();
  }

  getConnectionStatus(): 'connected' | 'connecting' | 'disconnected' {
    return this.isConnected() ? 'connected' : 'disconnected';
  }

  private getCurrentUrl(roomId?: number): string {
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const baseUrl = `${protocol}//${window.location.host}/ws/chat`;
      return roomId ? `${baseUrl}/${roomId}/` : baseUrl;
    }
    const baseUrl = 'ws://localhost:8003/ws/chat';
    return roomId ? `${baseUrl}/${roomId}/` : baseUrl;
  }

  override disconnect(): void {
    this.chatSubscriptions.clear();
    this.globalSubscriptions.clear();
    this.typingTimeouts.forEach((timeout) => clearTimeout(timeout));
    this.typingTimeouts.clear();
    super.disconnect();
    logger.info('[ChatSocket] Disconnected');
  }

  private sendMessage(data: string): void {
    if (this.isConnected()) {
      try {
        this.send(data);
      } catch (error) {
        logger.error('[ChatSocket] Failed to send message:', error);
      }
    } else {
      logger.warn('[ChatSocket] Cannot send message - not connected');
    }
  }

  private subscribe(channel: string, callback: (data: Record<string, unknown>) => void): void {
    const payload = {
      type: 'subscribe',
      channel,
    };
    this.sendMessage(JSON.stringify(payload));
  }
}

let chatSocketInstance: ChatSocketService | null = null;

export function initChatSocket(wsUrl?: string): ChatSocketService {
  if (!chatSocketInstance) {
    const url = wsUrl || getDefaultWebSocketUrl();
    chatSocketInstance = new ChatSocketService(url);
  }
  return chatSocketInstance;
}

export function getChatSocket(): ChatSocketService {
  if (!chatSocketInstance) {
    throw new Error('ChatSocket not initialized. Call initChatSocket first.');
  }
  return chatSocketInstance;
}

export function getDefaultWebSocketUrl(roomId?: number): string {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const baseUrl = `${protocol}//${window.location.host}/ws/chat`;
    return roomId ? `${baseUrl}/${roomId}/` : baseUrl;
  }
  const baseUrl = 'ws://localhost:8003/ws/chat';
  return roomId ? `${baseUrl}/${roomId}/` : baseUrl;
}
