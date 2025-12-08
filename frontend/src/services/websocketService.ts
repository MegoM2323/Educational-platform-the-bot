import { logger } from '@/utils/logger';

/**
 * WebSocket Service для real-time коммуникации
 * Поддерживает автоматическое переподключение, управление подписками и очереди сообщений
 */

export interface WebSocketMessage {
  type: string;
  data?: any;
  message?: any;
  user?: any;
  error?: string;
}

export interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
}

export interface Subscription {
  channel: string;
  callback: (data: any) => void;
  id: string;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private subscriptions = new Map<string, Subscription>();
  private messageQueue: WebSocketMessage[] = [];
  private isConnecting = false;
  private connectionState: 'disconnected' | 'connecting' | 'connected' = 'disconnected';
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  private currentUrl: string | null = null;

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      ...config
    };
    this.currentUrl = config.url;
  }

  /**
   * Подключение к WebSocket серверу с опциональным URL
   * @param url - Опциональный URL для подключения. Если не указан, используется текущий URL
   */
  async connect(url?: string): Promise<void> {
    // If URL provided, disconnect first if connected to different URL
    if (url && this.currentUrl !== url) {
      logger.debug(`[WebSocket] Switching URL from ${this.currentUrl} to ${url}`);
      this.disconnect();
      this.currentUrl = url;
    }

    const targetUrl = this.currentUrl || this.config.url;

    if (this.isConnecting || this.connectionState === 'connected') {
      logger.debug('[WebSocket] Already connecting or connected to:', targetUrl);
      return;
    }

    this.isConnecting = true;
    this.connectionState = 'connecting';
    this.notifyConnectionChange(false);

    // CRITICAL DEBUG: Log full WebSocket URL with token
    const urlParts = targetUrl.split('?');
    const hasQueryParams = urlParts.length > 1;
    const queryParams = hasQueryParams ? urlParts[1] : 'no-params';

    logger.info('[WebSocket] Connection attempt:', {
      fullUrl: targetUrl,
      basePath: urlParts[0],
      queryParams,
      hasToken: queryParams.includes('token='),
      tokenPreview: queryParams.includes('token=')
        ? queryParams.split('token=')[1]?.substring(0, 10) + '...'
        : 'NO-TOKEN'
    });

    try {
      this.ws = new WebSocket(targetUrl);

      this.ws.onopen = () => {
        logger.debug('[WebSocket] Connected successfully to:', targetUrl);
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.notifyConnectionChange(true);
        this.startHeartbeat();
        this.processMessageQueue();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          logger.debug('[WebSocketService] Raw WebSocket message received:', {
            type: message.type,
            hasMessage: !!message.message,
            messageId: message.message?.id,
            fullPayload: message
          });
          // Тестовая интеграция: сохраняем сообщения в window.__wsMessages для Playwright-тестов
          try {
            if (typeof window !== 'undefined') {
              const w = window as any;
              if (!Array.isArray(w.__wsMessages)) {
                w.__wsMessages = [];
              }
              w.__wsMessages.push(message);
            }
          } catch {}
          this.handleMessage(message);
        } catch (error) {
          logger.error('[WebSocket] Error parsing message:', error);
        }
      };

      this.ws.onclose = (event) => {
        logger.debug('[WebSocket] Disconnected:', event.code, event.reason);
        this.connectionState = 'disconnected';
        this.isConnecting = false;
        this.notifyConnectionChange(false);
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        logger.error('[WebSocket] Connection error:', error);
        this.isConnecting = false;
        this.connectionState = 'disconnected';
        this.notifyConnectionChange(false);
      };

    } catch (error) {
      logger.error('[WebSocket] Failed to create connection:', error);
      this.isConnecting = false;
      this.connectionState = 'disconnected';
      this.notifyConnectionChange(false);
      this.scheduleReconnect();
    }
  }

  /**
   * Отключение от WebSocket сервера
   */
  disconnect(): void {
    this.stopHeartbeat();
    this.clearReconnectTimer();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.connectionState = 'disconnected';
    this.isConnecting = false;
    this.notifyConnectionChange(false);
  }

  /**
   * Отправка сообщения через WebSocket
   */
  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        logger.error('Error sending WebSocket message:', error);
        this.queueMessage(message);
      }
    } else {
      this.queueMessage(message);
    }
  }

  /**
   * Подписка на канал
   */
  subscribe(channel: string, callback: (data: any) => void): string {
    const subscriptionId = `${channel}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    this.subscriptions.set(subscriptionId, {
      channel,
      callback,
      id: subscriptionId
    });

    // Отправляем сообщение о подписке на сервер
    this.send({
      type: 'subscribe',
      data: { channel }
    });

    return subscriptionId;
  }

  /**
   * Отписка от канала
   */
  unsubscribe(subscriptionId: string): void {
    const subscription = this.subscriptions.get(subscriptionId);
    if (subscription) {
      this.subscriptions.delete(subscriptionId);
      
      // Отправляем сообщение об отписке на сервер
      this.send({
        type: 'unsubscribe',
        data: { channel: subscription.channel }
      });
    }
  }

  /**
   * Проверка состояния соединения
   */
  isConnected(): boolean {
    return this.connectionState === 'connected' && 
           this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Подписка на изменения состояния соединения
   */
  onConnectionChange(callback: (connected: boolean) => void): void {
    this.connectionCallbacks.push(callback);
  }

  /**
   * Отписка от изменений состояния соединения
   */
  offConnectionChange(callback: (connected: boolean) => void): void {
    const index = this.connectionCallbacks.indexOf(callback);
    if (index > -1) {
      this.connectionCallbacks.splice(index, 1);
    }
  }

  /**
   * Обработка входящих сообщений
   */
  private handleMessage(message: WebSocketMessage): void {
    // Обрабатываем системные сообщения
    if (message.type === 'pong') {
      return; // Heartbeat response
    }

    if (message.type === 'error') {
      logger.error('WebSocket server error:', message.error);
      return;
    }

    logger.debug('[WebSocketService] Broadcasting to', this.subscriptions.size, 'subscriptions');
    // Уведомляем подписчиков
    this.subscriptions.forEach((subscription) => {
      try {
        logger.debug('[WebSocketService] Calling subscription callback for channel:', subscription.channel);
        subscription.callback(message);
      } catch (error) {
        logger.error('Error in subscription callback:', error);
      }
    });
  }

  /**
   * Планирование переподключения
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      logger.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.config.reconnectInterval! * Math.pow(2, this.reconnectAttempts - 1);
    
    logger.debug(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Очистка таймера переподключения
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Запуск heartbeat
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping' });
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Остановка heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Добавление сообщения в очередь
   */
  private queueMessage(message: WebSocketMessage): void {
    if (this.messageQueue.length >= this.config.messageQueueSize!) {
      this.messageQueue.shift(); // Удаляем самое старое сообщение
    }
    this.messageQueue.push(message);
  }

  /**
   * Обработка очереди сообщений
   */
  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  /**
   * Уведомление об изменении состояния соединения
   */
  private notifyConnectionChange(connected: boolean): void {
    this.connectionCallbacks.forEach(callback => {
      try {
        callback(connected);
      } catch (error) {
        logger.error('Error in connection change callback:', error);
      }
    });
  }
}

/**
 * Gets base WebSocket URL (without specific path like /chat/XXX/)
 * This consolidates the URL detection logic (no duplication)
 */
export function getWebSocketBaseUrl(): string {
  // Priority 1: Environment variable
  const envUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WEBSOCKET_URL);
  if (envUrl && envUrl !== 'undefined') {
    const url = envUrl.replace(/\/$/, '');
    logger.debug('[WebSocket Config] Using base URL from VITE_WEBSOCKET_URL env var:', url);
    return url;
  }

  // Priority 2: Auto-detect from current location
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;
    logger.debug('[WebSocket Config] Using auto-detected base URL from window.location:', url);
    return url;
  }

  // Fallback 3: SSR or build-time only
  logger.debug('[WebSocket Config] Using fallback base URL (SSR/build-time)');
  return 'ws://localhost:8000/ws';
}

// Initialize with a placeholder URL - actual URL will be provided when connecting
const WEBSOCKET_BASE_URL = getWebSocketBaseUrl();

export const websocketService = new WebSocketService({
  url: `${WEBSOCKET_BASE_URL}/chat/general/`, // Default fallback URL
  reconnectInterval: 5000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 100
});

// Экспортируем типы для использования в других модулях
export type { WebSocketMessage, WebSocketConfig, Subscription };
