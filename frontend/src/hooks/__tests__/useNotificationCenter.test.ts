import { renderHook, act, waitFor } from '@testing-library/react';
import { useNotificationCenter, type Notification } from '../useNotificationCenter';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
  },
}));

describe('useNotificationCenter', () => {
  const mockNotifications: Notification[] = [
    {
      id: 1,
      title: 'Test Notification',
      message: 'This is a test notification',
      type: 'system',
      priority: 'normal',
      created_at: new Date().toISOString(),
      is_read: false,
      is_sent: true,
    },
    {
      id: 2,
      title: 'Message Notification',
      message: 'You have a new message',
      type: 'message_new',
      priority: 'high',
      created_at: new Date().toISOString(),
      is_read: true,
      is_sent: true,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (unifiedAPI.get as any).mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: mockNotifications,
    });
  });

  it('should initialize with default values', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    expect(result.current.notifications).toEqual([]);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.page).toBe(1);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should fetch notifications', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.notifications).toEqual(mockNotifications);
    expect(result.current.totalCount).toBe(2);
  });

  it('should fetch unread count', async () => {
    (unifiedAPI.get as any).mockImplementation((url: string) => {
      if (url.includes('unread_count')) {
        return Promise.resolve({ unread_count: 1 });
      }
      return Promise.resolve({
        count: 2,
        next: null,
        previous: null,
        results: mockNotifications,
      });
    });

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.unreadCount).toBe(1);
    });
  });

  it('should mark notification as read', async () => {
    (unifiedAPI.post as any).mockResolvedValue({});

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    await act(async () => {
      await result.current.markAsRead(1);
    });

    expect(unifiedAPI.post).toHaveBeenCalledWith('/api/notifications/1/mark_read/', {});

    const updatedNotification = result.current.notifications.find((n) => n.id === 1);
    expect(updatedNotification?.is_read).toBe(true);
  });

  it('should mark multiple notifications as read', async () => {
    (unifiedAPI.post as any).mockResolvedValue({
      message: 'Marked as read',
    });

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    await act(async () => {
      await result.current.markMultipleAsRead([1, 2]);
    });

    expect(unifiedAPI.post).toHaveBeenCalledWith('/api/notifications/mark_multiple_read/', {
      mark_all: false,
      notification_ids: [1, 2],
    });
  });

  it('should mark all notifications as read', async () => {
    (unifiedAPI.post as any).mockResolvedValue({
      message: 'All marked as read',
    });

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    await act(async () => {
      await result.current.markMultipleAsRead([], true);
    });

    expect(unifiedAPI.post).toHaveBeenCalledWith('/api/notifications/mark_multiple_read/', {
      mark_all: true,
      notification_ids: [],
    });
  });

  it('should delete notification', async () => {
    (unifiedAPI.delete as any).mockResolvedValue({});

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    const initialCount = result.current.notifications.length;

    await act(async () => {
      await result.current.deleteNotification(1);
    });

    expect(unifiedAPI.delete).toHaveBeenCalledWith('/api/notifications/1/');
    expect(result.current.notifications.length).toBe(initialCount - 1);
  });

  it('should delete multiple notifications', async () => {
    (unifiedAPI.delete as any).mockResolvedValue({});

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    await act(async () => {
      await result.current.deleteMultiple([1, 2]);
    });

    expect(unifiedAPI.delete).toHaveBeenCalledTimes(2);
    expect(result.current.notifications.length).toBe(0);
  });

  it('should filter notifications by type', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({ type: 'system' });
    });

    expect(result.current.filters.type).toBe('system');
  });

  it('should filter notifications by priority', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({ priority: 'high' });
    });

    expect(result.current.filters.priority).toBe('high');
  });

  it('should search notifications', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({ search: 'test' });
    });

    expect(result.current.filters.search).toBe('test');
  });

  it('should paginate notifications', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setPage(2);
    });

    expect(result.current.page).toBe(2);
  });

  it('should handle API errors gracefully', async () => {
    const errorMessage = 'Network error';
    (unifiedAPI.get as any).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toContain(errorMessage);
  });

  it('should handle delete errors', async () => {
    (unifiedAPI.delete as any).mockRejectedValue(new Error('Delete failed'));

    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    await expect(
      act(async () => {
        await result.current.deleteNotification(1);
      })
    ).rejects.toThrow('Delete failed');
  });

  it('should refetch notifications', async () => {
    const { result } = renderHook(() => useNotificationCenter());

    await waitFor(() => {
      expect(result.current.notifications.length).toBeGreaterThan(0);
    });

    const callCount = (unifiedAPI.get as any).mock.calls.length;

    await act(async () => {
      await result.current.refetch();
    });

    expect((unifiedAPI.get as any).mock.calls.length).toBeGreaterThan(callCount);
  });
});
