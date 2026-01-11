import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Search,
  Loader2,
  AlertCircle,
  MessageCircle,
  Plus,
  CheckCircle2,
  Filter,
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { ChatContact, chatAPI } from '@/integrations/api/chatAPI';
import { useToast } from '@/hooks/use-toast';
import { logger } from '@/utils/logger';

interface ContactsListProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectContact: (contactId: number) => void;
}

export const ContactsList = ({ isOpen, onClose, onSelectContact }: ContactsListProps) => {
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
      logger.debug('[ContactsList] Chat initiated successfully:', data);
      queryClient.invalidateQueries({ queryKey: ['chat', 'chats'] });
      toast({
        title: data.created ? 'Чат создан' : 'Чат найден',
        description: data.created ? 'Новый чат успешно создан' : 'Вы перешли к существующему чату',
      });
      onSelectContact(data.id);
      onClose();
    },
    onError: (error: Error) => {
      logger.error('[ContactsList] Error initiating chat:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Ошибка при создании чата',
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

  const handleInitiateChat = (contact: ChatContact) => {
    if (contact.has_active_chat && contact.chat_id) {
      onSelectContact(contact.chat_id);
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
  };

  useEffect(() => {
    if (!isOpen) {
      setSearchQuery('');
      setRoleFilter('all');
    }
  }, [isOpen]);

  const availableRoles = useMemo(() => {
    const roles = new Set(contacts.map((c) => c.role));
    return Array.from(roles);
  }, [contacts]);

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'teacher':
        return 'default';
      case 'tutor':
        return 'secondary';
      default:
        return 'outline';
    }
  };

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
            />
          </div>

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
                {availableRoles.includes('student') && <SelectItem value="student">Студенты</SelectItem>}
                {availableRoles.includes('teacher') && <SelectItem value="teacher">Преподаватели</SelectItem>}
                {availableRoles.includes('tutor') && <SelectItem value="tutor">Тьюторы</SelectItem>}
                {availableRoles.includes('parent') && <SelectItem value="parent">Родители</SelectItem>}
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
              <p className="text-sm font-medium text-foreground mb-2">Не удалось загрузить контакты</p>
              <p className="text-xs text-muted-foreground mb-4">Проверьте подключение к интернету</p>
              <Button type="button" variant="outline" size="sm" onClick={() => refetchContacts()} className="gap-2">
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
                {searchQuery || roleFilter !== 'all' ? 'Контактов не найдено' : 'Нет доступных контактов'}
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
                const initials = `${contact.first_name.charAt(0)}${contact.last_name.charAt(0)}`.toUpperCase();
                const fullName = `${contact.first_name} ${contact.last_name}`.trim();

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
                        <Badge variant={getRoleBadgeVariant(contact.role)} className="text-xs shrink-0">
                          {getRoleLabel(contact.role)}
                        </Badge>
                        {contact.has_active_chat && (
                          <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0" title="Активный чат" />
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate mb-0.5">{contact.email}</p>
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
