import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Loader2, Paperclip, X, ImageIcon, FileText, Lock } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface MessageInputProps {
  onSend: (content: string, file?: File) => void;
  onTyping?: () => void;
  connectionStatus: 'connected' | 'disconnected' | 'error';
  isLoading: boolean;
  isReadOnly?: boolean;
  isChatInactive?: boolean;
}

export const MessageInput = ({
  onSend,
  onTyping,
  connectionStatus,
  isLoading,
  isReadOnly = false,
  isChatInactive = false,
}: MessageInputProps) => {
  const { toast } = useToast();
  const [messageInput, setMessageInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleSend = () => {
    if ((messageInput.trim() || selectedFile) && !isLoading) {
      onSend(messageInput.trim(), selectedFile || undefined);
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
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        toast({
          variant: 'destructive',
          title: 'Файл слишком большой',
          description: 'Максимальный размер файла: 10 МБ',
        });
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
    if (value.trim() && onTyping) {
      onTyping();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && messageInput.trim()) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isReadOnly || isChatInactive) {
    return (
      <div className="p-3 bg-muted/50 rounded-lg border border-muted-foreground/20 flex items-center justify-center gap-2">
        <Lock className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          {isChatInactive ? 'Чат заблокирован модератором' : 'Доступ только для чтения'}
        </span>
      </div>
    );
  }

  return (
    <>
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
          disabled={isLoading}
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
          disabled={isLoading}
          className="text-sm"
        />
        <Button
          type="button"
          onClick={handleSend}
          disabled={isLoading || (!messageInput.trim() && !selectedFile)}
          className="gradient-primary"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>

      {connectionStatus === 'disconnected' && (
        <div className="pt-2 text-xs text-muted-foreground text-center">
          Сообщения будут отправлены при восстановлении соединения
        </div>
      )}
    </>
  );
};
