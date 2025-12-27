import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useNotificationArchive } from '../useNotificationArchive';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import * as loggerModule from '@/utils/logger';

// Mock the API and logger
vi.mock('@/integrations/api/unifiedClient');
vi.mock('@/utils/logger');

const mockNotifications = [
  {
    id: 1,
    title: 'System Update',
    message: 'System has been updated',
    type: 'system',
    priority: 'normal',
    created_at: '2025-12-20T10:00:00Z',
    archived_at: '2025-12-27T10:00:00Z',
    is_read: true,
  },
  {
    id: 2,
    title: 'New Message',
    message: 'You have a new message',
    type: 'message_new',
    priority: 'high',
    created_at: '2025-12-25T14:30:00Z',
    archived_at: '2025-12-27T10:00:00Z',
    is_read: false,
  },
];

describe('useNotificationArchive Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(unifiedAPI.get).mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: mockNotifications,
    });
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useNotificationArchive());

    expect(result.current.notifications).toEqual([]);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe(null);
    expect(result.current.page).toBe(1);
    expect(result.current.pageSize).toBe(10);
    expect(result.current.totalCount).toBe(0);
  });

  it('fetches archived notifications on mount', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.notifications).toEqual(mockNotifications);
    expect(result.current.totalCount).toBe(2);
    expect(unifiedAPI.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/notifications/archive/')
    );
  });

  it('includes pagination params in API call', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const callArgs = vi.mocked(unifiedAPI.get).mock.calls[0][0];
    expect(callArgs).toContain('page=1');
    expect(callArgs).toContain('limit=10');
  });

  it('includes filters in API call when set', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({
        type: 'system',
        search: 'update',
      });
    });

    await waitFor(() => {
      const callArgs = vi.mocked(unifiedAPI.get).mock.calls[
        vi.mocked(unifiedAPI.get).mock.calls.length - 1
      ][0];
      expect(callArgs).toContain('type=system');
      expect(callArgs).toContain('search=update');
    });
  });

  it('updates page and refetches on page change', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setPage(2);
    });

    await waitFor(() => {
      const lastCall = vi.mocked(unifiedAPI.get).mock.calls[
        vi.mocked(unifiedAPI.get).mock.calls.length - 1
      ][0];
      expect(lastCall).toContain('page=2');
    });
  });

  it('handles restore notification request', async () => {
    vi.mocked(unifiedAPI.patch).mockResolvedValue({
      id: 1,
      title: 'System Update',
      message: 'System has been updated',
      type: 'system',
      priority: 'normal',
      created_at: '2025-12-20T10:00:00Z',
      archived_at: null,
      is_archived: false,
      is_read: true,
    });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let restoreResult;
    act(() => {
      restoreResult = result.current.restoreNotification(1);
    });

    const response = await restoreResult;

    expect(unifiedAPI.patch).toHaveBeenCalledWith(
      '/api/notifications/1/restore/',
      {}
    );
    expect(response.title).toBe('System Update');
  });

  it('removes restored notification from list', async () => {
    vi.mocked(unifiedAPI.patch).mockResolvedValue({
      id: 1,
      title: 'System Update',
      is_archived: false,
    });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.notifications.length).toBe(2);
    });

    act(() => {
      result.current.restoreNotification(1);
    });

    await waitFor(() => {
      expect(result.current.notifications.length).toBe(1);
      expect(result.current.notifications[0].id).toBe(2);
    });
  });

  it('handles bulk restore request', async () => {
    vi.mocked(unifiedAPI.post).mockResolvedValue({
      restored_count: 2,
      not_found: 0,
      errors: [],
    });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let restoreResult;
    act(() => {
      restoreResult = result.current.bulkRestore([1, 2]);
    });

    const response = await restoreResult;

    expect(unifiedAPI.post).toHaveBeenCalledWith(
      '/api/notifications/bulk-restore/',
      { notification_ids: [1, 2] }
    );
    expect(response.restored_count).toBe(2);
  });

  it('removes bulk restored notifications from list', async () => {
    vi.mocked(unifiedAPI.post).mockResolvedValue({
      restored_count: 2,
      not_found: 0,
      errors: [],
    });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.notifications.length).toBe(2);
    });

    act(() => {
      result.current.bulkRestore([1, 2]);
    });

    await waitFor(() => {
      expect(result.current.notifications.length).toBe(0);
      expect(result.current.totalCount).toBe(0);
    });
  });

  it('handles delete notification request', async () => {
    vi.mocked(unifiedAPI.delete).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const initialCount = result.current.notifications.length;

    act(() => {
      result.current.deleteNotification(1);
    });

    await waitFor(() => {
      expect(result.current.notifications.length).toBe(initialCount - 1);
    });

    expect(unifiedAPI.delete).toHaveBeenCalledWith('/api/notifications/1/');
  });

  it('handles bulk delete request', async () => {
    vi.mocked(unifiedAPI.delete).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.bulkDelete([1, 2]);
    });

    await waitFor(() => {
      expect(result.current.notifications.length).toBe(0);
      expect(unifiedAPI.delete).toHaveBeenCalledTimes(2);
    });
  });

  it('sets error state when fetch fails', async () => {
    vi.mocked(unifiedAPI.get).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.notifications).toEqual([]);
  });

  it('sets error state when restore fails', async () => {
    vi.mocked(unifiedAPI.patch).mockRejectedValue(new Error('Restore failed'));

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let error;
    try {
      await result.current.restoreNotification(1);
    } catch (err) {
      error = err;
    }

    expect(error?.message).toBe('Restore failed');
  });

  it('sets error state when delete fails', async () => {
    vi.mocked(unifiedAPI.delete).mockRejectedValue(new Error('Delete failed'));

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let error;
    try {
      await result.current.deleteNotification(1);
    } catch (err) {
      error = err;
    }

    expect(error?.message).toBe('Delete failed');
  });

  it('logs error when fetch fails', async () => {
    vi.mocked(unifiedAPI.get).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(vi.mocked(loggerModule.logger.error)).toHaveBeenCalled();
  });

  it('allows updating filters independently', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({
        search: 'test',
        type: 'system',
      });
    });

    expect(result.current.filters.search).toBe('test');
    expect(result.current.filters.type).toBe('system');
  });

  it('calculates total pages correctly', () => {
    const { result } = renderHook(() => useNotificationArchive());

    // totalCount is 2, pageSize is 10, so 1 page
    expect(Math.ceil(result.current.totalCount / result.current.pageSize)).toBe(1);
  });

  it('provides refetch function to manually reload data', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const initialCallCount = vi.mocked(unifiedAPI.get).mock.calls.length;

    act(() => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(vi.mocked(unifiedAPI.get).mock.calls.length).toBeGreaterThan(
        initialCallCount
      );
    });
  });

  it('handles partial bulk restore failures', async () => {
    vi.mocked(unifiedAPI.post).mockResolvedValue({
      restored_count: 1,
      not_found: 1,
      errors: ['Notification 2 not found'],
    });

    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let restoreResult;
    act(() => {
      restoreResult = result.current.bulkRestore([1, 2]);
    });

    const response = await restoreResult;

    expect(response.restored_count).toBe(1);
    expect(response.not_found).toBe(1);
    expect(response.errors.length).toBeGreaterThan(0);
  });

  it('maintains total count accuracy after operations', async () => {
    vi.mocked(unifiedAPI.patch).mockResolvedValue({
      id: 1,
      is_archived: false,
    });

    const { result } = renderHook(() => useNotificationArchive());

    const initialCount = mockNotifications.length;

    await waitFor(() => {
      expect(result.current.totalCount).toBe(initialCount);
    });

    act(() => {
      result.current.restoreNotification(1);
    });

    await waitFor(() => {
      expect(result.current.totalCount).toBe(initialCount - 1);
    });
  });

  it('handles date filter parameters', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({
        date_from: '2025-12-20T00:00:00Z',
        date_to: '2025-12-27T23:59:59Z',
      });
    });

    await waitFor(() => {
      const lastCall = vi.mocked(unifiedAPI.get).mock.calls[
        vi.mocked(unifiedAPI.get).mock.calls.length - 1
      ][0];
      expect(lastCall).toContain('date_from');
      expect(lastCall).toContain('date_to');
    });
  });

  it('handles status filter parameter', async () => {
    const { result } = renderHook(() => useNotificationArchive());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setFilters({
        status: 'read',
      });
    });

    await waitFor(() => {
      const lastCall = vi.mocked(unifiedAPI.get).mock.calls[
        vi.mocked(unifiedAPI.get).mock.calls.length - 1
      ][0];
      expect(lastCall).toContain('status=read');
    });
  });
});
