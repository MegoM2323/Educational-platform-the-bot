import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

interface TelegramLinkButtonProps {
  isLinked: boolean;
  onStatusChange?: () => void;
}

interface GenerateLinkResponse {
  token: string;
  link: string;
  expires_at: string;
  ttl_minutes: number;
}

export const TelegramLinkButton: React.FC<TelegramLinkButtonProps> = ({
  isLinked,
  onStatusChange,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const [fallbackLink, setFallbackLink] = useState<string | null>(null);

  const handleLink = async () => {
    setIsLoading(true);
    setFallbackLink(null);
    try {
      const response = await unifiedAPI.post<GenerateLinkResponse>(
        '/api/profile/telegram/generate-link/'
      );

      if (response.success && response.data) {
        const { link } = response.data;
        const popup = window.open(link, '_blank');
        if (popup === null) {
          setFallbackLink(link);
          toast({
            title: 'Всплывающее окно заблокировано',
            description: 'Нажмите на ссылку ниже для привязки аккаунта',
          });
        } else {
          toast({
            title: 'Ссылка создана',
            description: 'Перейдите в Telegram для привязки аккаунта',
          });
        }
      } else {
        throw new Error('Failed to generate link');
      }
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось создать ссылку',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnlink = async () => {
    setIsLoading(true);
    try {
      const response = await unifiedAPI.delete('/api/profile/telegram/unlink/');

      if (response.success) {
        toast({
          title: 'Готово',
          description: 'Telegram отвязан от аккаунта',
        });
        onStatusChange?.();
      } else {
        throw new Error('Failed to unlink');
      }
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось отвязать Telegram',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-4">
        {isLinked ? (
          <>
            <span className="text-green-600 flex items-center gap-2">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
              Telegram привязан
            </span>
            <Button variant="outline" size="sm" onClick={handleUnlink} disabled={isLoading}>
              {isLoading ? 'Отвязка...' : 'Отвязать'}
            </Button>
          </>
        ) : (
          <Button onClick={handleLink} disabled={isLoading}>
            {isLoading ? 'Загрузка...' : 'Привязать Telegram'}
          </Button>
        )}
      </div>
      {fallbackLink && (
        <a
          href={fallbackLink}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline text-sm"
        >
          Открыть ссылку для привязки Telegram
        </a>
      )}
    </div>
  );
};

export default TelegramLinkButton;
