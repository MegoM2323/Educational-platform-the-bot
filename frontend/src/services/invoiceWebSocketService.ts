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

  constructor() {
    // Подписываемся на системные события WebSocket
    websocketService.onConnectionChange((connected) => {
      if (connected) {
        this.resubscribeAll();
      } else {
        this.scheduleReconnect();
      }
    });
  }

  /**
   * Подключение к WebSocket для обновлений счетов
   * Автоматически определяет роль пользователя (tutor/parent) на backend
   */
  connect(handlers: InvoiceEventHandlers): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const subscriptionId = websocketService.subscribe('invoices', (message: WebSocketMessage) => {
      this.handleInvoiceMessage(message);
    });

    this.subscriptions.set('invoices', subscriptionId);

    // Подключаемся к WebSocket если еще не подключены
    if (!websocketService.isConnected()) {
      const baseUrl = getWebSocketBaseUrl();
      const { accessToken } = tokenStorage.getTokens();

      // Формируем URL с токеном для аутентификации
      const tokenParam = accessToken ? `?token=${accessToken}` : '';
      const fullUrl = `${baseUrl}/invoices/${tokenParam}`;

      logger.info('[InvoiceWebSocket] Connecting to invoice updates:', {
        hasToken: !!accessToken,
        tokenStart: accessToken ? accessToken.substring(0, 10) : 'no-token',
        fullUrl
      });

      websocketService.connect(fullUrl);
      this.reconnectAttempts = 0;
    }
  }

  /**
   * Отключение от WebSocket счетов
   */
  disconnect(): void {
    const subscriptionId = this.subscriptions.get('invoices');

    if (subscriptionId) {
      websocketService.unsubscribe(subscriptionId);
      this.subscriptions.delete('invoices');
    }

    logger.info('[InvoiceWebSocket] Disconnected from invoice updates');
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

    setTimeout(() => {
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
