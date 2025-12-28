import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { logger } from '@/utils/logger';
import { useQueryClient, useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  MessageCircle,
  Send,
  Search,
  Loader2,
  Wifi,
  WifiOff,
  AlertCircle,
  Plus,
  CheckCircle2,
  Filter,
  Paperclip,
  FileText,
  Image as ImageIcon,
  Download,
  X,
  MessageSquare,
  Users,
} from 'lucide-react';
import { useForumChats, useForumChatsWithRefresh } from '@/hooks/useForumChats';
import { useForumMessages, useSendForumMessage } from '@/hooks/useForumMessages';
import { ForumChat, ForumMessage, Contact, forumAPI } from '@/integrations/api/forumAPI';
import { Skeleton } from '@/components/ui/skeleton';
import {
  chatWebSocketService,
  ChatMessage,
  TypingUser,
} from '@/services/chatWebSocketService';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { StudentSidebar } from '@/components/layout/StudentSidebar';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { TutorSidebar } from '@/components/layout/TutorSidebar';
import { ParentSidebar } from '@/components/layout/ParentSidebar';
import { useToast } from '@/hooks/use-toast';
import { MessageActions } from '@/components/forum/MessageActions';
import { EditMessageDialog } from '@/components/forum/EditMessageDialog';
import { useForumMessageUpdate } from '@/hooks/useForumMessageUpdate';
import { useForumMessageDelete } from '@/hooks/useForumMessageDelete';

interface ChatListProps {
  chats: ForumChat[];
  selectedChat: ForumChat | null;
  onSelectChat: (chat: ForumChat) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isLoading: boolean;
  currentUserId: number;
}

interface ChatWindowProps {
  chat: ForumChat | null;
  messages: ForumMessage[];
  isLoadingMessages: boolean;
  isSending: boolean;
  onSendMessage: (content: string, file?: File) => void;
  isConnected: boolean;
  typingUsers: TypingUser[];
  error: string | null;
  onRetryConnection: () => void;
  onEditMessage: (messageId: number, content: string) => void;
  onDeleteMessage: (messageId: number) => void;
  isEditingOrDeleting: boolean;
  currentUserId: number;
  currentUserRole: string;
  isSwitchingChat?: boolean;
}

const ChatListItem = ({
  chat,
  selected,
  onClick,
  currentUserId,
}: {
  chat: ForumChat;
  selected: boolean;
  onClick: () => void;
  currentUserId: number;
}) => {
  const initials =
    chat.participants
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

const ChatList = ({
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
        chat.subject?.name.toLowerCase().includes(query) ||
        chat.participants.some((p) => p.full_name.toLowerCase().includes(query))
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

const ChatWindow = ({
  chat,
  messages,
  isLoadingMessages,
  isSending,
  onSendMessage,
  isConnected,
  typingUsers,
  error,
  onRetryConnection,
  onEditMessage,
  onDeleteMessage,
  isEditingOrDeleting,
  currentUserId,
  currentUserRole,
}: ChatWindowProps) => {
  const [messageInput, setMessageInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleSend = () => {
    if ((messageInput.trim() || selectedFile) && !isSending) {
      onSendMessage(messageInput.trim(), selectedFile || undefined);
      setMessageInput('');
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file size (max 10MB)
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        alert('Файл слишком большой. Максимальный размер: 10 МБ');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleMessageChange = (value: string) => {
    setMessageInput(value);

    // Send typing indicator if connected
    if (value.trim() && isConnected && chat) {
      chatWebSocketService.sendTyping(chat.id);
      chatWebSocketService.startTypingTimer(chat.id);
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

  const otherParticipants = chat.participants
    .filter((p) => p.id !== currentUserId)
    .map((p) => p.full_name)
    .join(', ');

  const displayName = chat.name || otherParticipants || 'Чат';

  return (
    <Card className="p-6 md:col-span-2 flex flex-col h-full overflow-hidden" data-testid="chat-window">
      {/* Error Banner */}
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

      {/* Chat Header - Fixed */}
      <div className="flex items-center gap-3 pb-4 border-b flex-shrink-0" data-testid="chat-header">
        <Avatar className="w-10 h-10">
          <AvatarFallback className="gradient-primary text-primary-foreground">
            {chat.participants
              .filter((p) => p.id !== currentUserId)
              .map((p) => p.full_name.charAt(0))
              .join('')
              .toUpperCase() || 'C'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className="font-bold text-sm">{displayName}</div>
            {/* Connection Status Indicator */}
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
          {chat.subject && <div className="text-xs text-muted-foreground">{chat.subject.name}</div>}
          {chat.participants.length > 1 && (
            <div className="text-xs text-muted-foreground">
              {
                chat.participants.filter(
                  (p) => p.id !== currentUserId
                ).length
              }{' '}
              участник(и)
            </div>
          )}
        </div>
      </div>

      {/* Messages - Scrollable Area */}
      <div className="flex-1 overflow-y-auto py-4 pr-4 min-h-0">
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
              <p className="text-gray-500">
                Напишите первое сообщение в этом чате!
              </p>
            </div>
          ) : (
            messages.map((msg) => {
              const isOwn = msg.sender.id === currentUserId;
              const canModerate = ['teacher', 'tutor', 'admin'].includes(currentUserRole);

              return (
                <div
                  key={msg.id}
                  className={`flex ${isOwn ? 'justify-end' : 'justify-start'} group`}
                >
                  <div
                    className={`max-w-[70%] p-3 rounded-lg relative ${
                      isOwn ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    }`}
                  >
                    {/* Sender name for other's messages */}
                    {!isOwn && (
                      <p className="text-xs font-medium mb-1 opacity-75">
                        {msg.sender.full_name}
                      </p>
                    )}

                    {/* Message content */}
                    <p className="text-sm break-words pr-6">{msg.content}</p>

                    {/* File attachment */}
                    {msg.is_image && msg.image_url && (
                      <div className="mt-2">
                        <a href={msg.image_url} target="_blank" rel="noopener noreferrer">
                          <img
                            src={msg.image_url}
                            alt={msg.file_name || 'Image'}
                            className="max-w-xs rounded border cursor-pointer hover:opacity-90 transition-opacity"
                          />
                        </a>
                      </div>
                    )}
                    {msg.file_url && !msg.is_image && (
                      <div className="mt-2 flex items-center gap-2 p-2 bg-background/10 rounded border">
                        <FileText className="w-4 h-4" />
                        <a
                          href={msg.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm hover:underline flex-1 truncate"
                        >
                          {msg.file_name || 'Файл'}
                        </a>
                        <Download className="w-4 h-4" />
                      </div>
                    )}

                    {/* Timestamp and edited indicator */}
                    <div
                      className={`text-xs mt-1 flex items-center gap-1 ${
                        isOwn ? 'text-primary-foreground/70' : 'text-muted-foreground'
                      }`}
                    >
                      {msg.is_edited && <span className="italic">(ред.)</span>}
                      {new Date(msg.created_at).toLocaleTimeString('ru-RU', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>

                    {/* Message actions dropdown */}
                    <div className="absolute top-2 right-2">
                      <MessageActions
                        messageId={msg.id}
                        isOwner={isOwn}
                        canModerate={canModerate}
                        onEdit={() => onEditMessage(msg.id, msg.content)}
                        onDelete={() => onDeleteMessage(msg.id)}
                        disabled={isEditingOrDeleting}
                      />
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Message Input - Fixed at Bottom */}
      <div className="pt-4 border-t flex-shrink-0">
        {/* Selected file preview */}
        {selectedFile && (
          <div className="mb-2 flex items-center gap-2 p-2 bg-muted rounded-lg border">
            {selectedFile.type.startsWith('image/') ? (
              <ImageIcon className="w-4 h-4 text-muted-foreground" />
            ) : (
              <FileText className="w-4 h-4 text-muted-foreground" />
            )}
            <span className="text-sm flex-1 truncate">
              {selectedFile.name} ({formatFileSize(selectedFile.size)})
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRemoveFile}
              className="h-6 w-6 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}

        {/* Input area */}
        <div className="flex gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.zip"
            style={{ display: 'none' }}
            data-testid="file-input-hidden"
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isSending}
            className="shrink-0"
            data-testid="file-attach-button"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
          <Input
            placeholder="Введите сообщение..."
            value={messageInput}
            onChange={(e) => handleMessageChange(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isSending}
            className="text-sm"
          />
          <Button
            type="button"
            onClick={handleSend}
            disabled={isSending || (!messageInput.trim() && !selectedFile)}
            className="gradient-primary"
          >
            {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Offline Notice */}
      {!isConnected && (
        <div className="pt-2 text-xs text-muted-foreground text-center flex-shrink-0">
          Сообщения будут отправлены при восстановлении соединения
        </div>
      )}
    </Card>
  );
};

// ContactSearchModal component
interface ContactSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onChatInitiated: (chatId: number) => void;
}

const ContactSearchModal = ({ isOpen, onClose, onChatInitiated }: ContactSearchModalProps) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch available contacts
  const {
    data: contacts = [],
    isLoading: isLoadingContacts,
    error: contactsError,
    refetch: refetchContacts,
  } = useQuery({
    queryKey: ['available-contacts'],
    queryFn: forumAPI.getAvailableContacts,
    enabled: isOpen,
    retry: 2,
  });

  // Initiate chat mutation
  const initiateChatMutation = useMutation({
    mutationFn: ({ contactUserId, subjectId }: { contactUserId: number; subjectId?: number }) =>
      forumAPI.initiateChat(contactUserId, subjectId),
    onSuccess: (data) => {
      logger.debug('[ContactSearchModal] Chat initiated successfully:', data);

      // Invalidate forum chats to refresh the list
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });

      // Show success message
      toast({
        title: data.created ? 'Чат создан' : 'Чат найден',
        description: data.created ? 'Новый чат успешно создан' : 'Вы перешли к существующему чату',
      });

      // Notify parent component about chat initiation
      onChatInitiated(data.chat.id);

      // Close modal
      onClose();
    },
    onError: (error: any) => {
      logger.error('[ContactSearchModal] Error initiating chat:', error);

      const errorMessage = error?.message || 'Ошибка при создании чата';
      toast({
        title: 'Ошибка',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  // Filter contacts by search query and role
  const filteredContacts = useMemo(() => {
    let filtered = contacts;

    // Apply role filter
    if (roleFilter !== 'all') {
      filtered = filtered.filter((contact) => contact.role === roleFilter);
    }

    // Apply search query filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (contact) =>
          contact.first_name.toLowerCase().includes(query) ||
          contact.last_name.toLowerCase().includes(query) ||
          contact.email.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [contacts, searchQuery, roleFilter]);

  // Handle chat initiation
  const handleInitiateChat = (contact: Contact) => {
    // For existing chats, notify parent immediately
    if (contact.has_active_chat && contact.chat_id) {
      onChatInitiated(contact.chat_id);
      onClose();
      return;
    }

    // For new chats, call API
    initiateChatMutation.mutate({
      contactUserId: contact.id,
      subjectId: contact.subject?.id,
    });
  };

  // Reset search and filters when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSearchQuery('');
      setRoleFilter('all');
    }
  }, [isOpen]);

  // Handle retry on error
  const handleRetry = () => {
    refetchContacts();
  };

  // Get unique roles from contacts
  const availableRoles = useMemo(() => {
    const roles = new Set(contacts.map((c) => c.role));
    return Array.from(roles);
  }, [contacts]);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Начать новый чат</DialogTitle>
          <DialogDescription>Выберите пользователя для начала общения</DialogDescription>
        </DialogHeader>

        {/* Search and Filter Controls */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по имени или email..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
          </div>

          {/* Role filter dropdown */}
          <div className="w-full sm:w-[200px]">
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-full">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-muted-foreground" />
                  <SelectValue placeholder="Все роли" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все роли</SelectItem>
                {availableRoles.includes('student') && (
                  <SelectItem value="student">Студенты</SelectItem>
                )}
                {availableRoles.includes('teacher') && (
                  <SelectItem value="teacher">Преподаватели</SelectItem>
                )}
                {availableRoles.includes('tutor') && <SelectItem value="tutor">Тьюторы</SelectItem>}
                {availableRoles.includes('parent') && (
                  <SelectItem value="parent">Родители</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Contacts list */}
        <ScrollArea className="flex-1 pr-4 mt-4">
          {isLoadingContacts ? (
            <div className="space-y-3" data-testid="contacts-skeleton">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-3 rounded-lg border animate-pulse"
                >
                  <Skeleton className="w-10 h-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-48" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                  <Skeleton className="h-8 w-24 rounded" />
                </div>
              ))}
            </div>
          ) : contactsError ? (
            <div
              className="flex flex-col items-center justify-center py-12 text-center"
              data-testid="contacts-error"
            >
              <AlertCircle className="w-12 h-12 text-destructive mb-3" />
              <p className="text-sm font-medium text-foreground mb-2">
                Не удалось загрузить контакты
              </p>
              <p className="text-xs text-muted-foreground mb-4">
                Проверьте подключение к интернету
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleRetry}
                className="gap-2"
              >
                <Loader2 className="w-4 h-4" />
                Повторить попытку
              </Button>
            </div>
          ) : filteredContacts.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-12 text-center"
              data-testid="contacts-empty"
            >
              <MessageCircle className="w-12 h-12 text-muted-foreground mb-3" />
              <p className="text-sm font-medium text-foreground mb-1">
                {searchQuery || roleFilter !== 'all'
                  ? 'Контактов не найдено'
                  : 'Нет доступных контактов'}
              </p>
              <p className="text-xs text-muted-foreground">
                {searchQuery || roleFilter !== 'all'
                  ? 'Попробуйте изменить фильтры поиска'
                  : 'У вас пока нет контактов для общения'}
              </p>
            </div>
          ) : (
            <div className="space-y-2" data-testid="contacts-list">
              {filteredContacts.map((contact) => {
                const initials =
                  `${contact.first_name.charAt(0)}${contact.last_name.charAt(0)}`.toUpperCase();
                const fullName = `${contact.first_name} ${contact.last_name}`.trim();

                // Role badge color mapping
                const getRoleBadgeVariant = (role: string) => {
                  switch (role) {
                    case 'teacher':
                      return 'default';
                    case 'tutor':
                      return 'secondary';
                    case 'student':
                      return 'outline';
                    case 'parent':
                      return 'outline';
                    default:
                      return 'outline';
                  }
                };

                // Role label mapping
                const getRoleLabel = (role: string) => {
                  switch (role) {
                    case 'teacher':
                      return 'Преподаватель';
                    case 'tutor':
                      return 'Тьютор';
                    case 'student':
                      return 'Студент';
                    case 'parent':
                      return 'Родитель';
                    default:
                      return role;
                  }
                };

                return (
                  <div
                    key={contact.id}
                    className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/50 hover:border-primary/50 transition-all duration-200 group"
                    data-testid="contact-item"
                  >
                    <Avatar className="w-10 h-10 ring-2 ring-transparent group-hover:ring-primary/20 transition-all">
                      <AvatarFallback className="gradient-primary text-primary-foreground font-semibold text-sm">
                        {initials}
                      </AvatarFallback>
                    </Avatar>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-sm truncate">{fullName}</p>
                        <Badge
                          variant={getRoleBadgeVariant(contact.role)}
                          className="text-xs shrink-0"
                        >
                          {getRoleLabel(contact.role)}
                        </Badge>
                        {contact.has_active_chat && (
                          <CheckCircle2
                            className="w-3 h-3 text-green-500 shrink-0"
                            title="Активный чат"
                          />
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate mb-0.5">
                        {contact.email}
                      </p>
                      {contact.subject && (
                        <p className="text-xs text-muted-foreground truncate flex items-center gap-1">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary/50" />
                          {contact.subject.name}
                        </p>
                      )}
                    </div>

                    <Button
                      type="button"
                      size="sm"
                      variant={contact.has_active_chat ? 'default' : 'outline'}
                      onClick={() => handleInitiateChat(contact)}
                      disabled={initiateChatMutation.isPending}
                      className={cn(
                        'shrink-0 transition-all duration-200',
                        contact.has_active_chat
                          ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                          : 'hover:bg-primary hover:text-primary-foreground'
                      )}
                    >
                      {initiateChatMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : contact.has_active_chat ? (
                        <>
                          <MessageCircle className="w-4 h-4 mr-1" />
                          Продолжить
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4 mr-1" />
                          Начать чат
                        </>
                      )}
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

// Helper function to get the appropriate sidebar component based on role
const getSidebarComponent = (role: string) => {
  switch (role) {
    case 'student':
      return StudentSidebar;
    case 'teacher':
      return TeacherSidebar;
    case 'tutor':
      return TutorSidebar;
    case 'parent':
      return ParentSidebar;
    default:
      return null;
  }
};

function Forum() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [selectedChat, setSelectedChat] = useState<ForumChat | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isNewChatModalOpen, setIsNewChatModalOpen] = useState(false);
  const [isSwitchingChat, setIsSwitchingChat] = useState(false);
  const queryClient = useQueryClient();

  // Edit/Delete message state
  const [editingMessage, setEditingMessage] = useState<{ id: number; content: string } | null>(
    null
  );
  const [deletingMessageId, setDeletingMessageId] = useState<number | null>(null);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

  // Connection status is managed per-chat in the WebSocket connection effect below

  const { chats = [], isLoadingChats, chatsError } = useForumChats();
  const { data: messages = [], isLoading: isLoadingMessages } = useForumMessages(
    selectedChat?.id || null
  );
  const sendMessageMutation = useSendForumMessage();

  // Edit message mutation
  const editMessageMutation = useForumMessageUpdate({
    chatId: selectedChat?.id || 0,
    onSuccess: () => {
      setEditingMessage(null);
    },
  });

  // Delete message mutation
  const deleteMessageMutation = useForumMessageDelete({
    chatId: selectedChat?.id || 0,
    onSuccess: () => {
      setDeletingMessageId(null);
      setIsDeleteConfirmOpen(false);
    },
  });

  // WebSocket handlers (memoized)
  const handleWebSocketMessage = useCallback(
    (wsMessage: ChatMessage) => {
      logger.debug('[Forum] WebSocket message received in component handler:', {
        messageId: wsMessage.id,
        content: wsMessage.content.substring(0, 50),
        senderId: wsMessage.sender.id,
        selectedChatId: selectedChat?.id,
      });

      if (!selectedChat) {
        logger.warn('[Forum] Received message but no chat selected');
        return;
      }

      try {
        // Transform WebSocket message to ForumMessage format
        const forumMessage: ForumMessage = {
          id: wsMessage.id,
          content: wsMessage.content,
          sender: {
            id: wsMessage.sender.id,
            full_name:
              `${wsMessage.sender.first_name} ${wsMessage.sender.last_name}`.trim() ||
              wsMessage.sender.username,
            role: wsMessage.sender.role,
          },
          created_at: wsMessage.created_at,
          updated_at: wsMessage.updated_at,
          is_read: wsMessage.is_read,
          is_edited: wsMessage.is_edited || false,
          message_type: wsMessage.message_type,
        };

        logger.debug('[Forum] Updating TanStack Query cache for chat:', selectedChat.id);
        // Update TanStack Query cache with new message - update ALL caches for this chat
        // Use partial key matching to update all queries for this chatId (regardless of limit/offset)
        queryClient.setQueriesData<ForumMessage[]>(
          { queryKey: ['forum-messages', selectedChat.id], exact: false },
          (oldData: ForumMessage[] | undefined) => {
            if (!oldData) {
              logger.debug('[Forum] No existing data, creating new array with message');
              return [forumMessage];
            }

            // Check if message already exists (avoid duplicates)
            const exists = oldData.some((msg: ForumMessage) => msg.id === forumMessage.id);
            if (exists) {
              logger.debug('[Forum] Message already exists in cache, skipping');
              return oldData;
            }

            logger.debug('[Forum] Adding new message to cache');
            return [...oldData, forumMessage];
          }
        );

        // Also invalidate to trigger refetch and update chat list
        queryClient.invalidateQueries({ queryKey: ['forum-messages', selectedChat.id] });
        queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });

        // Clear any errors on successful message
        setError(null);
      } catch (err) {
        logger.error('Error handling WebSocket message:', err);
        setError('Ошибка обработки сообщения');
      }
    },
    [selectedChat, queryClient]
  );

  const handleTyping = useCallback((user: TypingUser) => {
    setTypingUsers((prev) => {
      const filtered = prev.filter((u) => u.id !== user.id);
      return [...filtered, user];
    });

    // Remove user from typing list after 3 seconds
    setTimeout(() => {
      setTypingUsers((prev) => prev.filter((u) => u.id !== user.id));
    }, 3000);
  }, []);

  const handleTypingStop = useCallback((user: TypingUser) => {
    setTypingUsers((prev) => prev.filter((u) => u.id !== user.id));
  }, []);

  const handleError = useCallback((errorMessage: string) => {
    logger.error('WebSocket error:', errorMessage);
    setError(errorMessage);
  }, []);

  // WebSocket connection management
  useEffect(() => {
    if (!selectedChat || !user) return;

    const chatId = selectedChat.id;

    const handlers = {
      onMessage: handleWebSocketMessage,
      onTyping: handleTyping,
      onTypingStop: handleTypingStop,
      onError: handleError,
    };

    // Connect to WebSocket for this chat room
    const connectionSuccess = chatWebSocketService.connectToRoom(chatId, handlers);

    if (!connectionSuccess) {
      logger.error('[Forum] Failed to connect to chat room:', chatId);
      setError('Не удалось подключиться к чату. Проверьте авторизацию.');
    }

    // CRITICAL FIX: Set initial connection state immediately
    const initiallyConnected = chatWebSocketService.isConnected();
    logger.debug('[Forum] Initial connection state:', initiallyConnected);
    setIsConnected(initiallyConnected);
    if (initiallyConnected) {
      setError(null);
    }

    // Subscribe to connection state changes
    const connectionCallback = (connected: boolean) => {
      logger.debug('[Forum] Connection state changed to:', connected);
      setIsConnected(connected);
      if (!connected) {
        setError('Соединение потеряно. Попытка переподключения...');
      } else {
        setError(null);
      }
    };

    chatWebSocketService.onConnectionChange(connectionCallback);

    // Cleanup: disconnect when chat changes or component unmounts
    return () => {
      chatWebSocketService.disconnectFromRoom(chatId);
      setTypingUsers([]);
    };
  }, [selectedChat, user, handleWebSocketMessage, handleTyping, handleTypingStop, handleError]);

  const handleSelectChat = (chat: ForumChat) => {
    // Show loading state during chat switch
    setIsSwitchingChat(true);
    setSelectedChat(chat);
    setSearchQuery('');
    setError(null);
    setTypingUsers([]);

    // Reset loading state after a brief delay to allow WebSocket connection
    setTimeout(() => {
      setIsSwitchingChat(false);
    }, 300);
  };

  const handleSendMessage = (content: string, file?: File) => {
    if (!selectedChat) return;

    setError(null);

    // Send via REST API to persist in database
    // Optimistic update shows message immediately (in useSendForumMessage)
    // Backend will broadcast via WebSocket to other connected users
    sendMessageMutation.mutate({
      chatId: selectedChat.id,
      data: { content },
      file,
    });
  };

  const handleRetryConnection = () => {
    setError(null);
    if (selectedChat) {
      // Force reconnect by toggling chat
      const chat = selectedChat;
      setSelectedChat(null);
      setTimeout(() => {
        setSelectedChat(chat);
      }, 100);
    }
  };

  // Handle chat initiated from modal
  const handleChatInitiated = useCallback(
    (chatId: number) => {
      logger.debug('[Forum] Chat initiated, selecting chat:', chatId);

      // Wait for chat list to refresh, then select the chat
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] }).then(() => {
        // Find the chat in the updated list
        const updatedChats = queryClient.getQueryData<ForumChat[]>(['forum', 'chats']);
        const newChat = updatedChats?.find((chat) => chat.id === chatId);

        if (newChat) {
          setSelectedChat(newChat);
        }
      });
    },
    [queryClient]
  );

  // Handle edit message
  const handleEditMessage = (messageId: number, content: string) => {
    setEditingMessage({ id: messageId, content });
  };

  // Handle save edited message
  const handleSaveEdit = (newContent: string) => {
    if (editingMessage) {
      editMessageMutation.mutate({
        messageId: editingMessage.id,
        data: { content: newContent },
      });
    }
  };

  // Handle delete message
  const handleDeleteMessage = (messageId: number) => {
    setDeletingMessageId(messageId);
    setIsDeleteConfirmOpen(true);
  };

  // Confirm delete
  const handleConfirmDelete = () => {
    if (deletingMessageId) {
      deleteMessageMutation.mutate(deletingMessageId);
    }
  };


  // Get the appropriate sidebar component based on user role
  const SidebarComponent = getSidebarComponent(user?.role || '');

  if (!SidebarComponent) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Неизвестная роль пользователя</p>
      </div>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <SidebarComponent />
        <SidebarInset className="flex flex-col h-full overflow-hidden">
          <header className="flex-shrink-0 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="text-2xl font-bold ml-4">Форум</h1>
            <div className="flex-1" />
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={() => setIsNewChatModalOpen(true)}
              className="gradient-primary"
            >
              <Plus className="w-4 h-4 mr-2" />
              Новый чат
            </Button>
          </header>
          <main className="flex-1 overflow-hidden flex flex-col p-6 min-h-0">
            <div className="flex-shrink-0 mb-4">
              <p className="text-muted-foreground">Общайтесь с преподавателями и тьюторами</p>
            </div>

            {/* Connection status is shown in the chat header, no need for global banner */}

            <div className="grid md:grid-cols-3 gap-6 flex-1 overflow-hidden min-h-0">
              <ChatList
                chats={chats}
                selectedChat={selectedChat}
                onSelectChat={handleSelectChat}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                isLoading={isLoadingChats}
                currentUserId={user?.id || 0}
              />

              <ChatWindow
                chat={selectedChat}
                messages={messages}
                isLoadingMessages={isLoadingMessages}
                isSending={sendMessageMutation.isPending}
                onSendMessage={handleSendMessage}
                isConnected={isConnected}
                typingUsers={typingUsers}
                error={error}
                onRetryConnection={handleRetryConnection}
                onEditMessage={handleEditMessage}
                onDeleteMessage={handleDeleteMessage}
                isEditingOrDeleting={
                  editMessageMutation.isPending || deleteMessageMutation.isPending
                }
                currentUserId={user?.id || 0}
                currentUserRole={user?.role || ''}
                isSwitchingChat={isSwitchingChat}
              />
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Contact Search Modal */}
      <ContactSearchModal
        isOpen={isNewChatModalOpen}
        onClose={() => setIsNewChatModalOpen(false)}
        onChatInitiated={handleChatInitiated}
      />

      {/* Edit Message Dialog */}
      <EditMessageDialog
        isOpen={editingMessage !== null}
        onClose={() => setEditingMessage(null)}
        messageContent={editingMessage?.content || ''}
        onSave={handleSaveEdit}
        isLoading={editMessageMutation.isPending}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteConfirmOpen} onOpenChange={setIsDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить сообщение?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Сообщение будет удалено из чата.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setIsDeleteConfirmOpen(false);
                setDeletingMessageId(null);
              }}
            >
              Отмена
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMessageMutation.isPending ? 'Удаление...' : 'Удалить'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SidebarProvider>
  );
}
