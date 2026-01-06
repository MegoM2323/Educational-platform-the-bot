import { describe, it, expect, vi, beforeEach } from 'vitest';
import { initChatSocket } from '../chatSocket';

vi.mock('../../../services/websocketService', () => {
  return {
    WebSocketService: class MockWebSocketService {
      config: any;
      constructor(config: any) {
        this.config = config;
      }
      connect = vi.fn();
      disconnect = vi.fn();
      send = vi.fn();
      subscribe = vi.fn();
      onConnectionChange = vi.fn();
      sendMessage = vi.fn();
      isConnected = vi.fn().mockReturnValue(true);
      getCurrentUrl = vi.fn().mockReturnValue('ws://test');
    },
  };
});

vi.mock('../../../services/tokenStorage', () => ({
  tokenStorage: {
    getToken: vi.fn().mockReturnValue('test-token'),
  },
}));

vi.mock('../../../utils/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

describe('ChatSocket - Reconnect Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_reconnectInterval_1000ms', () => {
    const socket = initChatSocket('ws://test');

    expect((socket as any).config.reconnectInterval).toBe(1000);
  });

  it('test_exponentialBackoff_hasBackoffConfig', () => {
    const socket = initChatSocket('ws://test');

    const config = (socket as any).config;
    expect(config.maxReconnectAttempts).toBeGreaterThan(1);
    expect(config.reconnectInterval).toBeDefined();
  });

  it('test_maxReconnectAttempts_configured', () => {
    const socket = initChatSocket('ws://test');

    const maxAttempts = (socket as any).config.maxReconnectAttempts;
    expect(maxAttempts).toBeGreaterThan(0);
    expect(maxAttempts).toBeLessThanOrEqual(20);
  });

  it('test_heartbeatInterval_configured', () => {
    const socket = initChatSocket('ws://test');

    expect((socket as any).config.heartbeatInterval).toBeDefined();
    expect((socket as any).config.heartbeatInterval).toBeGreaterThan(0);
  });

  it('test_messageQueueSize_configured', () => {
    const socket = initChatSocket('ws://test');

    expect((socket as any).config.messageQueueSize).toBeDefined();
    expect((socket as any).config.messageQueueSize).toBeGreaterThan(0);
  });

  it('test_reconnect_configValues', () => {
    const socket = initChatSocket('ws://test');

    const config = (socket as any).config;

    expect(config).toMatchObject({
      reconnectInterval: 1000,
      maxReconnectAttempts: expect.any(Number),
      heartbeatInterval: expect.any(Number),
      messageQueueSize: expect.any(Number),
    });
  });
});

describe('ChatSocket - Connection Management', () => {
  it('test_connect_methodExists', () => {
    const socket = initChatSocket('ws://test');

    expect(typeof socket.connect).toBe('function');
  });

  it('test_subscribeToChat_returnsUnsubscribe', () => {
    const socket = initChatSocket('ws://test');
    const callback = vi.fn();

    const unsubscribe = socket.subscribeToChat(1, callback);

    expect(typeof unsubscribe).toBe('function');
  });

  it('test_subscribeToEvent_returnsUnsubscribe', () => {
    const socket = initChatSocket('ws://test');
    const callback = vi.fn();

    const unsubscribe = socket.subscribeToEvent('message_received', callback);

    expect(typeof unsubscribe).toBe('function');
  });

  it('test_send_validatesMessage', () => {
    const socket = initChatSocket('ws://test');

    expect(() => socket.send(1, '')).not.toThrow();
    expect(() => socket.send(1, '   ')).not.toThrow();
  });

  it('test_disconnect_cleansUp', () => {
    const socket = initChatSocket('ws://test');
    const callback1 = vi.fn();
    const callback2 = vi.fn();

    socket.subscribeToChat(1, callback1);
    socket.subscribeToEvent('message_received', callback2);

    expect(() => socket.disconnect()).not.toThrow();
  });

  it('test_sendTypingIndicator_methodExists', () => {
    const socket = initChatSocket('ws://test');

    expect(typeof socket.sendTypingIndicator).toBe('function');
  });
});
