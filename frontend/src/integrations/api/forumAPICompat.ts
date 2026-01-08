/**
 * Compatibility layer for old forumAPI usage
 * Maps old ForumChat/ForumMessage types to new Chat/ChatMessage types
 * This allows gradual migration without breaking existing code
 */

import { chatAPI, Chat, ChatMessage, ChatContact } from './chatAPI';

export type ForumChat = Chat;
export type ForumMessage = ChatMessage;
export type Contact = ChatContact;

export interface ForumUser {
  id: number;
  full_name: string;
  role: string;
}

export interface ForumSubject {
  id: number;
  name: string;
}

export interface SendForumMessageRequest {
  content: string;
  message_type?: string;
  reply_to?: number;
  file?: File;
}

export interface EditMessageRequest {
  content: string;
}

export interface InitiateChatResponse {
  success: boolean;
  chat: Chat;
  created: boolean;
}

export interface PinResponse {
  success: boolean;
  action: 'pinned' | 'unpinned';
  message_id: number;
  thread_id?: number;
}

export interface LockResponse {
  success: boolean;
  action: 'locked' | 'unlocked';
  chat_id: number;
}

export interface MuteResponse {
  success: boolean;
  action: 'muted' | 'unmuted';
  user_id: number;
  muted_until?: string;
}

export const forumAPI = {
  getForumChats: async (): Promise<ForumChat[]> => {
    const response = await chatAPI.getChatList();
    return response.results;
  },

  getForumMessages: async (
    chatId: number,
    limit: number = 50,
    offset: number = 0,
    signal?: AbortSignal
  ): Promise<ForumMessage[]> => {
    const page = Math.floor(offset / limit) + 1;
    const response = await chatAPI.getChatMessages(chatId, page, limit);
    return response.results;
  },

  sendForumMessage: async (
    chatId: number,
    data: SendForumMessageRequest
  ): Promise<ForumMessage> => {
    return await chatAPI.sendMessage(chatId, { content: data.content });
  },

  getAvailableContacts: async (): Promise<Contact[]> => {
    return await chatAPI.getContacts();
  },

  initiateChat: async (
    contactUserId: number,
    subjectId?: number
  ): Promise<InitiateChatResponse> => {
    const chat = await chatAPI.createOrGetChat(contactUserId, subjectId);
    return {
      success: true,
      chat,
      created: true,
    };
  },

  editForumMessage: async (
    chatId: number,
    messageId: number,
    data: EditMessageRequest
  ): Promise<ForumMessage> => {
    return await chatAPI.editMessage(chatId, messageId, data.content);
  },

  deleteForumMessage: async (chatId: number, messageId: number): Promise<void> => {
    await chatAPI.deleteMessage(chatId, messageId);
  },

  markChatAsRead: async (chatId: number): Promise<void> => {
    await chatAPI.markAsRead(chatId);
  },

  pinMessage: async (chatId: number, messageId: number): Promise<PinResponse> => {
    throw new Error('Pin message not yet implemented in new chat API');
  },

  lockChat: async (chatId: number): Promise<LockResponse> => {
    throw new Error('Lock chat not yet implemented in new chat API');
  },

  muteParticipant: async (chatId: number, userId: number): Promise<MuteResponse> => {
    throw new Error('Mute participant not yet implemented in new chat API');
  },
};
