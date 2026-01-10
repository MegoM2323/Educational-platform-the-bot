import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Wifi, WifiOff, Lock, Unlock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ForumChat } from '@/integrations/api/forumAPICompat';

interface ChatHeaderProps {
  chat: ForumChat;
  currentUserId: number;
  isConnected: boolean;
  currentUserRole: string;
  onLockChat?: (chatId: number) => void;
}

export const ChatHeader = ({
  chat,
  currentUserId,
  isConnected,
  currentUserRole,
  onLockChat,
}: ChatHeaderProps) => {
  const otherParticipants = chat.participants
    .filter((p) => p.id !== currentUserId)
    .map((p) => p.user_name)
    .join(', ');

  const displayName = chat.name || otherParticipants || 'Чат';
  const isChatInactive = !chat.is_active;

  return (
    <div className="flex items-center gap-3 pb-4 border-b flex-shrink-0" data-testid="chat-header">
      <Avatar className="w-10 h-10">
        <AvatarFallback className="gradient-primary text-primary-foreground">
          {chat.participants
            .filter((p) => p.id !== currentUserId)
            .map((p) => p.user_name.charAt(0))
            .join('')
            .toUpperCase() || 'C'}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <div className="font-bold text-sm">{displayName}</div>
          {isChatInactive && (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800">
              <Lock className="w-3 h-3" />
              <span className="text-xs">Заблокирован</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            {isConnected ? (
              <Wifi className="w-3 h-3 text-green-500" />
            ) : (
              <WifiOff className="w-3 h-3 text-red-500" />
            )}
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full',
                isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              )}
            >
              {isConnected ? 'Онлайн' : 'Оффлайн'}
            </span>
          </div>
          {['teacher', 'tutor', 'admin'].includes(currentUserRole) && onLockChat && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onLockChat(chat.id)}
              title={chat.is_active ? 'Заблокировать чат' : 'Разблокировать чат'}
              className="h-7 w-7 p-0"
            >
              {chat.is_active ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
            </Button>
          )}
        </div>
        {chat.subject && <div className="text-xs text-muted-foreground">{chat.subject.name}</div>}
        {chat.participants.length > 1 && (
          <div className="text-xs text-muted-foreground">
            {chat.participants.filter((p) => p.id !== currentUserId).length} участник(и)
          </div>
        )}
      </div>
    </div>
  );
};
