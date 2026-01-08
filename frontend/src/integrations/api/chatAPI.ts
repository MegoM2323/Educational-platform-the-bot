import { unifiedAPI } from './unifiedClient';
import { errorHandlingService } from '../../services/errorHandlingService';
import { toast } from 'sonner';
import { logger } from '../../utils/logger';

export interface Chat {
  id: number;
  name: string;
  description?: string;
  is_group: boolean;
  participant_count: number;
  last_message?: ChatMessage;
  last_message_at?: string;
  unread_count: number;
  created_at: string;
  updated_at: string;
  participants?: ChatParticipant[];
}

export interface ChatParticipant {
  id: number;
  user_id: number;
  user_name: string;
  user_avatar?: string;
  role?: string;
  joined_at: string;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  sender_id: number;
  sender_name: string;
  sender_avatar?: string;
  content: string;
  created_at: string;
  updated_at: string;
  is_edited: boolean;
  is_deleted: boolean;
  read_by?: number[];
}

export interface ChatContact {
  id: number;
  user_id: number;
  name: string;
  email: string;
  avatar?: string;
  role: string;
  is_online: boolean;
}

export interface CreateChatRequest {
  name?: string;
  description?: string;
  participant_ids: number[];
  is_group?: boolean;
}

export interface SendMessageRequest {
  content: string;
}

export interface MessageStatusUpdate {
  read_at?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

export type ChatListResponse = PaginatedResponse<Chat>;
export type ChatMessagesResponse = PaginatedResponse<ChatMessage>;

const CHAT_CACHE_KEY = 'chats_list';
const MESSAGE_CACHE_TTL = 5 * 60 * 1000;
const CHAT_CACHE_TTL = 10 * 60 * 1000;

export const chatAPI = {
  async getChatList(page: number = 1, pageSize: number = 20): Promise<ChatListResponse> {
    try {
      const response = await unifiedAPI.request<ChatListResponse>(
        `/chat/?page=${page}&page_size=${pageSize}`
      );

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data || { count: 0, results: [] };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка загрузки чатов';
      logger.error('[Chat API] getChatList error:', error);
      errorHandlingService.handleError(error);
      throw error;
    }
  },

  async createChat(data: CreateChatRequest): Promise<Chat> {
    try {
      const response = await unifiedAPI.request<Chat>('/chat/', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success('Чат создан');
      return response.data!;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка создания чата';
      logger.error('[Chat API] createChat error:', error);
      toast.error(message);
      throw error;
    }
  },

  async createOrGetChat(contactUserId: number, subjectId?: number): Promise<Chat> {
    try {
      const requestBody: { contact_user_id: number; subject_id?: number } = {
        contact_user_id: contactUserId,
      };

      if (subjectId !== undefined) {
        requestBody.subject_id = subjectId;
      }

      const response = await unifiedAPI.request<Chat>('/chat/', {
        method: 'POST',
        body: JSON.stringify(requestBody),
      });

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data!;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка создания чата';
      logger.error('[Chat API] createOrGetChat error:', error);
      toast.error(message);
      throw error;
    }
  },

  async getChatById(chatId: number): Promise<Chat> {
    try {
      const response = await unifiedAPI.request<Chat>(`/chat/${chatId}/`);

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data!;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка загрузки информации чата';
      logger.error('[Chat API] getChatById error:', error);
      errorHandlingService.handleError(error);
      throw error;
    }
  },

  async getChatMessages(
    chatId: number,
    page: number = 1,
    pageSize: number = 50
  ): Promise<ChatMessagesResponse> {
    try {
      const response = await unifiedAPI.request<ChatMessagesResponse>(
        `/chat/${chatId}/messages/?page=${page}&page_size=${pageSize}`
      );

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data || { count: 0, results: [] };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка загрузки сообщений';
      logger.error('[Chat API] getChatMessages error:', error);
      errorHandlingService.handleError(error);
      throw error;
    }
  },

  async sendMessage(chatId: number, data: SendMessageRequest): Promise<ChatMessage> {
    try {
      if (!data.content.trim()) {
        throw new Error('Сообщение не может быть пустым');
      }

      const response = await unifiedAPI.request<ChatMessage>(
        `/chat/${chatId}/send_message/`,
        {
          method: 'POST',
          body: JSON.stringify(data),
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data!;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка отправки сообщения';
      logger.error('[Chat API] sendMessage error:', error);
      toast.error(message);
      throw error;
    }
  },

  async editMessage(chatId: number, messageId: number, content: string): Promise<ChatMessage> {
    try {
      const response = await unifiedAPI.request<ChatMessage>(
        `/chat/${chatId}/messages/${messageId}/`,
        {
          method: 'PATCH',
          body: JSON.stringify({ content }),
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success('Сообщение отредактировано');
      return response.data!;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка редактирования сообщения';
      logger.error('[Chat API] editMessage error:', error);
      toast.error(message);
      throw error;
    }
  },

  async deleteMessage(chatId: number, messageId: number): Promise<void> {
    try {
      const response = await unifiedAPI.request(
        `/chat/${chatId}/messages/${messageId}/`,
        {
          method: 'DELETE',
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success('Сообщение удалено');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка удаления сообщения';
      logger.error('[Chat API] deleteMessage error:', error);
      toast.error(message);
      throw error;
    }
  },

  async markAsRead(chatId: number): Promise<void> {
    try {
      const response = await unifiedAPI.request(
        `/chat/${chatId}/mark_as_read/`,
        {
          method: 'POST',
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }
    } catch (error) {
      logger.error('[Chat API] markAsRead error:', error);
      throw error;
    }
  },

  async getContacts(): Promise<ChatContact[]> {
    try {
      const response = await unifiedAPI.request<ChatContact[]>('/chat/contacts/');

      if (response.error) {
        throw new Error(response.error);
      }

      return response.data || [];
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка загрузки контактов';
      logger.error('[Chat API] getContacts error:', error);
      errorHandlingService.handleError(error);
      throw error;
    }
  },

  async deleteChat(chatId: number): Promise<void> {
    try {
      const response = await unifiedAPI.request(`/chat/${chatId}/`, {
        method: 'DELETE',
      });

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success('Чат удален');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка удаления чата';
      logger.error('[Chat API] deleteChat error:', error);
      toast.error(message);
      throw error;
    }
  },

  async addParticipant(chatId: number, userId: number): Promise<ChatParticipant> {
    try {
      const response = await unifiedAPI.request<ChatParticipant>(
        `/chat/${chatId}/participants/`,
        {
          method: 'POST',
          body: JSON.stringify({ user_id: userId }),
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success('Участник добавлен');
      return response.data!;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка добавления участника';
      logger.error('[Chat API] addParticipant error:', error);
      toast.error(message);
      throw error;
    }
  },

  async removeParticipant(chatId: number, userId: number): Promise<void> {
    try {
      const response = await unifiedAPI.request(
        `/chat/${chatId}/participants/${userId}/`,
        {
          method: 'DELETE',
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success('Участник удален');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка удаления участника';
      logger.error('[Chat API] removeParticipant error:', error);
      toast.error(message);
      throw error;
    }
  },
};
