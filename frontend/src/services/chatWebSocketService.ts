/**
 * Chat WebSocket Service - специализированный сервис для чата
 * Обеспечивает real-time обмен сообщениями, индикаторы печати, уведомления и graceful degradation
 */

import {
  websocketService,
  WebSocketMessage,
  getWebSocketBaseUrl,
  ReconnectInfo,
} from "./websocketService";
import { tokenStorage } from "./tokenStorage";
import { logger } from "../utils/logger";
import { toast } from "sonner";

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
  message_type: "text" | "image" | "file" | "system";
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
  onMessagePinned?: (data: {
    message_id: number;
    is_pinned: boolean;
    thread_id?: number;
  }) => void;
  onChatLocked?: (data: { chat_id: number; is_active: boolean }) => void;
  onUserMuted?: (data: { user_id: number; is_muted: boolean }) => void;
  onMessageEdited?: (data: {
    message_id: number;
    content: string;
    is_edited: boolean;
    edited_at: string;
  }) => void;
  onMessageDeleted?: (data: { message_id: number }) => void;
}

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "auth_error"
  | "error";

export class ChatWebSocketService {
  private subscriptions = new Map<string, string>();
  private typingTimeouts = new Map<number, NodeJS.Timeout>();
  private eventHandlers: ChatEventHandlers = {};
  private connectionStatus: ConnectionStatus = "disconnected";
  private connectionStatusCallbacks: ((status: ConnectionStatus) => void)[] =
    [];
  private connectionUnsubscribe: (() => void) | null = null;
  private authErrorUnsubscribe: (() => void) | null = null;
  private reconnectAttemptUnsubscribe: (() => void) | null = null;
  private reconnectSuccessUnsubscribe: (() => void) | null = null;
  private reconnectFailedUnsubscribe: (() => void) | null = null;
  private activeSubscriptions = new Map<number, string>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout?: NodeJS.Timeout;
  private lastRoomId?: number;
  private isOfflineMode = false;
  private offlineModeStartTime: number | null = null;
  private lastError: string | null = null;
  private pollingInterval: NodeJS.Timeout | null = null;
  private offlineModeTimeout: NodeJS.Timeout | null = null;
  private pollingMessageIds = new Set<number>();
  private offlineModeThreshold = 10 * 1000; // 10 seconds for testing, normally 5 minutes
  private lastSuccessfulWsConnection = 0;
  private configuredPollingInterval = 3000;
  private pollingAttempts = 0;
  private messagesSyncedCount = 0;

  private chatLogger = {
    debug: (msg: string, data?: any) => {
      logger.debug(`[ChatWebSocket] ${msg}`, data || "");
    },
    info: (msg: string, data?: any) => {
      logger.info(`[ChatWebSocket] ${msg}`, data || "");
    },
    warn: (msg: string, data?: any) => {
      logger.warn(`[ChatWebSocket] ${msg}`, data || "");
    },
    error: (msg: string, error?: any) => {
      logger.error(`[ChatWebSocket] ${msg}`, error || "");
    },
  };

  constructor() {
    // Подписываемся на системные события WebSocket
    this.connectionUnsubscribe = websocketService.onConnectionChange(
      async (connected) => {
        if (connected) {
          this.reconnectAttempts = 0;
          this.setConnectionStatus("connected");
          this.stopOfflineModeTimeoutIfNeeded();
          try {
            await this.recoverFromOfflineMode();
          } catch (error) {
            this.eventHandlers.error(
              "[ChatWebSocket] Failed to recover from offline mode",
              error
            );
          }
          this.resubscribeAll();
          if (this.eventHandlers.onConnect) {
            this.eventHandlers.onConnect();
          }
        } else {
          this.onDisconnect();
        }
      },
    );

    // Подписываемся на ошибки аутентификации
    this.authErrorUnsubscribe = websocketService.onAuthError((code, reason) => {
      logger.error("[ChatWebSocket] Auth error received:", { code, reason });
      this.handleAuthError(code, reason);
    });

    // Подписываемся на события переподключения
    this.reconnectAttemptUnsubscribe = websocketService.onReconnectAttempt(
      (info: ReconnectInfo) => {
        logger.info("[ChatWebSocket] Reconnect attempt:", info);
        this.setConnectionStatus("connecting");
        this.startOfflineModeCountdown();
        toast.loading("Reconnecting...", { id: "ws-reconnect" });
      },
    );

    this.reconnectSuccessUnsubscribe = websocketService.onReconnectSuccess(
      () => {
        logger.info("[ChatWebSocket] Successfully reconnected");
        toast.success("Connected", { id: "ws-reconnect" });
      },
    );

    this.reconnectFailedUnsubscribe = websocketService.onReconnectFailed(() => {
      logger.error("[ChatWebSocket] Failed to reconnect after max attempts");
      toast.error("Connection failed, switching to offline mode", {
        id: "ws-reconnect",
      });
      this.initiateGracefulDegradation();
    });
  }

  /**
   * Обработка ошибок аутентификации
   * Вызывается при получении close codes 4001 (auth error), 4002 (access denied), 4003 (forbidden)
   */
  private handleAuthError(code: number, reason?: string): void {
    const errorCodeMeaning = this.getErrorCodeMeaning(code);

    this.chatLogger.error("[WEBSOCKET: error_handling]", {
      closeCode: code,
      errorCodeMeaning: errorCodeMeaning,
      reason,
      currentStatus: this.connectionStatus,
      handlingAuthError: true,
    });

    this.setConnectionStatus("auth_error");

    let errorMessage = reason || "Authentication error";
    let toastMessage = "";

    switch (code) {
      case 4001:
        errorMessage = "Session expired. Please log in again.";
        toastMessage = "Session expired, redirecting...";
        this.lastError = "Session expired";
        this.chatLogger.warn(
          "Session expired, clearing tokens and redirecting to login",
          {
            code,
          },
        );
        if (typeof window !== "undefined") {
          tokenStorage.clearTokens();
          toast.error(toastMessage, { id: "ws-auth" });
          setTimeout(() => {
            window.location.href = "/login";
          }, 1000);
        }
        break;

      case 4002:
        errorMessage = "You do not have access to this chat.";
        toastMessage = "You don't have access to this chat";
        this.lastError = "Access denied";
        this.chatLogger.warn("Access denied to chat", { code });
        toast.error(toastMessage, { id: "ws-auth" });
        break;

      case 4003:
        errorMessage =
          "Chat access denied. This chat may have been deleted or restricted.";
        toastMessage = "Chat access denied";
        this.lastError = "Forbidden";
        this.chatLogger.warn("Chat forbidden (deleted or restricted)", {
          code,
        });
        toast.error(toastMessage, { id: "ws-auth" });
        break;

      default:
        this.lastError = errorMessage;
        this.chatLogger.error("Unknown auth error code", { code, reason });
        toast.error(errorMessage, { id: "ws-auth" });
    }

    if (this.eventHandlers.onError) {
      this.eventHandlers.onError(errorMessage, code.toString());
    }
  }

  /**
   * Определение значения кода ошибки WebSocket
   */
  private getErrorCodeMeaning(code: number): string {
    switch (code) {
      case 4001:
        return "auth_error (token expired or invalid)";
      case 4002:
        return "access_denied (insufficient permissions)";
      case 4003:
        return "forbidden (resource deleted or restricted)";
      case 4029:
        return "rate_limit (too many requests)";
      default:
        return "unknown";
    }
  }

  /**
   * Запуск обратного отсчета для включения offline mode (5 минут)
   */
  private startOfflineModeCountdown(): void {
    this.stopOfflineModeTimeoutIfNeeded();

    if (this.offlineModeStartTime === null) {
      this.offlineModeStartTime = Date.now();
    }

    this.offlineModeTimeout = setTimeout(() => {
      const elapsed = Date.now() - (this.offlineModeStartTime || 0);
      if (elapsed >= this.offlineModeThreshold && !this.isOfflineMode) {
        logger.warn(
          "[ChatWebSocket] Offline for 5+ minutes, switching to polling mode",
        );
        this.initiateGracefulDegradation();
      }
    }, this.offlineModeThreshold);
  }

  /**
   * Остановка таймера offline mode если нужно
   */
  private stopOfflineModeTimeoutIfNeeded(): void {
    if (this.offlineModeTimeout) {
      clearTimeout(this.offlineModeTimeout);
      this.offlineModeTimeout = null;
    }
    this.offlineModeStartTime = null;
  }

  /**
   * Инициирование graceful degradation - переход на polling mode
   */
  private initiateGracefulDegradation(): void {
    if (this.isOfflineMode) {
      this.chatLogger.debug(
        "Already in offline mode, skipping graceful degradation",
      );
      return;
    }

    const fallbackStartTime = Date.now();
    this.offlineModeStartTime = fallbackStartTime;

    this.chatLogger.warn("[WEBSOCKET: fallback_triggered]", {
      currentStatus: this.connectionStatus,
      lastRoomId: this.lastRoomId,
      pollingInterval: this.configuredPollingInterval,
      reason: "max_reconnect_attempts_or_timeout",
      fallbackMode: "REST_API_polling",
    });

    this.isOfflineMode = true;
    this.notifyOfflineMode(true);
    this.stopPolling();

    this.chatLogger.info("[WEBSOCKET: fallback_triggered]", {
      action: "starting_REST_API_polling",
      roomId: this.lastRoomId,
      pollingIntervalMs: this.configuredPollingInterval,
    });

    this.startPolling();
  }

  /**
   * UI уведомления при переходе в offline mode и обратно
   */
  private notifyOfflineMode(isOffline: boolean): void {
    if (isOffline) {
      this.chatLogger.warn("Entering offline mode, switching to polling", {
        pollingIntervalMs: this.configuredPollingInterval,
        reason: "WebSocket connection lost",
      });
      toast.warning("Connection lost. Switching to offline mode (polling)");
    } else {
      this.chatLogger.info("Exiting offline mode, WebSocket recovered", {
        messagesSyncedDuringOfflineMode: this.messagesSyncedCount,
        offlineDurationMs:
          Date.now() - (this.offlineModeStartTime || Date.now()),
      });
      toast.success("Back online!");
    }
  }

  /**
   * Восстановление из offline mode - переход обратно на WebSocket
   * После успешного reconnect синхронизирует полную историю сообщений
   */
  private async recoverFromOfflineMode(): Promise<void> {
    if (!this.isOfflineMode) {
      return;
    }

    const offlineDuration =
      Date.now() - (this.offlineModeStartTime || Date.now());
    this.chatLogger.info("Recovering from offline mode", {
      offlineDurationMs: offlineDuration,
      offlineDurationMin: Math.round(offlineDuration / 60000),
      lastRoomId: this.lastRoomId,
      messagesSynced: this.messagesSyncedCount,
    });

    this.isOfflineMode = false;
    this.lastSuccessfulWsConnection = Date.now();
    this.messagesSyncedCount = 0;
    this.notifyOfflineMode(false);
    this.stopPolling();

    if (this.lastRoomId !== undefined) {
      try {
        const startTime = Date.now();
        const messages = await this.fetchMessagesViaRest();
        const syncDuration = Date.now() - startTime;

        this.pollingMessageIds.clear();
        messages.forEach((msg) => {
          this.pollingMessageIds.add(msg.id);
        });

        this.chatLogger.info("Message history synced after recovery", {
          messageCount: messages.length,
          syncDurationMs: syncDuration,
          roomId: this.lastRoomId,
        });

        if (this.eventHandlers.onRoomHistory) {
          this.eventHandlers.onRoomHistory(messages);
        }
      } catch (error) {
        this.chatLogger.error("Failed to sync messages during recovery", {
          error: error instanceof Error ? error.message : String(error),
          roomId: this.lastRoomId,
        });
      }
    }

    this.offlineModeStartTime = null;
  }

  /**
   * Запуск polling для получения сообщений через API (fallback режим)
   * Интервал: 3 сек по умолчанию (конфигурируется через configuredPollingInterval)
   */
  private startPolling(): void {
    if (this.pollingInterval) {
      this.chatLogger.debug("Polling already running, skipping start");
      return;
    }

    this.chatLogger.info("[WEBSOCKET: fallback_triggered]", {
      action: "REST_API_polling_started",
      intervalMs: this.configuredPollingInterval,
      roomId: this.lastRoomId,
      offlineMode: this.isOfflineMode,
      timeSinceOfflineStartMs:
        this.offlineModeStartTime !== null
          ? Date.now() - this.offlineModeStartTime
          : "unknown",
    });

    this.pollingAttempts = 0;
    this.pollingInterval = setInterval(() => {
      if (this.lastRoomId !== undefined) {
        this.pollingAttempts++;
        this.syncMessagesFromPolling();
      }
    }, this.configuredPollingInterval);
  }

  /**
   * Остановка polling
   */
  private stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;

      this.chatLogger.info("Polling stopped", {
        totalAttempts: this.pollingAttempts,
        messagesSynced: this.messagesSyncedCount,
        pollingDuration: this.pollingAttempts * this.configuredPollingInterval,
      });
    }
  }

  /**
   * Синхронизация сообщений через polling API (удаляет дубликаты)
   * Получает последние 10 сообщений и проверяет на дубликаты
   */
  private async syncMessagesFromPolling(): Promise<void> {
    if (this.lastRoomId === undefined) {
      return;
    }

    try {
      const startTime = Date.now();
      const messages = await this.fetchMessagesViaRest();
      const syncDuration = Date.now() - startTime;

      this.chatLogger.debug("[WEBSOCKET: fallback_triggered]", {
        action: "REST_API_polling_sync",
        roomId: this.lastRoomId,
        messagesReceived: messages.length,
        syncDurationMs: syncDuration,
        pollingAttempt: this.pollingAttempts,
      });

      this.mergePollMessages(messages);
    } catch (error) {
      if ((error as any)?.status === 401) {
        this.chatLogger.error("[WEBSOCKET: error_handling]", {
          source: "polling_fallback",
          closeCode: 4001,
          errorCodeMeaning: "auth_error (token expired)",
          pollingAttempt: this.pollingAttempts,
          handlingAuthError: true,
        });
        this.handleAuthError(4001, "Token expired during polling");
      } else {
        this.chatLogger.error("[WEBSOCKET: error_handling]", {
          source: "polling_fallback",
          error: error instanceof Error ? error.message : String(error),
          roomId: this.lastRoomId,
          pollingAttempt: this.pollingAttempts,
        });
      }
    }
  }

  /**
   * Получение сообщений через REST API (fallback при offline mode)
   */
  private async fetchMessagesViaRest(): Promise<ChatMessage[]> {
    if (this.lastRoomId === undefined) {
      return [];
    }

    const token = tokenStorage.getTokens().accessToken;
    if (!token) {
      this.chatLogger.error("[WEBSOCKET: fallback_triggered]", {
        action: "REST_API_fetch",
        error: "No authentication token available",
        roomId: this.lastRoomId,
      });
      throw new Error("No authentication token available");
    }

    const tokenPreview = this.getTokenPreview(token);
    this.chatLogger.debug("[WEBSOCKET: fallback_triggered]", {
      action: "REST_API_fetch_attempt",
      roomId: this.lastRoomId,
      tokenPreview: tokenPreview,
      endpoint: `/api/chat/${this.lastRoomId}/messages/?limit=50`,
    });

    const response = await fetch(
      `/api/chat/${this.lastRoomId}/messages/?limit=50`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      },
    );

    if (!response.ok) {
      const error = new Error(`REST API error: ${response.status}`);
      (error as any).status = response.status;

      this.chatLogger.error("[WEBSOCKET: error_handling]", {
        source: "REST_API_fetch",
        httpStatus: response.status,
        roomId: this.lastRoomId,
      });

      throw error;
    }

    const data = await response.json();
    return Array.isArray(data) ? data : data.results || [];
  }

  /**
   * Объединение сообщений из polling с дедупликацией по ID
   * Использует Set для быстрой проверки дубликатов
   */
  private mergePollMessages(newMessages: ChatMessage[]): void {
    let newMessageCount = 0;
    let duplicateCount = 0;

    newMessages.forEach((message: ChatMessage) => {
      if (!this.pollingMessageIds.has(message.id)) {
        this.pollingMessageIds.add(message.id);
        newMessageCount++;
        this.messagesSyncedCount++;

        if (this.eventHandlers.onMessage) {
          this.chatLogger.debug("New message from polling", {
            messageId: message.id,
            senderId: message.sender.id,
            senderName: message.sender.username,
            contentLength: message.content.length,
          });
          this.eventHandlers.onMessage(message);
        }
      } else {
        duplicateCount++;
      }
    });

    if (newMessageCount > 0 || duplicateCount > 0) {
      this.chatLogger.debug("Polling message merge result", {
        newMessages: newMessageCount,
        duplicates: duplicateCount,
        totalInCache: this.pollingMessageIds.size,
      });
    }
  }

  /**
   * Установка статуса подключения и уведомление подписчиков
   */
  private setConnectionStatus(status: ConnectionStatus): void {
    if (this.connectionStatus !== status) {
      this.connectionStatus = status;
      this.connectionStatusCallbacks.forEach((callback) => callback(status));
    }
  }

  /**
   * Подписка на изменения статуса подключения
   */
  onConnectionStatusChange(
    callback: (status: ConnectionStatus) => void,
  ): () => void {
    this.connectionStatusCallbacks.push(callback);
    return () => {
      this.connectionStatusCallbacks = this.connectionStatusCallbacks.filter(
        (cb) => cb !== callback,
      );
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
      const tokenFormat = this.detectTokenFormat(accessToken);
      const tokenPreview = this.getTokenPreview(accessToken);
      logger.debug("[WEBSOCKET: token_retrieval]", {
        source: "tokenStorage",
        format: tokenFormat,
        length: accessToken.length,
        preview: tokenPreview,
        found: true,
      });
      return accessToken;
    }

    // Fallback: прямой доступ к localStorage
    const localStorageToken = localStorage.getItem("auth_token");
    if (localStorageToken) {
      const tokenFormat = this.detectTokenFormat(localStorageToken);
      const tokenPreview = this.getTokenPreview(localStorageToken);
      logger.debug("[WEBSOCKET: token_retrieval]", {
        source: "localStorage",
        format: tokenFormat,
        length: localStorageToken.length,
        preview: tokenPreview,
        found: true,
      });
      return localStorageToken;
    }

    logger.error("[WEBSOCKET: token_retrieval]", {
      source: "none",
      format: "unknown",
      length: 0,
      found: false,
      message: "No authentication token found in any storage",
    });
    return null;
  }

  /**
   * Определение формата токена (JWT vs DRF Token)
   */
  private detectTokenFormat(token: string): string {
    if (!token) return "invalid";
    if (token.startsWith("eyJ")) return "JWT";
    if (/^[a-f0-9]{40}$/.test(token)) return "DRF_Token";
    return "unknown";
  }

  /**
   * Получение предпросмотра токена без раскрытия полного значения
   */
  private getTokenPreview(token: string | null): string {
    if (!token) return "null";
    if (token.length <= 10) return token;
    return `${token.substring(0, 10)}...`;
  }

  /**
   * Подключение к общему чату
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
   */
  connectToGeneralChat(handlers: ChatEventHandlers): void {
    this.chatLogger.info("Connecting to general chat", {
      handlersProvided: !!handlers,
      alreadyConnected: websocketService.isConnected(),
    });

    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const subscriptionId = websocketService.subscribe(
      "general_chat",
      (message: WebSocketMessage) => {
        this.handleChatMessage(message);
      },
    );

    this.subscriptions.set("general_chat", subscriptionId);

    if (!websocketService.isConnected()) {
      const baseUrl = getWebSocketBaseUrl();
      const token = this.getAuthToken();

      if (!token) {
        const errorMsg = "Authentication token not found. Please log in again.";
        this.chatLogger.error("[WEBSOCKET: connect_attempt]", {
          room: "general",
          tokenFound: false,
          error: errorMsg,
        });
        this.setConnectionStatus("auth_error");
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError(errorMsg);
        }
        return;
      }

      this.setConnectionStatus("connecting");
      const fullUrl = `${baseUrl}/chat/general/`;
      const tokenPreview = this.getTokenPreview(token);
      const hasTokenParam = fullUrl.includes("?token=");

      this.chatLogger.info("[WEBSOCKET: connect_attempt]", {
        room: "general",
        url: fullUrl,
        tokenFound: true,
        tokenPreview: tokenPreview,
        hasTokenParam: hasTokenParam,
      });

      logger.debug("[WEBSOCKET: websocket_service_call]", {
        method: "websocketService.connect",
        room: "general",
        tokenPreview: tokenPreview,
      });

      websocketService.connect(fullUrl, token);
    } else {
      this.chatLogger.info(
        "WebSocket already connected, skipping reconnection",
        {
          currentUrl: websocketService.isConnected()
            ? "connected"
            : "disconnected",
        },
      );
    }
  }

  /**
   * Подключение к конкретной чат-комнате
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
   * @returns Promise<boolean> - true если подключение установлено, false при ошибке
   */
  async connectToRoom(
    roomId: number,
    handlers: ChatEventHandlers,
  ): Promise<boolean> {
    const connectStartTime = Date.now();

    this.chatLogger.info("Connecting to chat room", {
      roomId,
      handlersProvided: !!handlers,
      alreadyConnected: websocketService.isConnected(),
    });

    this.eventHandlers = { ...this.eventHandlers, ...handlers };
    this.lastRoomId = roomId;

    const channel = `chat_${roomId}`;
    const token = this.getAuthToken();

    if (!token) {
      const errorMsg = "Authentication token not found. Please log in again.";
      this.chatLogger.error("[WEBSOCKET: connect_attempt]", {
        roomId,
        tokenFound: false,
        error: errorMsg,
      });
      this.setConnectionStatus("auth_error");
      if (handlers.onError) {
        handlers.onError(errorMsg);
      }
      return Promise.reject(new Error(errorMsg));
    }

    this.setConnectionStatus("connecting");

    const subscriptionId = websocketService.subscribe(
      channel,
      (message: WebSocketMessage) => {
        this.handleChatMessage(message);
      },
    );

    this.subscriptions.set(channel, subscriptionId);
    this.activeSubscriptions.set(roomId, subscriptionId);

    const baseUrl = getWebSocketBaseUrl();
    const fullUrl = `${baseUrl}/chat/${roomId}/`;
    const tokenPreview = this.getTokenPreview(token);
    const hasTokenParam = fullUrl.includes("?token=");

    this.chatLogger.info("[WEBSOCKET: connect_attempt]", {
      roomId,
      url: fullUrl,
      tokenFound: true,
      tokenPreview: tokenPreview,
      hasTokenParam: hasTokenParam,
    });

    return new Promise((resolve, reject) => {
      let unsubscribe: (() => void) | null = null;
      const connectionTimeoutMs = 5000;

      const timeout = setTimeout(() => {
        if (unsubscribe) unsubscribe();
        this.chatLogger.warn("[WEBSOCKET: fallback_triggered]", {
          roomId,
          reason: "connection_timeout",
          timeoutMs: connectionTimeoutMs,
          elapsedMs: Date.now() - connectStartTime,
          fallbackMode: "REST_API_polling",
        });
        this.setConnectionStatus("error");
        reject(new Error("Connection timeout"));
      }, connectionTimeoutMs);

      const checkConnection = () => {
        const status = this.getConnectionStatus();
        if (status === "connected") {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();

          const duration = Date.now() - connectStartTime;
          this.chatLogger.info("Room connection established", {
            roomId,
            durationMs: duration,
          });

          resolve(true);
        } else if (status === "error" || status === "auth_error") {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          reject(new Error(`Connection failed with status: ${status}`));
        }
      };

      unsubscribe = this.onConnectionStatusChange((status) => {
        if (status === "connected") {
          const duration = Date.now() - connectStartTime;
          this.chatLogger.info("Room connection ready (status changed)", {
            roomId,
            durationMs: duration,
          });

          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          resolve(true);
        } else if (status === "error" || status === "auth_error") {
          clearTimeout(timeout);
          if (unsubscribe) unsubscribe();
          reject(new Error(`Connection failed with status: ${status}`));
        }
      });

      try {
        logger.debug("[WEBSOCKET: websocket_service_call]", {
          method: "websocketService.connect",
          roomId,
          tokenPreview: tokenPreview,
        });

        websocketService.connect(fullUrl, token);
        checkConnection();
      } catch (error) {
        clearTimeout(timeout);
        if (unsubscribe) unsubscribe();

        this.chatLogger.error("Failed to initiate room connection", {
          roomId,
          error: error instanceof Error ? error.message : String(error),
          elapsedMs: Date.now() - connectStartTime,
        });

        this.setConnectionStatus("error");
        const errorMsg =
          error instanceof Error ? error.message : "Unknown error";
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
      logger.warn("[ChatWebSocket] Already disconnected from room", roomId);
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
    // Очищаем reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = undefined;
    }

    // Очищаем offline mode timeout
    this.stopOfflineModeTimeoutIfNeeded();

    // Остаиавливаем polling
    this.stopPolling();
    this.pollingMessageIds.clear();

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

    if (this.reconnectAttemptUnsubscribe) {
      this.reconnectAttemptUnsubscribe();
      this.reconnectAttemptUnsubscribe = null;
    }

    if (this.reconnectSuccessUnsubscribe) {
      this.reconnectSuccessUnsubscribe();
      this.reconnectSuccessUnsubscribe = null;
    }

    if (this.reconnectFailedUnsubscribe) {
      this.reconnectFailedUnsubscribe();
      this.reconnectFailedUnsubscribe = null;
    }

    // Очищаем обработчики событий
    this.eventHandlers = {};

    // Отключаемся от WebSocket
    websocketService.disconnect();

    // Сбрасываем статусы
    this.setConnectionStatus("disconnected");
    this.isOfflineMode = false;
    this.lastError = null;
  }

  /**
   * Обработка разрыва соединения
   */
  private onDisconnect(): void {
    this.setConnectionStatus("disconnected");
    this.scheduleReconnect();
  }

  /**
   * Планирование переподключения с exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error("[ChatWebSocket] Max reconnect attempts reached");
      this.setConnectionStatus("error");
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;

    logger.info(
      `[ChatWebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`,
    );

    this.reconnectTimeout = setTimeout(() => {
      if (this.lastRoomId !== undefined) {
        this.connectToRoom(this.lastRoomId, this.eventHandlers);
      }
    }, delay);
  }

  /**
   * Отправка сообщения в общий чат
   */
  sendGeneralMessage(content: string): void {
    if (!content || content.trim().length === 0) {
      this.chatLogger.warn("Attempt to send empty message to general chat");
      return;
    }

    this.chatLogger.debug("Sending message to general chat", {
      contentLength: content.length,
      contentPreview: content.substring(0, 50),
    });

    websocketService.send({
      type: "chat_message",
      data: { content },
    });
  }

  /**
   * Отправка сообщения в комнату
   */
  sendRoomMessage(roomId: number, content: string): void {
    if (!content || content.trim().length === 0) {
      this.chatLogger.warn("Attempt to send empty message to room", {
        roomId,
      });
      return;
    }

    this.chatLogger.debug("Sending message to room", {
      roomId,
      contentLength: content.length,
      contentPreview: content.substring(0, 50),
    });

    websocketService.send({
      type: "chat_message",
      data: { content },
    });
  }

  /**
   * Отправка индикатора печати
   */
  sendTyping(roomId?: number): void {
    this.chatLogger.debug("Sending typing indicator", {
      roomId: roomId || "general",
    });

    websocketService.send({
      type: "typing",
      data: roomId ? { room_id: roomId } : undefined,
    });
  }

  /**
   * Отправка остановки печати
   */
  sendTypingStop(roomId?: number): void {
    this.chatLogger.debug("Sending typing stop", {
      roomId: roomId || "general",
    });

    websocketService.send({
      type: "typing_stop",
      data: roomId ? { room_id: roomId } : undefined,
    });
  }

  /**
   * Отметка сообщения как прочитанного
   */
  markMessageAsRead(messageId: number): void {
    websocketService.send({
      type: "mark_read",
      data: { message_id: messageId },
    });
  }

  /**
   * Закрепить/открепить сообщение
   */
  sendPinMessage(roomId: number, messageId: number): void {
    websocketService.send({
      type: "pin_message",
      data: {
        room_id: roomId,
        message_id: messageId,
      },
    });
  }

  /**
   * Заблокировать/разблокировать чат
   */
  sendLockChat(roomId: number): void {
    websocketService.send({
      type: "lock_chat",
      data: {
        room_id: roomId,
      },
    });
  }

  /**
   * Замутить/размутить пользователя
   */
  sendMuteUser(roomId: number, userId: number): void {
    websocketService.send({
      type: "mute_user",
      data: {
        room_id: roomId,
        user_id: userId,
      },
    });
  }

  /**
   * Валидация структуры входящего сообщения
   */
  private validateMessage(message: WebSocketMessage): {
    valid: boolean;
    error?: string;
  } {
    if (!message || typeof message !== "object") {
      return { valid: false, error: "Message is not an object" };
    }

    if (!message.type || typeof message.type !== "string") {
      return { valid: false, error: "Message type is missing or invalid" };
    }

    // Валидация специфичных типов сообщений
    switch (message.type) {
      case "chat_message":
        if (!message.message || typeof message.message !== "object") {
          return {
            valid: false,
            error: "chat_message must contain message object",
          };
        }
        if (!message.message.id) {
          return { valid: false, error: "chat_message.message must have id" };
        }
        // Allow empty content for file/image messages
        if (
          !message.message.content &&
          !message.message.file &&
          !message.message.image
        ) {
          return {
            valid: false,
            error: "chat_message.message must have content, file, or image",
          };
        }
        break;

      case "typing":
      case "typing_stop":
      case "user_joined":
      case "user_left":
        if (!message.user || typeof message.user !== "object") {
          return {
            valid: false,
            error: `${message.type} must contain user object`,
          };
        }
        break;

      case "room_history":
        if (!Array.isArray(message.messages)) {
          return {
            valid: false,
            error: "room_history must contain messages array",
          };
        }
        break;

      case "error":
        if (!message.error || typeof message.error !== "string") {
          return {
            valid: false,
            error: "error message must contain error string",
          };
        }
        break;

      case "message_sent":
        if (typeof message.message_id !== "number") {
          return {
            valid: false,
            error: "message_sent must contain numeric message_id",
          };
        }
        if (message.status !== "delivered") {
          return {
            valid: false,
            error: 'message_sent must have status "delivered"',
          };
        }
        break;
    }

    return { valid: true };
  }

  /**
   * Обработка входящих сообщений чата
   */
  private handleChatMessage(message: WebSocketMessage): void {
    this.chatLogger.debug("Processing received chat message", {
      type: message.type,
      messageId: message.message?.id,
      hasHandler:
        !!this.eventHandlers[
          `on${message.type.charAt(0).toUpperCase()}${message.type.slice(1)}`
        ],
    });

    // Валидация структуры сообщения
    const validation = this.validateMessage(message);
    if (!validation.valid) {
      this.chatLogger.error("Invalid message structure received", {
        error: validation.error,
        messageType: message.type,
      });
      if (this.eventHandlers.onError) {
        this.eventHandlers.onError(
          `Invalid message: ${validation.error}`,
          "validation_error",
        );
      }
      return;
    }

    switch (message.type) {
      case "chat_message":
        if (message.message && this.eventHandlers.onMessage) {
          this.chatLogger.info(
            "Chat message received and delivered to handler",
            {
              messageId: message.message.id,
              senderId: message.message.sender.id,
              senderName: message.message.sender.username,
              contentLength: message.message.content.length,
              isEdited: message.message.is_edited,
            },
          );
          this.eventHandlers.onMessage(message.message);
        } else {
          this.chatLogger.warn("Chat message received but cannot process", {
            hasMessage: !!message.message,
            hasHandler: !!this.eventHandlers.onMessage,
          });
        }
        break;

      case "typing":
        if (message.user && this.eventHandlers.onTyping) {
          this.chatLogger.debug("User typing indicator", {
            userId: message.user.id,
            username: message.user.username,
          });
          this.eventHandlers.onTyping(message.user);
        }
        break;

      case "typing_stop":
        if (message.user && this.eventHandlers.onTypingStop) {
          this.chatLogger.debug("User typing stop", {
            userId: message.user.id,
            username: message.user.username,
          });
          this.eventHandlers.onTypingStop(message.user);
        }
        break;

      case "user_joined":
        if (message.user && this.eventHandlers.onUserJoined) {
          this.chatLogger.info("User joined chat", {
            userId: message.user.id,
            username: message.user.username,
          });
          this.eventHandlers.onUserJoined(message.user);
        }
        break;

      case "user_left":
        if (message.user && this.eventHandlers.onUserLeft) {
          this.chatLogger.info("User left chat", {
            userId: message.user.id,
            username: message.user.username,
          });
          this.eventHandlers.onUserLeft(message.user);
        }
        break;

      case "room_history":
        if (message.messages && this.eventHandlers.onRoomHistory) {
          this.chatLogger.info("Room history received", {
            messagesCount: message.messages.length,
          });
          this.eventHandlers.onRoomHistory(message.messages);
        }
        break;

      case "error":
        this.chatLogger.error("Server error message received", {
          error: message.error,
          code: message.code,
        });
        if (message.error && this.eventHandlers.onError) {
          this.eventHandlers.onError(message.error, message.code);
        }

        // Специальная обработка ошибок авторизации
        if (message.code === "auth_error" || message.code === "access_denied") {
          this.setConnectionStatus("auth_error");
        }
        break;

      case "message_sent":
        this.chatLogger.debug("Message delivery confirmation received", {
          messageId: message.message_id,
          status: message.status,
        });
        if (message.message_id && this.eventHandlers.onMessageDelivered) {
          this.eventHandlers.onMessageDelivered(message.message_id);
        }
        break;

      case "message_pinned":
        this.chatLogger.info("Message pinned event", {
          messageId: message.data?.message_id,
          isPinned: message.data?.is_pinned,
          threadId: message.data?.thread_id,
        });
        if (message.data && this.eventHandlers.onMessagePinned) {
          this.eventHandlers.onMessagePinned(message.data);
        }
        break;

      case "chat_locked":
        this.chatLogger.info("Chat locked event", {
          chatId: message.data?.chat_id,
          isActive: message.data?.is_active,
        });
        if (message.data && this.eventHandlers.onChatLocked) {
          this.eventHandlers.onChatLocked(message.data);
        }
        break;

      case "user_muted":
        this.chatLogger.info("User muted event", {
          userId: message.data?.user_id,
          isMuted: message.data?.is_muted,
        });
        if (message.data && this.eventHandlers.onUserMuted) {
          this.eventHandlers.onUserMuted(message.data);
        }
        break;

      case "message_edited":
        this.chatLogger.info("Message edited event", {
          messageId: message.message_id || message.data?.message_id,
          contentLength: message.data?.content?.length,
        });
        if (this.eventHandlers.onMessageEdited && message.data) {
          this.eventHandlers.onMessageEdited(message.data);
        }
        break;

      case "message_deleted":
        this.chatLogger.info("Message deleted event", {
          messageId: message.message_id || message.data?.message_id,
        });
        if (this.eventHandlers.onMessageDeleted) {
          const deleteData = message.data || { message_id: message.message_id };
          this.eventHandlers.onMessageDeleted(deleteData);
        }
        break;

      default:
        this.chatLogger.warn("Unknown message type received", {
          messageType: message.type,
        });
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError(
            `Unknown message type: ${message.type}`,
            "unknown_type",
          );
        }
    }
  }

  /**
   * Переподписка на все каналы после переподключения
   */
  private resubscribeAll(): void {
    this.subscriptions.forEach((subscriptionId, channel) => {
      const newSubscriptionId = websocketService.subscribe(
        channel,
        (message: WebSocketMessage) => {
          this.handleChatMessage(message);
        },
      );
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
    logger.info("[ChatWebSocket] Manual retry connection requested");
    websocketService.retryConnection();
  }

  /**
   * Конфигурирование интервала polling (в миллисекундах)
   * По умолчанию: 3000ms
   */
  setPollingInterval(intervalMs: number): void {
    if (intervalMs < 1000) {
      logger.warn(
        "[ChatWebSocket] Polling interval too low, setting to 1000ms minimum",
      );
      this.configuredPollingInterval = 1000;
    } else if (intervalMs > 60000) {
      logger.warn(
        "[ChatWebSocket] Polling interval too high, setting to 60000ms maximum",
      );
      this.configuredPollingInterval = 60000;
    } else {
      this.configuredPollingInterval = intervalMs;
      logger.info("[ChatWebSocket] Polling interval set to", { intervalMs });
    }

    if (this.pollingInterval) {
      this.stopPolling();
      this.startPolling();
    }
  }

  /**
   * Получение текущего интервала polling
   */
  getPollingInterval(): number {
    return this.configuredPollingInterval;
  }

  /**
   * Проверка статуса offline mode
   */
  isInOfflineMode(): boolean {
    return this.isOfflineMode;
  }
}

// Создаем глобальный экземпляр сервиса чата
export const chatWebSocketService = new ChatWebSocketService();

// Экспортируем типы
export type { ChatMessage, TypingUser, ChatEventHandlers };
