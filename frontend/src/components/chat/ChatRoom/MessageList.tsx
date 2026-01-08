import { useCallback } from 'react';
import { Loader2, MessageCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { ForumMessage } from '@/integrations/api/forumAPICompat';
import { MessageItem } from './MessageItem';

interface MessageListProps {
  messages: ForumMessage[];
  isLoading: boolean;
  hasMore: boolean;
  isFetchingMore: boolean;
  onLoadMore: () => void;
  onEditMessage?: (messageId: number, content: string) => void;
  onDeleteMessage?: (messageId: number) => void;
  onPinMessage?: (messageId: number) => void;
  currentUserId: number;
  currentUserRole: string;
  chatType?: string;
  isEditingOrDeleting: boolean;
  isSwitchingChat?: boolean;
}

export const MessageList = ({
  messages,
  isLoading,
  hasMore,
  isFetchingMore,
  onLoadMore,
  onEditMessage,
  onDeleteMessage,
  onPinMessage,
  currentUserId,
  currentUserRole,
  chatType,
  isEditingOrDeleting,
  isSwitchingChat = false,
}: MessageListProps) => {
  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const target = e.target as HTMLDivElement;
      if (target.scrollTop < 100 && hasMore && !isFetchingMore) {
        onLoadMore();
      }
    },
    [hasMore, isFetchingMore, onLoadMore]
  );

  const canModerate = (() => {
    if (currentUserRole === 'teacher') return true;
    if (currentUserRole === 'tutor' && chatType === 'forum_tutor') return true;
    if (currentUserRole === 'admin') return true;
    return false;
  })();

  return (
    <div
      className="flex-1 overflow-y-auto py-4 pr-4 min-h-0"
      onScroll={handleScroll}
    >
      <div className="space-y-4">
        {isFetchingMore && (
          <div className="flex items-center justify-center py-2">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground mr-2" />
            <span className="text-sm text-muted-foreground">Загрузка старых сообщений...</span>
          </div>
        )}

        {isSwitchingChat || isLoading ? (
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
              <MessageItem
                key={msg.id}
                message={msg}
                isOwn={isOwn}
                canModerate={canModerate}
                onEdit={(content) => onEditMessage?.(msg.id, content)}
                onDelete={() => onDeleteMessage?.(msg.id)}
                onPin={onPinMessage ? () => onPinMessage(msg.id) : undefined}
                isEditingOrDeleting={isEditingOrDeleting}
              />
            );
          })
        )}
      </div>
    </div>
  );
};
