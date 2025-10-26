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

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      ...config
    };
  }

  /**
   * Подключение к WebSocket серверу
   */
  async connect(): Promise<void> {
    if (this.isConnecting || this.connectionState === 'connected') {
      return;
    }

    this.isConnecting = true;
    this.connectionState = 'connecting';
    this.notifyConnectionChange(false);

    try {
      this.ws = new WebSocket(this.config.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
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
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.connectionState = 'disconnected';
        this.isConnecting = false;
        this.notifyConnectionChange(false);
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
        this.connectionState = 'disconnected';
        this.notifyConnectionChange(false);
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
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
        console.error('Error sending WebSocket message:', error);
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
      console.error('WebSocket server error:', message.error);
      return;
    }

    // Уведомляем подписчиков
    this.subscriptions.forEach((subscription) => {
      try {
        subscription.callback(message);
      } catch (error) {
        console.error('Error in subscription callback:', error);
      }
    });
  }

  /**
   * Планирование переподключения
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.config.reconnectInterval! * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
    
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
        console.error('Error in connection change callback:', error);
      }
    });
  }
}

// Создаем глобальный экземпляр WebSocket сервиса
const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws/';

export const websocketService = new WebSocketService({
  url: WEBSOCKET_URL,
  reconnectInterval: 5000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 100
});

// Экспортируем типы для использования в других модулях
export type { WebSocketMessage, WebSocketConfig, Subscription };
