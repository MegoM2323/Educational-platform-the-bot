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
    const response = await unifiedAPI.request<ForumChat[]>(
      '/chat/forum/'
    );

    if (response.error) {
      throw new Error(response.error);
    }

    // unifiedClient already extracts results array from paginated response
    // So response.data is already ForumChat[], not ForumChatsResponse
    return response.data || [];
  },

  getForumMessages: async (
    chatId: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<ForumMessagesResponse> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', String(limit));
    if (offset) params.append('offset', String(offset));

    const queryString = params.toString();
    const url = `/chat/forum/${chatId}/messages/${queryString ? '?' + queryString : ''}`;

    const response = await unifiedAPI.request<ForumMessagesResponse>(url);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data || {
      success: false,
      chat_id: chatId,
      limit,
      offset,
      count: 0,
      results: [],
    };
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
