import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useForumMessageUpdate } from '../useForumMessageUpdate';
import { chatAPI, ChatMessage } from '@/integrations/api/chatAPI';

// Mock chatAPI
vi.mock('@/integrations/api/chatAPI', () => ({
  chatAPI: {
    editMessage: vi.fn(),
  },
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('useForumMessageUpdate', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('should update message successfully', async () => {
    const mockMessage: ChatMessage = {
      id: 1,
      content: 'Updated content',
      sender: { id: 1, full_name: 'John Doe', role: 'student' },
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-01T10:01:00Z',
      is_read: true,
      is_edited: true,
    };

    vi.mocked(chatAPI.editMessage).mockResolvedValue(mockMessage);

    const { result } = renderHook(
      () => useForumMessageUpdate({ chatId: 1 }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate({
        messageId: 1,
        data: { content: 'Updated content' },
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockMessage);
  });

  it('should call onSuccess callback', async () => {
    const onSuccess = vi.fn();
    const mockMessage: ChatMessage = {
      id: 1,
      content: 'Updated content',
      sender: { id: 1, full_name: 'John Doe', role: 'student' },
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-01T10:01:00Z',
      is_read: true,
      is_edited: true,
    };

    vi.mocked(chatAPI.editMessage).mockResolvedValue(mockMessage);

    const { result } = renderHook(
      () => useForumMessageUpdate({ chatId: 1, onSuccess }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate({
        messageId: 1,
        data: { content: 'Updated content' },
      });
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(mockMessage);
    });
  });

  it('should handle error', async () => {
    const onError = vi.fn();
    const error = new Error('Update failed');

    vi.mocked(chatAPI.editMessage).mockRejectedValue(error);

    const { result } = renderHook(
      () => useForumMessageUpdate({ chatId: 1, onError }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate({
        messageId: 1,
        data: { content: 'Updated content' },
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('should perform optimistic update', async () => {
    const mockMessage: ChatMessage = {
      id: 1,
      content: 'Updated content',
      sender: { id: 1, full_name: 'John Doe', role: 'student' },
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-01T10:01:00Z',
      is_read: true,
      is_edited: true,
    };

    // Set initial cache
    const initialMessages: ChatMessage[] = [
      {
        id: 1,
        content: 'Original content',
        sender: { id: 1, full_name: 'John Doe', role: 'student' },
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:00:00Z',
        is_read: true,
      },
    ];

    queryClient.setQueryData(['forum-messages', 1, 50, 0], initialMessages);

    vi.mocked(chatAPI.editMessage).mockResolvedValue(mockMessage);

    const { result } = renderHook(
      () => useForumMessageUpdate({ chatId: 1 }),
      { wrapper }
    );

    await act(async () => {
      await result.current.mutate({
        messageId: 1,
        data: { content: 'Updated content' },
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify cache was updated
    const cachedMessages = queryClient.getQueryData<ChatMessage[]>([
      'forum-messages',
      1,
      50,
      0,
    ]);

    expect(cachedMessages?.[0]?.content).toBe('Updated content');
  });
});
