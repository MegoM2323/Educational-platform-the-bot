// Chat API Service
import { unifiedAPI } from './unifiedClient';

export interface ChatMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  sender_role: string;
  content: string;
  thread_id?: number;
  parent_message_id?: number;
  created_at: string;
  updated_at: string;
  is_edited?: boolean;
}

export interface MessageThread {
  id: number;
  parent_message_id: number;
  thread_title: string;
  message_count: number;
  last_message_time: string;
  created_at: string;
}

export interface ChatRoom {
  id: number;
  name: string;
  description?: string;
  room_type: string;
  participant_count: number;
  created_at: string;
}

export interface SendMessageRequest {
  content: string;
  thread_id?: number;
  parent_message_id?: number;
}

export interface CreateThreadRequest {
  parent_message_id: number;
  content: string;
}

// Chat API
export const chatAPI = {
  // Get general chat room
  getGeneralChat: async (): Promise<ChatRoom> => {
    const response = await unifiedAPI.getGeneralChat();
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get general chat messages with pagination
  getGeneralMessages: async (page: number = 1, pageSize: number = 50): Promise<{
    results: ChatMessage[];
    count: number;
    next?: string;
    previous?: string;
  }> => {
    const response = await unifiedAPI.getGeneralMessages(page, pageSize);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Send message to general chat
  sendMessage: async (data: SendMessageRequest): Promise<ChatMessage> => {
    const response = await unifiedAPI.sendMessage(data);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Create thread (reply to message)
  createThread: async (messageId: number, data: SendMessageRequest): Promise<MessageThread> => {
    const response = await unifiedAPI.request<MessageThread>(`/chat/general/thread/${messageId}/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get threads for a message
  getThreads: async (parentMessageId: number): Promise<MessageThread[]> => {
    const response = await unifiedAPI.request<MessageThread[]>(`/chat/general/threads/?parent_message_id=${parentMessageId}`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get thread messages
  getThreadMessages: async (threadId: number): Promise<ChatMessage[]> => {
    const response = await unifiedAPI.request<ChatMessage[]>(`/chat/general/threads/${threadId}/messages/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Update message
  updateMessage: async (messageId: number, content: string): Promise<ChatMessage> => {
    const response = await unifiedAPI.request<ChatMessage>(`/chat/messages/${messageId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Delete message
  deleteMessage: async (messageId: number): Promise<void> => {
    const response = await unifiedAPI.request(`/chat/messages/${messageId}/`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // Get all chat rooms
  getChatRooms: async (): Promise<ChatRoom[]> => {
    const response = await unifiedAPI.request<ChatRoom[]>('/chat/rooms/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get room messages
  getRoomMessages: async (roomId: number): Promise<ChatMessage[]> => {
    const response = await unifiedAPI.request<ChatMessage[]>(`/chat/rooms/${roomId}/messages/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};
