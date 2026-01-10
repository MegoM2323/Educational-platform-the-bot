import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useForumChats, useForumChatsWithRefresh } from '../useForumChats';
import { chatAPI } from '@/integrations/api/chatAPI';
import React from 'react';

// Mock chatAPI
vi.mock('@/integrations/api/chatAPI', () => ({
  chatAPI: {
    getChatList: vi.fn(),
    getContacts: vi.fn(),
    createOrGetChat: vi.fn(),
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
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(result.current.chats).toEqual(mockForumChats);
    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);
  });

  it('должен возвращать корректную структуру данных чата', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([mockForumChats[0]]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const chat = result.current.chats?.[0];
    expect(chat).toBeDefined();
    expect(chat?.id).toBe(1);
    expect(chat?.name).toBe('Mathematics - Student ↔ Teacher');
    expect(chat?.type).toBe('forum_subject');
    expect(chat?.participants).toHaveLength(2);
    expect(chat?.unread_count).toBe(3);
    expect(chat?.subject?.name).toBe('Mathematics');
  });

  it('должен показывать состояние загрузки', () => {
    vi.mocked(chatAPI.getChatList).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoadingChats).toBe(true);
    expect(result.current.chats).toEqual([]); // Hook returns empty array by default
  });


  it('должен правильно устанавливать staleTime в 5 минут', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result, rerender } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);

    // Re-render immediately - should use cache (staleTime 300s = 5 minutes)
    rerender();

    // API should not be called again
    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);
  });

  it('должен поддерживать retry с 2 попытками', async () => {
    // First call fails, second succeeds
    vi.mocked(chatAPI.getChatList)
      .mockRejectedValueOnce(new Error('First fail'))
      .mockResolvedValueOnce(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // Wait for the query to settle after retries
    await waitFor(() => {
      expect(result.current.isLoadingChats).toBe(false);
    }, { timeout: 3000 });

    // Should succeed after retry
    expect(result.current.isLoadingChats).toBe(false);
    expect(result.current.chats).toEqual(mockForumChats);
  });

  it('должен отличать чаты по типам (forum_subject, forum_tutor)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const chats = result.current.chats || [];
    const subjectChats = chats.filter((c) => c.type === 'forum_subject');
    const tutorChats = chats.filter((c) => c.type === 'forum_tutor');

    expect(subjectChats).toHaveLength(1);
    expect(tutorChats).toHaveLength(1);
  });

  it('должен включать информацию об непрочитанных сообщениях', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const chats = result.current.chats || [];
    expect(chats[0].unread_count).toBe(3);
    expect(chats[1].unread_count).toBe(0);
  });

  it('должен включать последнее сообщение в чате', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([mockForumChats[0]]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const chat = result.current.chats?.[0];
    expect(chat?.last_message).toBeDefined();
    expect(chat?.last_message?.content).toBe('Hello, how are you?');
    expect(chat?.last_message?.sender.full_name).toBe('Jane Teacher');
  });

  it('должен обновлять данные при refetch (через useForumChatsWithRefresh)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);

    // Trigger refetch via refreshChats
    result.current.refreshChats();

    await waitFor(() => {
      expect(chatAPI.getChatList).toHaveBeenCalledTimes(2);
    });
  });

  it('должен кешировать результаты между вызовами', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    // Use same wrapper for cache sharing
    const wrapper = createWrapper();

    const { result: result1 } = renderHook(() => useForumChats(), { wrapper });

    await waitFor(() => expect(result1.current.isLoadingChats).toBe(false));

    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);

    const { result: result2 } = renderHook(() => useForumChats(), { wrapper });

    await waitFor(() => expect(result2.current.isLoadingChats).toBe(false));

    // Should still be 1 call because of caching with same QueryClient
    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);
  });
});

describe('useForumChatsWithRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен предоставлять функцию refreshChats для инвалидации кеша', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);

    // Call refreshChats
    result.current.refreshChats();

    // After refresh, should trigger a new API call
    await waitFor(() => {
      expect(chatAPI.getChatList).toHaveBeenCalledTimes(2);
    });
  });

  it('должен включать все свойства базового хука useForumChats', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Should have all original query properties
    expect(result.current.chats).toBeDefined();
    expect(result.current.isLoadingChats).toBe(false);
    expect(result.current.isLoadingChats).toBe(false);
    expect(result.current.chatsError).toBeNull();

    // Plus the refresh function
    expect(typeof result.current.refreshChats).toBe('function');
  });

  it('должен успешно обновлять данные после refreshChats', async () => {
    const initialChats = [mockForumChats[0]];
    const updatedChats = mockForumChats;

    vi.mocked(chatAPI.getChatList)
      .mockResolvedValueOnce(initialChats)
      .mockResolvedValueOnce(updatedChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(result.current.chats).toHaveLength(1);

    // Refresh and wait for new data
    result.current.refreshChats();

    await waitFor(() => {
      expect(result.current.chats).toHaveLength(2);
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
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // Should immediately start loading
    expect(result.current.isLoadingChats).toBe(true);

    // Wait for data to load
    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Data should be available
    expect(result.current.chats).toEqual(mockForumChats);
    expect(chatAPI.getChatList).toHaveBeenCalled();
  });

  // REGRESSION TEST: Ensure refetchOnMount triggers on every component mount
  it('должен повторно загружать данные при повторном монтировании (refetchOnMount: true)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    // First mount - create fresh wrapper
    const wrapper1 = createWrapper();
    const { result: result1, unmount: unmount1 } = renderHook(() => useForumChats(), {
      wrapper: wrapper1,
    });

    await waitFor(() => expect(result1.current.isLoadingChats).toBe(false));
    expect(chatAPI.getChatList).toHaveBeenCalledTimes(1);

    // Unmount
    unmount1();

    // Second mount - create new wrapper with fresh QueryClient
    const wrapper2 = createWrapper();
    const { result: result2 } = renderHook(() => useForumChats(), {
      wrapper: wrapper2,
    });

    await waitFor(() => expect(result2.current.isLoadingChats).toBe(false));

    // API should be called again due to refetchOnMount
    expect(chatAPI.getChatList).toHaveBeenCalledTimes(2);
  });

  // Test scenario: User with no chats
  it('должен возвращать пустой список для пользователя без чатов', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(result.current.chats).toEqual([]);
    expect(result.current.chats).toHaveLength(0);
  });

  // Test scenario: Network error
  it('должен обрабатывать ошибку сети', async () => {
    const networkError = new Error('Network error: Failed to fetch');
    vi.mocked(chatAPI.getChatList).mockRejectedValue(networkError);
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // With retry: 2, wait longer for all retries to fail
    await waitFor(
      () => expect(result.current.chatsError).not.toBeNull(),
      { timeout: 5000 }
    );

    expect(result.current.isLoadingChats).toBe(false);
    expect(result.current.chatsError).toBeDefined();
    expect(result.current.chats).toEqual([]); // Hook returns empty array on error
  });

  // Test scenario: Server error (500)
  it('должен обрабатывать ошибку сервера (500)', async () => {
    const serverError = new Error('Internal Server Error');
    vi.mocked(chatAPI.getChatList).mockRejectedValue(serverError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.chatsError).not.toBeNull(),
      { timeout: 5000 }
    );

    expect(result.current.chatsError).toBeDefined();
  });

  // Test scenario: Authentication error
  it('должен обрабатывать ошибку аутентификации (401)', async () => {
    const authError = new Error('Unauthorized: Token expired');
    vi.mocked(chatAPI.getChatList).mockRejectedValue(authError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.chatsError).not.toBeNull(),
      { timeout: 5000 }
    );

    expect(result.current.chatsError?.message).toContain('Unauthorized');
  });

  // Test scenario: Timeout
  it('должен обрабатывать timeout при запросе', async () => {
    const timeoutError = new Error('Request timeout');
    vi.mocked(chatAPI.getChatList).mockRejectedValue(timeoutError);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.chatsError).not.toBeNull(),
      { timeout: 5000 }
    );

    expect(result.current.chatsError?.message).toContain('timeout');
  });

  // Test scenario: Active chats with proper attributes
  it('должен возвращать список активных чатов с правильными атрибутами', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const chats = result.current.chats || [];
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
    vi.mocked(chatAPI.getChatList).mockResolvedValue([inactiveChat]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const chat = result.current.chats?.[0];
    expect(chat?.is_active).toBe(false);
  });

  // Test scenario: Multiple retries on failure
  it('должен повторять запрос дважды при сбое (retry: 2)', async () => {
    vi.mocked(chatAPI.getChatList)
      .mockRejectedValueOnce(new Error('Fail 1'))
      .mockRejectedValueOnce(new Error('Fail 2'))
      .mockResolvedValueOnce(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isLoadingChats).toBe(false);
      },
      { timeout: 5000 }
    );

    // Should succeed after retries
    expect(result.current.isLoadingChats).toBe(false);
    expect(result.current.chats).toEqual(mockForumChats);
    // API should be called 3 times (2 retries + 1 success)
    expect(chatAPI.getChatList).toHaveBeenCalledTimes(3);
  });

  // Test scenario: Window focus behavior
  it('должен не загружать при получении фокуса окна (refetchOnWindowFocus: false)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockForumChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    const initialCallCount = vi.mocked(chatAPI.getChatList).mock.calls.length;

    // Simulate window focus event
    const focusEvent = new Event('focus');
    window.dispatchEvent(focusEvent);

    // Wait a moment
    await new Promise((resolve) => setTimeout(resolve, 100));

    // API should not be called again (refetchOnWindowFocus: false)
    const finalCallCount = vi.mocked(chatAPI.getChatList).mock.calls.length;
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
    vi.mocked(chatAPI.getChatList).mockResolvedValue(partialChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.chats).toBeDefined());

    const chat = result.current.chats[0];
    expect(chat?.last_message).toBeUndefined();
    // Chat should still be valid
    expect(chat?.id).toBe(1);
  });
});

// Mock data for available contacts
const mockAvailableContacts = [
  {
    id: 10,
    email: 'teacher@example.com',
    first_name: 'Jane',
    last_name: 'Teacher',
    role: 'teacher' as const,
    avatar: undefined,
    subject: { id: 1, name: 'Mathematics' },
    has_active_chat: true,
    chat_id: 1,
  },
  {
    id: 20,
    email: 'tutor@example.com',
    first_name: 'Mark',
    last_name: 'Tutor',
    role: 'tutor' as const,
    avatar: undefined,
    subject: undefined,
    has_active_chat: false,
    chat_id: undefined,
  },
];

const mockChatDetail = {
  id: 99,
  room_id: 'chat_room_99',
  type: 'forum_subject' as const,
  other_user: {
    id: 10,
    email: 'teacher@example.com',
    first_name: 'Jane',
    last_name: 'Teacher',
    role: 'teacher' as const,
  },
  created_at: '2025-12-14T10:30:00Z',
  name: 'Mathematics - Student ↔ Teacher',
  last_message: undefined,
  unread_count: 0,
};

describe('useForumChats - Available Contacts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно загружать список доступных контактов', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingContacts).toBe(false));

    expect(result.current.availableContacts).toEqual(mockAvailableContacts);
    expect(chatAPI.getContacts).toHaveBeenCalledTimes(1);
  });

  it('должен кешировать контакты на 5 минут (staleTime)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);

    const wrapper = createWrapper();
    const { result, rerender } = renderHook(() => useForumChats(), { wrapper });

    await waitFor(() => expect(result.current.isLoadingContacts).toBe(false));

    expect(chatAPI.getContacts).toHaveBeenCalledTimes(1);

    // Re-render immediately - should use cache (staleTime 5 minutes)
    rerender();

    // API should not be called again
    expect(chatAPI.getContacts).toHaveBeenCalledTimes(1);
  });

  it('должен показывать состояние загрузки для контактов', () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoadingContacts).toBe(true);
    expect(result.current.availableContacts).toEqual([]);
  });

  it('должен обрабатывать ошибку при загрузке контактов', async () => {
    const error = new Error('Failed to fetch contacts');
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockRejectedValue(error);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.contactsError).toBeDefined());

    expect(result.current.contactsError).toBeDefined();
    expect(result.current.availableContacts).toEqual([]);
  });

  it('должен отличать контакты с активными чатами от контактов без чатов', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingContacts).toBe(false));

    const contacts = result.current.availableContacts;
    const withActiveChat = contacts.filter((c) => c.has_active_chat);
    const withoutActiveChat = contacts.filter((c) => !c.has_active_chat);

    expect(withActiveChat).toHaveLength(1);
    expect(withActiveChat[0].chat_id).toBe(1);
    expect(withoutActiveChat).toHaveLength(1);
    expect(withoutActiveChat[0].chat_id).toBeUndefined();
  });

  it('должен возвращать пустой список для пользователя без доступных контактов', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingContacts).toBe(false));

    expect(result.current.availableContacts).toEqual([]);
    expect(result.current.availableContacts).toHaveLength(0);
  });
});

describe('useForumChats - Initiate Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно инициировать новый чат', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockResolvedValue({
      success: true,
      chat: mockChatDetail,
      created: true,
    });

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Initiate chat
    const chatResponse = await result.current.initiateChat(10, 1);

    expect(chatResponse.success).toBe(true);
    expect(chatResponse.chat.id).toBe(99);
    expect(chatResponse.created).toBe(true);
    expect(chatAPI.createOrGetChat).toHaveBeenCalledWith(10, 1);
  });

  it('должен инициировать чат без subject_id (для FORUM_TUTOR)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockResolvedValue({
      success: true,
      chat: { ...mockChatDetail, type: 'FORUM_TUTOR' },
      created: true,
    });

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Initiate chat without subject_id
    const chatResponse = await result.current.initiateChat(20);

    expect(chatResponse.success).toBe(true);
    expect(chatAPI.createOrGetChat).toHaveBeenCalledWith(20, undefined);
  });

  it('должен показывать состояние загрузки при инициации чата', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Start initiate chat (don't await)
    result.current.initiateChat(10, 1);

    await waitFor(() => expect(result.current.isInitiatingChat).toBe(true));
  });

  it('должен обрабатывать ошибку при инициации чата', async () => {
    const error = new Error('Unauthorized to chat with this user');
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockRejectedValue(error);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Initiate chat and expect error
    await expect(result.current.initiateChat(10, 1)).rejects.toThrow(
      'Unauthorized to chat with this user'
    );

    await waitFor(() => expect(result.current.initiateError).toBeDefined());
  });

  it('должен инвалидировать список чатов после успешной инициации', async () => {
    vi.mocked(chatAPI.getChatList)
      .mockResolvedValueOnce([]) // Initial load
      .mockResolvedValueOnce([...mockForumChats]); // After initiate
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockResolvedValue({
      success: true,
      chat: mockChatDetail,
      created: true,
    });

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    expect(result.current.chats).toHaveLength(0);

    // Initiate chat
    await result.current.initiateChat(10, 1);

    // Wait for chats to refetch
    await waitFor(() => {
      expect(result.current.chats.length).toBeGreaterThan(0);
    });

    expect(chatAPI.getChatList).toHaveBeenCalledTimes(2);
  });

  it('должен инвалидировать список доступных контактов после успешной инициации', async () => {
    const updatedContacts = [
      { ...mockAvailableContacts[0], has_active_chat: true, chat_id: 99 },
      mockAvailableContacts[1],
    ];

    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts)
      .mockResolvedValueOnce(mockAvailableContacts) // Initial load
      .mockResolvedValueOnce(updatedContacts); // After initiate
    vi.mocked(chatAPI.createOrGetChat).mockResolvedValue({
      success: true,
      chat: mockChatDetail,
      created: true,
    });

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingContacts).toBe(false));

    const initialContacts = result.current.availableContacts;
    expect(initialContacts[0].has_active_chat).toBe(true);

    // Initiate chat
    await result.current.initiateChat(10, 1);

    // Wait for contacts to refetch
    await waitFor(() => {
      expect(chatAPI.getContacts).toHaveBeenCalledTimes(2);
    });
  });

  it('должен возвращать существующий чат если он уже создан (idempotent)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockResolvedValue({
      success: true,
      chat: mockChatDetail,
      created: false, // Chat already exists
    });

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Initiate chat
    const chatResponse = await result.current.initiateChat(10, 1);

    expect(chatResponse.success).toBe(true);
    expect(chatResponse.created).toBe(false);
    expect(chatResponse.chat.id).toBe(99);
  });

  it('должен очищать ошибку инициации чата через clearInitiateError', async () => {
    const error = new Error('Network error');
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockRejectedValue(error);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Initiate chat and expect error
    await expect(result.current.initiateChat(10, 1)).rejects.toThrow('Network error');

    await waitFor(() => expect(result.current.initiateError).toBeDefined());

    // Clear error
    result.current.clearInitiateError();

    await waitFor(() => expect(result.current.initiateError).toBeNull());
  });

  it('должен возвращать room_id для WebSocket подключения', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);
    vi.mocked(chatAPI.getContacts).mockResolvedValue(mockAvailableContacts);
    vi.mocked(chatAPI.createOrGetChat).mockResolvedValue({
      success: true,
      chat: mockChatDetail,
      created: true,
    });

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoadingChats).toBe(false));

    // Initiate chat
    const chatResponse = await result.current.initiateChat(10, 1);

    expect(chatResponse.chat.room_id).toBe('chat_room_99');
  });
});
