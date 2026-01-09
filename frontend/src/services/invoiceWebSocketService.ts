/**
 * Invoice WebSocket Service - специализированный сервис для счетов
 * Обеспечивает real-time обновления статусов счетов для тьюторов и родителей
 */

import { websocketService, WebSocketMessage, getWebSocketBaseUrl } from './websocketService';
import { tokenStorage } from './tokenStorage';
import { logger } from '../utils/logger';

export interface InvoiceWebSocketData {
  invoice_id: number;
  old_status?: string;
  new_status?: string;
  data?: any;
  timestamp?: string;
}

export interface InvoiceEventHandlers {
  onInvoiceCreated?: (data: InvoiceWebSocketData) => void;
  onStatusUpdate?: (data: InvoiceWebSocketData) => void;
  onInvoicePaid?: (data: InvoiceWebSocketData) => void;
  onError?: (error: string) => void;
}

export class InvoiceWebSocketService {
  private subscriptions = new Map<string, string>();
  private eventHandlers: InvoiceEventHandlers = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private reconnectTimeoutId: NodeJS.Timeout | null = null;
  private connectionChangeUnsubscribe: (() => void) | null = null;

  constructor() {
    // Подписываемся на системные события WebSocket с управлением памятью
    this.connectionChangeUnsubscribe = websocketService.onConnectionChange((connected) => {
      if (connected) {
        this.clearReconnectTimeout();
        this.resubscribeAll();
      } else {
        this.scheduleReconnect();
      }
    });
  }

  /**
   * Подключение к WebSocket для обновлений счетов
   * Автоматически определяет роль пользователя (tutor/parent) на backend
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
   */
  connect(handlers: InvoiceEventHandlers): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const subscriptionId = websocketService.subscribe('invoices', (message: WebSocketMessage) => {
      this.handleInvoiceMessage(message);
    });

    this.subscriptions.set('invoices', subscriptionId);

    if (!websocketService.isConnected()) {
      const baseUrl = getWebSocketBaseUrl();
      const { accessToken } = tokenStorage.getTokens();
      const token = accessToken || localStorage.getItem('auth_token');

      if (!token) {
        logger.error('[InvoiceWebSocket] No auth token available for WebSocket connection');
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError('Authentication token not found. Please log in again.');
        }
        return;
      }

      const fullUrl = `${baseUrl}/invoices/`;

      logger.info('[InvoiceWebSocket] Connecting to invoice updates:', {
        hasToken: !!token,
        tokenLength: token.length
      });

      websocketService.connect(fullUrl, token);
      this.reconnectAttempts = 0;
    }
  }

  /**
   * Отключение от WebSocket счетов с полной очисткой памяти
   */
  disconnect(): void {
    // Очищаем все подписки
    this.subscriptions.forEach((subscriptionId) => {
      websocketService.unsubscribe(subscriptionId);
    });
    this.subscriptions.clear();

    // Очищаем таймут переподключения
    this.clearReconnectTimeout();

    // Очищаем обработчики событий
    this.eventHandlers = {};

    // Отписываемся от изменений соединения
    if (this.connectionChangeUnsubscribe) {
      this.connectionChangeUnsubscribe();
      this.connectionChangeUnsubscribe = null;
    }

    logger.info('[InvoiceWebSocket] Disconnected from invoice updates and cleaned up all resources');
  }

  /**
   * Очистка таймаута переподключения
   */
  private clearReconnectTimeout(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
  }

  /**
   * Обработка входящих сообщений о счетах
   */
  private handleInvoiceMessage(message: WebSocketMessage): void {
    logger.debug('[InvoiceWebSocketService] Received message:', {
      type: message.type,
      data: message.data
    });

    switch (message.type) {
      case 'connection.established':
        logger.info('[InvoiceWebSocket] Connection established:', message.data);
        this.reconnectAttempts = 0;
        break;

      case 'invoice.created':
        if (message.data && this.eventHandlers.onInvoiceCreated) {
          logger.debug('[InvoiceWebSocket] Invoice created event:', message.data);
          this.eventHandlers.onInvoiceCreated({
            invoice_id: message.invoice_id || message.data.invoice_id,
            data: message.data,
            timestamp: message.timestamp
          });
        }
        break;

      case 'invoice.status_update':
        if (message.data && this.eventHandlers.onStatusUpdate) {
          logger.debug('[InvoiceWebSocket] Status update event:', message.data);
          this.eventHandlers.onStatusUpdate({
            invoice_id: message.invoice_id || message.data.invoice_id,
            old_status: message.old_status || message.data.old_status,
            new_status: message.new_status || message.data.new_status,
            data: message.data,
            timestamp: message.timestamp
          });
        }
        break;

      case 'invoice.paid':
        if (message.data && this.eventHandlers.onInvoicePaid) {
          logger.debug('[InvoiceWebSocket] Invoice paid event:', message.data);
          this.eventHandlers.onInvoicePaid({
            invoice_id: message.invoice_id || message.data.invoice_id,
            data: message.data,
            timestamp: message.timestamp
          });
        }
        break;

      case 'error':
        if (message.error && this.eventHandlers.onError) {
          logger.error('[InvoiceWebSocket] Server error:', message.error);
          this.eventHandlers.onError(message.error);
        }
        break;

      case 'pong':
        // Heartbeat response - не требует обработки
        break;

      default:
        logger.warn('[InvoiceWebSocket] Unknown message type:', message.type);
    }
  }

  /**
   * Переподписка на все каналы после переподключения
   */
  private resubscribeAll(): void {
    logger.debug('[InvoiceWebSocket] Resubscribing to invoice updates');

    this.subscriptions.forEach((subscriptionId, channel) => {
      const newSubscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
        this.handleInvoiceMessage(message);
      });
      this.subscriptions.set(channel, newSubscriptionId);
    });

    this.reconnectAttempts = 0;
  }

  /**
   * Планирование переподключения с экспоненциальной задержкой
   */
  private scheduleReconnect(): void {
    // Очищаем старый таймаут перед созданием нового (FIX 5: утечка памяти при reconnect)
    this.clearReconnectTimeout();

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('[InvoiceWebSocket] Max reconnection attempts reached');
      if (this.eventHandlers.onError) {
        this.eventHandlers.onError('Failed to reconnect after multiple attempts');
      }
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    logger.debug(
      `[InvoiceWebSocket] Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`
    );

    // Используем управляемый таймаут для контроля памяти (FIX 4 & 5)
    this.reconnectTimeoutId = setTimeout(() => {
      if (this.subscriptions.size > 0) {
        // Повторное подключение если есть активные подписки
        this.connect(this.eventHandlers);
      }
    }, delay);
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

// Создаем глобальный экземпляр сервиса счетов
export const invoiceWebSocketService = new InvoiceWebSocketService();

// Экспортируем типы
export type { InvoiceWebSocketData, InvoiceEventHandlers };
