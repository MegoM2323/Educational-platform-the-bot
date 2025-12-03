import { unifiedAPI } from './unifiedClient';

export interface ForumUser {
  id: number;
  full_name: string;
  role: string;
}

export interface ForumSubject {
  id: number;
  name: string;
}

export interface ForumMessage {
  id: number;
  content: string;
  sender: ForumUser;
  created_at: string;
  updated_at: string;
  is_read: boolean;
  message_type?: string;
}

export interface ForumChat {
  id: number;
  name: string;
  type: 'forum_subject' | 'forum_tutor';
  subject?: ForumSubject;
  participants: ForumUser[];
  unread_count: number;
  last_message?: {
    content: string;
    created_at: string;
    sender: ForumUser;
  };
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface ForumMessagesResponse {
  success: boolean;
  chat_id: number;
  limit: number;
  offset: number;
  count: number;
  results: ForumMessage[];
}

export interface ForumChatsResponse {
  success: boolean;
  count: number;
  results: ForumChat[];
}

export interface SendForumMessageRequest {
  content: string;
  message_type?: string;
  reply_to?: number;
}

export interface SendForumMessageResponse {
  success: boolean;
  message: ForumMessage;
}

export const forumAPI = {
  getForumChats: async (): Promise<ForumChat[]> => {
    const response = await unifiedAPI.request<any>(
      '/chat/forum/'
    );

    if (response.error) {
      throw new Error(response.error);
    }

    // Backend returns paginated response: {count, results, next, previous}
    // unifiedClient returns the full paginated object, not just the array
    // We need to extract the results array
    if (response.data && typeof response.data === 'object') {
      if (Array.isArray(response.data.results)) {
        return response.data.results;
      }
      // Fallback: if response.data is already an array (unlikely but safe)
      if (Array.isArray(response.data)) {
        return response.data;
      }
    }

    return [];
  },

  getForumMessages: async (
    chatId: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<ForumMessage[]> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', String(limit));
    if (offset) params.append('offset', String(offset));

    const queryString = params.toString();
    const url = `/chat/forum/${chatId}/messages/${queryString ? '?' + queryString : ''}`;

    const response = await unifiedAPI.request<any>(url);

    if (response.error) {
      throw new Error(response.error);
    }

    // Backend returns paginated response: {count, results, next, previous}
    // unifiedClient returns the full paginated object, not just the array
    // We need to extract the results array
    if (response.data && typeof response.data === 'object') {
      if (Array.isArray(response.data.results)) {
        return response.data.results;
      }
      // Fallback: if response.data is already an array (unlikely but safe)
      if (Array.isArray(response.data)) {
        return response.data;
      }
    }

    return [];
  },

  sendForumMessage: async (
    chatId: number,
    data: SendForumMessageRequest
  ): Promise<ForumMessage> => {
    const response = await unifiedAPI.request<SendForumMessageResponse>(
      `/chat/forum/${chatId}/send_message/`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
    if (response.error) {
      throw new Error(response.error);
    }
    if (!response.data?.message) {
      throw new Error('Invalid response from server');
    }
    return response.data.message;
  },
};
