import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageCircle, Search, Users, Calendar } from 'lucide-react';
import { useAdminChats, useAdminChatMessages } from '@/hooks/useAdminChats';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface ChatRoom {
  id: number;
  name: string;
  description?: string;
  type: string;
  participants_count: number;
  participants: Array<{
    id: number;
    full_name: string;
    role: string;
  }>;
  subject?: {
    id: number;
    name: string;
  };
  last_message?: {
    id: number;
    content: string;
    sender: {
      id: number;
      full_name: string;
      role: string;
    };
    created_at: string;
  };
  unread_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Message {
  id: number;
  content: string;
  sender: {
    id: number;
    full_name: string;
    role: string;
  };
  sender_name: string;
  sender_role: string;
  created_at: string;
  updated_at: string;
  is_read: boolean;
  message_type: string;
}

interface ChatListProps {
  rooms: ChatRoom[];
  selectedRoom: ChatRoom | null;
  onSelectRoom: (room: ChatRoom) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isLoading: boolean;
}

interface MessageHistoryProps {
  room: ChatRoom | null;
  messages: Message[];
  isLoadingMessages: boolean;
}

const ChatListItem = ({ room, selected, onClick }: { room: ChatRoom; selected: boolean; onClick: () => void }) => {
  const initials = room.participants
    .map((p) => p.full_name.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 3) || 'C';

  const participantNames = room.participants
    .map((p) => p.full_name)
    .join(', ');

  const displayName = room.name || participantNames || 'Чат';
  const lastMessagePreview = room.last_message?.content || 'Нет сообщений';
  const lastMessageTime = room.last_message?.created_at
    ? new Date(room.last_message.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div
      onClick={onClick}
      className={cn(
        'p-3 rounded-lg cursor-pointer transition-colors border',
        selected
          ? 'bg-primary/10 border-primary'
          : 'border-transparent hover:bg-muted'
      )}
    >
      <div className="flex items-start gap-3">
        <Avatar className="w-10 h-10">
          <AvatarFallback className="gradient-primary text-primary-foreground text-xs">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="font-medium truncate text-sm">{displayName}</div>
            <Badge variant="outline" className="ml-2 text-xs">
              {room.participants_count} <Users className="w-3 h-3 ml-1" />
            </Badge>
          </div>
          {room.subject && (
            <p className="text-xs text-muted-foreground mb-1 truncate">
              Предмет: {room.subject.name}
            </p>
          )}
          <p className="text-xs text-blue-600 mb-1">
            Тип: {room.type === 'forum_subject' ? 'Форум (предмет)' : room.type}
          </p>
          <p className="text-xs text-muted-foreground truncate">{lastMessagePreview}</p>
          {lastMessageTime && (
            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {lastMessageTime}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ChatList = ({
  rooms,
  selectedRoom,
  onSelectRoom,
  searchQuery,
  onSearchChange,
  isLoading,
}: ChatListProps) => {
  const filteredRooms = useMemo(() => {
    if (!searchQuery) return rooms;
    const query = searchQuery.toLowerCase();
    return rooms.filter(
      (room) =>
        room.name.toLowerCase().includes(query) ||
        room.subject?.name?.toLowerCase().includes(query) ||
        room.participants.some((p) => p.full_name.toLowerCase().includes(query))
    );
  }, [rooms, searchQuery]);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <MessageCircle className="h-5 w-5" />
          Чаты ({rooms.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col overflow-hidden">
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
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
              </>
            ) : filteredRooms.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <MessageCircle className="w-8 h-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  {searchQuery ? 'Чатов не найдено' : 'Нет активных чатов'}
                </p>
              </div>
            ) : (
              filteredRooms.map((room) => (
                <ChatListItem
                  key={room.id}
                  room={room}
                  selected={selectedRoom?.id === room.id}
                  onClick={() => onSelectRoom(room)}
                />
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

const MessageHistory = ({ room, messages, isLoadingMessages }: MessageHistoryProps) => {
  if (!room) {
    return (
      <Card className="flex flex-col items-center justify-center h-full p-6">
        <MessageCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Выберите чат для просмотра истории сообщений</p>
      </Card>
    );
  }

  const participantNames = room.participants
    .map((p) => p.full_name)
    .join(', ');

  const displayName = room.name || participantNames || 'Чат';

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="border-b">
        <div className="flex items-center gap-3">
          <Avatar className="w-10 h-10">
            <AvatarFallback className="gradient-primary text-primary-foreground text-xs">
              {room.participants
                .map((p) => p.full_name.charAt(0))
                .join('')
                .toUpperCase()
                .slice(0, 3) || 'C'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <div className="font-bold text-sm">{displayName}</div>
            {room.subject && (
              <div className="text-xs text-muted-foreground">Предмет: {room.subject.name}</div>
            )}
            {room.participants.length > 0 && (
              <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                <Users className="w-3 h-3" />
                {room.participants_count} участник(ов)
              </div>
            )}
          </div>
          <Badge variant={room.is_active ? 'default' : 'secondary'}>
            {room.is_active ? 'Активен' : 'Неактивен'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full py-4 px-6">
          <div className="space-y-4">
            {isLoadingMessages ? (
              <>
                <Skeleton className="h-16 rounded w-[70%]" />
                <Skeleton className="h-16 rounded w-[70%] ml-auto" />
                <Skeleton className="h-16 rounded w-[70%]" />
              </>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <MessageCircle className="w-10 h-10 text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground">Нет сообщений в этом чате</p>
              </div>
            ) : (
              <>
                {messages.map((msg) => {
                  const senderInitials = msg.sender.full_name
                    .split(' ')
                    .map((n) => n.charAt(0))
                    .join('')
                    .toUpperCase();

                  return (
                    <div key={msg.id} className="flex gap-3">
                      <Avatar className="w-8 h-8 flex-shrink-0">
                        <AvatarFallback className="text-xs">
                          {senderInitials}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2 mb-1">
                          <span className="font-medium text-sm">{msg.sender.full_name}</span>
                          <Badge variant="outline" className="text-xs">
                            {msg.sender.role === 'student' ? 'Студент' :
                             msg.sender.role === 'teacher' ? 'Преподаватель' :
                             msg.sender.role === 'tutor' ? 'Тьютор' :
                             msg.sender.role === 'parent' ? 'Родитель' : msg.sender.role}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(msg.created_at).toLocaleString('ru-RU', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        <div className="bg-muted p-3 rounded-lg">
                          <p className="text-sm break-words whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </ScrollArea>
      </CardContent>

      {/* Read-only notice */}
      <div className="px-6 py-3 border-t bg-muted/30">
        <p className="text-xs text-muted-foreground text-center">
          Просмотр истории сообщений (только для чтения)
        </p>
      </div>
    </Card>
  );
};

export default function AdminChatsPage() {
  const [selectedRoom, setSelectedRoom] = useState<ChatRoom | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { rooms, isLoading: isLoadingChats, roomsError } = useAdminChats();
  const { messages, isLoading: isLoadingMessages } = useAdminChatMessages(selectedRoom?.id || null);

  const chatsError = roomsError ? new Error(roomsError) : null;

  const handleSelectRoom = (room: ChatRoom) => {
    setSelectedRoom(room);
    setSearchQuery('');
  };

  if (chatsError) {
    return (
      <div className="container mx-auto p-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-500">Ошибка загрузки чатов: {chatsError.message}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Управление чатами</h1>
        <p className="text-muted-foreground">Просмотр всех чатов и истории сообщений (только для чтения)</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        <div className="md:col-span-1">
          <ChatList
            rooms={rooms}
            selectedRoom={selectedRoom}
            onSelectRoom={handleSelectRoom}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            isLoading={isLoadingChats}
          />
        </div>

        <div className="md:col-span-2">
          <MessageHistory
            room={selectedRoom}
            messages={messages}
            isLoadingMessages={isLoadingMessages}
          />
        </div>
      </div>
    </div>
  );
}
