import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, Users } from 'lucide-react';
import { Chat, ChatMessage } from '@/integrations/api/chatAPI';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

interface ChatRoomProps {
  chat: Chat | null;
  messages: ChatMessage[];
  isLoadingMessages: boolean;
  isSending: boolean;
  onSendMessage: (content: string, file?: File) => void;
  isConnected: boolean;
  error: string | null;
  onRetryConnection: () => void;
  onEditMessage: (messageId: number, content: string) => void;
  onDeleteMessage: (messageId: number) => void;
  onPinMessage?: (messageId: number) => void;
  onLockChat?: (chatId: number) => void;
  isEditingOrDeleting: boolean;
  currentUserId: number;
  currentUserRole: string;
  isSwitchingChat?: boolean;
  fetchNextPage?: () => void;
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  onTyping?: () => void;
}

export const ChatRoom = ({
  chat,
  messages,
  isLoadingMessages,
  isSending,
  onSendMessage,
  isConnected,
  error,
  onRetryConnection,
  onEditMessage,
  onDeleteMessage,
  onPinMessage,
  onLockChat,
  isEditingOrDeleting,
  currentUserId,
  currentUserRole,
  isSwitchingChat = false,
  fetchNextPage,
  hasNextPage = false,
  isFetchingNextPage = false,
  onTyping,
}: ChatRoomProps) => {
  const isReadOnly = currentUserRole === 'admin';
  const isChatInactive = chat && !chat.is_active;

  if (!chat) {
    return (
      <Card
        className="p-6 md:col-span-2 flex flex-col items-center justify-center h-full overflow-hidden"
        data-testid="chat-window-empty"
      >
        <Users className="h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium">Выберите чат</h3>
        <p className="text-gray-500">Выберите чат из списка слева для начала общения</p>
      </Card>
    );
  }

  return (
    <Card className="p-6 md:col-span-2 flex flex-col h-full overflow-hidden" data-testid="chat-window">
      {error && (
        <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-3 flex-shrink-0">
          <AlertCircle className="w-5 h-5 text-destructive" />
          <div className="flex-1">
            <p className="text-sm text-destructive font-medium">{error}</p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={onRetryConnection}
            className="text-xs"
          >
            Повторить
          </Button>
        </div>
      )}

      <ChatHeader
        chat={chat}
        currentUserId={currentUserId}
        isConnected={isConnected}
        currentUserRole={currentUserRole}
        onLockChat={onLockChat}
      />

      <MessageList
        messages={messages}
        isLoading={isLoadingMessages}
        hasMore={hasNextPage}
        isFetchingMore={isFetchingNextPage}
        onLoadMore={fetchNextPage || (() => {})}
        onEditMessage={onEditMessage}
        onDeleteMessage={onDeleteMessage}
        onPinMessage={onPinMessage}
        currentUserId={currentUserId}
        currentUserRole={currentUserRole}
        chatType={chat.type}
        isEditingOrDeleting={isEditingOrDeleting}
        isSwitchingChat={isSwitchingChat}
      />

      <div className="pt-4 border-t flex-shrink-0">
        <MessageInput
          onSend={onSendMessage}
          onTyping={onTyping}
          connectionStatus={isConnected ? 'connected' : 'disconnected'}
          isLoading={isSending}
          isReadOnly={isReadOnly}
          isChatInactive={isChatInactive}
        />
      </div>
    </Card>
  );
};
