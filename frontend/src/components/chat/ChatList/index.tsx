import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, MessageSquare } from 'lucide-react';
import { Chat } from '@/integrations/api/chatAPI';
import { ChatListItem } from './ChatListItem';
import { ChatListSkeleton } from './ChatListSkeleton';

interface ChatListProps {
  chats: Chat[];
  selectedChat: Chat | null;
  onSelectChat: (chat: Chat) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isLoading: boolean;
  currentUserId: number;
}

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
        chat.participants.some((p) => p.user_name.toLowerCase().includes(query))
    );
  }, [chats, searchQuery]);

  return (
    <Card className="p-4 md:col-span-1 flex flex-col h-full overflow-hidden" data-testid="chat-list">
      <div className="relative mb-4 flex-shrink-0">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Поиск чатов..."
          className="pl-10 text-sm"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          data-testid="chat-search"
        />
      </div>
      <ScrollArea className="flex-1 min-h-0">
        <div className="space-y-2 pr-4">
          {isLoading ? (
            <ChatListSkeleton />
          ) : filteredChats.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-8 text-center"
              data-testid="no-chats-message"
            >
              <MessageSquare className="h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium">Нет чатов</h3>
              <p className="text-gray-500">
                {searchQuery ? 'Чатов не найдено' : 'У вас пока нет доступных чатов. Начните общение!'}
              </p>
            </div>
          ) : (
            filteredChats.map((chat) => (
              <ChatListItem
                key={chat.id}
                chat={chat}
                selected={selectedChat?.id === chat.id}
                onClick={() => onSelectChat(chat)}
                currentUserId={currentUserId}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </Card>
  );
};
