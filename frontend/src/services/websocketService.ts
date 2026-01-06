import { logger } from '@/utils/logger';

/**
 * WebSocket Service для real-time коммуникации
 * Поддерживает автоматическое переподключение, управление подписками и очереди сообщений
 */

export interface WebSocketMessage {
  type: string;
  data?: any;
  message?: any;
  messages?: any[];
  user?: any;
  error?: string;
  code?: string;
  message_id?: number;
  status?: string;
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
  private authErrorCallbacks: ((code: number, reason: string) => void)[] = [];

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

        // Проверка на permanent errors (не пытаемся переподключиться)
        if (event.code === 4001) {
          // 4001: Authentication error
          logger.error('[WebSocket] Authentication error - token invalid or expired');
          this.notifyAuthError(event.code, event.reason || 'Authentication failed');
        } else if (event.code === 4002) {
          // 4002: Access denied
          logger.error('[WebSocket] Access denied - insufficient permissions');
          this.notifyAuthError(event.code, event.reason || 'Access denied');
        } else {
          // Другие ошибки - пытаемся переподключиться
          this.scheduleReconnect();
        }
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
   * Ручная повторная попытка подключения (сброс счетчика попыток)
   */
  retryConnection(): void {
    logger.info('[WebSocket] Manual retry connection requested');
    this.clearReconnectTimer();
    this.reconnectAttempts = 0;
    this.connect();
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
   * Получение информации о текущем состоянии переподключения
   */
  getReconnectionInfo(): {
    isReconnecting: boolean;
    attempt: number;
    maxAttempts: number;
    nextRetryDelay: number;
  } {
    const isReconnecting = this.reconnectTimer !== null;
    return {
      isReconnecting,
      attempt: this.reconnectAttempts,
      maxAttempts: this.config.maxReconnectAttempts || 10,
      nextRetryDelay: isReconnecting ? this.getReconnectDelay() : 0,
    };
  }

  /**
   * Подписка на ошибки аутентификации
   * @param callback - Функция обработчик, принимающая код ошибки и описание
   */
  onAuthError(callback: (code: number, reason: string) => void): void {
    this.authErrorCallbacks.push(callback);
  }

  /**
   * Отписка от ошибок аутентификации
   */
  offAuthError(callback: (code: number, reason: string) => void): void {
    const index = this.authErrorCallbacks.indexOf(callback);
    if (index > -1) {
      this.authErrorCallbacks.splice(index, 1);
    }
  }

  /**
   * Уведомление об ошибке аутентификации
   */
  private notifyAuthError(code: number, reason: string): void {
    this.authErrorCallbacks.forEach(callback => {
      try {
        callback(code, reason);
      } catch (error) {
        logger.error('Error in auth error callback:', error);
      }
    });
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
   * Вычисление задержки переподключения с экспоненциальной отсрочкой
   * Начинается с 1s, удваивается каждую попытку: 1s, 2s, 4s, 8s, 16s, 30s (max)
   *
   * Эта стратегия (exponential backoff) предотвращает перегрузку сервера при сетевых сбоях,
   * пока одновременно обеспечивает быстрое переподключение при краткосрочных прерываниях.
   *
   * Примеры задержек:
   * - Попытка 1: 1s
   * - Попытка 2: 2s
   * - Попытка 3: 4s
   * - Попытка 4: 8s
   * - Попытка 5: 16s
   * - Попытка 6+: 30s (максимум)
   */
  private getReconnectDelay(): number {
    const baseDelay = 1000; // 1 секунда
    const maxDelay = 30000; // 30 секунд максимум
    const exponentialDelay = baseDelay * Math.pow(2, this.reconnectAttempts);
    return Math.min(exponentialDelay, maxDelay);
  }

  /**
   * Планирование переподключения с экспоненциальной отсрочкой
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      logger.error(`[WebSocket] Max reconnection attempts (${this.config.maxReconnectAttempts}) reached`);
      this.notifyConnectionChange(false);
      return;
    }

    this.reconnectAttempts++;
    const delay = this.getReconnectDelay();

    logger.info(`[WebSocket] Scheduling reconnection attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      logger.info(`[WebSocket] Executing reconnection attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts}`);
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
    if (this.messageQueue.length === 0) {
      return;
    }

    logger.info(`[WebSocket] Processing message queue: ${this.messageQueue.length} messages`);

    let processedCount = 0;
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        try {
          this.send(message);
          processedCount++;
        } catch (error) {
          logger.error('[WebSocket] Error processing queued message:', error);
          // Если ошибка при отправке, возвращаем сообщение в очередь
          this.messageQueue.unshift(message);
          break;
        }
      }
    }

    logger.info(`[WebSocket] Processed ${processedCount} queued messages, ${this.messageQueue.length} remaining`);
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
  reconnectInterval: 1000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 100
});

// Экспортируем типы для использования в других модулях
export type { WebSocketMessage, WebSocketConfig, Subscription };
