// Chat API Service для работы с общим чатом-форумом
import { unifiedAPI } from './unifiedClient';

export interface ChatMessage {
  id: number;
  content: string;
  message_type: 'text' | 'image' | 'file' | 'system';
  sender: {
    id: number;
    first_name: string;
    last_name: string;
    role: string;
    role_display: string;
  };
  thread?: {
    id: number;
    title: string;
  };
  reply_to?: {
    id: number;
    content: string;
    sender: {
      first_name: string;
      last_name: string;
    };
  };
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatThread {
  id: number;
  title: string;
  created_by: {
    id: number;
    first_name: string;
    last_name: string;
    role: string;
  };
  is_pinned: boolean;
  is_locked: boolean;
  messages_count: number;
  last_message?: ChatMessage;
  created_at: string;
  updated_at: string;
}

export interface ChatRoom {
  id: number;
  name: string;
  description: string;
  type: 'direct' | 'group' | 'support' | 'class' | 'general';
  participants_count: number;
  last_message?: ChatMessage;
  created_at: string;
  updated_at: string;
}

export interface SendMessageRequest {
  content: string;
  message_type?: 'text' | 'image' | 'file';
  thread_id?: number;
  reply_to?: number;
}

export interface CreateThreadRequest {
  title: string;
}

class ChatService {
  // Получить общий чат
  async getGeneralChat(): Promise<ChatRoom> {
    const response = await unifiedAPI.getGeneralChat();
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Получить сообщения общего чата
  async getGeneralChatMessages(limit: number = 50, offset: number = 0): Promise<ChatMessage[]> {
    const response = await unifiedAPI.request<ChatMessage[]>(
      `/chat/general/messages/?limit=${limit}&offset=${offset}`
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Отправить сообщение в общий чат
  async sendGeneralMessage(data: SendMessageRequest): Promise<ChatMessage> {
    const response = await unifiedAPI.request<ChatMessage>('/chat/general/send_message/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Получить треды общего чата
  async getGeneralChatThreads(limit: number = 20, offset: number = 0): Promise<ChatThread[]> {
    const response = await unifiedAPI.request<ChatThread[]>(
      `/chat/general/threads/?limit=${limit}&offset=${offset}`
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Создать новый тред
  async createThread(data: CreateThreadRequest): Promise<ChatThread> {
    const response = await unifiedAPI.request<ChatThread>('/chat/general/threads/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Получить сообщения треда
  async getThreadMessages(threadId: number, limit: number = 50, offset: number = 0): Promise<ChatMessage[]> {
    const response = await unifiedAPI.request<ChatMessage[]>(
      `/chat/threads/${threadId}/messages/?limit=${limit}&offset=${offset}`
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Отправить сообщение в тред
  async sendThreadMessage(threadId: number, data: SendMessageRequest): Promise<ChatMessage> {
    const response = await unifiedAPI.request<ChatMessage>(`/chat/threads/${threadId}/send_message/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Закрепить тред
  async pinThread(threadId: number): Promise<ChatThread> {
    const response = await unifiedAPI.request<ChatThread>(`/chat/threads/${threadId}/pin/`, {
      method: 'POST',
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Открепить тред
  async unpinThread(threadId: number): Promise<ChatThread> {
    const response = await unifiedAPI.request<ChatThread>(`/chat/threads/${threadId}/unpin/`, {
      method: 'POST',
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Заблокировать тред
  async lockThread(threadId: number): Promise<ChatThread> {
    const response = await unifiedAPI.request<ChatThread>(`/chat/threads/${threadId}/lock/`, {
      method: 'POST',
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }

  // Разблокировать тред
  async unlockThread(threadId: number): Promise<ChatThread> {
    const response = await unifiedAPI.request<ChatThread>(`/chat/threads/${threadId}/unlock/`, {
      method: 'POST',
    });
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data!;
  }
}

export const chatService = new ChatService();
