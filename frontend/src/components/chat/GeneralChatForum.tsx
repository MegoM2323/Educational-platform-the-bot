import { useState, useRef, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  MessageCircle, 
  Send, 
  Pin, 
  PinOff, 
  Lock, 
  Unlock, 
  Plus,
  Reply,
  MoreVertical,
  Users,
  Wifi,
  WifiOff
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/contexts/AuthContext';
import {
  useGeneralChatMessages,
  useGeneralChatThreads,
  useSendGeneralMessage,
  useSendThreadMessage,
  useCreateThread,
  usePinThread,
  useUnpinThread,
  useLockThread,
  useUnlockThread,
} from '@/hooks/useGeneralChatHooks';
import { ChatMessage, ChatThread } from '@/integrations/api/chatService';
import { cn } from '@/lib/utils';
import { useErrorNotification, useSuccessNotification } from '@/components/NotificationSystem';
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/LoadingStates';
import { chatWebSocketService, ChatMessage as WebSocketChatMessage, TypingUser } from '@/services/chatWebSocketService';

interface GeneralChatForumProps {
  className?: string;
}

export function GeneralChatForum({ className }: GeneralChatForumProps) {
  const { user } = useAuth();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();
  
  const [selectedThread, setSelectedThread] = useState<ChatThread | null>(null);
  const [message, setMessage] = useState('');
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null);
  const [isCreateThreadOpen, setIsCreateThreadOpen] = useState(false);
  const [newThreadTitle, setNewThreadTitle] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  const [messages, setMessages] = useState<WebSocketChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Запросы данных
  const { data: threads = [], isLoading: threadsLoading } = useGeneralChatThreads(20, 0);
  const { data: generalMessages = [], isLoading: messagesLoading } = useGeneralChatMessages(50, 0);
  const { data: threadMessagesData = [], isLoading: threadMessagesLoading } = useThreadMessages(
    selectedThread?.id || 0,
    50, 
    0
  );
  const threadMessages = selectedThread ? threadMessagesData : [];

  // Мутации
  const sendGeneralMessage = useSendGeneralMessage();
  const sendThreadMessage = useSendThreadMessage(selectedThread?.id || 0);
  const createThread = useCreateThread();
  const pinThread = usePinThread();
  const unpinThread = useUnpinThread();
  const lockThread = useLockThread();
  const unlockThread = useUnlockThread();

  // WebSocket обработчики
  const handleWebSocketMessage = useCallback((message: WebSocketChatMessage) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const handleTyping = useCallback((user: TypingUser) => {
    setTypingUsers(prev => {
      const filtered = prev.filter(u => u.id !== user.id);
      return [...filtered, user];
    });

    // Убираем пользователя из списка печатающих через 3 секунды
    setTimeout(() => {
      setTypingUsers(prev => prev.filter(u => u.id !== user.id));
    }, 3000);
  }, []);

  const handleTypingStop = useCallback((user: TypingUser) => {
    setTypingUsers(prev => prev.filter(u => u.id !== user.id));
  }, []);

  const handleRoomHistory = useCallback((historyMessages: WebSocketChatMessage[]) => {
    setMessages(historyMessages);
  }, []);

  const handleError = useCallback((error: string) => {
    setError(error);
    showError(error);
  }, [showError]);

  // Подключение к WebSocket при монтировании компонента
  useEffect(() => {
    if (user) {
      chatWebSocketService.connectToGeneralChat({
        onMessage: handleWebSocketMessage,
        onTyping: handleTyping,
        onTypingStop: handleTypingStop,
        onRoomHistory: handleRoomHistory,
        onError: handleError,
      });

      // Подписка на изменения состояния соединения
      chatWebSocketService.onConnectionChange(setIsConnected);
    }

    return () => {
      chatWebSocketService.disconnectFromChat();
    };
  }, [user, handleWebSocketMessage, handleTyping, handleTypingStop, handleRoomHistory, handleError]);

  // Автоскролл к последнему сообщению
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typingUsers]);

  // Обработчики
  const handleSendMessage = async () => {
    if (!message.trim()) return;

    const messageContent = message.trim();

    try {
      setError(null);
      
      // Отправляем через WebSocket для real-time обновления
      if (selectedThread) {
        chatWebSocketService.sendRoomMessage(selectedThread.id, messageContent);
      } else {
        chatWebSocketService.sendGeneralMessage(messageContent);
      }

      // Также отправляем через API для сохранения в базе данных
      const messageData = {
        content: messageContent,
        message_type: 'text' as const,
        thread_id: selectedThread?.id,
        reply_to: replyTo?.id,
      };

      if (selectedThread) {
        await sendThreadMessage.mutateAsync(messageData);
      } else {
        await sendGeneralMessage.mutateAsync(messageData);
      }

      setMessage('');
      setReplyTo(null);
      showSuccess('Сообщение отправлено');
    } catch (error: any) {
      console.error('Ошибка отправки сообщения:', error);
      const errorMessage = error?.message || 'Ошибка отправки сообщения';
      setError(errorMessage);
      showError(errorMessage, {
        action: {
          label: 'Повторить',
          onClick: handleSendMessage,
        },
      });
    }
  };

  // Обработчик изменения текста с индикатором печати
  const handleMessageChange = (value: string) => {
    setMessage(value);
    
    // Отправляем индикатор печати
    if (value.trim() && isConnected) {
      chatWebSocketService.sendTyping();
      chatWebSocketService.startTypingTimer();
    }
  };

  const handleCreateThread = async () => {
    if (!newThreadTitle.trim()) return;

    try {
      setError(null);
      await createThread.mutateAsync({ title: newThreadTitle.trim() });
      setNewThreadTitle('');
      setIsCreateThreadOpen(false);
      showSuccess('Тред создан успешно');
    } catch (error: any) {
      console.error('Ошибка создания треда:', error);
      const errorMessage = error?.message || 'Ошибка создания треда';
      setError(errorMessage);
      showError(errorMessage, {
        action: {
          label: 'Повторить',
          onClick: handleCreateThread,
        },
      });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'teacher':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'student':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'parent':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRoleDisplay = (role: string) => {
    switch (role) {
      case 'teacher':
        return 'Преподаватель';
      case 'student':
        return 'Студент';
      case 'parent':
        return 'Родитель';
      default:
        return role;
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 1) {
      return 'только что';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)}ч назад`;
    } else {
      return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
  };

  const currentMessages = selectedThread ? threadMessagesData : messages;
  const isLoading = selectedThread ? threadMessagesLoading : messagesLoading;

  return (
    <div className={cn('flex h-[calc(100vh-200px)] gap-4', className)}>
      {/* Обработка ошибок */}
      {error && (
        <div className="absolute top-4 left-4 right-4 z-50">
          <ErrorState 
            error={error}
            onRetry={() => setError(null)}
            className="mb-4"
          />
        </div>
      )}

      {/* Список тредов */}
      <Card className="w-80 p-4 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Общий форум</h3>
          <Dialog open={isCreateThreadOpen} onOpenChange={setIsCreateThreadOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gradient-primary">
                <Plus className="w-4 h-4 mr-2" />
                Новый тред
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Создать новый тред</DialogTitle>
                <DialogDescription>
                  Создайте новый тред для обсуждения темы
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="thread-title">Заголовок треда</Label>
                  <Input
                    id="thread-title"
                    value={newThreadTitle}
                    onChange={(e) => setNewThreadTitle(e.target.value)}
                    placeholder="Введите заголовок треда..."
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateThreadOpen(false)}>
                  Отмена
                </Button>
                <Button 
                  onClick={handleCreateThread}
                  disabled={!newThreadTitle.trim() || createThread.isPending}
                  className="gradient-primary"
                >
                  {createThread.isPending ? 'Создание...' : 'Создать'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <ScrollArea className="flex-1">
          <div className="space-y-2">
            {/* Общий чат */}
            <div
              onClick={() => setSelectedThread(null)}
              className={cn(
                'p-3 rounded-lg cursor-pointer transition-colors border',
                !selectedThread 
                  ? 'bg-primary/10 border-primary' 
                  : 'hover:bg-muted border-transparent'
              )}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
                  <MessageCircle className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium">Общий чат</div>
                  <div className="text-sm text-muted-foreground">
                    {generalMessages.length} сообщений
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Треды */}
            {threadsLoading ? (
              <div className="text-center py-4">
                <LoadingSpinner size="sm" text="Загрузка тредов..." />
              </div>
            ) : (
              threads.map((thread) => (
                <div
                  key={thread.id}
                  onClick={() => setSelectedThread(thread)}
                  className={cn(
                    'p-3 rounded-lg cursor-pointer transition-colors border',
                    selectedThread?.id === thread.id
                      ? 'bg-primary/10 border-primary'
                      : 'hover:bg-muted border-transparent'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-r from-green-500 to-blue-500 flex items-center justify-center">
                      <MessageCircle className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="font-medium truncate">{thread.title}</div>
                        {thread.is_pinned && (
                          <Pin className="w-3 h-3 text-yellow-500" />
                        )}
                        {thread.is_locked && (
                          <Lock className="w-3 h-3 text-red-500" />
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {thread.messages_count} сообщений
                      </div>
                      {thread.last_message && (
                        <div className="text-xs text-muted-foreground mt-1 truncate">
                          {thread.last_message.content}
                        </div>
                      )}
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {thread.is_pinned ? (
                          <DropdownMenuItem onClick={() => unpinThread.mutate(thread.id)}>
                            <PinOff className="w-4 h-4 mr-2" />
                            Открепить
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => pinThread.mutate(thread.id)}>
                            <Pin className="w-4 h-4 mr-2" />
                            Закрепить
                          </DropdownMenuItem>
                        )}
                        {thread.is_locked ? (
                          <DropdownMenuItem onClick={() => unlockThread.mutate(thread.id)}>
                            <Unlock className="w-4 h-4 mr-2" />
                            Разблокировать
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => lockThread.mutate(thread.id)}>
                            <Lock className="w-4 h-4 mr-2" />
                            Заблокировать
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </Card>

      {/* Область сообщений */}
      <Card className="flex-1 flex flex-col">
        {/* Заголовок */}
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold">
                  {selectedThread ? selectedThread.title : 'Общий чат'}
                </h2>
                <div className="flex items-center gap-2">
                  {isConnected ? (
                    <Wifi className="w-4 h-4 text-green-500" />
                  ) : (
                    <WifiOff className="w-4 h-4 text-red-500" />
                  )}
                  <span className={cn(
                    "text-xs px-2 py-1 rounded-full",
                    isConnected 
                      ? "bg-green-100 text-green-800" 
                      : "bg-red-100 text-red-800"
                  )}>
                    {isConnected ? 'Подключено' : 'Отключено'}
                  </span>
                </div>
              </div>
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Users className="w-4 h-4" />
                {selectedThread ? selectedThread.messages_count : messages.length} сообщений
                {selectedThread && selectedThread.is_locked && (
                  <Badge variant="destructive" className="ml-2">
                    <Lock className="w-3 h-3 mr-1" />
                    Заблокирован
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Сообщения */}
        <ScrollArea className="flex-1 p-4">
          {isLoading ? (
            <div className="text-center py-8">
              <LoadingSpinner size="md" text="Загрузка сообщений..." />
            </div>
          ) : currentMessages.length === 0 ? (
            <EmptyState
              title="Пока нет сообщений"
              description="Начните обсуждение, отправив первое сообщение!"
              icon={<MessageCircle className="w-8 h-8 text-muted-foreground" />}
            />
          ) : (
            <div className="space-y-4">
              {currentMessages.map((msg) => (
                <div key={msg.id} className="flex gap-3">
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="text-xs">
                      {msg.sender.first_name[0]}{msg.sender.last_name[0]}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">
                        {msg.sender.first_name} {msg.sender.last_name}
                      </span>
                      <Badge 
                        variant="outline" 
                        className={cn('text-xs', getRoleColor(msg.sender.role))}
                      >
                        {getRoleDisplay(msg.sender.role)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(msg.created_at)}
                      </span>
                    </div>
                    <div className="text-sm">
                      {msg.reply_to && (
                        <div className="bg-muted p-2 rounded mb-2 text-xs border-l-2 border-primary">
                          <div className="font-medium">
                            {msg.reply_to.sender.first_name} {msg.reply_to.sender.last_name}
                          </div>
                          <div className="text-muted-foreground">
                            {msg.reply_to.content}
                          </div>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-2 text-xs"
                        onClick={() => setReplyTo(msg)}
                      >
                        <Reply className="w-3 h-3 mr-1" />
                        Ответить
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
              
              {/* Индикатор печати */}
              {typingUsers.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <div className="flex -space-x-1">
                    {typingUsers.slice(0, 3).map((user) => (
                      <Avatar key={user.id} className="w-6 h-6 border-2 border-background">
                        <AvatarFallback className="text-xs">
                          {user.first_name[0]}{user.last_name[0]}
                        </AvatarFallback>
                      </Avatar>
                    ))}
                  </div>
                  <span>
                    {typingUsers.length === 1 
                      ? `${typingUsers[0].first_name} печатает...`
                      : `${typingUsers.length} пользователя печатают...`
                    }
                  </span>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Поле ввода */}
        {selectedThread?.is_locked ? (
          <div className="p-4 border-t bg-muted/50">
            <div className="text-center text-muted-foreground">
              <Lock className="w-5 h-5 mx-auto mb-2" />
              Этот тред заблокирован для новых сообщений
            </div>
          </div>
        ) : (
          <div className="p-4 border-t">
            {replyTo && (
              <div className="mb-3 p-2 bg-muted rounded border-l-2 border-primary">
                <div className="flex items-center justify-between">
                  <div className="text-sm">
                    <span className="font-medium">Ответ на:</span>
                    <span className="ml-2 text-muted-foreground">
                      {replyTo.sender.first_name} {replyTo.sender.last_name}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setReplyTo(null)}
                    className="h-6 w-6 p-0"
                  >
                    ×
                  </Button>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {replyTo.content}
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <Textarea
                value={message}
                onChange={(e) => handleMessageChange(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={isConnected ? "Введите сообщение..." : "Подключение к чату..."}
                className="min-h-[40px] max-h-32 resize-none"
                disabled={!isConnected || sendGeneralMessage.isPending || sendThreadMessage.isPending}
              />
              <Button
                onClick={handleSendMessage}
                disabled={!message.trim() || !isConnected || sendGeneralMessage.isPending || sendThreadMessage.isPending}
                className="gradient-primary"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
