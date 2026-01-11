import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Loader2 } from 'lucide-react';

interface EditMessageDialogProps {
  isOpen: boolean;
  onClose: () => void;
  messageContent: string;
  onSave: (newContent: string) => void;
  isLoading?: boolean;
}

export const EditMessageDialog: React.FC<EditMessageDialogProps> = ({
  isOpen,
  onClose,
  messageContent,
  onSave,
  isLoading = false,
}) => {
  const [content, setContent] = useState(messageContent);
  const [error, setError] = useState<string | null>(null);

  // Reset content when dialog opens with new message
  useEffect(() => {
    if (isOpen) {
      setContent(messageContent);
      setError(null);
    }
  }, [isOpen, messageContent]);

  // T034: Check if content is unchanged
  const isUnchanged = content.trim() === messageContent.trim();

  const handleSave = () => {
    const trimmedContent = content.trim();

    if (!trimmedContent) {
      setError('Сообщение не может быть пустым');
      return;
    }

    if (trimmedContent.length > 5000) {
      setError('Сообщение слишком длинное (максимум 5000 символов)');
      return;
    }

    // T034: Don't save if unchanged
    if (trimmedContent === messageContent.trim()) {
      onClose();
      return;
    }

    onSave(trimmedContent);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      if (!isUnchanged) {
        handleSave();
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Редактировать сообщение</DialogTitle>
          <DialogDescription>
            Измените текст сообщения. Нажмите Ctrl+Enter для сохранения.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Введите сообщение..."
            className="min-h-[100px] resize-none"
            disabled={isLoading}
            autoFocus
          />
          {error && (
            <p className="text-sm text-destructive mt-2">{error}</p>
          )}
          {/* T034: Show hint when content is unchanged */}
          {isUnchanged && !error && (
            <p className="text-xs text-muted-foreground mt-2">
              Сообщение не изменено
            </p>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            {content.length}/5000 символов
          </p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Отмена
          </Button>
          {/* T034: Disable save button if content unchanged */}
          <Button onClick={handleSave} disabled={isLoading || isUnchanged}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Сохранение...
              </>
            ) : (
              'Сохранить'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default EditMessageDialog;
