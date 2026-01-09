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
};
