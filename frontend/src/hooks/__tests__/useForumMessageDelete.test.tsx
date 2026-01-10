import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useForumMessageDelete } from '../useForumMessageDelete';
import { chatAPI, ChatMessage } from '@/integrations/api/chatAPI';

// Mock chatAPI
vi.mock('@/integrations/api/chatAPI', () => ({
  chatAPI: {
    deleteMessage: vi.fn(),
  },
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('useForumMessageDelete', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('should delete message successfully', async () => {
    vi.mocked(chatAPI.deleteMessage).mockResolvedValue(undefined);

    const { result } = renderHook(
      () => useForumMessageDelete({ chatId: 1 }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate(1);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(chatAPI.deleteMessage).toHaveBeenCalledWith(1);
  });

  it('should call onSuccess callback', async () => {
    const onSuccess = vi.fn();

    vi.mocked(chatAPI.deleteMessage).mockResolvedValue(undefined);

    const { result } = renderHook(
      () => useForumMessageDelete({ chatId: 1, onSuccess }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate(1);
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('should handle error', async () => {
    const onError = vi.fn();
    const error = new Error('Delete failed');

    vi.mocked(chatAPI.deleteMessage).mockRejectedValue(error);

    const { result } = renderHook(
      () => useForumMessageDelete({ chatId: 1, onError }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate(1);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('should perform optimistic removal', async () => {
    const mockMessages: ChatMessage[] = [
      {
        id: 1,
        content: 'Message to delete',
        sender: { id: 1, full_name: 'John Doe', role: 'student' },
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:00:00Z',
        is_read: true,
      },
      {
        id: 2,
        content: 'Keep this message',
        sender: { id: 2, full_name: 'Jane Doe', role: 'student' },
        created_at: '2025-01-01T10:01:00Z',
        updated_at: '2025-01-01T10:01:00Z',
        is_read: true,
      },
    ];

    // Set initial cache
    queryClient.setQueryData(['forum-messages', 1, 50, 0], mockMessages);

    vi.mocked(chatAPI.deleteMessage).mockResolvedValue(undefined);

    const { result } = renderHook(
      () => useForumMessageDelete({ chatId: 1 }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate(1);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify cache was updated - message should be removed
    const cachedMessages = queryClient.getQueryData<ChatMessage[]>([
      'forum-messages',
      1,
      50,
      0,
    ]);

    expect(cachedMessages).toHaveLength(1);
    expect(cachedMessages?.[0]?.id).toBe(2);
  });

  it('should rollback on error', async () => {
    const mockMessages: ChatMessage[] = [
      {
        id: 1,
        content: 'Message',
        sender: { id: 1, full_name: 'John Doe', role: 'student' },
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:00:00Z',
        is_read: true,
      },
    ];

    queryClient.setQueryData(['forum-messages', 1, 50, 0], mockMessages);

    const error = new Error('Delete failed');
    vi.mocked(chatAPI.deleteMessage).mockRejectedValue(error);

    const { result } = renderHook(
      () => useForumMessageDelete({ chatId: 1 }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate(1);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Cache should still have the message after rollback
    const cachedMessages = queryClient.getQueryData<ChatMessage[]>([
      'forum-messages',
      1,
      50,
      0,
    ]);

    expect(cachedMessages).toHaveLength(1);
    expect(cachedMessages?.[0]?.id).toBe(1);
  });
});
