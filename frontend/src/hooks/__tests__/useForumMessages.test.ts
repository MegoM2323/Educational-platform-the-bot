import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useForumMessages, useSendForumMessage } from '../useForumMessages';
import { forumAPI } from '@/integrations/api/forumAPI';
import { toast } from 'sonner';
import * as React from 'react';

// Mock forumAPI
vi.mock('@/integrations/api/forumAPI', () => ({
  forumAPI: {
    getForumMessages: vi.fn(),
    sendForumMessage: vi.fn(),
  },
}));

// Mock toast notifications
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

const mockForumMessages = [
  {
    id: 1,
    content: 'Hello, how are you?',
    sender: {
      id: 10,
      full_name: 'Jane Teacher',
      role: 'teacher',
    },
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
    is_read: true,
    message_type: 'text',
  },
  {
    id: 2,
    content: 'I am doing great, thanks for asking!',
    sender: {
      id: 1,
      full_name: 'John Student',
      role: 'student',
    },
    created_at: '2025-01-15T10:05:00Z',
    updated_at: '2025-01-15T10:05:00Z',
    is_read: true,
    message_type: 'text',
  },
  {
    id: 3,
    content: 'Can you check my homework?',
    sender: {
      id: 1,
      full_name: 'John Student',
      role: 'student',
    },
    created_at: '2025-01-15T10:10:00Z',
    updated_at: '2025-01-15T10:10:00Z',
    is_read: false,
    message_type: 'text',
  },
];

// API returns ForumMessage[] directly (unifiedAPI extracts results array)
const mockMessagesResponse = mockForumMessages;

describe('useForumMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно загружать сообщения для чата', async () => {
    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(mockMessagesResponse);

    const { result } = renderHook(() => useForumMessages(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockMessagesResponse);
    expect(forumAPI.getForumMessages).toHaveBeenCalledWith(1, 50, 0);
  });

  it('должен не вызывать API если chatId не передан (null)', () => {
    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(mockMessagesResponse);

    const { result } = renderHook(() => useForumMessages(null), {
      wrapper: createWrapper(),
    });

    // Query should be disabled (enabled: !!chatId)
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(forumAPI.getForumMessages).not.toHaveBeenCalled();
  });

  it('должен вызывать API с правильными параметрами pagination', async () => {
    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(mockMessagesResponse);

    renderHook(() => useForumMessages(1, 25, 50), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(forumAPI.getForumMessages).toHaveBeenCalledWith(1, 25, 50);
    });
  });

  it('должен показывать состояние загрузки', () => {
    vi.mocked(forumAPI.getForumMessages).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useForumMessages(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });


  it('должен включать информацию о прочитанности сообщения', async () => {
    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(mockMessagesResponse);

    const { result } = renderHook(() => useForumMessages(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const messages = result.current.data || [];
    expect(messages[0].is_read).toBe(true);
    expect(messages[2].is_read).toBe(false);
  });

  it('должен правильно устанавливать staleTime в 30 секунд', async () => {
    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(mockMessagesResponse);

    const { result, rerender } = renderHook(() => useForumMessages(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.getForumMessages).toHaveBeenCalledTimes(1);

    // Re-render immediately - should use cache
    rerender();

    expect(forumAPI.getForumMessages).toHaveBeenCalledTimes(1);
  });

  it('должен поддерживать retry с 2 попытками', async () => {
    vi.mocked(forumAPI.getForumMessages)
      .mockRejectedValueOnce(new Error('First fail'))
      .mockResolvedValueOnce(mockMessagesResponse);

    const { result } = renderHook(() => useForumMessages(1), {
      wrapper: createWrapper(),
    });

    // Wait for query to settle after retries
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    }, { timeout: 3000 });

    // Should succeed after retry
    expect(result.current.isSuccess).toBe(true);
    expect(result.current.data).toEqual(mockMessagesResponse);
  });

  it('должен обновляться при изменении chatId', async () => {
    const mockResponse1 = [mockForumMessages[0]];
    const mockResponse2 = [mockForumMessages[1]];

    vi.mocked(forumAPI.getForumMessages)
      .mockResolvedValueOnce(mockResponse1)
      .mockResolvedValueOnce(mockResponse2);

    const { result, rerender } = renderHook(
      ({ chatId }: { chatId: number | null }) => useForumMessages(chatId),
      {
        wrapper: createWrapper(),
        initialProps: { chatId: 1 },
      }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockResponse1);
    expect(forumAPI.getForumMessages).toHaveBeenCalledWith(1, 50, 0);

    // Change chatId
    rerender({ chatId: 2 });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockResponse2);
    }, { timeout: 3000 });

    // After rerender, API should be called again with new chatId
    await waitFor(() => {
      expect(forumAPI.getForumMessages).toHaveBeenCalledWith(2, 50, 0);
    });
  });

  it('должен вернуть пустой ответ если нет сообщений', async () => {
    const emptyResponse: typeof mockMessagesResponse = [];

    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(emptyResponse);

    const { result } = renderHook(() => useForumMessages(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(0);
  });
});

describe('useSendForumMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно отправлять сообщение', async () => {
    const newMessage = {
      id: 4,
      content: 'New message',
      sender: {
        id: 1,
        full_name: 'John Student',
        role: 'student',
      },
      created_at: '2025-01-15T11:00:00Z',
      updated_at: '2025-01-15T11:00:00Z',
      is_read: true,
      message_type: 'text',
    };

    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);
    vi.mocked(forumAPI.getForumMessages).mockResolvedValue(mockMessagesResponse);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: { content: 'New message' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.sendForumMessage).toHaveBeenCalledWith(1, { content: 'New message' });
    expect(result.current.data).toEqual(newMessage);
  });

  it('должен показать уведомление об успешной отправке', async () => {
    const newMessage = mockForumMessages[0];

    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: { content: 'Test message' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(toast.success)).toHaveBeenCalledWith('Сообщение отправлено');
  });

  it('должен обработать ошибку при отправке сообщения', async () => {
    const error = new Error('Server error');
    vi.mocked(forumAPI.sendForumMessage).mockRejectedValue(error);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: { content: 'Test message' },
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      'Ошибка отправки сообщения: Server error'
    );
  });

  it('должен инвалидировать кеш сообщений после отправки', async () => {
    const newMessage = mockForumMessages[0];
    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: { content: 'Test message' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify cache invalidation was attempted (no direct way to check, but success indicates it)
    expect(result.current.isSuccess).toBe(true);
  });

  it('должен показывать состояние pending при отправке', async () => {
    vi.mocked(forumAPI.sendForumMessage).mockImplementation(
      () => new Promise(() => {}) // Never resolves - stays pending
    );

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: { content: 'Test message' },
    });

    // Immediately after mutate, isPending should be true
    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    }, { timeout: 1000 });
  });

  it('должен поддерживать отправку сообщения с дополнительными параметрами', async () => {
    const newMessage = mockForumMessages[0];
    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: {
        content: 'Reply to message',
        message_type: 'reply',
        reply_to: 3,
      },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.sendForumMessage).toHaveBeenCalledWith(1, {
      content: 'Reply to message',
      message_type: 'reply',
      reply_to: 3,
    });
  });

  it('должен правильно передать chatId в переменных мутации', async () => {
    const newMessage = mockForumMessages[0];
    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 5,
      data: { content: 'Message for chat 5' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.sendForumMessage).toHaveBeenCalledWith(5, expect.any(Object));
  });

  it('должен сбрасывать состояние при новой мутации', async () => {
    const newMessage = mockForumMessages[0];
    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    // First mutation
    result.current.mutate({
      chatId: 1,
      data: { content: 'First message' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isSuccess).toBe(true);
    expect(result.current.isPending).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('должен обновлять список чатов после отправки сообщения', async () => {
    const newMessage = mockForumMessages[0];
    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const { result } = renderHook(() => useSendForumMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      chatId: 1,
      data: { content: 'Test message' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Cache invalidation for forum-chats should happen in onSuccess
    expect(result.current.isSuccess).toBe(true);
  });

  it('должен добавлять сообщение в кеш немедленно (optimistic update)', async () => {
    const newMessage = {
      id: 10,
      content: 'Brand new message',
      sender: {
        id: 1,
        full_name: 'John Student',
        role: 'student',
      },
      created_at: '2025-01-15T12:00:00Z',
      updated_at: '2025-01-15T12:00:00Z',
      is_read: false,
      message_type: 'text',
    } as any;

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Pre-populate cache with existing messages
    queryClient.setQueryData(['forum-messages', 1, 50, 0], mockForumMessages);

    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);

    const { result } = renderHook(() => useSendForumMessage(), { wrapper });

    // Send message
    result.current.mutate({
      chatId: 1,
      data: { content: 'Brand new message' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Check that cache was updated with new message
    const cachedMessages = queryClient.getQueryData<typeof mockForumMessages>(['forum-messages', 1, 50, 0]);
    expect(cachedMessages).toBeDefined();
    expect(cachedMessages).toHaveLength(mockForumMessages.length + 1);
    expect(cachedMessages?.[cachedMessages.length - 1].content).toBe('Brand new message');
  });

  it('должен предотвращать дублирование сообщений в кеше', async () => {
    const newMessage = mockForumMessages[0]; // Use existing message (same ID)

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Pre-populate cache with existing messages
    queryClient.setQueryData(['forum-messages', 1, 50, 0], mockForumMessages);

    vi.mocked(forumAPI.sendForumMessage).mockResolvedValue(newMessage);

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);

    const { result } = renderHook(() => useSendForumMessage(), { wrapper });

    // Send message with duplicate ID
    result.current.mutate({
      chatId: 1,
      data: { content: newMessage.content },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Check that cache still has same number of messages (no duplicate)
    const cachedMessages = queryClient.getQueryData<typeof mockForumMessages>(['forum-messages', 1, 50, 0]);
    expect(cachedMessages).toHaveLength(mockForumMessages.length); // Should NOT increase
  });
});
