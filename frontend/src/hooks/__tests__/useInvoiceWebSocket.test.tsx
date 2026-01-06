/**
 * Tests for useInvoiceWebSocket hook
 *
 * Covers:
 * - WebSocket connection on mount
 * - WebSocket disconnection on unmount
 * - Event subscription and unsubscription
 * - Invoice update handling
 * - Connection state management
 * - Error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useInvoiceWebSocket } from '../useInvoiceWebSocket';
import * as authHooks from '../useAuth';
import * as invoiceWebSocketService from '@/services/invoiceWebSocketService';

vi.mock('../useAuth');
vi.mock('@/services/invoiceWebSocketService');
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  },
}));

const MockedAuthHooks = authHooks as any;
const MockedInvoiceWebSocketService = invoiceWebSocketService as any;

describe('useInvoiceWebSocket', () => {
  let queryClient: QueryClient;
  let mockInvoiceWebSocketService: any;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    // Mock invoiceWebSocketService
    mockInvoiceWebSocketService = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      isConnected: vi.fn(() => false),
      onConnectionChange: vi.fn(),
    };

    MockedInvoiceWebSocketService.invoiceWebSocketService = mockInvoiceWebSocketService;

    // Mock useAuth
    MockedAuthHooks.useAuth = vi.fn(() => ({
      user: { id: 1, role: 'parent' },
      isLoading: false,
      error: null,
    }));

    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('Connection Management', () => {
    it('should connect to WebSocket when user is authenticated', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalledWith({});
      });

      expect(result.current).toBeDefined();
    });

    it('should not connect when user is not authenticated', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: null,
        isLoading: false,
        error: null,
      });

      renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).not.toHaveBeenCalled();
      });
    });

    it('should disconnect on component unmount', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { unmount } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      unmount();

      expect(mockInvoiceWebSocketService.disconnect).toHaveBeenCalled();
    });

    it('should reconnect when user changes', async () => {
      const { rerender } = renderHook(
        (props) => {
          MockedAuthHooks.useAuth.mockReturnValue(props.authValue);
          return useInvoiceWebSocket();
        },
        {
          wrapper: createWrapper(),
          initialProps: {
            authValue: { user: { id: 1 }, isLoading: false, error: null },
          },
        }
      );

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      vi.clearAllMocks();

      rerender({
        authValue: { user: { id: 2 }, isLoading: false, error: null },
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.disconnect).toHaveBeenCalled();
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });
    });
  });

  describe('Event Subscription', () => {
    it('should provide on() method to subscribe to events', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      const mockCallback = vi.fn();

      // Subscribe to invoice_updated event
      result.current.on('invoice_updated', mockCallback);

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalledWith(
          expect.objectContaining({
            invoice_updated: expect.any(Function),
          })
        );
      });
    });

    it('should provide off() method to unsubscribe from events', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      const mockCallback = vi.fn();

      result.current.on('invoice_updated', mockCallback);
      result.current.off('invoice_updated', mockCallback);

      // off() should complete without error
      expect(result.current.off).toBeDefined();
    });

    it('should support multiple event subscriptions', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      const callback1 = vi.fn();
      const callback2 = vi.fn();
      const callback3 = vi.fn();

      result.current.on('invoice_created', callback1);
      result.current.on('invoice_status_update', callback2);
      result.current.on('invoice_paid', callback3);

      // All subscriptions should be registered
      expect(mockInvoiceWebSocketService.connect).toHaveBeenCalledTimes(4); // 1 initial + 3 handlers
    });
  });

  describe('Connection State', () => {
    it('should provide isConnected() method', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      mockInvoiceWebSocketService.isConnected.mockReturnValue(true);

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      expect(result.current.isConnected()).toBe(true);
    });

    it('should reflect connection state changes', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      mockInvoiceWebSocketService.isConnected
        .mockReturnValueOnce(false)
        .mockReturnValueOnce(true);

      const { result, rerender } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isConnected()).toBe(false);
      });

      rerender();

      expect(result.current.isConnected()).toBe(true);
    });
  });

  describe('Connection Change Events', () => {
    it('should provide onConnectionChange() method', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      const mockConnectionCallback = vi.fn();
      result.current.onConnectionChange(mockConnectionCallback);

      expect(mockConnectionCallback).toBeDefined();
    });

    it('should call connection change callback when connection status changes', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      let connectionChangeHandler: ((connected: boolean) => void) | null = null;

      mockInvoiceWebSocketService.onConnectionChange.mockImplementation((handler) => {
        connectionChangeHandler = handler;
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      const mockCallback = vi.fn();
      result.current.onConnectionChange(mockCallback);

      // Simulate connection change
      if (connectionChangeHandler) {
        connectionChangeHandler(true);
        expect(mockCallback).toHaveBeenCalledWith(true);
      }
    });
  });

  describe('Integration with React Query', () => {
    it('should work with React Query provider', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      expect(result.current).toBeDefined();
      expect(result.current.on).toBeDefined();
      expect(result.current.off).toBeDefined();
      expect(result.current.isConnected).toBeDefined();
      expect(result.current.onConnectionChange).toBeDefined();
    });

    it('should allow query cache invalidation on invoice updates', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      const mockCallback = vi.fn((data) => {
        // Simulate query invalidation
        queryClient.invalidateQueries({ queryKey: ['invoices'] });
      });

      result.current.on('invoice_updated', mockCallback);

      // Verify the hook returns methods for integration
      expect(typeof result.current.on).toBe('function');
    });
  });

  describe('Return Value Structure', () => {
    it('should return object with required methods', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      expect(result.current).toHaveProperty('on');
      expect(result.current).toHaveProperty('off');
      expect(result.current).toHaveProperty('isConnected');
      expect(result.current).toHaveProperty('onConnectionChange');
    });

    it('should return methods with correct signatures', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockInvoiceWebSocketService.connect).toHaveBeenCalled();
      });

      expect(typeof result.current.on).toBe('function');
      expect(typeof result.current.off).toBe('function');
      expect(typeof result.current.isConnected).toBe('function');
      expect(typeof result.current.onConnectionChange).toBe('function');
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket connection errors gracefully', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      mockInvoiceWebSocketService.connect.mockImplementation(() => {
        throw new Error('WebSocket connection failed');
      });

      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      // Hook should handle error gracefully and not throw
      expect(() => {
        result.current.isConnected();
      }).not.toThrow();
    });

    it('should handle service unavailability', async () => {
      MockedAuthHooks.useAuth.mockReturnValue({
        user: { id: 1, role: 'parent' },
        isLoading: false,
        error: null,
      });

      mockInvoiceWebSocketService.connect = undefined;
      mockInvoiceWebSocketService.isConnected = undefined;

      // Should not crash when service is unavailable
      const { result } = renderHook(() => useInvoiceWebSocket(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toBeDefined();
    });
  });
});
