import { useState, useMemo, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageCircle, Send, Search, Loader2 } from 'lucide-react';
import { useForumChats, useForumChatsWithRefresh } from '@/hooks/useForumChats';
import { useForumMessages, useSendForumMessage } from '@/hooks/useForumMessages';
import { ForumChat, ForumMessage } from '@/integrations/api/forumAPI';
import { Skeleton } from '@/components/ui/skeleton';
import { chatWebSocketService, ChatMessage } from '@/services/chatWebSocketService';

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
}: ChatWindowProps) => {
  const [messageInput, setMessageInput] = useState('');

  const handleSend = () => {
    if (messageInput.trim() && !isSending) {
      onSendMessage(messageInput.trim());
      setMessageInput('');
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
          <div className="font-bold text-sm">{displayName}</div>
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
            messages.map((msg) => {
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
            })
          )}
        </div>
      </ScrollArea>

      {/* Message Input */}
      <div className="flex gap-2 pt-4 border-t">
        <Input
          placeholder="Введите сообщение..."
          value={messageInput}
          onChange={(e) => setMessageInput(e.target.value)}
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
    </Card>
  );
};

export default function Forum() {
  const [selectedChat, setSelectedChat] = useState<ForumChat | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();

  const { data: chats = [], isLoading: isLoadingChats } = useForumChats();
  const { data: messages = [], isLoading: isLoadingMessages } = useForumMessages(
    selectedChat?.id || null
  );
  const sendMessageMutation = useSendForumMessage();

  // WebSocket integration for real-time messages
  useEffect(() => {
    if (!selectedChat) return;

    const chatId = selectedChat.id;

    const handlers = {
      onMessage: (wsMessage: ChatMessage) => {
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

        // Update TanStack Query cache with new message
        queryClient.setQueryData(
          ['forum-messages', chatId, 50, 0],
          (oldData: ForumMessage[] | undefined) => {
            if (!oldData) {
              return [forumMessage];
            }

            // Check if message already exists (avoid duplicates)
            const exists = oldData.some((msg: ForumMessage) => msg.id === forumMessage.id);
            if (exists) {
              return oldData;
            }

            return [...oldData, forumMessage];
          }
        );

        // Also invalidate chat list to update last_message and unread_count
        queryClient.invalidateQueries({ queryKey: ['forum-chats'] });
      },
    };

    // Connect to WebSocket for this chat room
    chatWebSocketService.connectToRoom(chatId, handlers);

    // Cleanup: disconnect when chat changes or component unmounts
    return () => {
      chatWebSocketService.disconnectFromRoom(chatId);
    };
  }, [selectedChat, queryClient]);

  const handleSelectChat = (chat: ForumChat) => {
    setSelectedChat(chat);
    setSearchQuery('');
  };

  const handleSendMessage = (content: string) => {
    if (selectedChat) {
      sendMessageMutation.mutate({
        chatId: selectedChat.id,
        data: { content },
      });
    }
  };

  return (
    <div className="space-y-6 h-full">
      <div>
        <h1 className="text-3xl font-bold">Форум</h1>
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
        />
      </div>
    </div>
  );
}
