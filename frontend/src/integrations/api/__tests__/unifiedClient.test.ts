// Unit tests for Unified API Client
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UnifiedAPIClient } from '../unifiedClient';

// Mock fetch globally
global.fetch = vi.fn();
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

// Mock environment variables
vi.mock('import.meta', () => ({
  env: {
    VITE_DJANGO_API_URL: 'http://localhost:8000/api',
    VITE_WS_URL: 'ws://localhost:8000/ws',
  },
}));

describe('UnifiedAPIClient', () => {
  let client: UnifiedAPIClient;
  const mockFetch = vi.mocked(fetch);

  beforeEach(() => {
    client = new UnifiedAPIClient();
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Constructor and Configuration', () => {
    it('should initialize with default configuration', () => {
      expect(client).toBeDefined();
      expect(client.isAuthenticated()).toBe(false);
    });

    it('should load tokens from localStorage on initialization', () => {
      const mockToken = 'test-token';
      const mockRefreshToken = 'test-refresh-token';
      
      vi.mocked(localStorage.getItem)
        .mockReturnValueOnce(mockToken)
        .mockReturnValueOnce(mockRefreshToken);

      const newClient = new UnifiedAPIClient();
      expect(newClient.getToken()).toBe(mockToken);
    });
  });

  describe('Token Management', () => {
    it('should set and get token correctly', () => {
      const testToken = 'test-token-123';
      client.setToken(testToken);
      expect(client.getToken()).toBe(testToken);
      expect(client.isAuthenticated()).toBe(true);
    });

    it('should clear tokens on logout', async () => {
      client.setToken('test-token');
      expect(client.isAuthenticated()).toBe(true);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: {} }),
      } as Response);

      await client.logout();
      expect(client.isAuthenticated()).toBe(false);
      expect(localStorage.removeItem).toHaveBeenCalledWith('authToken');
    });
  });

  describe('Authentication Methods', () => {
    it('should handle successful login', async () => {
      const mockLoginResponse = {
        success: true,
        data: {
          token: 'new-token',
          user: {
            id: 1,
            email: 'test@example.com',
            first_name: 'Test',
            last_name: 'User',
            role: 'student',
            role_display: 'Student',
            phone: '1234567890',
            is_verified: true,
            date_joined: '2024-01-01T00:00:00Z',
            full_name: 'Test User',
          },
          message: 'Login successful',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLoginResponse),
      } as Response);

      const result = await client.login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result.success).toBe(true);
      expect(result.data?.token).toBe('new-token');
      expect(client.isAuthenticated()).toBe(true);
      expect(localStorage.setItem).toHaveBeenCalledWith('authToken', 'new-token');
    });

    it('should handle login failure', async () => {
      const mockErrorResponse = {
        success: false,
        error: 'Invalid credentials',
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve(mockErrorResponse),
      } as Response);

      const result = await client.login({
        email: 'test@example.com',
        password: 'wrong-password',
      });

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid credentials');
      expect(client.isAuthenticated()).toBe(false);
    });

    it('should handle network errors during login', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await client.login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error: Unable to connect to server');
    });
  });

  describe('Dashboard Methods', () => {
    beforeEach(() => {
      client.setToken('test-token');
    });

    it('should get student dashboard data', async () => {
      const mockDashboardData = {
        materials_count: 10,
        completed_materials: 5,
        progress_percentage: 50,
        recent_materials: [],
        upcoming_deadlines: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockDashboardData,
        }),
      } as Response);

      const result = await client.getStudentDashboard();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockDashboardData);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/materials/dashboard/student/',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Token test-token',
          }),
        })
      );
    });

    it('should get teacher dashboard data', async () => {
      const mockDashboardData = {
        total_students: 25,
        total_materials: 15,
        pending_reports: 3,
        recent_activity: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockDashboardData,
        }),
      } as Response);

      const result = await client.getTeacherDashboard();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockDashboardData);
    });

    it('should get parent dashboard data', async () => {
      const mockDashboardData = {
        total_children: 2,
        total_subjects: 5,
        pending_payments: 1,
        recent_reports: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockDashboardData,
        }),
      } as Response);

      const result = await client.getParentDashboard();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockDashboardData);
    });
  });

  describe('Chat Methods', () => {
    beforeEach(() => {
      client.setToken('test-token');
    });

    it('should get general chat room', async () => {
      const mockChatRoom = {
        id: 1,
        name: 'General Chat',
        description: 'General discussion room',
        room_type: 'general',
        participant_count: 10,
        created_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockChatRoom,
        }),
      } as Response);

      const result = await client.getGeneralChat();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockChatRoom);
    });

    it('should get general messages with pagination', async () => {
      const mockMessages = {
        results: [
          {
            id: 1,
            sender_id: 1,
            sender_name: 'Test User',
            sender_role: 'student',
            content: 'Hello world',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        count: 1,
        next: null,
        previous: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockMessages,
        }),
      } as Response);

      const result = await client.getGeneralMessages(1, 50);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockMessages);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/general/messages/?page=1&page_size=50',
        expect.any(Object)
      );
    });

    it('should send message to general chat', async () => {
      const mockMessage = {
        id: 1,
        sender_id: 1,
        sender_name: 'Test User',
        sender_role: 'student',
        content: 'Test message',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockMessage,
        }),
      } as Response);

      const result = await client.sendMessage({
        content: 'Test message',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockMessage);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/general/messages/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ content: 'Test message' }),
        })
      );
    });
  });

  describe('Payment Methods', () => {
    beforeEach(() => {
      client.setToken('test-token');
    });

    it('should create payment', async () => {
      const mockPayment = {
        id: 'payment-123',
        amount: '100.00',
        status: 'pending',
        service_name: 'Test Service',
        customer_fio: 'Test Customer',
        description: 'Test payment',
        created: '2024-01-01T00:00:00Z',
        updated: '2024-01-01T00:00:00Z',
        metadata: {},
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockPayment,
        }),
      } as Response);

      const result = await client.createPayment({
        amount: '100.00',
        service_name: 'Test Service',
        customer_fio: 'Test Customer',
        description: 'Test payment',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockPayment);
    });

    it('should get payment by ID', async () => {
      const mockPayment = {
        id: 'payment-123',
        amount: '100.00',
        status: 'succeeded',
        service_name: 'Test Service',
        customer_fio: 'Test Customer',
        created: '2024-01-01T00:00:00Z',
        updated: '2024-01-01T00:00:00Z',
        metadata: {},
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockPayment,
        }),
      } as Response);

      const result = await client.getPayment('payment-123');

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockPayment);
    });
  });

  describe('Error Handling and Retry Logic', () => {
    it('should retry on network errors', async () => {
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { status: 'ok' },
          }),
        } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('should not retry on authentication errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({
          success: false,
          error: 'Unauthorized',
        }),
      } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should handle server errors with retry', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: () => Promise.resolve({
            success: false,
            error: 'Internal server error',
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { status: 'ok' },
          }),
        } as Response);

      const result = await client.healthCheck();

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Request Queue Management', () => {
    it('should prevent duplicate requests', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { status: 'ok' },
        }),
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      // Make two identical requests simultaneously
      const promise1 = client.healthCheck();
      const promise2 = client.healthCheck();

      const [result1, result2] = await Promise.all([promise1, promise2]);

      expect(result1).toEqual(result2);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('WebSocket Connection', () => {
    it('should create WebSocket connection', () => {
      const mockWebSocket = {
        close: vi.fn(),
        send: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        readyState: WebSocket.OPEN,
      };

      // Mock WebSocket constructor
      global.WebSocket = vi.fn(() => mockWebSocket) as any;

      const ws = client.connectWebSocket();

      expect(ws).toBe(mockWebSocket);
      expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws/chat/');
    });

    it('should handle WebSocket creation failure', () => {
      // Mock WebSocket constructor to throw error
      global.WebSocket = vi.fn(() => {
        throw new Error('WebSocket not supported');
      }) as any;

      const ws = client.connectWebSocket();

      expect(ws).toBeNull();
    });
  });
});
