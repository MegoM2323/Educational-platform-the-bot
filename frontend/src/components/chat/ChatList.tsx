import { useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, MessageSquare } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { ForumChat } from '@/integrations/api/forumAPICompat';

interface ChatListProps {
  chats: ForumChat[];
  selectedChat: ForumChat | null;
  onSelectChat: (chat: ForumChat) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isLoading: boolean;
  currentUserId: number;
}

interface ChatListItemProps {
  chat: ForumChat;
  selected: boolean;
  onClick: () => void;
  currentUserId: number;
}

const ChatListItem = ({ chat, selected, onClick, currentUserId }: ChatListItemProps) => {
  const initials = chat.participants
    .filter((p) => p.id !== currentUserId)
    .map((p) => p.full_name.charAt(0))
    .join('')
    .toUpperCase() || 'C';

  const otherParticipants = chat.participants
    .filter((p) => p.id !== currentUserId)
    .map((p) => p.full_name)
    .join(', ');

  const displayName = chat.name || otherParticipants || 'Чат';
  const lastMessagePreview = chat.last_message?.content || 'Нет сообщений';
  const lastMessageTime = chat.last_message?.created_at
    ? new Date(chat.last_message.created_at).toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      aria-selected={selected}
      aria-label={`Чат с ${displayName}`}
      className={cn(
        'p-3 rounded-lg cursor-pointer transition-colors border',
        selected ? 'bg-primary/10 border-primary' : 'border-transparent hover:bg-muted'
      )}
    >
      <div className="flex items-start gap-3">
        <Avatar className="w-10 h-10 flex-shrink-0">
          <AvatarFallback className="gradient-primary text-primary-foreground text-xs font-semibold">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="font-medium truncate text-sm">{displayName}</div>
            {chat.unread_count > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs flex-shrink-0">
                {chat.unread_count}
              </Badge>
            )}
          </div>
          {chat.subject && (
            <p className="text-xs text-muted-foreground mb-1 truncate">{chat.subject.name}</p>
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

export const ChatList = ({
  chats,
  selectedChat,
  onSelectChat,
  searchQuery,
  onSearchChange,
  isLoading,
  currentUserId,
}: ChatListProps) => {
  const filteredChats = useMemo(() => {
    if (!searchQuery) return chats;
    const query = searchQuery.toLowerCase();
    return chats.filter(
      (chat) =>
        chat.name.toLowerCase().includes(query) ||
        chat.subject?.name?.toLowerCase().includes(query) ||
        chat.participants.some((p) => p.full_name.toLowerCase().includes(query))
    );
  }, [chats, searchQuery]);

  return (
    <Card
      className="p-4 md:col-span-1 flex flex-col h-full overflow-hidden"
      data-testid="chat-list"
    >
      <div className="relative mb-4 flex-shrink-0">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Поиск чатов..."
          className="pl-10 text-sm"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Поиск чатов по названию или участнику"
          data-testid="chat-search"
        />
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="space-y-2 pr-4">
          {isLoading ? (
            <>
              <Skeleton className="h-20 rounded-lg" data-testid="chat-list-skeleton" />
              <Skeleton className="h-20 rounded-lg" data-testid="chat-list-skeleton" />
              <Skeleton className="h-20 rounded-lg" data-testid="chat-list-skeleton" />
            </>
          ) : filteredChats.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-8 text-center"
              data-testid="no-chats-message"
            >
              <MessageSquare className="h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium">Нет чатов</h3>
              <p className="text-gray-500">
                {searchQuery
                  ? 'Чатов не найдено'
                  : 'У вас пока нет доступных чатов. Начните общение!'}
              </p>
            </div>
          ) : (
            <div role="listbox" className="space-y-2">
              {filteredChats.map((chat) => (
                <ChatListItem
                  key={chat.id}
                  chat={chat}
                  selected={selectedChat?.id === chat.id}
                  onClick={() => onSelectChat(chat)}
                  currentUserId={currentUserId}
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </Card>
  );
};
