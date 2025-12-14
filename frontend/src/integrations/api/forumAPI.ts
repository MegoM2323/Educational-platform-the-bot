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

export interface Contact {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'student' | 'teacher' | 'tutor' | 'parent';
  avatar?: string;
  subject?: { id: number; name: string };
  has_active_chat: boolean;
  chat_id?: number;
}

export interface ContactsResponse {
  success: boolean;
  count: number;
  results: Contact[];
}

export interface ChatDetail {
  id: number;
  room_id: string;
  type: 'FORUM_SUBJECT' | 'FORUM_TUTOR';
  other_user: Contact;
  created_at: string;
  name: string;
  last_message?: any;
  unread_count: number;
}

export interface InitiateChatResponse {
  success: boolean;
  chat: ChatDetail;
  created: boolean;
}

export const forumAPI = {
  getForumChats: async (): Promise<ForumChat[]> => {
    console.log('[forumAPI] getForumChats called');
    const response = await unifiedAPI.request<any>(
      '/chat/forum/'
    );

    console.log('[forumAPI] getForumChats response:', {
      success: response.success,
      error: response.error,
      hasData: !!response.data,
      dataType: typeof response.data,
      isDataArray: Array.isArray(response.data),
      hasResults: response.data?.results !== undefined,
      resultsLength: response.data?.results?.length,
      fullResponse: response
    });

    if (response.error) {
      console.error('[forumAPI] getForumChats error:', response.error);
      throw new Error(response.error);
    }

    // Backend returns paginated response: {count, results, next, previous}
    // unifiedClient returns the full paginated object, not just the array
    // We need to extract the results array
    if (response.data && typeof response.data === 'object') {
      if (Array.isArray(response.data.results)) {
        console.log('[forumAPI] Returning results array:', response.data.results);
        return response.data.results;
      }
      // Fallback: if response.data is already an array (unlikely but safe)
      if (Array.isArray(response.data)) {
        console.log('[forumAPI] Response.data is array, returning:', response.data);
        return response.data;
      }
    }

    console.warn('[forumAPI] Unexpected response structure, returning empty array. Response:', response);
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

  getAvailableContacts: async (): Promise<Contact[]> => {
    console.debug('[forumAPI] getAvailableContacts called');

    const response = await unifiedAPI.request<ContactsResponse>(
      '/chat/available-contacts/'
    );

    console.debug('[forumAPI] getAvailableContacts response:', {
      success: response.success,
      error: response.error,
      hasData: !!response.data,
      resultsLength: response.data?.results?.length,
    });

    if (response.error) {
      console.error('[forumAPI] getAvailableContacts error:', response.error);
      throw new Error(response.error);
    }

    // Extract results array from paginated response
    if (response.data && typeof response.data === 'object') {
      if (Array.isArray(response.data.results)) {
        console.debug('[forumAPI] Returning contacts array:', response.data.results.length);
        return response.data.results;
      }
      // Fallback: if response.data is already an array
      if (Array.isArray(response.data)) {
        console.debug('[forumAPI] Response.data is array, returning:', response.data.length);
        return response.data;
      }
    }

    console.warn('[forumAPI] Unexpected response structure, returning empty array. Response:', response);
    return [];
  },

  initiateChat: async (
    contactUserId: number,
    subjectId?: number
  ): Promise<InitiateChatResponse> => {
    console.debug('[forumAPI] initiateChat called:', { contactUserId, subjectId });

    const requestBody: { contact_user_id: number; subject_id?: number } = {
      contact_user_id: contactUserId,
    };

    if (subjectId !== undefined) {
      requestBody.subject_id = subjectId;
    }

    const response = await unifiedAPI.request<InitiateChatResponse>(
      '/chat/initiate-chat/',
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
      }
    );

    console.debug('[forumAPI] initiateChat response:', {
      success: response.success,
      error: response.error,
      hasData: !!response.data,
      created: response.data?.created,
      chatId: response.data?.chat?.id,
    });

    if (response.error) {
      console.error('[forumAPI] initiateChat error:', response.error);
      throw new Error(response.error);
    }

    if (!response.data) {
      throw new Error('Invalid response from server: missing data');
    }

    return response.data;
  },
};
