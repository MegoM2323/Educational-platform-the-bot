// Fallback UI Components for Network Issues and Offline Mode
// Provides graceful degradation when services are unavailable

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  WifiOff, 
  RefreshCw, 
  AlertTriangle, 
  Clock, 
  FileText, 
  MessageSquare,
  BookOpen,
  Users,
  Home,
  Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FallbackUIProps {
  type: 'offline' | 'server-error' | 'maintenance' | 'slow-connection';
  title?: string;
  message?: string;
  onRetry?: () => void;
  onGoHome?: () => void;
  className?: string;
  showRetry?: boolean;
  showHome?: boolean;
}

export const FallbackUI: React.FC<FallbackUIProps> = ({
  type,
  title,
  message,
  onRetry,
  onGoHome,
  className,
  showRetry = true,
  showHome = true,
}) => {
  const getFallbackContent = () => {
    switch (type) {
      case 'offline':
        return {
          icon: <WifiOff className="w-16 h-16 text-muted-foreground" />,
          title: title || 'Нет подключения к интернету',
          message: message || 'Проверьте подключение к интернету и попробуйте снова.',
          color: 'text-destructive',
        };
      
      case 'server-error':
        return {
          icon: <AlertTriangle className="w-16 h-16 text-destructive" />,
          title: title || 'Ошибка сервера',
          message: message || 'На сервере произошла ошибка. Мы уже работаем над её исправлением.',
          color: 'text-destructive',
        };
      
      case 'maintenance':
        return {
          icon: <Settings className="w-16 h-16 text-warning" />,
          title: title || 'Техническое обслуживание',
          message: message || 'Сайт временно недоступен из-за технических работ. Попробуйте позже.',
          color: 'text-warning',
        };
      
      case 'slow-connection':
        return {
          icon: <Clock className="w-16 h-16 text-warning" />,
          title: title || 'Медленное подключение',
          message: message || 'Ваше подключение работает медленно. Некоторые функции могут быть недоступны.',
          color: 'text-warning',
        };
      
      default:
        return {
          icon: <AlertTriangle className="w-16 h-16 text-muted-foreground" />,
          title: title || 'Что-то пошло не так',
          message: message || 'Произошла неожиданная ошибка.',
          color: 'text-muted-foreground',
        };
    }
  };

  const content = getFallbackContent();

  return (
    <div className={cn('min-h-screen flex items-center justify-center p-4', className)}>
      <Card className="w-full max-w-md p-8 text-center">
        <div className="flex flex-col items-center space-y-6">
          <div className="w-20 h-20 bg-muted/50 rounded-full flex items-center justify-center">
            {content.icon}
          </div>
          
          <div className="space-y-2">
            <h2 className={cn('text-2xl font-semibold', content.color)}>
              {content.title}
            </h2>
            <p className="text-muted-foreground">
              {content.message}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full">
            {showRetry && onRetry && (
              <Button type="button"
                onClick={onRetry}
                className="flex-1"
                variant={type === 'offline' ? 'default' : 'outline'}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Попробовать снова
              </Button>
            )}
            
            {showHome && onGoHome && (
              <Button type="button"
                onClick={onGoHome}
                variant="outline"
                className="flex-1"
              >
                <Home className="w-4 h-4 mr-2" />
                На главную
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

// Offline mode content with cached data
interface OfflineContentProps {
  cachedData?: {
    materials?: any[];
    messages?: any[];
    reports?: any[];
  };
  onRetry?: () => void;
  className?: string;
}

export const OfflineContent: React.FC<OfflineContentProps> = ({
  cachedData,
  onRetry,
  className
}) => {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Offline indicator */}
      <Card className="p-4 border-warning">
        <div className="flex items-center gap-3">
          <WifiOff className="w-5 h-5 text-warning" />
          <div>
            <h3 className="font-semibold text-warning">Режим офлайн</h3>
            <p className="text-sm text-muted-foreground">
              Некоторые данные могут быть устаревшими
            </p>
          </div>
          {onRetry && (
            <Button type="button" size="sm" onClick={onRetry} className="ml-auto">
              <RefreshCw className="w-4 h-4 mr-2" />
              Обновить
            </Button>
          )}
        </div>
      </Card>

      {/* Cached content sections */}
      {cachedData?.materials && cachedData.materials.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5" />
            <h3 className="font-semibold">Материалы (кэшированные)</h3>
            <Badge variant="secondary">Офлайн</Badge>
          </div>
          <div className="space-y-2">
            {cachedData.materials.slice(0, 3).map((material, index) => (
              <div key={index} className="p-2 bg-muted rounded text-sm">
                {material.title || `Материал ${index + 1}`}
              </div>
            ))}
            {cachedData.materials.length > 3 && (
              <p className="text-xs text-muted-foreground">
                И еще {cachedData.materials.length - 3} материалов...
              </p>
            )}
          </div>
        </Card>
      )}

      {cachedData?.messages && cachedData.messages.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="w-5 h-5" />
            <h3 className="font-semibold">Сообщения (кэшированные)</h3>
            <Badge variant="secondary">Офлайн</Badge>
          </div>
          <div className="space-y-2">
            {cachedData.messages.slice(0, 3).map((message, index) => (
              <div key={index} className="p-2 bg-muted rounded text-sm">
                <div className="font-medium">{message.sender_name || 'Пользователь'}</div>
                <div className="text-muted-foreground">{message.content}</div>
              </div>
            ))}
            {cachedData.messages.length > 3 && (
              <p className="text-xs text-muted-foreground">
                И еще {cachedData.messages.length - 3} сообщений...
              </p>
            )}
          </div>
        </Card>
      )}

      {cachedData?.reports && cachedData.reports.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5" />
            <h3 className="font-semibold">Отчеты (кэшированные)</h3>
            <Badge variant="secondary">Офлайн</Badge>
          </div>
          <div className="space-y-2">
            {cachedData.reports.slice(0, 3).map((report, index) => (
              <div key={index} className="p-2 bg-muted rounded text-sm">
                <div className="font-medium">{report.student_name || `Отчет ${index + 1}`}</div>
                <div className="text-muted-foreground">{report.created_at}</div>
              </div>
            ))}
            {cachedData.reports.length > 3 && (
              <p className="text-xs text-muted-foreground">
                И еще {cachedData.reports.length - 3} отчетов...
              </p>
            )}
          </div>
        </Card>
      )}

      {/* Empty state if no cached data */}
      {(!cachedData || Object.keys(cachedData).length === 0) && (
        <Card className="p-8 text-center">
          <div className="space-y-4">
            <WifiOff className="w-12 h-12 text-muted-foreground mx-auto" />
            <div>
              <h3 className="font-semibold">Нет кэшированных данных</h3>
              <p className="text-sm text-muted-foreground">
                Восстановите подключение к интернету для загрузки данных
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

// Service unavailable component
interface ServiceUnavailableProps {
  service: 'chat' | 'materials' | 'reports' | 'payments';
  onRetry?: () => void;
  className?: string;
}

export const ServiceUnavailable: React.FC<ServiceUnavailableProps> = ({
  service,
  onRetry,
  className
}) => {
  const getServiceInfo = () => {
    switch (service) {
      case 'chat':
        return {
          icon: <MessageSquare className="w-8 h-8" />,
          title: 'Чат временно недоступен',
          message: 'Сервис чата временно недоступен. Попробуйте позже.',
        };
      case 'materials':
        return {
          icon: <BookOpen className="w-8 h-8" />,
          title: 'Материалы недоступны',
          message: 'Не удается загрузить материалы. Проверьте подключение.',
        };
      case 'reports':
        return {
          icon: <FileText className="w-8 h-8" />,
          title: 'Отчеты недоступны',
          message: 'Не удается загрузить отчеты. Попробуйте позже.',
        };
      case 'payments':
        return {
          icon: <Users className="w-8 h-8" />,
          title: 'Платежи недоступны',
          message: 'Сервис платежей временно недоступен. Попробуйте позже.',
        };
    }
  };

  const serviceInfo = getServiceInfo();

  return (
    <Card className={cn('p-6 text-center', className)}>
      <div className="space-y-4">
        <div className="w-16 h-16 bg-muted/50 rounded-full flex items-center justify-center mx-auto">
          {serviceInfo.icon}
        </div>
        
        <div className="space-y-2">
          <h3 className="font-semibold">{serviceInfo.title}</h3>
          <p className="text-sm text-muted-foreground">{serviceInfo.message}</p>
        </div>

        {onRetry && (
          <Button type="button" onClick={onRetry} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Попробовать снова
          </Button>
        )}
      </div>
    </Card>
  );
};

// Loading state with timeout
interface LoadingWithTimeoutProps {
  timeout?: number;
  onTimeout?: () => void;
  children: React.ReactNode;
  className?: string;
}

export const LoadingWithTimeout: React.FC<LoadingWithTimeoutProps> = ({
  timeout = 10000,
  onTimeout,
  children,
  className
}) => {
  const [hasTimedOut, setHasTimedOut] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setHasTimedOut(true);
      onTimeout?.();
    }, timeout);

    return () => clearTimeout(timer);
  }, [timeout, onTimeout]);

  if (hasTimedOut) {
    return (
      <FallbackUI
        type="server-error"
        title="Загрузка занимает слишком много времени"
        message="Попробуйте обновить страницу или проверить подключение к интернету."
        onRetry={() => window.location.reload()}
        className={className}
      />
    );
  }

  return <>{children}</>;
};

export default FallbackUI;

