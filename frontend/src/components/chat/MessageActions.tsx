import React from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { Button } from '../ui/button';
import { MoreVertical, Pencil, Trash2 } from 'lucide-react';

interface MessageActionsProps {
  messageId: number;
  isOwner: boolean;
  canModerate?: boolean;
  onEdit: () => void;
  onDelete: () => void;
  disabled?: boolean;
}

export const MessageActions: React.FC<MessageActionsProps> = ({
  messageId,
  isOwner,
  canModerate = false,
  onEdit,
  onDelete,
  disabled = false,
}) => {
  // Only show if user can perform any action
  if (!isOwner && !canModerate) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
          disabled={disabled}
        >
          <MoreVertical className="h-4 w-4" />
          <span className="sr-only">Действия с сообщением</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {isOwner && (
          <DropdownMenuItem onClick={onEdit}>
            <Pencil className="mr-2 h-4 w-4" />
            Редактировать
          </DropdownMenuItem>
        )}
        {(isOwner || canModerate) && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onDelete}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Удалить
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default MessageActions;
