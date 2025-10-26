/**
 * Тесты для WebSocket Service
 */

import { WebSocketService } from '../websocketService';

// Мокаем WebSocket
class MockWebSocket {
  public readyState = WebSocket.CONNECTING;
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    // Симулируем подключение через небольшую задержку
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // Симулируем отправку данных
    console.log('Mock WebSocket send:', data);
  }

  close(code?: number, reason?: string) {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }
}

// Заменяем глобальный WebSocket на мок
(global as any).WebSocket = MockWebSocket;

describe('WebSocketService', () => {
  let service: WebSocketService;
  const mockConfig = {
    url: 'ws://localhost:8000/ws/',
    reconnectInterval: 1000,
    maxReconnectAttempts: 3,
    heartbeatInterval: 5000,
    messageQueueSize: 10
  };

  beforeEach(() => {
    service = new WebSocketService(mockConfig);
  });

  afterEach(() => {
    service.disconnect();
  });

  describe('Connection Management', () => {
    it('should connect to WebSocket server', async () => {
      const connectPromise = service.connect();
      
      // Ждем подключения
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(service.isConnected()).toBe(true);
      await connectPromise;
    });

    it('should disconnect from WebSocket server', () => {
      service.connect();
      service.disconnect();
      
      expect(service.isConnected()).toBe(false);
    });

    it('should notify connection state changes', (done) => {
      let connectionStates: boolean[] = [];
      
      service.onConnectionChange((connected) => {
        connectionStates.push(connected);
        if (connectionStates.length === 2) {
          expect(connectionStates).toEqual([false, true]);
          done();
        }
      });

      service.connect();
    });
  });

  describe('Message Handling', () => {
    it('should send messages when connected', async () => {
      await service.connect();
      
      const sendSpy = jest.spyOn(MockWebSocket.prototype, 'send');
      
      service.send({
        type: 'test',
        data: { message: 'hello' }
      });

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({
        type: 'test',
        data: { message: 'hello' }
      }));
    });

    it('should queue messages when disconnected', () => {
      const sendSpy = jest.spyOn(MockWebSocket.prototype, 'send');
      
      service.send({
        type: 'test',
        data: { message: 'hello' }
      });

      // Сообщение должно быть в очереди, а не отправлено
      expect(sendSpy).not.toHaveBeenCalled();
    });

    it('should process queued messages after connection', async () => {
      const sendSpy = jest.spyOn(MockWebSocket.prototype, 'send');
      
      // Отправляем сообщение до подключения
      service.send({
        type: 'test',
        data: { message: 'queued' }
      });

      // Подключаемся
      await service.connect();
      
      // Сообщение должно быть отправлено
      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({
        type: 'test',
        data: { message: 'queued' }
      }));
    });
  });

  describe('Subscription System', () => {
    it('should subscribe to channels', async () => {
      await service.connect();
      
      const callback = jest.fn();
      const subscriptionId = service.subscribe('test_channel', callback);
      
      expect(subscriptionId).toBeDefined();
      expect(typeof subscriptionId).toBe('string');
    });

    it('should unsubscribe from channels', async () => {
      await service.connect();
      
      const callback = jest.fn();
      const subscriptionId = service.subscribe('test_channel', callback);
      
      service.unsubscribe(subscriptionId);
      
      // Проверяем, что подписка удалена
      expect(() => service.unsubscribe(subscriptionId)).not.toThrow();
    });

    it('should call subscription callbacks on messages', async () => {
      await service.connect();
      
      const callback = jest.fn();
      service.subscribe('test_channel', callback);
      
      // Симулируем получение сообщения
      const mockMessage = {
        type: 'test',
        data: { message: 'hello' }
      };
      
      // Получаем WebSocket instance и вызываем onmessage
      const ws = (service as any).ws;
      if (ws && ws.onmessage) {
        ws.onmessage({
          data: JSON.stringify(mockMessage)
        } as MessageEvent);
      }
      
      expect(callback).toHaveBeenCalledWith(mockMessage);
    });
  });

  describe('Reconnection Logic', () => {
    it('should attempt reconnection on disconnect', (done) => {
      let reconnectAttempts = 0;
      
      // Мокаем connect для подсчета попыток
      const originalConnect = service.connect.bind(service);
      service.connect = jest.fn().mockImplementation(async () => {
        reconnectAttempts++;
        if (reconnectAttempts === 1) {
          // Первое подключение успешно
          await originalConnect();
        } else if (reconnectAttempts === 2) {
          // Вторая попытка - успешно
          await originalConnect();
          expect(reconnectAttempts).toBe(2);
          done();
        }
      });

      service.connect().then(() => {
        // Симулируем отключение
        const ws = (service as any).ws;
        if (ws && ws.onclose) {
          ws.onclose(new CloseEvent('close'));
        }
      });
    });

    it('should stop reconnection after max attempts', (done) => {
      const serviceWithLimitedAttempts = new WebSocketService({
        ...mockConfig,
        maxReconnectAttempts: 2
      });

      let connectCalls = 0;
      serviceWithLimitedAttempts.connect = jest.fn().mockImplementation(async () => {
        connectCalls++;
        if (connectCalls > 2) {
          done(new Error('Too many connection attempts'));
        }
      });

      serviceWithLimitedAttempts.connect().then(() => {
        // Симулируем отключение
        const ws = (serviceWithLimitedAttempts as any).ws;
        if (ws && ws.onclose) {
          ws.onclose(new CloseEvent('close'));
        }
      });

      // Ждем завершения всех попыток переподключения
      setTimeout(() => {
        expect(connectCalls).toBeLessThanOrEqual(2);
        done();
      }, 5000);
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid JSON messages', async () => {
      await service.connect();
      
      const callback = jest.fn();
      service.subscribe('test_channel', callback);
      
      // Симулируем получение невалидного JSON
      const ws = (service as any).ws;
      if (ws && ws.onmessage) {
        ws.onmessage({
          data: 'invalid json'
        } as MessageEvent);
      }
      
      // Callback не должен быть вызван для невалидного JSON
      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle connection errors gracefully', async () => {
      const errorCallback = jest.fn();
      service.onConnectionChange(errorCallback);
      
      // Симулируем ошибку подключения
      const ws = (service as any).ws;
      if (ws && ws.onerror) {
        ws.onerror(new Event('error'));
      }
      
      expect(errorCallback).toHaveBeenCalledWith(false);
    });
  });

  describe('Heartbeat', () => {
    it('should send heartbeat messages', async () => {
      await service.connect();
      
      const sendSpy = jest.spyOn(MockWebSocket.prototype, 'send');
      
      // Ждем отправки heartbeat
      await new Promise(resolve => setTimeout(resolve, 6000));
      
      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }));
    });
  });
});
