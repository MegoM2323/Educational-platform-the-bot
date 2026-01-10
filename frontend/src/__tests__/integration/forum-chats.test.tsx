/**
 * Integration tests for Forum Chats functionality
 *
 * Tests the full stack of forum chat loading with mock API
 * Tests the behavior of useForumChats hook with actual TanStack Query setup
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useForumChats, useForumChatsWithRefresh } from '@/hooks/useForumChats';
import { chatAPI, Chat } from '@/integrations/api/chatAPI';

// Mock the chatAPI
vi.mock('@/integrations/api/chatAPI', () => ({
  chatAPI: {
    getChatList: vi.fn(),
  },
}));

const mockChats: Chat[] = [
  {
    id: 1,
    name: 'Mathematics - Student ↔ Teacher',
    type: 'forum_subject',
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
    name: 'English - Student ↔ Tutor',
    type: 'forum_tutor',
    subject: undefined,
    participants: [
      { id: 1, full_name: 'John Student', role: 'student' },
      { id: 20, full_name: 'Mark Tutor', role: 'tutor' },
    ],
    unread_count: 0,
    last_message: undefined,
    created_at: '2025-01-12T10:00:00Z',
    updated_at: '2025-01-12T10:00:00Z',
    is_active: true,
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('Forum Chats Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Test 1: Hook loads chats successfully
  it('должен загружать чаты и предоставлять их через хук', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockChats);
    expect(result.current.data).toHaveLength(2);
  });

  // Test 2: Empty chats scenario
  it('должен обрабатывать пустой список чатов', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue([]);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
    expect(result.current.data).toHaveLength(0);
  });

  // Test 3: Error handling (after retries exhaust)
  it('должен обрабатывать ошибку при загрузке чатов после всех попыток', async () => {
    const errorMessage = 'Failed to fetch chats';
    vi.mocked(chatAPI.getChatList).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // With retry: 2, wait longer for all retries to fail
    await waitFor(
      () => expect(result.current.isError).toBe(true),
      { timeout: 5000 }
    );

    expect(result.current.error?.message).toContain(errorMessage);
  });

  // Test 4: Loading state
  it('должен показывать состояние загрузки', () => {
    vi.mocked(chatAPI.getChatList).mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  // Test 5: Verify API call is made
  it('должен вызывать chatAPI.getChatList при монтировании', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

    renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(vi.mocked(chatAPI.getChatList)).toHaveBeenCalledTimes(1);
    });
  });

  // Test 6: Refresh chats functionality
  it('должен загружать новые данные при вызове refreshChats', async () => {
    const initialChats = [mockChats[0]];
    const updatedChats = mockChats;

    vi.mocked(chatAPI.getChatList)
      .mockResolvedValueOnce(initialChats)
      .mockResolvedValueOnce(updatedChats);

    const { result } = renderHook(() => useForumChatsWithRefresh(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);

    // Trigger refresh
    result.current.refreshChats();

    await waitFor(() => {
      expect(result.current.data).toHaveLength(2);
    });

    expect(vi.mocked(chatAPI.getChatList)).toHaveBeenCalledTimes(2);
  });

  // Test 7: Verify chat structure
  it('должен предоставлять чаты с правильной структурой', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data?.[0];
    expect(chat).toBeDefined();
    expect(chat?.id).toBe(1);
    expect(chat?.name).toBe('Mathematics - Student ↔ Teacher');
    expect(chat?.type).toBe('forum_subject');
    expect(chat?.subject?.name).toBe('Mathematics');
    expect(chat?.participants).toHaveLength(2);
    expect(chat?.unread_count).toBe(3);
    expect(chat?.is_active).toBe(true);
  });

  // Test 8: Different chat types (forum_subject vs forum_tutor)
  it('должен различать типы чатов (forum_subject и forum_tutor)', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

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

  // Test 9: Unread count handling
  it('должен правильно отображать количество непрочитанных сообщений', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chats = result.current.data || [];
    expect(chats[0].unread_count).toBe(3);
    expect(chats[1].unread_count).toBe(0);
  });

  // Test 10: Last message information
  it('должен включать информацию о последнем сообщении в чате', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chat = result.current.data?.[0];
    expect(chat?.last_message).toBeDefined();
    expect(chat?.last_message?.content).toBe('Hello, how are you?');
    expect(chat?.last_message?.sender.full_name).toBe('Jane Teacher');
  });

  // Test 11: Active/inactive chats
  it('должен обрабатывать как активные, так и неактивные чаты', async () => {
    const mixedChats: ForumChat[] = [
      ...mockChats,
      {
        id: 3,
        name: 'Inactive Chat',
        type: 'forum_subject',
        subject: { id: 3, name: 'Inactive' },
        participants: [],
        unread_count: 0,
        last_message: undefined,
        created_at: '2025-01-10T10:00:00Z',
        updated_at: '2025-01-10T10:00:00Z',
        is_active: false,
      },
    ];

    vi.mocked(chatAPI.getChatList).mockResolvedValue(mixedChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const chats = result.current.data || [];
    expect(chats).toHaveLength(3);
    expect(chats.filter((c) => c.is_active)).toHaveLength(2);
    expect(chats.filter((c) => !c.is_active)).toHaveLength(1);
  });

  // Test 12: Regression test - refetchOnMount behavior
  it('должен загружать чаты при монтировании компонента', async () => {
    vi.mocked(chatAPI.getChatList).mockResolvedValue(mockChats);

    const { result } = renderHook(() => useForumChats(), {
      wrapper: createWrapper(),
    });

    // Should immediately be loading
    expect(result.current.isLoading).toBe(true);

    // Wait for data to load
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // API should have been called
    expect(vi.mocked(chatAPI.getChatList)).toHaveBeenCalled();
    expect(result.current.data).toBeDefined();
  });
});
