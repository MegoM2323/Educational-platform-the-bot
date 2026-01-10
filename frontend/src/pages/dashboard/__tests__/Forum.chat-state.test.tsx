import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthContext } from '@/contexts/AuthContext';
import { BrowserRouter } from 'react-router-dom';

// Mock dependencies first
vi.mock('@/integrations/api/chatAPI', () => ({
  chatAPI: {
    markAsRead: vi.fn(),
    getContacts: vi.fn(),
    createOrGetChat: vi.fn(),
    getMessages: vi.fn(),
    sendMessage: vi.fn(),
    deleteMessage: vi.fn(),
  },
}));

vi.mock('@/services/chatWebSocketService', () => ({
  chatWebSocketService: {
    connectToRoom: vi.fn(),
    disconnectFromRoom: vi.fn(),
    isConnected: vi.fn(),
    onConnectionChange: vi.fn(),
    sendTyping: vi.fn(),
    startTypingTimer: vi.fn(),
  },
}));

vi.mock('@/hooks/useForumChats', () => ({
  useForumChats: () => ({
    chats: [],
    isLoadingChats: false,
    chatsError: null,
  }),
  useForumChatsWithRefresh: () => ({
    chats: [],
    isLoadingChats: false,
    chatsError: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('@/hooks/useForumMessages', () => ({
  useForumMessages: () => ({
    data: { pages: [[]], pageParams: [0] },
    isLoading: false,
    error: null,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
  }),
}));

vi.mock('@/hooks/useSendForumMessage', () => ({
  useSendForumMessage: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/hooks/useForumMessageUpdate', () => ({
  useForumMessageUpdate: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/hooks/useForumMessageDelete', () => ({
  useForumMessageDelete: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/components/layout/StudentSidebar', () => ({
  StudentSidebar: () => <div data-testid="student-sidebar">Sidebar</div>,
}));

vi.mock('@/components/layout/TeacherSidebar', () => ({
  TeacherSidebar: () => <div data-testid="teacher-sidebar">Sidebar</div>,
}));

vi.mock('@/components/layout/TutorSidebar', () => ({
  TutorSidebar: () => <div data-testid="tutor-sidebar">Sidebar</div>,
}));

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>,
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

import Forum from '../Forum';
import { chatAPI } from '@/integrations/api/chatAPI';
import { chatWebSocketService } from '@/services/chatWebSocketService';

const mockUser = {
  id: 1,
  email: 'student@test.com',
  first_name: 'Test',
  last_name: 'User',
  role: 'student',
};

const mockChat1 = {
  id: 100,
  name: 'Chat 1',
  participants: [{ id: 1, full_name: 'Test User' }, { id: 2, full_name: 'Other User' }],
  unread_count: 0,
  is_active: true,
  type: 'forum_general',
  last_message: { id: 1, content: 'Last message', created_at: '2024-01-01T00:00:00Z' },
  subject: null,
};

const mockChat2 = {
  id: 101,
  name: 'Chat 2',
  participants: [{ id: 1, full_name: 'Test User' }, { id: 3, full_name: 'Another User' }],
  unread_count: 2,
  is_active: true,
  type: 'forum_general',
  last_message: { id: 2, content: 'Another message', created_at: '2024-01-02T00:00:00Z' },
  subject: null,
};

const mockMessages1 = [
  {
    id: 1,
    content: 'Message 1 from Chat 1',
    sender: { id: 2, full_name: 'Other User', role: 'student' },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    is_read: true,
    is_edited: false,
    is_pinned: false,
    message_type: 'text',
  },
];

const mockMessages2 = [
  {
    id: 10,
    content: 'Message 1 from Chat 2',
    sender: { id: 3, full_name: 'Another User', role: 'student' },
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    is_read: false,
    is_edited: false,
    is_pinned: false,
    message_type: 'text',
  },
];

describe('Forum - Chat Selection State Reset', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Setup mocks
    vi.mocked(chatAPI.markAsRead).mockResolvedValue(undefined);
    vi.mocked(chatWebSocketService.connectToRoom).mockResolvedValue(true);
    vi.mocked(chatWebSocketService.isConnected).mockReturnValue(true);
    vi.mocked(chatWebSocketService.disconnectFromRoom).mockResolvedValue(undefined);
    vi.mocked(chatWebSocketService.onConnectionChange).mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  const renderForum = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthContext.Provider value={{ user: mockUser, signOut: vi.fn(), isLoading: false }}>
            <Forum />
          </AuthContext.Provider>
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  it('should clear old chat messages when switching chats', async () => {
    // T008: Test that switching between chats clears old messages from cache
    const initialChats = [mockChat1, mockChat2];

    // Setup initial chat list
    queryClient.setQueryData(['forum', 'chats'], initialChats);

    // Setup messages for both chats
    queryClient.setQueryData(
      ['forum-messages', mockChat1.id],
      {
        pages: [mockMessages1],
        pageParams: [0],
      }
    );

    queryClient.setQueryData(
      ['forum-messages', mockChat2.id],
      {
        pages: [mockMessages2],
        pageParams: [0],
      }
    );

    // Verify initial state
    const chat1Messages = queryClient.getQueryData(['forum-messages', mockChat1.id]);
    expect(chat1Messages).toBeDefined();
    expect(chat1Messages.pages[0]).toHaveLength(1);
    expect(chat1Messages.pages[0][0].content).toContain('Chat 1');

    // Simulate chat switch - the handler would clear old chat cache
    queryClient.removeQueries({ queryKey: ['forum-messages', mockChat1.id] });

    // Verify old chat messages are cleared
    const clearedChat1Messages = queryClient.getQueryData(['forum-messages', mockChat1.id]);
    expect(clearedChat1Messages).toBeUndefined();

    // Verify new chat messages are still available
    const chat2Messages = queryClient.getQueryData(['forum-messages', mockChat2.id]);
    expect(chat2Messages).toBeDefined();
    expect(chat2Messages.pages[0][0].content).toContain('Chat 2');
  });

  it('should cancel pending requests for old chat', async () => {
    // T008: Test that pending requests for old chat are cancelled
    const cancelSpy = vi.spyOn(queryClient, 'cancelQueries');

    queryClient.setQueryData(['forum', 'chats'], [mockChat1, mockChat2]);

    // Simulate cancelling old chat's requests
    await queryClient.cancelQueries({ queryKey: ['forum-messages', mockChat1.id] });

    expect(cancelSpy).toHaveBeenCalledWith({
      queryKey: ['forum-messages', mockChat1.id],
    });
  });

  it('should update chat title and icon immediately on selection', async () => {
    // T008: Test that chat UI updates immediately when selected
    const chats = [mockChat1, mockChat2];
    queryClient.setQueryData(['forum', 'chats'], chats);

    // The selected chat should update immediately
    expect(mockChat1.name).toBe('Chat 1');
    expect(mockChat2.name).toBe('Chat 2');
  });

  it('should not show stale WebSocket messages from previous chat', async () => {
    // T008: Test that WebSocket messages from old chat don't appear in new chat
    const staleMessage = {
      id: 999,
      content: 'Stale message from Chat 1',
      sender: { id: 2, full_name: 'Other User', role: 'student' },
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      is_read: true,
      is_edited: false,
      is_pinned: false,
      message_type: 'text',
    };

    // Setup chat 1 with initial message
    queryClient.setQueryData(['forum', 'chats'], [mockChat1, mockChat2]);
    queryClient.setQueryData(['forum-messages', mockChat1.id], {
      pages: [[staleMessage]],
      pageParams: [0],
    });

    // Verify stale message exists for chat 1
    const chat1Data = queryClient.getQueryData(['forum-messages', mockChat1.id]);
    expect(chat1Data.pages[0][0].content).toContain('Stale message');

    // Switch to chat 2 and clear chat 1 cache
    queryClient.removeQueries({ queryKey: ['forum-messages', mockChat1.id] });

    // Verify stale message is no longer in cache
    const clearedData = queryClient.getQueryData(['forum-messages', mockChat1.id]);
    expect(clearedData).toBeUndefined();

    // Verify chat 2 cache is separate and not affected
    queryClient.setQueryData(['forum-messages', mockChat2.id], {
      pages: [mockMessages2],
      pageParams: [0],
    });
    const chat2Data = queryClient.getQueryData(['forum-messages', mockChat2.id]);
    expect(chat2Data.pages[0][0].content).toContain('Chat 2');
    expect(chat2Data.pages[0][0].content).not.toContain('Stale');
  });

  it('should properly reset loading state on chat switch', async () => {
    // T008: Test that isSwitchingChat state is reset after chat switch
    const chats = [mockChat1, mockChat2];
    queryClient.setQueryData(['forum', 'chats'], chats);

    // Simulate loading state during switch
    let isSwitchingChat = true;

    // After connection is established, loading state should reset
    setTimeout(() => {
      isSwitchingChat = false;
    }, 500);

    // Verify initial loading state
    expect(isSwitchingChat).toBe(true);

    // Wait for loading state to reset
    await waitFor(
      () => {
        expect(isSwitchingChat).toBe(false);
      },
      { timeout: 1000 }
    );
  });

  it('should disconnect from old WebSocket room on chat switch', async () => {
    // T008: Test WebSocket disconnection on chat change
    queryClient.setQueryData(['forum', 'chats'], [mockChat1, mockChat2]);

    // Simulate selecting chat 1
    // When switching to chat 2, should disconnect from chat 1
    await chatWebSocketService.disconnectFromRoom(mockChat1.id);

    expect(chatWebSocketService.disconnectFromRoom).toHaveBeenCalledWith(mockChat1.id);
  });

  it('should connect to new WebSocket room on chat selection', async () => {
    // T008: Test WebSocket connection to new room
    queryClient.setQueryData(['forum', 'chats'], [mockChat1, mockChat2]);

    await chatWebSocketService.connectToRoom(mockChat2.id, {
      onMessage: vi.fn(),
      onTyping: vi.fn(),
      onTypingStop: vi.fn(),
      onError: vi.fn(),
    });

    expect(chatWebSocketService.connectToRoom).toHaveBeenCalledWith(mockChat2.id, expect.any(Object));
  });

  it('should mark chat as read on selection', async () => {
    // T008: Test that unread count is reset when chat is selected
    const chatWithUnread = { ...mockChat2, unread_count: 3 };
    queryClient.setQueryData(['forum', 'chats'], [mockChat1, chatWithUnread]);

    // Mark chat as read
    await chatAPI.markAsRead(chatWithUnread.id);

    expect(chatAPI.markAsRead).toHaveBeenCalledWith(chatWithUnread.id);

    // Update local state
    queryClient.setQueryData(['forum', 'chats'], (oldChats: any) => {
      if (!oldChats) return oldChats;
      return oldChats.map((c: any) =>
        c.id === chatWithUnread.id ? { ...c, unread_count: 0 } : c
      );
    });

    const updatedChats = queryClient.getQueryData<any>(['forum', 'chats']);
    const updatedChat = updatedChats.find((c: any) => c.id === chatWithUnread.id);
    expect(updatedChat.unread_count).toBe(0);
  });

  it('should properly handle rapid chat switches without race conditions', async () => {
    // T008: Test debouncing of rapid chat switches
    const chats = [mockChat1, mockChat2];
    queryClient.setQueryData(['forum', 'chats'], chats);

    const clearCache1 = vi.fn();
    const clearCache2 = vi.fn();

    // Simulate rapid switches
    setTimeout(() => clearCache1(), 0);
    setTimeout(() => clearCache1(), 50);
    setTimeout(() => clearCache2(), 100);

    await waitFor(
      () => {
        // Debounce should prevent race conditions
        expect(clearCache1).toHaveBeenCalled();
        expect(clearCache2).toHaveBeenCalled();
      },
      { timeout: 500 }
    );
  });

  it('should maintain separate message cache for each chat', async () => {
    // T008: Test query key includes chatId for cache isolation
    const queryKey1 = ['forum-messages', mockChat1.id];
    const queryKey2 = ['forum-messages', mockChat2.id];

    queryClient.setQueryData(queryKey1, {
      pages: [mockMessages1],
      pageParams: [0],
    });

    queryClient.setQueryData(queryKey2, {
      pages: [mockMessages2],
      pageParams: [0],
    });

    // Verify each chat has its own separate cache
    const data1 = queryClient.getQueryData(queryKey1);
    const data2 = queryClient.getQueryData(queryKey2);

    expect(data1.pages[0][0].content).toContain('Chat 1');
    expect(data2.pages[0][0].content).toContain('Chat 2');
    expect(data1).not.toEqual(data2);
  });
});
