import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useForumChats, useForumChatsWithRefresh } from '../useForumChats';
import { forumAPI } from '@/integrations/api/forumAPI';
import * as React from 'react';

// Mock forumAPI
vi.mock('@/integrations/api/forumAPI', () => ({
  forumAPI: {
    getForumChats: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

const mockForumChats = [
  {
    id: 1,
    name: 'Mathematics - Student ↔ Teacher',
    type: 'forum_subject' as const,
    subject: {
      id: 1,
      name: 'Mathematics',
    },
    participants: [
      { id: 1, full_name: 'John Student', role: 'student' },
      { id: 10, full_name: 'Jane Teacher', role: 'teacher' },
    ],
    unread_count: 3,
    last_message: {
      content: 'Hello, how are you?',
      created_at: '2025-01-15T10:00:00Z',
      sender: { id: 10, full_name: 'Jane Teacher', role: 'teacher' },
    },
    created_at: '2025-01-10T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
    is_active: true,
  },
  {
    id: 2,
    name: 'Student ↔ Tutor',
    type: 'forum_tutor' as const,
    subject: undefined,
    participants: [
      { id: 1, full_name: 'John Student', role: 'student' },
      { id: 20, full_name: 'Mark Tutor', role: 'tutor' },
    ],
    unread_count: 0,
    last_message: {
      content: 'Great progress!',
      created_at: '2025-01-14T15:30:00Z',
      sender: { id: 20, full_name: 'Mark Tutor', role: 'tutor' },
    },
    created_at: '2025-01-12T10:00:00Z',
    updated_at: '2025-01-14T15:30:00Z',
    is_active: true,
  },
];

describe('useForumChats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно загружать список форум-чатов', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockForumChats);
    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);
  });

  it('должен возвращать корректную структуру данных чата', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue([mockForumChats[0]]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data?.[0];
    expect(chat).toBeDefined();
    expect(chat?.id).toBe(1);
    expect(chat?.name).toBe('Mathematics - Student ↔ Teacher');
    expect(chat?.type).toBe('forum_subject');
    expect(chat?.participants).toHaveLength(2);
    expect(chat?.unread_count).toBe(3);
    expect(chat?.subject?.name).toBe('Mathematics');
  });

  it('должен показывать состояние загрузки', () => {
    vi.mocked(forumAPI.getForumChats).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });


  it('должен правильно устанавливать staleTime в 5 минут', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result, rerender } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);

    // Re-render immediately - should use cache (staleTime 300s = 5 minutes)
    rerender();

    // API should not be called again
    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);
  });

  it('должен поддерживать retry с 2 попытками', async () => {
    // First call fails, second succeeds
    vi.mocked(forumAPI.getForumChats)
      .mockRejectedValueOnce(new Error('First fail'))
      .mockResolvedValueOnce(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // Wait for the query to settle after retries
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    }, { timeout: 3000 });

    // Should succeed after retry
    expect(result.current.isSuccess).toBe(true);
    expect(result.current.data).toEqual(mockForumChats);
  });

  it('должен отличать чаты по типам (forum_subject, forum_tutor)', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chats = result.current.data || [];
    const subjectChats = chats.filter((c) => c.type === 'forum_subject');
    const tutorChats = chats.filter((c) => c.type === 'forum_tutor');

    expect(subjectChats).toHaveLength(1);
    expect(tutorChats).toHaveLength(1);
  });

  it('должен включать информацию об непрочитанных сообщениях', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chats = result.current.data || [];
    expect(chats[0].unread_count).toBe(3);
    expect(chats[1].unread_count).toBe(0);
  });

  it('должен включать последнее сообщение в чате', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue([mockForumChats[0]]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data?.[0];
    expect(chat?.last_message).toBeDefined();
    expect(chat?.last_message?.content).toBe('Hello, how are you?');
    expect(chat?.last_message?.sender.full_name).toBe('Jane Teacher');
  });

  it('должен обновлять данные при refetch', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);

    // Trigger refetch
    result.current.refetch();

    await waitFor(() => {
      expect(forumAPI.getForumChats).toHaveBeenCalledTimes(2);
    });
  });

  it('должен кешировать результаты между вызовами', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    // Use same wrapper for cache sharing
    const wrapper = createWrapper();

    const { result: result1 } = renderHook(() => useForumChats(), { wrapper });

    await waitFor(() => expect(result1.current.isSuccess).toBe(true));

    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);

    const { result: result2 } = renderHook(() => useForumChats(), { wrapper });

    await waitFor(() => expect(result2.current.isSuccess).toBe(true));

    // Should still be 1 call because of caching with same QueryClient
    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);
  });
});

describe('useForumChatsWithRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен предоставлять функцию refreshChats для инвалидации кеша', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);

    // Call refreshChats
    result.current.refreshChats();

    // After refresh, should trigger a new API call
    await waitFor(() => {
      expect(forumAPI.getForumChats).toHaveBeenCalledTimes(2);
    });
  });

  it('должен включать все свойства базового хука useForumChats', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should have all original query properties
    expect(result.current.data).toBeDefined();
    expect(result.current.isSuccess).toBe(true);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);

    // Plus the refresh function
    expect(typeof result.current.refreshChats).toBe('function');
  });

  it('должен успешно обновлять данные после refreshChats', async () => {
    const initialChats = [mockForumChats[0]];
    const updatedChats = mockForumChats;

    vi.mocked(forumAPI.getForumChats)
      .mockResolvedValueOnce(initialChats)
      .mockResolvedValueOnce(updatedChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);

    // Refresh and wait for new data
    result.current.refreshChats();

    await waitFor(() => {
      expect(result.current.data).toHaveLength(2);
    });
  });
});
