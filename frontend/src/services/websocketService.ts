import { logger } from "@/utils/logger";

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

export interface ReconnectInfo {
  attempt: number;
  maxAttempts: number;
  nextDelay: number;
  lastDelay: number;
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
  private connectionState: "disconnected" | "connecting" | "connected" =
    "disconnected";
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  private currentUrl: string | null = null;
  private authErrorCallbacks: ((code: number, reason: string) => void)[] = [];
  private maxReconnectDelay = 32000;
  private isReconnecting = false;
  private lastConnectTime = 0;
  private reconnectAttemptCallbacks: ((info: ReconnectInfo) => void)[] = [];
  private reconnectSuccessCallbacks: (() => void)[] = [];
  private reconnectFailedCallbacks: (() => void)[] = [];
  private lastSuccessfulConnection = 0;
  private heartbeatStartTime = 0;
  private lastHeartbeatTime = 0;
  private messageCount = 0;

  private wsLogger = {
    debug: (msg: string, data?: any) => {
      if (typeof window !== "undefined" && (window as any).__WS_DEBUG) {
        console.debug(`[WebSocket] ${msg}`, data || "");
      }
    },
    info: (msg: string, data?: any) => {
      console.info(`[WebSocket] ${msg}`, data || "");
    },
    warn: (msg: string, data?: any) => {
      console.warn(`[WebSocket] ${msg}`, data || "");
    },
    error: (msg: string, error?: any) => {
      console.error(`[WebSocket] ${msg}`, error || "");
    },
  };

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      ...config,
    };
    this.currentUrl = config.url;
    this.lastSuccessfulConnection = Date.now();
  }

  private log(
    level: "debug" | "info" | "warn" | "error",
    msg: string,
    context?: Record<string, any>,
  ): void {
    const timestamp = new Date().toISOString();
    const state = {
      connected: this.connectionState === "connected",
      connecting: this.connectionState === "connecting",
      reconnecting: this.isReconnecting,
      reconnect_attempts: this.reconnectAttempts,
      subscriptions_count: this.subscriptions.size,
      message_queue_size: this.messageQueue.length,
      uptime_ms: Date.now() - this.lastSuccessfulConnection,
    };

    const logEntry = {
      timestamp,
      level: level.toUpperCase(),
      message: msg,
      context: context || {},
      state,
    };

    if (level === "error") {
      this.wsLogger.error(msg, { ...context, state, timestamp });
      this.sendToMonitoring(logEntry);
    } else if (level === "warn") {
      this.wsLogger.warn(msg, { ...context, state, timestamp });
    } else if (level === "info") {
      this.wsLogger.info(msg, { ...context, state, timestamp });
    } else {
      this.wsLogger.debug(msg, { ...context, state, timestamp });
    }
  }

  private sendToMonitoring(logEntry: any): void {
    if (typeof window !== "undefined" && (window as any).__SENTRY) {
      try {
        (window as any).__SENTRY.captureException(new Error(logEntry.message), {
          extra: logEntry,
        });
      } catch (err) {
        // Silently fail monitoring
      }
    }
  }

  /**
   * Подключение к WebSocket серверу с опциональным URL и токеном
   * @param url - Опциональный URL для подключения. Если не указан, используется текущий URL
   * @param token - Опциональный JWT токен для отправки в первом сообщении
   */
  async connect(url?: string, token?: string): Promise<void> {
    // If URL provided, disconnect first if connected to different URL
    if (url && this.currentUrl !== url) {
      this.log("debug", "URL switching", {
        from: this.currentUrl,
        to: url,
      });
      this.disconnect();
      this.currentUrl = url;
    }

    const targetUrl = this.currentUrl || this.config.url;
    const cleanUrl = targetUrl.split("?")[0];

    if (this.isConnecting || this.connectionState === "connected") {
      this.log("debug", "Connection already in progress or established", {
        isConnecting: this.isConnecting,
        connectionState: this.connectionState,
      });
      return;
    }

    this.isConnecting = true;
    this.connectionState = "connecting";
    this.notifyConnectionChange(false);

    this.log("info", "Attempting WebSocket connection", {
      url: cleanUrl,
      attempt: this.reconnectAttempts + 1,
      maxAttempts: this.config.maxReconnectAttempts,
      hasToken: !!token,
      tokenLength: token?.length || 0,
    });

    try {
      this.ws = new WebSocket(cleanUrl);

      this.ws.onopen = () => {
        this.log("info", "WebSocket connection established", {
          url: cleanUrl,
          connectedAt: new Date().toISOString(),
          reconnectionSuccess: this.reconnectAttempts > 0,
        });

        this.connectionState = "connected";
        this.lastConnectTime = Date.now();
        this.lastSuccessfulConnection = Date.now();
        this.isConnecting = false;
        this.isReconnecting = false;
        this.notifyConnectionChange(true);

        if (this.reconnectAttempts > 0) {
          this.log("info", "Successfully reconnected", {
            attemptsTaken: this.reconnectAttempts,
            recoveryTime: Date.now() - (this.lastConnectTime || Date.now()),
          });
          this.notifyReconnectSuccess();
        }

        this.reconnectAttempts = 0;
        this.startHeartbeat();

        if (token) {
          this.log("debug", "Sending authentication message", {
            tokenLength: token.length,
            type: "auth",
          });
          this.send({
            type: "auth",
            token: token,
          });
        }

        this.processMessageQueue();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.messageCount++;

          // Only log details for special messages, not every message
          if (message.type === "pong") {
            const now = Date.now();
            const latency = now - this.lastHeartbeatTime;
            this.log("debug", "Pong received (heartbeat)", {
              latency_ms: latency,
              messageNumber: this.messageCount,
            });
          } else {
            this.log("debug", "Message received from server", {
              type: message.type,
              messageCount: this.messageCount,
              payloadSize: event.data.length,
            });
          }

          try {
            if (typeof window !== "undefined") {
              const w = window as any;
              if (!Array.isArray(w.__wsMessages)) {
                w.__wsMessages = [];
              }
              w.__wsMessages.push(message);
            }
          } catch {}
          this.handleMessage(message);
        } catch (error) {
          this.log("error", "Failed to parse WebSocket message", {
            error: error instanceof Error ? error.message : String(error),
            dataLength: event.data.length,
          });
        }
      };

      this.ws.onclose = (event) => {
        this.log("info", "WebSocket connection closed", {
          code: event.code,
          reason: event.reason,
          wasConnected: this.connectionState === "connected",
          connectionDuration: Date.now() - this.lastConnectTime,
        });

        this.connectionState = "disconnected";
        this.isConnecting = false;
        this.notifyConnectionChange(false);
        this.stopHeartbeat();

        if (event.code === 4001) {
          this.log("error", "Authentication error - token invalid or expired", {
            code: event.code,
            reason: event.reason,
          });
          this.notifyAuthError(
            event.code,
            event.reason || "Authentication failed",
          );
        } else if (event.code === 4002) {
          this.log("error", "Access denied - insufficient permissions", {
            code: event.code,
            reason: event.reason,
          });
          this.notifyAuthError(event.code, event.reason || "Access denied");
        } else if (event.code === 4003) {
          this.log("error", "Forbidden - chat access denied or chat deleted", {
            code: event.code,
            reason: event.reason,
          });
          this.notifyAuthError(
            event.code,
            event.reason || "Chat access forbidden",
          );
        } else {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (event) => {
        this.log("error", "WebSocket connection error", {
          readyState: this.ws?.readyState,
          url: cleanUrl,
        });
        this.isConnecting = false;
        this.connectionState = "disconnected";
        this.notifyConnectionChange(false);
      };
    } catch (error) {
      this.log("error", "Failed to create WebSocket connection", {
        error: error instanceof Error ? error.message : String(error),
        url: cleanUrl,
      });
      this.isConnecting = false;
      this.connectionState = "disconnected";
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
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }

    this.connectionState = "disconnected";
    this.isConnecting = false;
    this.notifyConnectionChange(false);
  }

  /**
   * Ручная повторная попытка подключения (сброс счетчика попыток)
   */
  retryConnection(): void {
    logger.info("[WebSocket] Manual retry connection requested");
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
        const startTime = Date.now();
        this.ws.send(JSON.stringify(message));
        const duration = Date.now() - startTime;

        this.log("debug", "Message sent", {
          type: message.type,
          payloadSize: JSON.stringify(message).length,
          duration_ms: duration,
        });

        if (duration > 100) {
          this.log("warn", "Slow message send", {
            type: message.type,
            duration_ms: duration,
          });
        }
      } catch (error) {
        this.log("error", "Failed to send WebSocket message", {
          type: message.type,
          error: error instanceof Error ? error.message : String(error),
        });
        this.queueMessage(message);
      }
    } else {
      this.log("debug", "Message queued (connection not open)", {
        type: message.type,
        queueSize: this.messageQueue.length + 1,
      });
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
      id: subscriptionId,
    });

    this.log("debug", "Subscribed to channel", {
      channel,
      subscriptionId: subscriptionId.substring(0, 20) + "...",
      totalSubscriptions: this.subscriptions.size,
    });

    // Отправляем сообщение о подписке на сервер
    this.send({
      type: "subscribe",
      data: { channel },
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

      this.log("debug", "Unsubscribed from channel", {
        channel: subscription.channel,
        subscriptionId: subscriptionId.substring(0, 20) + "...",
        remainingSubscriptions: this.subscriptions.size,
      });

      // Отправляем сообщение об отписке на сервер
      this.send({
        type: "unsubscribe",
        data: { channel: subscription.channel },
      });
    } else {
      this.log(
        "warn",
        "Attempted to unsubscribe from non-existent subscription",
        {
          subscriptionId: subscriptionId.substring(0, 20) + "...",
        },
      );
    }
  }

  /**
   * Проверка состояния соединения
   */
  isConnected(): boolean {
    return (
      this.connectionState === "connected" &&
      this.ws?.readyState === WebSocket.OPEN
    );
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
   * Подписка на события попытки переподключения
   */
  onReconnectAttempt(callback: (info: ReconnectInfo) => void): () => void {
    this.reconnectAttemptCallbacks.push(callback);
    return () => {
      this.reconnectAttemptCallbacks = this.reconnectAttemptCallbacks.filter(
        (cb) => cb !== callback,
      );
    };
  }

  /**
   * Подписка на успешное переподключение
   */
  onReconnectSuccess(callback: () => void): () => void {
    this.reconnectSuccessCallbacks.push(callback);
    return () => {
      this.reconnectSuccessCallbacks = this.reconnectSuccessCallbacks.filter(
        (cb) => cb !== callback,
      );
    };
  }

  /**
   * Подписка на неудачное переподключение (исчерпаны попытки)
   */
  onReconnectFailed(callback: () => void): () => void {
    this.reconnectFailedCallbacks.push(callback);
    return () => {
      this.reconnectFailedCallbacks = this.reconnectFailedCallbacks.filter(
        (cb) => cb !== callback,
      );
    };
  }

  /**
   * Уведомление о попытке переподключения
   */
  private notifyReconnectAttempt(): void {
    const lastDelay = this.getReconnectDelay();
    const nextDelay =
      this.reconnectAttempts < (this.config.maxReconnectAttempts || 10)
        ? Math.min(
            1000 * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay,
          )
        : 0;

    const info: ReconnectInfo = {
      attempt: this.reconnectAttempts,
      maxAttempts: this.config.maxReconnectAttempts || 10,
      nextDelay,
      lastDelay,
    };

    this.reconnectAttemptCallbacks.forEach((callback) => {
      try {
        callback(info);
      } catch (error) {
        this.log("error", "Error in reconnect attempt callback", {
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
  }

  /**
   * Уведомление об успешном переподключении
   */
  private notifyReconnectSuccess(): void {
    this.log("info", "Notifying reconnect success", {
      callbackCount: this.reconnectSuccessCallbacks.length,
    });

    this.reconnectSuccessCallbacks.forEach((callback) => {
      try {
        callback();
      } catch (error) {
        this.log("error", "Error in reconnect success callback", {
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
  }

  /**
   * Уведомление о неудачном переподключении
   */
  private notifyReconnectFailed(): void {
    this.log("error", "Notifying reconnect failed", {
      callbackCount: this.reconnectFailedCallbacks.length,
      attemptsMade: this.reconnectAttempts,
    });

    this.reconnectFailedCallbacks.forEach((callback) => {
      try {
        callback();
      } catch (error) {
        this.log("error", "Error in reconnect failed callback", {
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
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
    this.authErrorCallbacks.forEach((callback) => {
      try {
        callback(code, reason);
      } catch (error) {
        logger.error("Error in auth error callback:", error);
      }
    });
  }

  /**
   * Обработка входящих сообщений
   */
  private handleMessage(message: WebSocketMessage): void {
    // Обрабатываем системные сообщения
    if (message.type === "pong") {
      return; // Heartbeat response - уже залогирована в onmessage
    }

    if (message.type === "error") {
      this.log("error", "Server error received", {
        error: message.error,
        code: message.code,
      });
      return;
    }

    // Уведомляем подписчиков
    this.log("debug", "Broadcasting message to subscriptions", {
      messageType: message.type,
      subscriptionCount: this.subscriptions.size,
    });

    this.subscriptions.forEach((subscription) => {
      try {
        subscription.callback(message);
      } catch (error) {
        this.log("error", "Error in subscription callback", {
          channel: subscription.channel,
          error: error instanceof Error ? error.message : String(error),
        });
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
      this.log("error", "Max reconnection attempts exceeded", {
        attemptsMade: this.reconnectAttempts,
        maxAttempts: this.config.maxReconnectAttempts,
        url: this.currentUrl?.split("?")[0],
      });
      this.isReconnecting = false;
      this.notifyReconnectFailed();
      this.notifyConnectionChange(false);
      return;
    }

    this.reconnectAttempts++;
    this.isReconnecting = true;
    const delay = this.getReconnectDelay();

    this.log("warn", "Scheduling reconnection", {
      attempt: this.reconnectAttempts,
      maxAttempts: this.config.maxReconnectAttempts,
      delayMs: delay,
      url: this.currentUrl?.split("?")[0],
    });

    this.notifyReconnectAttempt();

    this.reconnectTimer = setTimeout(() => {
      this.log("info", "Executing scheduled reconnection", {
        attempt: this.reconnectAttempts,
        maxAttempts: this.config.maxReconnectAttempts,
      });
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

    this.heartbeatStartTime = Date.now();
    this.log("debug", "Heartbeat started", {
      interval_ms: this.config.heartbeatInterval,
    });

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.lastHeartbeatTime = Date.now();
        this.log("debug", "Ping sent", {
          timestamp: new Date().toISOString(),
        });
        this.send({ type: "ping" });
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

    const initialQueueSize = this.messageQueue.length;
    this.log("info", "Processing message queue", {
      queueSize: initialQueueSize,
    });

    let processedCount = 0;
    const startTime = Date.now();

    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        try {
          this.send(message);
          processedCount++;
        } catch (error) {
          this.log("error", "Error processing queued message", {
            messageType: message.type,
            error: error instanceof Error ? error.message : String(error),
          });
          // Если ошибка при отправке, возвращаем сообщение в очередь
          this.messageQueue.unshift(message);
          break;
        }
      }
    }

    const duration = Date.now() - startTime;
    this.log("info", "Message queue processing completed", {
      processed: processedCount,
      remaining: this.messageQueue.length,
      duration_ms: duration,
      avgPerMessage: duration / (processedCount || 1),
    });
  }

  /**
   * Уведомление об изменении состояния соединения
   */
  private notifyConnectionChange(connected: boolean): void {
    this.log("debug", "Connection state changed", {
      connected,
      callbackCount: this.connectionCallbacks.length,
    });

    this.connectionCallbacks.forEach((callback) => {
      try {
        callback(connected);
      } catch (error) {
        this.log("error", "Error in connection change callback", {
          error: error instanceof Error ? error.message : String(error),
        });
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
  const envUrl =
    typeof import.meta !== "undefined" && import.meta.env?.VITE_WEBSOCKET_URL;
  if (envUrl && envUrl !== "undefined") {
    const url = envUrl.replace(/\/$/, "");
    logger.debug(
      "[WebSocket Config] Using base URL from VITE_WEBSOCKET_URL env var:",
      url,
    );
    return url;
  }

  // Priority 2: Auto-detect from current location
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;
    logger.debug(
      "[WebSocket Config] Using auto-detected base URL from window.location:",
      url,
    );
    return url;
  }

  // Fallback 3: SSR or build-time only
  logger.debug("[WebSocket Config] Using fallback base URL (SSR/build-time)");
  return "ws://localhost:8000/ws";
}

// Initialize with a placeholder URL - actual URL will be provided when connecting
const WEBSOCKET_BASE_URL = getWebSocketBaseUrl();

export const websocketService = new WebSocketService({
  url: `${WEBSOCKET_BASE_URL}/chat/general/`, // Default fallback URL
  reconnectInterval: 1000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 100,
});

// Экспортируем типы для использования в других модулях
export type { WebSocketMessage, WebSocketConfig, Subscription, ReconnectInfo };
