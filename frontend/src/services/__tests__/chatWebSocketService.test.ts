/**
 * Тесты для Chat WebSocket Service
 */

import { ChatWebSocketService } from '../chatWebSocketService';

// Мокаем WebSocket service
const mockWebSocketService = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  send: jest.fn(),
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
  isConnected: jest.fn(() => true),
  onConnectionChange: jest.fn()
};

// Мокаем websocketService
jest.mock('../websocketService', () => ({
  websocketService: mockWebSocketService
}));

describe('ChatWebSocketService', () => {
  let service: ChatWebSocketService;

  beforeEach(() => {
    service = new ChatWebSocketService();
    jest.clearAllMocks();
  });

  describe('General Chat Connection', () => {
    it('should connect to general chat', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToGeneralChat(handlers);

      expect(mockWebSocketService.subscribe).toHaveBeenCalledWith(
        'general_chat',
        expect.any(Function)
      );
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle general chat messages', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToGeneralChat(handlers);

      // Получаем callback функцию
      const subscribeCallback = mockWebSocketService.subscribe.mock.calls[0][1];

      // Тестируем обработку сообщения
      subscribeCallback({
        type: 'chat_message',
        message: { id: 1, content: 'Hello' }
      });

      expect(handlers.onMessage).toHaveBeenCalledWith({ id: 1, content: 'Hello' });
    });

    it('should handle typing indicators', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToGeneralChat(handlers);
      const subscribeCallback = mockWebSocketService.subscribe.mock.calls[0][1];

      // Тестируем индикатор печати
      subscribeCallback({
        type: 'typing',
        user: { id: 1, username: 'test', first_name: 'Test', last_name: 'User' }
      });

      expect(handlers.onTyping).toHaveBeenCalledWith({
        id: 1,
        username: 'test',
        first_name: 'Test',
        last_name: 'User'
      });
    });

    it('should handle room history', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToGeneralChat(handlers);
      const subscribeCallback = mockWebSocketService.subscribe.mock.calls[0][1];

      const historyMessages = [
        { id: 1, content: 'Message 1' },
        { id: 2, content: 'Message 2' }
      ];

      subscribeCallback({
        type: 'room_history',
        messages: historyMessages
      });

      expect(handlers.onRoomHistory).toHaveBeenCalledWith(historyMessages);
    });
  });

  describe('Room Chat Connection', () => {
    it('should connect to specific room', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToRoom(123, handlers);

      expect(mockWebSocketService.subscribe).toHaveBeenCalledWith(
        'chat_123',
        expect.any(Function)
      );
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });
  });

  describe('Message Sending', () => {
    it('should send general messages', () => {
      service.sendGeneralMessage('Hello, world!');

      expect(mockWebSocketService.send).toHaveBeenCalledWith({
        type: 'chat_message',
        data: { content: 'Hello, world!' }
      });
    });

    it('should send room messages', () => {
      service.sendRoomMessage(123, 'Hello, room!');

      expect(mockWebSocketService.send).toHaveBeenCalledWith({
        type: 'chat_message',
        data: { content: 'Hello, room!' }
      });
    });

    it('should send typing indicators', () => {
      service.sendTyping();

      expect(mockWebSocketService.send).toHaveBeenCalledWith({
        type: 'typing',
        data: {}
      });
    });

    it('should send typing stop indicators', () => {
      service.sendTypingStop();

      expect(mockWebSocketService.send).toHaveBeenCalledWith({
        type: 'typing_stop',
        data: {}
      });
    });

    it('should mark messages as read', () => {
      service.markMessageAsRead(456);

      expect(mockWebSocketService.send).toHaveBeenCalledWith({
        type: 'mark_read',
        data: { message_id: 456 }
      });
    });
  });

  describe('Disconnection', () => {
    it('should disconnect from chat', () => {
      service.connectToGeneralChat({});
      service.disconnectFromChat();

      expect(mockWebSocketService.unsubscribe).toHaveBeenCalled();
    });
  });

  describe('Connection State', () => {
    it('should check connection state', () => {
      mockWebSocketService.isConnected.mockReturnValue(true);
      expect(service.isConnected()).toBe(true);

      mockWebSocketService.isConnected.mockReturnValue(false);
      expect(service.isConnected()).toBe(false);
    });

    it('should handle connection state changes', () => {
      const callback = jest.fn();
      service.onConnectionChange(callback);

      expect(mockWebSocketService.onConnectionChange).toHaveBeenCalledWith(callback);
    });
  });

  describe('Typing Timer', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should start typing timer', () => {
      const sendTypingStopSpy = jest.spyOn(service, 'sendTypingStop');
      
      service.startTypingTimer(123);
      
      // Быстро перематываем время на 3 секунды
      jest.advanceTimersByTime(3000);
      
      expect(sendTypingStopSpy).toHaveBeenCalledWith(123);
    });

    it('should clear previous typing timer', () => {
      const sendTypingStopSpy = jest.spyOn(service, 'sendTypingStop');
      
      service.startTypingTimer(123);
      service.startTypingTimer(123); // Второй вызов должен очистить первый таймер
      
      jest.advanceTimersByTime(3000);
      
      // sendTypingStop должен быть вызван только один раз
      expect(sendTypingStopSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Handling', () => {
    it('should handle errors gracefully', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToGeneralChat(handlers);
      const subscribeCallback = mockWebSocketService.subscribe.mock.calls[0][1];

      // Тестируем обработку ошибки
      subscribeCallback({
        type: 'error',
        error: 'Connection failed'
      });

      expect(handlers.onError).toHaveBeenCalledWith('Connection failed');
    });
  });

  describe('Reconnection', () => {
    it('should resubscribe on reconnection', () => {
      const handlers = {
        onMessage: jest.fn(),
        onTyping: jest.fn(),
        onTypingStop: jest.fn(),
        onUserJoined: jest.fn(),
        onUserLeft: jest.fn(),
        onRoomHistory: jest.fn(),
        onError: jest.fn()
      };

      service.connectToGeneralChat(handlers);
      
      // Симулируем переподключение
      const connectionCallback = mockWebSocketService.onConnectionChange.mock.calls[0][0];
      connectionCallback(true);

      // Должна быть создана новая подписка
      expect(mockWebSocketService.subscribe).toHaveBeenCalledTimes(2);
    });
  });
});
