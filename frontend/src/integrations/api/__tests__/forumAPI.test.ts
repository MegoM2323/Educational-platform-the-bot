import { describe, it, expect, vi, beforeEach } from 'vitest';
import { forumAPI } from '../forumAPI';
import { unifiedAPI } from '../unifiedClient';
import type { Contact, InitiateChatResponse } from '../forumAPI';

// Mock unifiedAPI at file level
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

describe('forumAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getAvailableContacts', () => {
    it('should fetch available contacts successfully', async () => {
      const mockContacts: Contact[] = [
        {
          id: 1,
          email: 'teacher@test.com',
          first_name: 'Ivan',
          last_name: 'Petrov',
          role: 'teacher',
          avatar: '/avatars/teacher1.jpg',
          subject: { id: 1, name: 'Mathematics' },
          has_active_chat: false,
        },
        {
          id: 2,
          email: 'tutor@test.com',
          first_name: 'Maria',
          last_name: 'Ivanova',
          role: 'tutor',
          has_active_chat: true,
          chat_id: 42,
        },
      ];

      const mockResponse = {
        success: true,
        data: {
          count: 2,
          results: mockContacts,
        },
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getAvailableContacts();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/chat/available-contacts/');
      expect(result).toEqual(mockContacts);
      expect(result.length).toBe(2);
      expect(result[0].first_name).toBe('Ivan');
      expect(result[1].has_active_chat).toBe(true);
    });

    it('should handle array response (fallback)', async () => {
      const mockContacts: Contact[] = [
        {
          id: 3,
          email: 'student@test.com',
          first_name: 'Alex',
          last_name: 'Sokolov',
          role: 'student',
          has_active_chat: false,
        },
      ];

      const mockResponse = {
        success: true,
        data: mockContacts, // Directly as array
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getAvailableContacts();

      expect(result).toEqual(mockContacts);
      expect(result.length).toBe(1);
    });

    it('should return empty array on unexpected response structure', async () => {
      const mockResponse = {
        success: true,
        data: { unexpected: 'structure' },
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getAvailableContacts();

      expect(result).toEqual([]);
    });

    it('should throw error on API error', async () => {
      const mockResponse = {
        success: false,
        error: 'Authentication failed',
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.getAvailableContacts()).rejects.toThrow(
        'Authentication failed'
      );
    });

    it('should return empty array when no contacts available', async () => {
      const mockResponse = {
        success: true,
        data: {
          count: 0,
          results: [],
        },
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.getAvailableContacts();

      expect(result).toEqual([]);
      expect(result.length).toBe(0);
    });
  });

  describe('initiateChat', () => {
    it('should initiate chat successfully (new chat)', async () => {
      const contactUserId = 42;
      const subjectId = 1;

      const mockChatResponse: InitiateChatResponse = {
        success: true,
        chat: {
          id: 123,
          room_id: 'room_42_1_forum_subject',
          type: 'FORUM_SUBJECT',
          other_user: {
            id: 42,
            email: 'teacher@test.com',
            first_name: 'Ivan',
            last_name: 'Petrov',
            role: 'teacher',
            has_active_chat: true,
            chat_id: 123,
          },
          created_at: '2025-12-14T10:00:00Z',
          name: 'Mathematics - Ivan Petrov',
          unread_count: 0,
        },
        created: true,
      };

      const mockResponse = {
        success: true,
        data: mockChatResponse,
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.initiateChat(contactUserId, subjectId);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/chat/initiate-chat/', {
        method: 'POST',
        body: JSON.stringify({ contact_user_id: 42, subject_id: 1 }),
      });
      expect(result.success).toBe(true);
      expect(result.created).toBe(true);
      expect(result.chat.id).toBe(123);
      expect(result.chat.room_id).toBe('room_42_1_forum_subject');
      expect(result.chat.other_user.first_name).toBe('Ivan');
    });

    it('should initiate chat without subject_id (tutor chat)', async () => {
      const contactUserId = 99;

      const mockChatResponse: InitiateChatResponse = {
        success: true,
        chat: {
          id: 456,
          room_id: 'room_99_forum_tutor',
          type: 'FORUM_TUTOR',
          other_user: {
            id: 99,
            email: 'tutor@test.com',
            first_name: 'Maria',
            last_name: 'Ivanova',
            role: 'tutor',
            has_active_chat: true,
            chat_id: 456,
          },
          created_at: '2025-12-14T10:00:00Z',
          name: 'Maria Ivanova (Tutor)',
          unread_count: 0,
        },
        created: true,
      };

      const mockResponse = {
        success: true,
        data: mockChatResponse,
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.initiateChat(contactUserId);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/chat/initiate-chat/', {
        method: 'POST',
        body: JSON.stringify({ contact_user_id: 99 }),
      });
      expect(result.chat.type).toBe('FORUM_TUTOR');
    });

    it('should return existing chat (created: false)', async () => {
      const contactUserId = 42;
      const subjectId = 1;

      const mockChatResponse: InitiateChatResponse = {
        success: true,
        chat: {
          id: 123,
          room_id: 'room_42_1_forum_subject',
          type: 'FORUM_SUBJECT',
          other_user: {
            id: 42,
            email: 'teacher@test.com',
            first_name: 'Ivan',
            last_name: 'Petrov',
            role: 'teacher',
            has_active_chat: true,
            chat_id: 123,
          },
          created_at: '2025-12-10T10:00:00Z',
          name: 'Mathematics - Ivan Petrov',
          unread_count: 5,
        },
        created: false, // Existing chat
      };

      const mockResponse = {
        success: true,
        data: mockChatResponse,
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      const result = await forumAPI.initiateChat(contactUserId, subjectId);

      expect(result.created).toBe(false);
      expect(result.chat.unread_count).toBe(5);
    });

    it('should throw error on invalid contact_user_id (400)', async () => {
      const mockResponse = {
        success: false,
        error: 'Invalid contact_user_id',
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.initiateChat(0)).rejects.toThrow(
        'Invalid contact_user_id'
      );
    });

    it('should throw error on permission denied (403)', async () => {
      const mockResponse = {
        success: false,
        error: 'Permission denied: You cannot chat with this user',
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.initiateChat(999, 1)).rejects.toThrow(
        'Permission denied: You cannot chat with this user'
      );
    });

    it('should throw error on contact not found (404)', async () => {
      const mockResponse = {
        success: false,
        error: 'Contact user not found',
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.initiateChat(9999)).rejects.toThrow(
        'Contact user not found'
      );
    });

    it('should throw error if response data is missing', async () => {
      const mockResponse = {
        success: true,
        data: null, // Missing data
        timestamp: new Date().toISOString(),
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue(mockResponse);

      await expect(forumAPI.initiateChat(42, 1)).rejects.toThrow(
        'Invalid response from server: missing data'
      );
    });
  });
});
