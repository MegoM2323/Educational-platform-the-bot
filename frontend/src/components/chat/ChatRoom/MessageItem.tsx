import { Pin, FileText, Download } from 'lucide-react';
import { ForumMessage } from '@/integrations/api/forumAPICompat';
import { MessageActions } from '@/components/forum/MessageActions';

interface MessageItemProps {
  message: ForumMessage;
  isOwn: boolean;
  canModerate: boolean;
  onEdit: (content: string) => void;
  onDelete: () => void;
  onPin?: () => void;
  isEditingOrDeleting: boolean;
}

export const MessageItem = ({
  message,
  isOwn,
  canModerate,
  onEdit,
  onDelete,
  onPin,
  isEditingOrDeleting,
}: MessageItemProps) => {
  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} group`}>
      <div
        className={`max-w-[70%] p-3 rounded-lg relative ${
          isOwn ? 'bg-primary text-primary-foreground' : 'bg-muted'
        }`}
      >
        {!isOwn && (
          <p className="text-xs font-medium mb-1 opacity-75 flex items-center gap-1">
            {message.sender.full_name}
            {message.is_pinned && (
              <Pin className="h-3 w-3 text-yellow-500" title="Закрепленное сообщение" />
            )}
          </p>
        )}

        {isOwn && message.is_pinned && (
          <div className="absolute top-1 left-1">
            <Pin className="h-3 w-3 text-yellow-500" title="Закрепленное сообщение" />
          </div>
        )}

        <p className="text-sm break-words pr-6">{message.content}</p>

        {message.is_image && (message.image_url || message.image) && (
          <div className="mt-2">
            <a href={message.image_url || message.image} target="_blank" rel="noopener noreferrer">
              <img
                src={message.image_url || message.image}
                alt={message.file_name || 'Image'}
                className="max-w-xs rounded border cursor-pointer hover:opacity-90 transition-opacity"
              />
            </a>
          </div>
        )}
        {(message.file_url || message.file) && !message.is_image && (
          <div className="mt-2 flex items-center gap-2 p-2 bg-background/10 rounded border">
            <FileText className="w-4 h-4" />
            <a
              href={message.file_url || message.file}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm hover:underline flex-1 truncate"
            >
              {message.file_name || 'Файл'}
            </a>
            <Download className="w-4 h-4" />
          </div>
        )}

        <div
          className={`text-xs mt-1 flex items-center gap-1 ${
            isOwn ? 'text-primary-foreground/70' : 'text-muted-foreground'
          }`}
        >
          {message.is_edited && <span className="italic">(ред.)</span>}
          {new Date(message.created_at).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>

        <div className="absolute top-2 right-2">
          <MessageActions
            messageId={message.id}
            isOwner={isOwn}
            canModerate={canModerate}
            onEdit={() => onEdit(message.content)}
            onDelete={onDelete}
            onPin={onPin}
            isPinned={message.is_pinned}
            disabled={isEditingOrDeleting}
          />
        </div>
      </div>
    </div>
  );
};
