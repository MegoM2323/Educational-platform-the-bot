/**
 * Notification WebSocket Service - специализированный сервис для уведомлений
 * Обеспечивает real-time получение уведомлений и обновлений дашборда
 */

import { websocketService, WebSocketMessage, getWebSocketBaseUrl } from './websocketService';
import { tokenStorage } from './tokenStorage';
import { logger } from '../utils/logger';

export interface Notification {
  id: number;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  data?: any;
  created_at: string;
  is_read: boolean;
  action_url?: string;
}

export interface DashboardUpdate {
  type: 'materials' | 'assignments' | 'reports' | 'payments' | 'general';
  data: any;
  timestamp: string;
}

export interface NotificationEventHandlers {
  onNotification?: (notification: Notification) => void;
  onDashboardUpdate?: (update: DashboardUpdate) => void;
  onError?: (error: string) => void;
}

export class NotificationWebSocketService {
  private subscriptions = new Map<string, string>();
  private eventHandlers: NotificationEventHandlers = {};
  private userId: number | null = null;

  constructor() {
    // Подписываемся на системные события WebSocket
    websocketService.onConnectionChange((connected) => {
      if (connected) {
        this.resubscribeAll();
      }
    });
  }

  /**
   * Подключение к уведомлениям пользователя
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
   */
  connectToNotifications(userId: number, handlers: NotificationEventHandlers): void {
    this.userId = userId;
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const channel = `notifications_${userId}`;
    const subscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
      this.handleNotificationMessage(message);
    });

    this.subscriptions.set(channel, subscriptionId);

    if (!websocketService.isConnected()) {
      const baseUrl = getWebSocketBaseUrl();
      const { accessToken } = tokenStorage.getTokens();
      const token = accessToken || localStorage.getItem('auth_token');

      if (!token) {
        logger.error('[NotificationWebSocket] No auth token available for WebSocket connection', { userId });
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError('Authentication token not found. Please log in again.');
        }
        return;
      }

      const fullUrl = `${baseUrl}/notifications/${userId}/?token=${encodeURIComponent(token)}`;

      logger.info('[NotificationWebSocket] Connecting to notifications:', {
        userId,
        hasToken: !!token,
        tokenLength: token.length,
        fullUrl: fullUrl.substring(0, 100) + '...',
        baseUrl: baseUrl,
        tokenStart: token.substring(0, 20) + '...',
      });

      // Log to window for debugging
      if (typeof window !== 'undefined') {
        (window as any).__WS_DEBUG_URL = fullUrl;
        console.log('[DEBUG] WebSocket URL:', fullUrl);
      }

      websocketService.connect(fullUrl);
    }
  }

  /**
   * Подключение к обновлениям дашборда пользователя
   * CRITICAL: Ensures auth token is available before establishing WebSocket connection
   */
  connectToDashboard(userId: number, handlers: NotificationEventHandlers): void {
    this.userId = userId;
    this.eventHandlers = { ...this.eventHandlers, ...handlers };

    const channel = `dashboard_${userId}`;
    const subscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
      this.handleNotificationMessage(message);
    });

    this.subscriptions.set(channel, subscriptionId);

    if (!websocketService.isConnected()) {
      const baseUrl = getWebSocketBaseUrl();
      const { accessToken } = tokenStorage.getTokens();
      const token = accessToken || localStorage.getItem('auth_token');

      if (!token) {
        logger.error('[NotificationWebSocket] No auth token available for dashboard WebSocket connection', { userId });
        if (this.eventHandlers.onError) {
          this.eventHandlers.onError('Authentication token not found. Please log in again.');
        }
        return;
      }

      const fullUrl = `${baseUrl}/notifications/${userId}/?token=${encodeURIComponent(token)}`;

      logger.info('[NotificationWebSocket] Connecting to dashboard updates:', {
        userId,
        hasToken: !!token,
        tokenLength: token.length,
        fullUrl: fullUrl.substring(0, 100) + '...',
        baseUrl: baseUrl,
        tokenStart: token.substring(0, 20) + '...',
      });

      // Log to window for debugging
      if (typeof window !== 'undefined') {
        (window as any).__WS_DEBUG_URL_DASHBOARD = fullUrl;
        console.log('[DEBUG] WebSocket Dashboard URL:', fullUrl);
      }

      websocketService.connect(fullUrl);
    }
  }

  /**
   * Отключение от уведомлений
   */
  disconnectFromNotifications(): void {
    this.subscriptions.forEach((subscriptionId) => {
      websocketService.unsubscribe(subscriptionId);
    });
    this.subscriptions.clear();
    this.userId = null;
  }

  /**
   * Отправка тестового уведомления (для разработки)
   */
  sendTestNotification(type: Notification['type'], title: string, message: string): void {
    if (!this.userId) return;

    const notification: Notification = {
      id: Date.now(),
      type,
      title,
      message,
      created_at: new Date().toISOString(),
      is_read: false
    };

    if (this.eventHandlers.onNotification) {
      this.eventHandlers.onNotification(notification);
    }
  }

  /**
   * Обработка входящих сообщений уведомлений
   */
  private handleNotificationMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'notification':
        if (message.data && this.eventHandlers.onNotification) {
          this.eventHandlers.onNotification(message.data);
        }
        break;
        
      case 'dashboard_update':
        if (message.data && this.eventHandlers.onDashboardUpdate) {
          this.eventHandlers.onDashboardUpdate(message.data);
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
    if (!this.userId) return;

    this.subscriptions.forEach((subscriptionId, channel) => {
      const newSubscriptionId = websocketService.subscribe(channel, (message: WebSocketMessage) => {
        this.handleNotificationMessage(message);
      });
      this.subscriptions.set(channel, newSubscriptionId);
    });
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
   * Получение текущего пользователя
   */
  getCurrentUserId(): number | null {
    return this.userId;
  }
}

// Создаем глобальный экземпляр сервиса уведомлений
export const notificationWebSocketService = new NotificationWebSocketService();

// Экспортируем типы
export type { Notification, DashboardUpdate, NotificationEventHandlers };
