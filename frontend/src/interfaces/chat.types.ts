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
  avatar?: string;
}

export interface ChatParticipant {
  id: number;
  user_id: number;
  user_name: string;
  user_avatar?: string;
  role?: string;
  is_online?: boolean;
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
  read_at?: string;
}

export interface ChatContact {
  id: number;
  user_id: number;
  name: string;
  email: string;
  avatar?: string;
  role: string;
  is_online: boolean;
  last_seen?: string;
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

export interface TypingStatus {
  chatId: number;
  userId: number;
  userName: string;
  isTyping: boolean;
  timestamp: string;
}

export interface OnlineStatus {
  userId: number;
  userName: string;
  isOnline: boolean;
  lastSeen?: string;
  timestamp: string;
}

export interface ChatNotification {
  id: string;
  chatId: number;
  type: 'new_message' | 'message_deleted' | 'user_joined' | 'user_left';
  message?: ChatMessage;
  user?: ChatParticipant;
  createdAt: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}
