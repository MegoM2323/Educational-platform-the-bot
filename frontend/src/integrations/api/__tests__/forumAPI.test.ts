import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  forumAPI,
  ForumMessage,
  ForumChat,
  EditMessageRequest,
} from '../forumAPI';
import { unifiedAPI } from '../unifiedClient';

// Mock the unifiedAPI
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

describe('forumAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getForumChats', () => {
    it('should return forum chats from results array', async () => {
      const mockChats: ForumChat[] = [
        {
          id: 1,
          name: 'Math Class',
          type: 'forum_subject',
          participants: [],
          unread_count: 0,
          created_at: '2025-01-01',
          updated_at: '2025-01-01',
          is_active: true,
        },
      ];

      const mockResponse = {
        success: true,
        data: { results: mockChats },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getForumChats();

      expect(result).toEqual(mockChats);
      expect(unifiedAPI.request).toHaveBeenCalledWith('/chat/forum/');
    });

    it('should handle empty results', async () => {
      const mockResponse = {
        success: true,
        data: { results: [] },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getForumChats();

      expect(result).toEqual([]);
    });

    it('should throw error on API failure', async () => {
      const mockResponse = {
        success: false,
        error: 'Failed to fetch chats',
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.getForumChats()).rejects.toThrow('Failed to fetch chats');
    });
  });

  describe('getForumMessages', () => {
    it('should return paginated forum messages', async () => {
      const mockMessages: ForumMessage[] = [
        {
          id: 1,
          content: 'Hello',
          sender: { id: 1, full_name: 'John Doe', role: 'student' },
          created_at: '2025-01-01T10:00:00Z',
          updated_at: '2025-01-01T10:00:00Z',
          is_read: true,
        },
      ];

      const mockResponse = {
        success: true,
        data: { results: mockMessages },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getForumMessages(1, 50, 0);

      expect(result).toEqual(mockMessages);
      expect(unifiedAPI.request).toHaveBeenCalled();
    });

    it('should handle missing results gracefully', async () => {
      const mockResponse = {
        success: true,
        data: null,
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getForumMessages(1);

      expect(result).toEqual([]);
    });
  });

  describe('sendForumMessage', () => {
    it('should send forum message successfully', async () => {
      const mockMessage: ForumMessage = {
        id: 1,
        content: 'Test message',
        sender: { id: 1, full_name: 'John Doe', role: 'student' },
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:00:00Z',
        is_read: true,
      };

      const mockResponse = {
        success: true,
        data: { message: mockMessage },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.sendForumMessage(1, { content: 'Test message' });

      expect(result).toEqual(mockMessage);
    });

    it('should throw error on missing message in response', async () => {
      const mockResponse = {
        success: true,
        data: {},
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.sendForumMessage(1, { content: 'Test' })).rejects.toThrow(
        'Invalid response from server'
      );
    });
  });

  describe('editForumMessage', () => {
    it('should edit message successfully', async () => {
      const editData: EditMessageRequest = { content: 'Updated message' };
      const mockMessage: ForumMessage = {
        id: 1,
        content: 'Updated message',
        sender: { id: 1, full_name: 'John Doe', role: 'student' },
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:01:00Z',
        is_read: true,
        is_edited: true,
      };

      const mockResponse = {
        success: true,
        data: mockMessage,
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.editForumMessage(1, editData);

      expect(result).toEqual(mockMessage);
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/chat/messages/1/',
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });

    it('should throw error on missing data', async () => {
      const mockResponse = {
        success: true,
        data: null,
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.editForumMessage(1, { content: 'Test' })).rejects.toThrow(
        'Invalid response from server'
      );
    });
  });

  describe('deleteForumMessage', () => {
    it('should delete message successfully', async () => {
      const mockResponse = {
        success: true,
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.deleteForumMessage(1)).resolves.not.toThrow();

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/chat/messages/1/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should throw error on API failure', async () => {
      const mockResponse = {
        success: false,
        error: 'Failed to delete',
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.deleteForumMessage(1)).rejects.toThrow('Failed to delete');
    });
  });

  describe('getAvailableContacts', () => {
    it('should return available contacts', async () => {
      const mockContacts = [
        {
          id: 1,
          email: 'john@example.com',
          first_name: 'John',
          last_name: 'Doe',
          role: 'teacher' as const,
          has_active_chat: false,
        },
      ];

      const mockResponse = {
        success: true,
        data: { results: mockContacts },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getAvailableContacts();

      expect(result).toEqual(mockContacts);
    });
  });

  describe('initiateChat', () => {
    it('should initiate chat with contact', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          chat: {
            id: 1,
            room_id: 'room-1',
            type: 'forum_subject' as const,
            other_user: {
              id: 2,
              email: 'john@example.com',
              first_name: 'John',
              last_name: 'Doe',
              role: 'teacher' as const,
              has_active_chat: true,
            },
            created_at: '2025-01-01',
            name: 'Chat with John',
            unread_count: 0,
          },
          created: true,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.initiateChat(2);

      expect(result).toEqual(mockResponse.data);
      expect(result.created).toBe(true);
    });

    it('should handle existing chat', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          chat: {
            id: 1,
            room_id: 'room-1',
            type: 'forum_subject' as const,
            other_user: {
              id: 2,
              email: 'john@example.com',
              first_name: 'John',
              last_name: 'Doe',
              role: 'teacher' as const,
              has_active_chat: true,
            },
            created_at: '2025-01-01',
            name: 'Chat with John',
            unread_count: 0,
          },
          created: false,
        },
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.initiateChat(2);

      expect(result.created).toBe(false);
    });
  });
});
