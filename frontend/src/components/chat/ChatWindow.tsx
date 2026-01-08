import { useRef, useEffect, useCallback, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import {
  MessageCircle,
  Loader2,
  Wifi,
  WifiOff,
  AlertCircle,
  Users,
  Lock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ForumChat, ForumMessage, TypingUser } from '@/integrations/api/forumAPICompat';

interface ChatWindowProps {
  chat: ForumChat | null;
  messages: ForumMessage[];
  isLoadingMessages: boolean;
  isSending: boolean;
  onSendMessage: (content: string) => void;
  isConnected: boolean;
  typingUsers?: TypingUser[];
  error?: string | null;
  onRetryConnection?: () => void;
  currentUserId: number;
  currentUserRole?: string;
  isSwitchingChat?: boolean;
  renderMessageInput?: () => React.ReactNode;
  renderHeader?: (chat: ForumChat) => React.ReactNode;
}

interface TypingUser {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
}

const MessageBubble = ({
  message,
  isOwn,
  currentUserId,
}: {
  message: ForumMessage;
  isOwn: boolean;
  currentUserId: number;
}) => {
  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
      <div
        className={cn(
          'max-w-[70%] p-3 rounded-lg',
          isOwn ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        {!isOwn && (
          <p className="text-xs font-medium mb-1 opacity-75">{message.sender.full_name}</p>
        )}
        <p className="text-sm break-words">{message.content}</p>
        <div
          className={cn(
            'text-xs mt-1',
            isOwn ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}
        >
          {new Date(message.created_at).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  );
};

export const ChatWindow = ({
  chat,
  messages,
  isLoadingMessages,
  isSending,
  onSendMessage,
  isConnected,
  typingUsers = [],
  error = null,
  onRetryConnection,
  currentUserId,
  currentUserRole = '',
  isSwitchingChat = false,
  renderMessageInput,
  renderHeader,
}: ChatWindowProps) => {
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);

  const scrollToBottom = useCallback(() => {
    if (shouldAutoScrollRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const isAtBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100;
    shouldAutoScrollRef.current = isAtBottom;
  }, []);

  const isReadOnly = currentUserRole === 'admin';
  const isChatInactive = chat && !chat.is_active;

  const otherParticipants = useMemo(() => {
    if (!chat) return '';
    return chat.participants
      .filter((p) => p.id !== currentUserId)
      .map((p) => p.full_name)
      .join(', ');
  }, [chat, currentUserId]);

  const displayName = useMemo(() => {
    if (!chat) return '';
    return chat.name || otherParticipants || 'Чат';
  }, [chat, otherParticipants]);

  if (!chat) {
    return (
      <Card
        className="p-6 md:col-span-2 flex flex-col items-center justify-center h-full overflow-hidden"
        data-testid="chat-window-empty"
      >
        <Users className="h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium">Выберите чат</h3>
        <p className="text-gray-500">
          Выберите чат из списка слева для начала общения
        </p>
      </Card>
    );
  }

  return (
    <Card
      className="p-6 md:col-span-2 flex flex-col h-full overflow-hidden"
      data-testid="chat-window"
    >
      {error && (
        <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-3 flex-shrink-0">
          <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-destructive font-medium">{error}</p>
          </div>
          {onRetryConnection && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onRetryConnection}
              className="text-xs flex-shrink-0"
            >
              Повторить
            </Button>
          )}
        </div>
      )}

      {renderHeader ? (
        renderHeader(chat)
      ) : (
        <div className="flex items-center gap-3 pb-4 border-b flex-shrink-0" data-testid="chat-header">
          <Avatar className="w-10 h-10">
            <AvatarFallback className="gradient-primary text-primary-foreground text-xs font-semibold">
              {chat.participants
                .filter((p) => p.id !== currentUserId)
                .map((p) => p.full_name.charAt(0))
                .join('')
                .toUpperCase() || 'C'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
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
            </div>
            {chat.subject && (
              <div className="text-xs text-muted-foreground">{chat.subject.name}</div>
            )}
            {chat.participants.length > 1 && (
              <div className="text-xs text-muted-foreground">
                {chat.participants.filter((p) => p.id !== currentUserId).length} участник(и)
              </div>
            )}
          </div>
        </div>
      )}

      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto py-4 pr-4 min-h-0"
        onScroll={handleScroll}
        role="log"
        aria-live="polite"
        aria-label="Сообщения чата"
      >
        <div className="space-y-4">
          {isSwitchingChat || isLoadingMessages ? (
            <div className="space-y-4" data-testid="messages-loading">
              <Skeleton className="h-12 rounded w-[70%]" />
              <Skeleton className="h-12 rounded w-[70%] ml-auto" />
              <Skeleton className="h-12 rounded w-[70%]" />
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground mr-2" />
                <span className="text-sm text-muted-foreground">
                  {isSwitchingChat ? 'Переключение чата...' : 'Загрузка сообщений...'}
                </span>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <MessageCircle className="h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium">Нет сообщений</h3>
              <p className="text-gray-500">Напишите первое сообщение в этом чате!</p>
            </div>
          ) : (
            messages.map((msg) => {
              const isOwn = msg.sender.id === currentUserId;
              return (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isOwn={isOwn}
                  currentUserId={currentUserId}
                />
              );
            })
          )}

          {typingUsers.length > 0 && (
            <div className="flex gap-2 items-center text-xs text-muted-foreground italic">
              <span>
                {typingUsers.map((u) => u.first_name).join(', ')} печатает...
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="pt-4 border-t flex-shrink-0">
        {isReadOnly || isChatInactive ? (
          <div className="p-3 bg-muted/50 rounded-lg border border-muted-foreground/20 flex items-center justify-center gap-2">
            <Lock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <span className="text-sm text-muted-foreground">
              {isChatInactive ? 'Чат заблокирован модератором' : 'Доступ только для чтения'}
            </span>
          </div>
        ) : renderMessageInput ? (
          renderMessageInput()
        ) : (
          <div className="text-sm text-muted-foreground text-center p-2">
            Передайте renderMessageInput проп для отображения ввода сообщения
          </div>
        )}
      </div>
    </Card>
  );
};
