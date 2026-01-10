import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Chat } from '@/integrations/api/chatAPI';

interface ChatListItemProps {
  chat: Chat;
  selected: boolean;
  onClick: () => void;
  currentUserId: number;
}

export const ChatListItem = ({ chat, selected, onClick, currentUserId }: ChatListItemProps) => {
  const initials =
    chat.participants
      .filter((p) => p.id !== currentUserId)
      .map((p) => p.user_name.charAt(0))
      .join('')
      .toUpperCase() || 'C';

  const otherParticipants = chat.participants
    .filter((p) => p.id !== currentUserId)
    .map((p) => p.user_name)
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
      data-testid="chat-item"
      className={`p-3 rounded-lg cursor-pointer transition-colors border ${
        selected ? 'bg-primary/10 border-primary' : 'border-transparent hover:bg-muted'
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
