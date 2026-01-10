import { useState, useMemo, useEffect, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search,
  Filter,
  AlertCircle,
  MessageCircle,
  Plus,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useQueryClient } from '@tanstack/react-query';
import { ChatContact, chatAPI, Chat } from '@/integrations/api/chatAPI';
import { logger } from '@/utils/logger';
import { cn } from '@/lib/utils';

interface ContactSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onChatInitiated?: (chatId: number) => void;
}

const getRoleBadgeVariant = (role: string): 'default' | 'secondary' | 'outline' => {
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

const getRoleLabel = (role: string): string => {
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

const ContactItem = ({
  contact,
  isLoading,
  onSelect,
}: {
  contact: ChatContact;
  isLoading: boolean;
  onSelect: (contact: ChatContact) => void;
}) => {
  const initials = `${contact.first_name.charAt(0)}${contact.last_name.charAt(0)}`.toUpperCase();
  const fullName = `${contact.first_name} ${contact.last_name}`.trim();

  return (
    <div
      className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/50 hover:border-primary/50 transition-all duration-200 group"
      data-testid="contact-item"
      role="option"
      aria-selected={false}
    >
      <Avatar className="w-10 h-10 ring-2 ring-transparent group-hover:ring-primary/20 transition-all flex-shrink-0">
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
        onClick={() => onSelect(contact)}
        disabled={isLoading}
        className={cn(
          'shrink-0 transition-all duration-200',
          contact.has_active_chat
            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
            : 'hover:bg-primary hover:text-primary-foreground'
        )}
        aria-label={
          contact.has_active_chat
            ? `Продолжить чат с ${fullName}`
            : `Начать чат с ${fullName}`
        }
      >
        {isLoading ? (
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
};

export const ContactSelector = ({
  isOpen,
  onClose,
  onChatInitiated,
}: ContactSelectorProps) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    data: contacts = [],
    isLoading: isLoadingContacts,
    error: contactsError,
    refetch: refetchContacts,
  } = useQuery({
    queryKey: ['available-contacts'],
    queryFn: chatAPI.getContacts,
    enabled: isOpen,
    retry: 2,
  });

  const initiateChatMutation = useMutation({
    mutationFn: ({ contactUserId, subjectId }: { contactUserId: number; subjectId?: number }) =>
      chatAPI.createOrGetChat(contactUserId, subjectId),
    onSuccess: (data) => {
      logger.debug('[ContactSelector] Chat initiated successfully:', data);

      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });

      toast({
        title: data.created ? 'Чат создан' : 'Чат найден',
        description: data.created
          ? 'Новый чат успешно создан'
          : 'Вы перешли к существующему чату',
      });

      if (onChatInitiated) {
        onChatInitiated(data.id);
      }

      onClose();
    },
    onError: (error: Error) => {
      logger.error('[ContactSelector] Error initiating chat:', error);

      const errorMessage = error.message || 'Ошибка при создании чата';
      toast({
        title: 'Ошибка',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  const filteredContacts = useMemo(() => {
    let filtered = contacts;

    if (roleFilter !== 'all') {
      filtered = filtered.filter((contact) => contact.role === roleFilter);
    }

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

  const handleInitiateChat = useCallback(
    (contact: ChatContact) => {
      if (contact.has_active_chat && contact.chat_id) {
        if (onChatInitiated) {
          onChatInitiated(contact.chat_id);
        }
        onClose();
        return;
      }

      if (contact.role === 'teacher' && !contact.subject?.id) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось создать чат: предмет не найден',
          variant: 'destructive',
        });
        return;
      }

      initiateChatMutation.mutate({
        contactUserId: contact.id,
        subjectId: contact.subject?.id,
      });
    },
    [onChatInitiated, onClose, toast, initiateChatMutation]
  );

  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setRoleFilter('all');
    }
  }, [isOpen]);

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

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по имени или email..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
              aria-label="Поиск контактов"
              data-testid="contact-search"
            />
          </div>

          <div className="w-full sm:w-[200px]">
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-full" aria-label="Фильтр по роли">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-muted-foreground" />
                  <SelectValue placeholder="Все роли" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все роли</SelectItem>
                {availableRoles.includes('student' as never) && (
                  <SelectItem value="student">Студенты</SelectItem>
                )}
                {availableRoles.includes('teacher' as never) && (
                  <SelectItem value="teacher">Преподаватели</SelectItem>
                )}
                {availableRoles.includes('tutor' as never) && (
                  <SelectItem value="tutor">Тьюторы</SelectItem>
                )}
                {availableRoles.includes('parent' as never) && (
                  <SelectItem value="parent">Родители</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        <ScrollArea className="flex-1 pr-4 mt-4">
          {isLoadingContacts ? (
            <div className="space-y-3" data-testid="contacts-skeleton">
              {[...Array(5)].map((_, i) => (
                <div
                  key={`contact-skeleton-${i}`}
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
                onClick={() => refetchContacts()}
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
            <div
              className="space-y-2"
              data-testid="contacts-list"
              role="listbox"
            >
              {filteredContacts.map((contact) => (
                <ContactItem
                  key={contact.id}
                  contact={contact}
                  isLoading={initiateChatMutation.isPending}
                  onSelect={handleInitiateChat}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};
