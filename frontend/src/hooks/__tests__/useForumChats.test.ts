import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useForumChats, useForumChatsWithRefresh } from '../useForumChats';
import { forumAPI } from '@/integrations/api/forumAPI';
import React from 'react';

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

describe('useForumChats - Edge Cases and Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // REGRESSION TEST: Bug fix from commit 0309b83
  // Issue: refetchOnMount was missing, causing chats not to load on component mount
  it('должен загружать данные при монтировании компонента (refetchOnMount: true)', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // Should immediately start loading
    expect(result.current.isLoading).toBe(true);

    // Wait for data to load
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Data should be available
    expect(result.current.data).toEqual(mockForumChats);
    expect(forumAPI.getForumChats).toHaveBeenCalled();
  });

  // REGRESSION TEST: Ensure refetchOnMount triggers on every component mount
  it('должен повторно загружать данные при повторном монтировании (refetchOnMount: true)', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    // First mount - create fresh wrapper
    const wrapper1 = createWrapper();
    const { result: result1, unmount: unmount1 } = renderHook(() => useForumChats(), {
      wrapper: wrapper1,
    });

    await waitFor(() => expect(result1.current.isSuccess).toBe(true));
    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(1);

    // Unmount
    unmount1();

    // Second mount - create new wrapper with fresh QueryClient
    const wrapper2 = createWrapper();
    const { result: result2 } = renderHook(() => useForumChats(), {
      wrapper: wrapper2,
    });

    await waitFor(() => expect(result2.current.isSuccess).toBe(true));

    // API should be called again due to refetchOnMount
    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(2);
  });

  // Test scenario: User with no chats
  it('должен возвращать пустой список для пользователя без чатов', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
    expect(result.current.data).toHaveLength(0);
  });

  // Test scenario: Network error
  it('должен обрабатывать ошибку сети', async () => {
    const networkError = new Error('Network error: Failed to fetch');
    vi.mocked(forumAPI.getForumChats).mockRejectedValue(networkError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // With retry: 2, wait longer for all retries to fail
    await waitFor(
      () => expect(result.current.isError).toBe(true),
      { timeout: 5000 }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  // Test scenario: Server error (500)
  it('должен обрабатывать ошибку сервера (500)', async () => {
    const serverError = new Error('Internal Server Error');
    vi.mocked(forumAPI.getForumChats).mockRejectedValue(serverError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.isError).toBe(true),
      { timeout: 5000 }
    );

    expect(result.current.error).toBeDefined();
  });

  // Test scenario: Authentication error
  it('должен обрабатывать ошибку аутентификации (401)', async () => {
    const authError = new Error('Unauthorized: Token expired');
    vi.mocked(forumAPI.getForumChats).mockRejectedValue(authError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.isError).toBe(true),
      { timeout: 5000 }
    );

    expect(result.current.error?.message).toContain('Unauthorized');
  });

  // Test scenario: Timeout
  it('должен обрабатывать timeout при запросе', async () => {
    const timeoutError = new Error('Request timeout');
    vi.mocked(forumAPI.getForumChats).mockRejectedValue(timeoutError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.isError).toBe(true),
      { timeout: 5000 }
    );

    expect(result.current.error?.message).toContain('timeout');
  });

  // Test scenario: Active chats with proper attributes
  it('должен возвращать список активных чатов с правильными атрибутами', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chats = result.current.data || [];
    chats.forEach((chat) => {
      // All chats should have required attributes
      expect(chat.id).toBeDefined();
      expect(typeof chat.id).toBe('number');
      expect(chat.name).toBeDefined();
      expect(typeof chat.name).toBe('string');
      expect(chat.type).toBeDefined();
      expect(['forum_subject', 'forum_tutor']).toContain(chat.type);
      expect(chat.participants).toBeDefined();
      expect(Array.isArray(chat.participants)).toBe(true);
      expect(chat.unread_count).toBeDefined();
      expect(typeof chat.unread_count).toBe('number');
      expect(chat.is_active).toBeDefined();
      expect(typeof chat.is_active).toBe('boolean');
    });
  });

  // Test scenario: Inactive chats
  it('должен включать неактивные чаты в список', async () => {
    const inactiveChat = { ...mockForumChats[0], is_active: false };
    vi.mocked(forumAPI.getForumChats).mockResolvedValue([inactiveChat]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data?.[0];
    expect(chat?.is_active).toBe(false);
  });

  // Test scenario: Multiple retries on failure
  it('должен повторять запрос дважды при сбое (retry: 2)', async () => {
    vi.mocked(forumAPI.getForumChats)
      .mockRejectedValueOnce(new Error('Fail 1'))
      .mockRejectedValueOnce(new Error('Fail 2'))
      .mockResolvedValueOnce(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false);
      },
      { timeout: 5000 }
    );

    // Should succeed after retries
    expect(result.current.isSuccess).toBe(true);
    expect(result.current.data).toEqual(mockForumChats);
    // API should be called 3 times (2 retries + 1 success)
    expect(forumAPI.getForumChats).toHaveBeenCalledTimes(3);
  });

  // Test scenario: Window focus behavior
  it('должен не загружать при получении фокуса окна (refetchOnWindowFocus: false)', async () => {
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const initialCallCount = vi.mocked(forumAPI.getForumChats).mock.calls.length;

    // Simulate window focus event
    const focusEvent = new Event('focus');
    window.dispatchEvent(focusEvent);

    // Wait a moment
    await new Promise((resolve) => setTimeout(resolve, 100));

    // API should not be called again (refetchOnWindowFocus: false)
    const finalCallCount = vi.mocked(forumAPI.getForumChats).mock.calls.length;
    expect(finalCallCount).toBe(initialCallCount);
  });

  // Test scenario: Partial data response
  it('должен обрабатывать случай когда backend вернул результаты с пустыми полями', async () => {
    const partialChats = [
      {
        ...mockForumChats[0],
        last_message: undefined, // Missing last_message
      },
    ];
    vi.mocked(forumAPI.getForumChats).mockResolvedValue(partialChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data?.[0];
    expect(chat?.last_message).toBeUndefined();
    // Chat should still be valid
    expect(chat?.id).toBe(1);
  });
});
