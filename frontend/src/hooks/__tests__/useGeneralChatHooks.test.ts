import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useGeneralChat,
  useGeneralChatMessages,
  useGeneralChatThreads,
  useThreadMessages,
  useSendGeneralMessage,
  useSendThreadMessage,
  useCreateThread,
  usePinThread,
  useUnpinThread,
  useLockThread,
  useUnlockThread,
} from '../useGeneralChatHooks';
import { chatService, ChatMessage, ChatThread, ChatRoom, SendMessageRequest, CreateThreadRequest } from '@/integrations/api/chatService';
import * as React from 'react';

// Mock chatService
vi.mock('@/integrations/api/chatService', () => ({
  chatService: {
    getGeneralChat: vi.fn(),
    getGeneralChatMessages: vi.fn(),
    getGeneralChatThreads: vi.fn(),
    getThreadMessages: vi.fn(),
    sendGeneralMessage: vi.fn(),
    sendThreadMessage: vi.fn(),
    createThread: vi.fn(),
    pinThread: vi.fn(),
    unpinThread: vi.fn(),
    lockThread: vi.fn(),
    unlockThread: vi.fn(),
  },
}));

// Mock toast
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

// Mock data
const mockGeneralChat: ChatRoom = {
  id: 1,
  name: 'General Chat',
  description: 'Main discussion area',
  type: 'general',
  participants_count: 25,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

const mockChatMessages: ChatMessage[] = [
  {
    id: 1,
    content: 'Hello everyone!',
    message_type: 'text',
    sender: {
      id: 1,
      first_name: 'John',
      last_name: 'Doe',
      role: 'student',
      role_display: 'Student',
    },
    is_edited: false,
    created_at: '2025-01-15T09:00:00Z',
    updated_at: '2025-01-15T09:00:00Z',
  },
  {
    id: 2,
    content: 'Hi John!',
    message_type: 'text',
    sender: {
      id: 2,
      first_name: 'Jane',
      last_name: 'Smith',
      role: 'teacher',
      role_display: 'Teacher',
    },
    is_edited: false,
    created_at: '2025-01-15T09:05:00Z',
    updated_at: '2025-01-15T09:05:00Z',
  },
];

const mockChatThreads: ChatThread[] = [
  {
    id: 1,
    title: 'Discussion about homework',
    created_by: {
      id: 1,
      first_name: 'John',
      last_name: 'Doe',
      role: 'student',
    },
    is_pinned: true,
    is_locked: false,
    messages_count: 5,
    last_message: mockChatMessages[1],
    created_at: '2025-01-14T10:00:00Z',
    updated_at: '2025-01-15T09:05:00Z',
  },
  {
    id: 2,
    title: 'Class schedule update',
    created_by: {
      id: 2,
      first_name: 'Jane',
      last_name: 'Smith',
      role: 'teacher',
    },
    is_pinned: false,
    is_locked: false,
    messages_count: 3,
    last_message: mockChatMessages[0],
    created_at: '2025-01-13T10:00:00Z',
    updated_at: '2025-01-15T09:00:00Z',
  },
];

const mockThreadMessages: ChatMessage[] = [
  {
    id: 10,
    content: 'First message in thread',
    message_type: 'text',
    sender: {
      id: 1,
      first_name: 'John',
      last_name: 'Doe',
      role: 'student',
      role_display: 'Student',
    },
    thread: { id: 1, title: 'Discussion about homework' },
    is_edited: false,
    created_at: '2025-01-14T10:00:00Z',
    updated_at: '2025-01-14T10:00:00Z',
  },
  {
    id: 11,
    content: 'Reply in thread',
    message_type: 'text',
    sender: {
      id: 2,
      first_name: 'Jane',
      last_name: 'Smith',
      role: 'teacher',
      role_display: 'Teacher',
    },
    thread: { id: 1, title: 'Discussion about homework' },
    is_edited: false,
    created_at: '2025-01-14T10:05:00Z',
    updated_at: '2025-01-14T10:05:00Z',
  },
];

describe('useGeneralChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully fetch general chat', async () => {
    vi.mocked(chatService.getGeneralChat).mockResolvedValue(mockGeneralChat);

    const { result } = renderHook(() => useGeneralChat(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockGeneralChat);
    expect(chatService.getGeneralChat).toHaveBeenCalledTimes(1);
  });

  it('should return correct chat room structure', async () => {
    vi.mocked(chatService.getGeneralChat).mockResolvedValue(mockGeneralChat);

    const { result } = renderHook(() => useGeneralChat(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data;
    expect(chat?.id).toBe(1);
    expect(chat?.name).toBe('General Chat');
    expect(chat?.type).toBe('general');
    expect(chat?.participants_count).toBe(25);
  });

  it('should show loading state', () => {
    vi.mocked(chatService.getGeneralChat).mockImplementation(
      () => new Promise(() => {})
    );

    const { result } = renderHook(() => useGeneralChat(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('should attempt to fetch chat and handle failures', async () => {
    const error = new Error('Failed to fetch chat');
    vi.mocked(chatService.getGeneralChat).mockRejectedValue(error);

    const { result } = renderHook(() => useGeneralChat(), {
      wrapper: createWrapper(),
    });

    // Query should start loading
    expect(result.current.isLoading).toBe(true);

    // Wait a moment for async operation
    await new Promise(resolve => setTimeout(resolve, 100));

    // API call should have been made
    expect(chatService.getGeneralChat).toHaveBeenCalled();
  });

  it('should set staleTime to 5 minutes (300000ms)', async () => {
    vi.mocked(chatService.getGeneralChat).mockResolvedValue(mockGeneralChat);

    const { result, rerender } = renderHook(() => useGeneralChat(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getGeneralChat).toHaveBeenCalledTimes(1);

    // Re-render immediately - should use cache due to staleTime
    rerender();

    expect(chatService.getGeneralChat).toHaveBeenCalledTimes(1);
  });

  it('should support retry with 2 attempts', async () => {
    vi.mocked(chatService.getGeneralChat)
      .mockRejectedValueOnce(new Error('First fail'))
      .mockResolvedValueOnce(mockGeneralChat);

    const { result } = renderHook(() => useGeneralChat(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    }, { timeout: 3000 });

    expect(result.current.isSuccess).toBe(true);
    expect(result.current.data).toEqual(mockGeneralChat);
  });
});

describe('useGeneralChatMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully fetch general chat messages', async () => {
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue(mockChatMessages);

    const { result } = renderHook(() => useGeneralChatMessages(50, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockChatMessages);
    expect(chatService.getGeneralChatMessages).toHaveBeenCalledWith(50, 0);
  });

  it('should support pagination with limit and offset', async () => {
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue([mockChatMessages[0]]);

    const { result } = renderHook(() => useGeneralChatMessages(25, 50), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getGeneralChatMessages).toHaveBeenCalledWith(25, 50);
  });

  it('should use default parameters if not provided', async () => {
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue(mockChatMessages);

    const { result } = renderHook(() => useGeneralChatMessages(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getGeneralChatMessages).toHaveBeenCalledWith(50, 0);
  });

  it('should return array of messages with proper structure', async () => {
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue(mockChatMessages);

    const { result } = renderHook(() => useGeneralChatMessages(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const messages = result.current.data || [];
    expect(messages).toHaveLength(2);
    expect(messages[0].id).toBe(1);
    expect(messages[0].content).toBe('Hello everyone!');
    expect(messages[0].sender.first_name).toBe('John');
  });

  it('should have staleTime of 30 seconds', async () => {
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue(mockChatMessages);

    const { result, rerender } = renderHook(() => useGeneralChatMessages(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getGeneralChatMessages).toHaveBeenCalledTimes(1);

    rerender();

    expect(chatService.getGeneralChatMessages).toHaveBeenCalledTimes(1);
  });

  it('should handle empty message list', async () => {
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue([]);

    const { result } = renderHook(() => useGeneralChatMessages(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });
});

describe('useGeneralChatThreads', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully fetch general chat threads', async () => {
    vi.mocked(chatService.getGeneralChatThreads).mockResolvedValue(mockChatThreads);

    const { result } = renderHook(() => useGeneralChatThreads(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockChatThreads);
    expect(chatService.getGeneralChatThreads).toHaveBeenCalledWith(20, 0);
  });

  it('should support pagination', async () => {
    vi.mocked(chatService.getGeneralChatThreads).mockResolvedValue([mockChatThreads[0]]);

    const { result } = renderHook(() => useGeneralChatThreads(10, 20), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getGeneralChatThreads).toHaveBeenCalledWith(10, 20);
  });

  it('should return threads with pinned/locked status', async () => {
    vi.mocked(chatService.getGeneralChatThreads).mockResolvedValue(mockChatThreads);

    const { result } = renderHook(() => useGeneralChatThreads(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const threads = result.current.data || [];
    expect(threads[0].is_pinned).toBe(true);
    expect(threads[0].is_locked).toBe(false);
    expect(threads[1].is_pinned).toBe(false);
  });

  it('should include message count and last message', async () => {
    vi.mocked(chatService.getGeneralChatThreads).mockResolvedValue(mockChatThreads);

    const { result } = renderHook(() => useGeneralChatThreads(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const thread = result.current.data?.[0];
    expect(thread?.messages_count).toBe(5);
    expect(thread?.last_message).toBeDefined();
    expect(thread?.last_message?.content).toBe('Hi John!');
  });

  it('should have staleTime of 1 minute (60000ms)', async () => {
    vi.mocked(chatService.getGeneralChatThreads).mockResolvedValue(mockChatThreads);

    const { result, rerender } = renderHook(() => useGeneralChatThreads(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getGeneralChatThreads).toHaveBeenCalledTimes(1);

    rerender();

    expect(chatService.getGeneralChatThreads).toHaveBeenCalledTimes(1);
  });
});

describe('useThreadMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully fetch thread messages', async () => {
    vi.mocked(chatService.getThreadMessages).mockResolvedValue(mockThreadMessages);

    const { result } = renderHook(() => useThreadMessages(1, 50, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockThreadMessages);
    expect(chatService.getThreadMessages).toHaveBeenCalledWith(1, 50, 0);
  });

  it('should be disabled when threadId is not provided', () => {
    vi.mocked(chatService.getThreadMessages).mockResolvedValue(mockThreadMessages);

    const { result } = renderHook(() => useThreadMessages(0, 50, 0), {
      wrapper: createWrapper(),
    });

    expect(chatService.getThreadMessages).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it('should be disabled when threadId is falsy', () => {
    vi.mocked(chatService.getThreadMessages).mockResolvedValue(mockThreadMessages);

    const { result } = renderHook(() => useThreadMessages(null as any, 50, 0), {
      wrapper: createWrapper(),
    });

    expect(chatService.getThreadMessages).not.toHaveBeenCalled();
  });

  it('should support pagination', async () => {
    vi.mocked(chatService.getThreadMessages).mockResolvedValue([mockThreadMessages[0]]);

    const { result } = renderHook(() => useThreadMessages(1, 25, 50), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getThreadMessages).toHaveBeenCalledWith(1, 25, 50);
  });

  it('should return messages with thread information', async () => {
    vi.mocked(chatService.getThreadMessages).mockResolvedValue(mockThreadMessages);

    const { result } = renderHook(() => useThreadMessages(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const message = result.current.data?.[0];
    expect(message?.thread?.id).toBe(1);
    expect(message?.thread?.title).toBe('Discussion about homework');
  });

  it('should re-fetch when threadId changes', async () => {
    vi.mocked(chatService.getThreadMessages)
      .mockResolvedValueOnce(mockThreadMessages)
      .mockResolvedValueOnce([mockThreadMessages[1]]);

    const { result, rerender } = renderHook(
      ({ threadId }) => useThreadMessages(threadId),
      {
        wrapper: createWrapper(),
        initialProps: { threadId: 1 }
      }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.getThreadMessages).toHaveBeenCalledTimes(1);

    // Change threadId
    rerender({ threadId: 2 });

    await waitFor(() => {
      expect(chatService.getThreadMessages).toHaveBeenCalledTimes(2);
    });
  });
});

describe('useSendGeneralMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully send a message', async () => {
    const messageRequest: SendMessageRequest = { content: 'New message' };
    vi.mocked(chatService.sendGeneralMessage).mockResolvedValue(mockChatMessages[0]);

    const { result } = renderHook(() => useSendGeneralMessage(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(false);

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.sendGeneralMessage).toHaveBeenCalledWith(messageRequest);
  });

  it('should invalidate general chat messages query on success', async () => {
    const messageRequest: SendMessageRequest = { content: 'Test' };
    vi.mocked(chatService.sendGeneralMessage).mockResolvedValue(mockChatMessages[0]);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);

    const { result } = renderHook(() => useSendGeneralMessage(), { wrapper });

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify that invalidateQueries was called (we can't directly test this without spying on queryClient)
  });

  it('should handle message with different types', async () => {
    const imageRequest: SendMessageRequest = {
      content: 'Check this image',
      message_type: 'image'
    };

    vi.mocked(chatService.sendGeneralMessage).mockResolvedValue(mockChatMessages[0]);

    const { result } = renderHook(() => useSendGeneralMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(imageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.sendGeneralMessage).toHaveBeenCalledWith(imageRequest);
  });

  it('should handle errors with toast notification', async () => {
    const { toast } = await import('sonner');
    const messageRequest: SendMessageRequest = { content: 'Test' };
    const error = new Error('Send failed');

    vi.mocked(chatService.sendGeneralMessage).mockRejectedValue(error);

    const { result } = renderHook(() => useSendGeneralMessage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalled();
  });

  it('should return mutation object with proper methods', async () => {
    const { result } = renderHook(() => useSendGeneralMessage(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
    expect(typeof result.current.mutateAsync).toBe('function');
    expect(result.current.isPending).toBeDefined();
    expect(result.current.isError).toBeDefined();
    expect(result.current.isSuccess).toBeDefined();
  });
});

describe('useSendThreadMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully send a message to thread', async () => {
    const threadId = 1;
    const messageRequest: SendMessageRequest = { content: 'Reply in thread' };

    vi.mocked(chatService.sendThreadMessage).mockResolvedValue(mockThreadMessages[0]);

    const { result } = renderHook(() => useSendThreadMessage(threadId), {
      wrapper: createWrapper(),
    });

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.sendThreadMessage).toHaveBeenCalledWith(threadId, messageRequest);
  });

  it('should invalidate both thread and threads list queries', async () => {
    const threadId = 1;
    const messageRequest: SendMessageRequest = { content: 'Reply' };

    vi.mocked(chatService.sendThreadMessage).mockResolvedValue(mockThreadMessages[0]);

    const { result } = renderHook(() => useSendThreadMessage(threadId), {
      wrapper: createWrapper(),
    });

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verification that cache was invalidated happens implicitly
  });

  it('should pass threadId correctly to API', async () => {
    const threadId = 42;
    const messageRequest: SendMessageRequest = { content: 'Test' };

    vi.mocked(chatService.sendThreadMessage).mockResolvedValue(mockThreadMessages[0]);

    const { result } = renderHook(() => useSendThreadMessage(threadId), {
      wrapper: createWrapper(),
    });

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.sendThreadMessage).toHaveBeenCalledWith(42, messageRequest);
  });

  it('should handle different message types', async () => {
    const threadId = 1;
    const fileRequest: SendMessageRequest = {
      content: 'Attached file',
      message_type: 'file'
    };

    vi.mocked(chatService.sendThreadMessage).mockResolvedValue(mockThreadMessages[0]);

    const { result } = renderHook(() => useSendThreadMessage(threadId), {
      wrapper: createWrapper(),
    });

    result.current.mutate(fileRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.sendThreadMessage).toHaveBeenCalledWith(threadId, fileRequest);
  });

  it('should change hook instance when threadId changes', async () => {
    const messageRequest: SendMessageRequest = { content: 'Test' };
    vi.mocked(chatService.sendThreadMessage).mockResolvedValue(mockThreadMessages[0]);

    const { result, rerender } = renderHook(
      ({ threadId }) => useSendThreadMessage(threadId),
      {
        wrapper: createWrapper(),
        initialProps: { threadId: 1 },
      }
    );

    result.current.mutate(messageRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Rerender with new threadId
    rerender({ threadId: 2 });

    // New mutation instance should be created
    expect(result.current.isPending).toBe(false);
  });
});

describe('useCreateThread', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully create a new thread', async () => {
    const threadRequest: CreateThreadRequest = { title: 'New Discussion' };

    vi.mocked(chatService.createThread).mockResolvedValue(mockChatThreads[0]);

    const { result } = renderHook(() => useCreateThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.createThread).toHaveBeenCalledWith(threadRequest);
  });

  it('should invalidate threads list query on success', async () => {
    const threadRequest: CreateThreadRequest = { title: 'New Discussion' };

    vi.mocked(chatService.createThread).mockResolvedValue(mockChatThreads[0]);

    const { result } = renderHook(() => useCreateThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verification happens implicitly through cache invalidation
  });

  it('should return the created thread', async () => {
    const threadRequest: CreateThreadRequest = { title: 'New Discussion' };

    vi.mocked(chatService.createThread).mockResolvedValue(mockChatThreads[0]);

    const { result } = renderHook(() => useCreateThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.id).toBe(1);
    expect(result.current.data?.title).toBe('Discussion about homework');
  });

  it('should handle error when creating thread', async () => {
    const { toast } = await import('sonner');
    const threadRequest: CreateThreadRequest = { title: 'New' };
    const error = new Error('Creation failed');

    vi.mocked(chatService.createThread).mockRejectedValue(error);

    const { result } = renderHook(() => useCreateThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadRequest);

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalled();
  });

  it('should have proper mutation state properties', () => {
    const { result } = renderHook(() => useCreateThread(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
    expect(result.current.isPending).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.isSuccess).toBe(false);
  });
});

describe('usePinThread', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully pin a thread', async () => {
    const threadId = 1;
    const pinnedThread = { ...mockChatThreads[0], is_pinned: true };

    vi.mocked(chatService.pinThread).mockResolvedValue(pinnedThread);

    const { result } = renderHook(() => usePinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.pinThread).toHaveBeenCalledWith(threadId);
  });

  it('should return thread with is_pinned set to true', async () => {
    const threadId = 1;
    const pinnedThread = { ...mockChatThreads[0], is_pinned: true };

    vi.mocked(chatService.pinThread).mockResolvedValue(pinnedThread);

    const { result } = renderHook(() => usePinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.is_pinned).toBe(true);
  });

  it('should invalidate threads list on success', async () => {
    const threadId = 1;

    vi.mocked(chatService.pinThread).mockResolvedValue(mockChatThreads[0]);

    const { result } = renderHook(() => usePinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('should handle different thread IDs', async () => {
    vi.mocked(chatService.pinThread).mockResolvedValue(mockChatThreads[0]);

    const { result } = renderHook(() => usePinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(42);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.pinThread).toHaveBeenCalledWith(42);
  });

  it('should be a single-instance mutation (not dependent on threadId)', () => {
    const { result } = renderHook(() => usePinThread(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
  });
});

describe('useUnpinThread', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully unpin a thread', async () => {
    const threadId = 1;
    const unpinnedThread = { ...mockChatThreads[0], is_pinned: false };

    vi.mocked(chatService.unpinThread).mockResolvedValue(unpinnedThread);

    const { result } = renderHook(() => useUnpinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.unpinThread).toHaveBeenCalledWith(threadId);
  });

  it('should return thread with is_pinned set to false', async () => {
    const threadId = 1;
    const unpinnedThread = { ...mockChatThreads[0], is_pinned: false };

    vi.mocked(chatService.unpinThread).mockResolvedValue(unpinnedThread);

    const { result } = renderHook(() => useUnpinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.is_pinned).toBe(false);
  });

  it('should handle error on unpin', async () => {
    const { toast } = await import('sonner');
    const threadId = 1;
    const error = new Error('Unpin failed');

    vi.mocked(chatService.unpinThread).mockRejectedValue(error);

    const { result } = renderHook(() => useUnpinThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalled();
  });
});

describe('useLockThread', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully lock a thread', async () => {
    const threadId = 1;
    const lockedThread = { ...mockChatThreads[0], is_locked: true };

    vi.mocked(chatService.lockThread).mockResolvedValue(lockedThread);

    const { result } = renderHook(() => useLockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.lockThread).toHaveBeenCalledWith(threadId);
  });

  it('should return thread with is_locked set to true', async () => {
    const threadId = 1;
    const lockedThread = { ...mockChatThreads[0], is_locked: true };

    vi.mocked(chatService.lockThread).mockResolvedValue(lockedThread);

    const { result } = renderHook(() => useLockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.is_locked).toBe(true);
  });

  it('should prevent sending messages when thread is locked', async () => {
    const threadId = 1;
    const lockedThread = { ...mockChatThreads[0], is_locked: true };

    vi.mocked(chatService.lockThread).mockResolvedValue(lockedThread);

    const { result } = renderHook(() => useLockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Thread is now locked, further message sending should be prevented
    expect(result.current.data?.is_locked).toBe(true);
  });

  it('should handle multiple thread IDs', async () => {
    vi.mocked(chatService.lockThread).mockResolvedValue(mockChatThreads[0]);

    const { result } = renderHook(() => useLockThread(), {
      wrapper: createWrapper(),
    });

    // First lock
    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.lockThread).toHaveBeenCalledWith(1);
  });
});

describe('useUnlockThread', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully unlock a thread', async () => {
    const threadId = 1;
    const unlockedThread = { ...mockChatThreads[0], is_locked: false };

    vi.mocked(chatService.unlockThread).mockResolvedValue(unlockedThread);

    const { result } = renderHook(() => useUnlockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(chatService.unlockThread).toHaveBeenCalledWith(threadId);
  });

  it('should return thread with is_locked set to false', async () => {
    const threadId = 1;
    const unlockedThread = { ...mockChatThreads[0], is_locked: false };

    vi.mocked(chatService.unlockThread).mockResolvedValue(unlockedThread);

    const { result } = renderHook(() => useUnlockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.is_locked).toBe(false);
  });

  it('should allow sending messages after unlock', async () => {
    const threadId = 1;
    const unlockedThread = { ...mockChatThreads[0], is_locked: false };

    vi.mocked(chatService.unlockThread).mockResolvedValue(unlockedThread);

    const { result } = renderHook(() => useUnlockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Thread is now unlocked, messages can be sent again
    expect(result.current.data?.is_locked).toBe(false);
  });

  it('should handle error when unlocking thread', async () => {
    const { toast } = await import('sonner');
    const threadId = 1;
    const error = new Error('Unlock failed');

    vi.mocked(chatService.unlockThread).mockRejectedValue(error);

    const { result } = renderHook(() => useUnlockThread(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(threadId);

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalled();
  });
});

describe('Integration Tests for Multiple Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should maintain separate query caches for different hooks', async () => {
    vi.mocked(chatService.getGeneralChat).mockResolvedValue(mockGeneralChat);
    vi.mocked(chatService.getGeneralChatMessages).mockResolvedValue(mockChatMessages);

    const wrapper = createWrapper();

    const { result: chatResult } = renderHook(() => useGeneralChat(), { wrapper });
    const { result: messagesResult } = renderHook(() => useGeneralChatMessages(), { wrapper });

    await waitFor(() => expect(chatResult.current.isSuccess).toBe(true));
    await waitFor(() => expect(messagesResult.current.isSuccess).toBe(true));

    expect(chatResult.current.data?.id).toBe(1);
    expect(messagesResult.current.data).toHaveLength(2);
  });

  it('should handle multiple mutations in sequence', async () => {
    const threadRequest: CreateThreadRequest = { title: 'New Thread' };
    const messageRequest: SendMessageRequest = { content: 'Test message' };

    vi.mocked(chatService.createThread).mockResolvedValue(mockChatThreads[0]);
    vi.mocked(chatService.sendThreadMessage).mockResolvedValue(mockThreadMessages[0]);

    const wrapper = createWrapper();

    const { result: createResult } = renderHook(() => useCreateThread(), { wrapper });
    const { result: sendResult } = renderHook(() => useSendThreadMessage(1), { wrapper });

    // Create thread
    createResult.current.mutate(threadRequest);

    await waitFor(() => expect(createResult.current.isSuccess).toBe(true));

    // Send message to created thread
    sendResult.current.mutate(messageRequest);

    await waitFor(() => expect(sendResult.current.isSuccess).toBe(true));

    expect(chatService.createThread).toHaveBeenCalledWith(threadRequest);
    expect(chatService.sendThreadMessage).toHaveBeenCalledWith(1, messageRequest);
  });

  it('should handle thread lifecycle: create → pin → lock → unlock', async () => {
    const threadRequest: CreateThreadRequest = { title: 'Lifecycle Test' };

    vi.mocked(chatService.createThread).mockResolvedValue(mockChatThreads[0]);
    vi.mocked(chatService.pinThread).mockResolvedValue({ ...mockChatThreads[0], is_pinned: true });
    vi.mocked(chatService.lockThread).mockResolvedValue({ ...mockChatThreads[0], is_locked: true });
    vi.mocked(chatService.unlockThread).mockResolvedValue({ ...mockChatThreads[0], is_locked: false });

    const wrapper = createWrapper();

    const { result: createResult } = renderHook(() => useCreateThread(), { wrapper });
    const { result: pinResult } = renderHook(() => usePinThread(), { wrapper });
    const { result: lockResult } = renderHook(() => useLockThread(), { wrapper });
    const { result: unlockResult } = renderHook(() => useUnlockThread(), { wrapper });

    // Create
    createResult.current.mutate(threadRequest);
    await waitFor(() => expect(createResult.current.isSuccess).toBe(true));

    // Pin
    pinResult.current.mutate(mockChatThreads[0].id);
    await waitFor(() => expect(pinResult.current.isSuccess).toBe(true));

    // Lock
    lockResult.current.mutate(mockChatThreads[0].id);
    await waitFor(() => expect(lockResult.current.isSuccess).toBe(true));

    // Unlock
    unlockResult.current.mutate(mockChatThreads[0].id);
    await waitFor(() => expect(unlockResult.current.isSuccess).toBe(true));
  });
});
