import { useState, useMemo, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { MessageCircle, Send, Search, Loader2, Wifi, WifiOff, AlertCircle, LogOut } from 'lucide-react';
import { useForumChats, useForumChatsWithRefresh } from '@/hooks/useForumChats';
import { useForumMessages, useSendForumMessage } from '@/hooks/useForumMessages';
import { ForumChat, ForumMessage } from '@/integrations/api/forumAPI';
import { Skeleton } from '@/components/ui/skeleton';
import { chatWebSocketService, ChatMessage, TypingUser } from '@/services/chatWebSocketService';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { StudentSidebar } from '@/components/layout/StudentSidebar';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { TutorSidebar } from '@/components/layout/TutorSidebar';
import { ParentSidebar } from '@/components/layout/ParentSidebar';

interface ChatListProps {
  chats: ForumChat[];
  selectedChat: ForumChat | null;
  onSelectChat: (chat: ForumChat) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isLoading: boolean;
}

interface ChatWindowProps {
  chat: ForumChat | null;
  messages: ForumMessage[];
  isLoadingMessages: boolean;
  isSending: boolean;
  onSendMessage: (content: string) => void;
  isConnected: boolean;
  typingUsers: TypingUser[];
  error: string | null;
  onRetryConnection: () => void;
}

const ChatListItem = ({ chat, selected, onClick }: { chat: ForumChat; selected: boolean; onClick: () => void }) => {
  const initials = chat.participants
    .filter((p) => p.id !== parseInt(localStorage.getItem('user_id') || '0'))
    .map((p) => p.full_name.charAt(0))
    .join('')
    .toUpperCase() || 'C';

  const otherParticipants = chat.participants
    .filter((p) => p.id !== parseInt(localStorage.getItem('user_id') || '0'))
    .map((p) => p.full_name)
    .join(', ');

  const displayName = chat.name || otherParticipants || 'Чат';
  const lastMessagePreview = chat.last_message?.content || 'Нет сообщений';
  const lastMessageTime = chat.last_message?.created_at ? new Date(chat.last_message.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg cursor-pointer transition-colors border ${
        selected
          ? 'bg-primary/10 border-primary'
          : 'border-transparent hover:bg-muted'
      }`}
    >
      <div className="flex items-start gap-3">
        <Avatar className="w-10 h-10">
          <AvatarFallback className="gradient-primary text-primary-foreground">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="font-medium truncate text-sm">{displayName}</div>
            {chat.unread_count > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs">
                {chat.unread_count}
              </Badge>
            )}
          </div>
          {chat.subject && (
            <p className="text-xs text-muted-foreground mb-1 truncate">
              {chat.subject.name}
            </p>
          )}
          <p className="text-xs text-muted-foreground truncate">{lastMessagePreview}</p>
          {lastMessageTime && (
            <div className="text-xs text-muted-foreground mt-1">{lastMessageTime}</div>
          )}
        </div>
      </div>
    </div>
  );
};

const ChatList = ({
  chats,
  selectedChat,
  onSelectChat,
  searchQuery,
  onSearchChange,
  isLoading,
}: ChatListProps) => {
  const filteredChats = useMemo(() => {
    if (!searchQuery) return chats;
    const query = searchQuery.toLowerCase();
    return chats.filter(
      (chat) =>
        chat.name.toLowerCase().includes(query) ||
        chat.subject?.name.toLowerCase().includes(query) ||
        chat.participants.some((p) => p.full_name.toLowerCase().includes(query))
    );
  }, [chats, searchQuery]);

  return (
    <Card className="p-4 md:col-span-1 flex flex-col h-full">
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Поиск чатов..."
          className="pl-10 text-sm"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-2 pr-4">
          {isLoading ? (
            <>
              <Skeleton className="h-20 rounded-lg" />
              <Skeleton className="h-20 rounded-lg" />
              <Skeleton className="h-20 rounded-lg" />
            </>
          ) : filteredChats.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <MessageCircle className="w-8 h-8 text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                {searchQuery ? 'Чатов не найдено' : 'Нет активных чатов'}
              </p>
            </div>
          ) : (
            filteredChats.map((chat) => (
              <ChatListItem
                key={chat.id}
                chat={chat}
                selected={selectedChat?.id === chat.id}
                onClick={() => onSelectChat(chat)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </Card>
  );
};

const ChatWindow = ({
  chat,
  messages,
  isLoadingMessages,
  isSending,
  onSendMessage,
  isConnected,
  typingUsers,
  error,
  onRetryConnection,
}: ChatWindowProps) => {
  const [messageInput, setMessageInput] = useState('');

  const handleSend = () => {
    if (messageInput.trim() && !isSending) {
      onSendMessage(messageInput.trim());
      setMessageInput('');
    }
  };

  const handleMessageChange = (value: string) => {
    setMessageInput(value);

    // Send typing indicator if connected
    if (value.trim() && isConnected && chat) {
      chatWebSocketService.sendTyping(chat.id);
      chatWebSocketService.startTypingTimer(chat.id);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && messageInput.trim()) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!chat) {
    return (
      <Card className="p-6 md:col-span-2 flex flex-col items-center justify-center h-full">
        <MessageCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Выберите чат для начала общения</p>
      </Card>
    );
  }

  const otherParticipants = chat.participants
    .filter((p) => p.id !== parseInt(localStorage.getItem('user_id') || '0'))
    .map((p) => p.full_name)
    .join(', ');

  const displayName = chat.name || otherParticipants || 'Чат';

  return (
    <Card className="p-6 md:col-span-2 flex flex-col h-full">
      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-destructive" />
          <div className="flex-1">
            <p className="text-sm text-destructive font-medium">{error}</p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={onRetryConnection}
            className="text-xs"
          >
            Повторить
          </Button>
        </div>
      )}

      {/* Chat Header */}
      <div className="flex items-center gap-3 pb-4 border-b">
        <Avatar className="w-10 h-10">
          <AvatarFallback className="gradient-primary text-primary-foreground">
            {chat.participants
              .filter((p) => p.id !== parseInt(localStorage.getItem('user_id') || '0'))
              .map((p) => p.full_name.charAt(0))
              .join('')
              .toUpperCase() || 'C'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className="font-bold text-sm">{displayName}</div>
            {/* Connection Status Indicator */}
            <div className="flex items-center gap-1">
              {isConnected ? (
                <Wifi className="w-3 h-3 text-green-500" />
              ) : (
                <WifiOff className="w-3 h-3 text-red-500" />
              )}
              <span
                className={cn(
                  'text-xs px-2 py-0.5 rounded-full',
                  isConnected
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                )}
              >
                {isConnected ? 'Онлайн' : 'Оффлайн'}
              </span>
            </div>
          </div>
          {chat.subject && (
            <div className="text-xs text-muted-foreground">{chat.subject.name}</div>
          )}
          {chat.participants.length > 1 && (
            <div className="text-xs text-muted-foreground">
              {chat.participants.filter((p) => p.id !== parseInt(localStorage.getItem('user_id') || '0')).length} участник(и)
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 py-4 pr-4">
        <div className="space-y-4">
          {isLoadingMessages ? (
            <>
              <Skeleton className="h-12 rounded w-[70%]" />
              <Skeleton className="h-12 rounded w-[70%] ml-auto" />
              <Skeleton className="h-12 rounded w-[70%]" />
            </>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <MessageCircle className="w-8 h-8 text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">Начните общение с первого сообщения</p>
            </div>
          ) : (
            <>
              {messages.map((msg) => {
                const isOwn = msg.sender.id === parseInt(localStorage.getItem('user_id') || '0');
                return (
                  <div
                    key={msg.id}
                    className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[70%] p-3 rounded-lg ${
                        isOwn
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      {!isOwn && (
                        <p className="text-xs font-medium mb-1 opacity-75">
                          {msg.sender.full_name}
                        </p>
                      )}
                      <p className="text-sm break-words">{msg.content}</p>
                      <div
                        className={`text-xs mt-1 ${
                          isOwn
                            ? 'text-primary-foreground/70'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {new Date(msg.created_at).toLocaleTimeString('ru-RU', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Typing Indicator */}
              {typingUsers.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <div className="flex -space-x-1">
                    {typingUsers.slice(0, 3).map((user) => (
                      <Avatar key={user.id} className="w-6 h-6 border-2 border-background">
                        <AvatarFallback className="text-xs">
                          {user.first_name.charAt(0)}{user.last_name.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                    ))}
                  </div>
                  <span>
                    {typingUsers.length === 1
                      ? `${typingUsers[0].first_name} печатает...`
                      : `${typingUsers.length} пользователя печатают...`}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Message Input */}
      <div className="flex gap-2 pt-4 border-t">
        <Input
          placeholder="Введите сообщение..."
          value={messageInput}
          onChange={(e) => handleMessageChange(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isSending}
          className="text-sm"
        />
        <Button
          onClick={handleSend}
          disabled={!messageInput.trim() || isSending}
          className="gradient-primary"
        >
          {isSending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Offline Notice */}
      {!isConnected && (
        <div className="pt-2 text-xs text-muted-foreground text-center">
          Сообщения будут отправлены при восстановлении соединения
        </div>
      )}
    </Card>
  );
};

// Helper function to get the appropriate sidebar component based on role
const getSidebarComponent = (role: string) => {
  switch (role) {
    case 'student':
      return StudentSidebar;
    case 'teacher':
      return TeacherSidebar;
    case 'tutor':
      return TutorSidebar;
    case 'parent':
      return ParentSidebar;
    default:
      return null;
  }
};

export default function Forum() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [selectedChat, setSelectedChat] = useState<ForumChat | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: chats = [], isLoading: isLoadingChats } = useForumChats();
  const { data: messages = [], isLoading: isLoadingMessages } = useForumMessages(
    selectedChat?.id || null
  );
  const sendMessageMutation = useSendForumMessage();

  // WebSocket handlers (memoized)
  const handleWebSocketMessage = useCallback(
    (wsMessage: ChatMessage) => {
      console.log('[Forum] WebSocket message received in component handler:', {
        messageId: wsMessage.id,
        content: wsMessage.content.substring(0, 50),
        senderId: wsMessage.sender.id,
        selectedChatId: selectedChat?.id
      });

      if (!selectedChat) {
        console.warn('[Forum] Received message but no chat selected');
        return;
      }

      try {
        // Transform WebSocket message to ForumMessage format
        const forumMessage: ForumMessage = {
          id: wsMessage.id,
          content: wsMessage.content,
          sender: {
            id: wsMessage.sender.id,
            full_name: `${wsMessage.sender.first_name} ${wsMessage.sender.last_name}`.trim() || wsMessage.sender.username,
            role: wsMessage.sender.role,
          },
          created_at: wsMessage.created_at,
          updated_at: wsMessage.updated_at,
          is_read: wsMessage.is_read,
          message_type: wsMessage.message_type,
        };

        console.log('[Forum] Updating TanStack Query cache for chat:', selectedChat.id);
        // Update TanStack Query cache with new message
        queryClient.setQueryData(
          ['forum-messages', selectedChat.id, 50, 0],
          (oldData: ForumMessage[] | undefined) => {
            if (!oldData) {
              console.log('[Forum] No existing data, creating new array with message');
              return [forumMessage];
            }

            // Check if message already exists (avoid duplicates)
            const exists = oldData.some((msg: ForumMessage) => msg.id === forumMessage.id);
            if (exists) {
              console.log('[Forum] Message already exists in cache, skipping');
              return oldData;
            }

            console.log('[Forum] Adding new message to cache');
            return [...oldData, forumMessage];
          }
        );

        // Also invalidate chat list to update last_message and unread_count
        queryClient.invalidateQueries({ queryKey: ['forum-chats'] });

        // Clear any errors on successful message
        setError(null);
      } catch (err) {
        console.error('Error handling WebSocket message:', err);
        setError('Ошибка обработки сообщения');
      }
    },
    [selectedChat, queryClient]
  );

  const handleTyping = useCallback((user: TypingUser) => {
    setTypingUsers((prev) => {
      const filtered = prev.filter((u) => u.id !== user.id);
      return [...filtered, user];
    });

    // Remove user from typing list after 3 seconds
    setTimeout(() => {
      setTypingUsers((prev) => prev.filter((u) => u.id !== user.id));
    }, 3000);
  }, []);

  const handleTypingStop = useCallback((user: TypingUser) => {
    setTypingUsers((prev) => prev.filter((u) => u.id !== user.id));
  }, []);

  const handleError = useCallback((errorMessage: string) => {
    console.error('WebSocket error:', errorMessage);
    setError(errorMessage);
  }, []);

  // WebSocket connection management
  useEffect(() => {
    if (!selectedChat || !user) return;

    const chatId = selectedChat.id;

    const handlers = {
      onMessage: handleWebSocketMessage,
      onTyping: handleTyping,
      onTypingStop: handleTypingStop,
      onError: handleError,
    };

    // Connect to WebSocket for this chat room
    chatWebSocketService.connectToRoom(chatId, handlers);

    // Subscribe to connection state changes
    const connectionCallback = (connected: boolean) => {
      setIsConnected(connected);
      if (!connected) {
        setError('Соединение потеряно. Попытка переподключения...');
      } else {
        setError(null);
      }
    };

    chatWebSocketService.onConnectionChange(connectionCallback);

    // Cleanup: disconnect when chat changes or component unmounts
    return () => {
      chatWebSocketService.disconnectFromRoom(chatId);
      setTypingUsers([]);
    };
  }, [selectedChat, user, handleWebSocketMessage, handleTyping, handleTypingStop, handleError]);

  const handleSelectChat = (chat: ForumChat) => {
    setSelectedChat(chat);
    setSearchQuery('');
    setError(null);
    setTypingUsers([]);
  };

  const handleSendMessage = async (content: string) => {
    if (!selectedChat) return;

    try {
      setError(null);

      // Send ONLY via REST API to persist in database
      // Backend will broadcast via WebSocket to other connected users
      // This prevents duplicate sends and ensures message persistence
      await sendMessageMutation.mutateAsync({
        chatId: selectedChat.id,
        data: { content },
      });
    } catch (error: any) {
      console.error('Error sending message:', error);
      const errorMessage = error?.message || 'Ошибка отправки сообщения';
      setError(errorMessage);
    }
  };

  const handleRetryConnection = () => {
    setError(null);
    if (selectedChat) {
      // Force reconnect by toggling chat
      const chat = selectedChat;
      setSelectedChat(null);
      setTimeout(() => {
        setSelectedChat(chat);
      }, 100);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/auth', { replace: true });
    } catch (error) {
      console.error('Forum sign out error:', error);
    }
  };

  // Get the appropriate sidebar component based on user role
  const SidebarComponent = getSidebarComponent(user?.role || '');

  if (!SidebarComponent) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Неизвестная роль пользователя</p>
      </div>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <SidebarComponent />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="text-2xl font-bold ml-4">Форум</h1>
            <div className="flex-1" />
            <Button variant="outline" onClick={handleSignOut}>
              <LogOut className="w-4 h-4 mr-2" />
              Выйти
            </Button>
          </header>
          <main className="flex-1 overflow-auto p-6">
            <div className="space-y-6">
              <div>
                <p className="text-muted-foreground">Общайтесь с преподавателями и тьюторами</p>
              </div>

              <div className="grid md:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
                <ChatList
                  chats={chats}
                  selectedChat={selectedChat}
                  onSelectChat={handleSelectChat}
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  isLoading={isLoadingChats}
                />

                <ChatWindow
                  chat={selectedChat}
                  messages={messages}
                  isLoadingMessages={isLoadingMessages}
                  isSending={sendMessageMutation.isPending}
                  onSendMessage={handleSendMessage}
                  isConnected={isConnected}
                  typingUsers={typingUsers}
                  error={error}
                  onRetryConnection={handleRetryConnection}
                />
              </div>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
