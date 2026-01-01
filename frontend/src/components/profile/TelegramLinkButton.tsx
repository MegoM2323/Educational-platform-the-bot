import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { telegramAPI, type TelegramProfile } from '@/integrations/api/telegramAPI';

interface TelegramLinkButtonProps {
  isLinked: boolean;
  telegramUsername?: string;
  onStatusChange?: () => void;
}

export const TelegramLinkButton: React.FC<TelegramLinkButtonProps> = ({
  isLinked,
  telegramUsername,
  onStatusChange,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [fallbackLink, setFallbackLink] = useState<string | null>(null);
  const [telegramData, setTelegramData] = useState<TelegramProfile | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (isLinked) {
      fetchTelegramProfile();
    }
  }, [isLinked]);

  const fetchTelegramProfile = async () => {
    try {
      const response = await telegramAPI.getTelegramProfile();
      if (response.success && response.data) {
        setTelegramData(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch Telegram profile:', error);
    }
  };

  const handleLink = async () => {
    setIsLoading(true);
    setFallbackLink(null);
    try {
      const response = await telegramAPI.generateLinkToken();

      if (response.success && response.data) {
        const { link } = response.data;
        const popup = window.open(link, '_blank', 'width=600,height=700');
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
        throw new Error(response.error || 'Failed to generate link');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Не удалось создать ссылку';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnlink = async () => {
    setIsLoading(true);
    try {
      const response = await telegramAPI.unlinkTelegram();

      if (response.success) {
        setTelegramData(null);
        toast({
          title: 'Готово',
          description: 'Telegram отвязан от аккаунта',
        });
        onStatusChange?.();
      } else {
        throw new Error(response.error || 'Failed to unlink');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Не удалось отвязать Telegram';
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 p-4 rounded-lg border border-gray-200 bg-gray-50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5"
            fill="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.146-.28.292-.576.292-.482 0-.403-.178-.568-.631l-1.25-4.405-3.51-1.094c-.532-.17-.547-.547.12-.816l13.863-5.338c.684-.256 1.29.063 1.061 1.196z" />
          </svg>
          {isLinked && telegramData ? (
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-900">
                Telegram привязан: @{telegramData.telegram_username}
              </span>
              <span className="text-xs text-gray-500">
                Привязано: {new Date(telegramData.linked_at).toLocaleDateString('ru-RU')}
              </span>
            </div>
          ) : (
            <span className="text-sm text-gray-600">Telegram не привязан</span>
          )}
        </div>

        <div className="flex gap-2">
          {isLinked ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleUnlink}
              disabled={isLoading}
              className="whitespace-nowrap"
            >
              {isLoading ? 'Отвязка...' : 'Отвязать'}
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={handleLink}
              disabled={isLoading}
              className="whitespace-nowrap"
            >
              {isLoading ? 'Загрузка...' : 'Привязать'}
            </Button>
          )}
        </div>
      </div>

      {fallbackLink && (
        <div className="mt-2">
          <a
            href={fallbackLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
            </svg>
            Открыть ссылку для привязки Telegram
          </a>
        </div>
      )}
    </div>
  );
};

export default TelegramLinkButton;
