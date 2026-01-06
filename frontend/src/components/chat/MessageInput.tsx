import { useRef, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Paperclip, X, FileText, Image as ImageIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  maxLength?: number;
  onFileSelect?: (file: File) => void;
  selectedFile?: File | null;
  onRemoveFile?: () => void;
  placeholder?: string;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

export const MessageInput = ({
  value,
  onChange,
  onSend,
  isLoading = false,
  disabled = false,
  maxLength = 1000,
  onFileSelect,
  selectedFile,
  onRemoveFile,
  placeholder = 'Введите сообщение...',
}: MessageInputProps) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { toast } = useToast();
  const [charCount, setCharCount] = useState(0);

  const handleChange = useCallback(
    (newValue: string) => {
      if (newValue.length <= maxLength) {
        onChange(newValue);
        setCharCount(newValue.length);
      }
    },
    [onChange, maxLength]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > MAX_FILE_SIZE) {
        toast({
          variant: 'destructive',
          title: 'Файл слишком большой',
          description: `Максимальный размер файла: ${formatFileSize(MAX_FILE_SIZE)}`,
        });
        return;
      }

      if (onFileSelect) {
        onFileSelect(file);
      }
    },
    [onFileSelect, toast]
  );

  const handleRemoveFile = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (onRemoveFile) {
      onRemoveFile();
    }
  }, [onRemoveFile]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey && value.trim()) {
        e.preventDefault();
        onSend();
      }
    },
    [value, onSend]
  );

  const isMessageEmpty = !value.trim() && !selectedFile;
  const canSend = !isMessageEmpty && !isLoading;

  return (
    <div className="space-y-2">
      {selectedFile && (
        <div className="flex items-center gap-2 p-2 bg-muted rounded-lg border">
          {selectedFile.type.startsWith('image/') ? (
            <ImageIcon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          ) : (
            <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          )}
          <span className="text-sm flex-1 truncate" title={selectedFile.name}>
            {selectedFile.name} ({formatFileSize(selectedFile.size)})
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleRemoveFile}
            className="h-6 w-6 p-0"
            aria-label="Удалить файл"
            disabled={isLoading}
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
          aria-label="Выберите файл для отправки"
          disabled={isLoading || disabled}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading || disabled}
          className="shrink-0"
          data-testid="file-attach-button"
          aria-label="Прикрепить файл"
        >
          <Paperclip className="w-4 h-4" />
        </Button>
        <div className="relative flex-1">
          <Input
            placeholder={placeholder}
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading || disabled}
            className="text-sm pr-12"
            aria-label="Текст сообщения"
            data-testid="message-input"
            maxLength={maxLength}
          />
          {maxLength > 0 && (
            <span
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2 text-xs',
                charCount > maxLength * 0.8
                  ? 'text-orange-500'
                  : 'text-muted-foreground'
              )}
              aria-live="polite"
            >
              {charCount}/{maxLength}
            </span>
          )}
        </div>
        <Button
          type="button"
          onClick={onSend}
          disabled={!canSend}
          className="gradient-primary shrink-0"
          data-testid="send-button"
          aria-label="Отправить сообщение"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </Button>
      </div>
    </div>
  );
};
