import React from 'react';
import { CreditCard, Repeat, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export interface PayButtonProps {
  paymentStatus?: string;
  subscriptionStatus?: string;
  expiresAt?: string;
  nextPaymentDate?: string;
  hasSubscription?: boolean;
  onPayClick: () => void;
  onCancelClick: () => void;
  isLoading?: boolean;
  className?: string;
}

interface PayButtonState {
  case: 'cancelled' | 'active' | 'overdue' | 'waiting';
  badge: {
    text: string;
    className: string;
  };
  button?: {
    text: string;
    variant: 'default' | 'destructive' | 'outline';
    icon: React.ReactNode;
  };
  tooltip: string;
  disabled: boolean;
  showCancelButton: boolean;
}

const getPayButtonState = (props: PayButtonProps): PayButtonState => {
  const {
    paymentStatus,
    subscriptionStatus,
    expiresAt,
    nextPaymentDate,
    hasSubscription,
    isLoading,
  } = props;

  const isNextPaymentInFuture = nextPaymentDate
    ? new Date(nextPaymentDate) > new Date()
    : false;

  if (subscriptionStatus === 'cancelled' && expiresAt) {
    return {
      case: 'cancelled',
      badge: {
        text: 'Доступ ограничен',
        className: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100',
      },
      tooltip: `Доступ ограничен до ${new Date(expiresAt).toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })}. После этой даты нужно будет возобновить подписку.`,
      disabled: true,
      showCancelButton: false,
    };
  }

  const hasActivePayment =
    paymentStatus === 'paid' && (isNextPaymentInFuture || hasSubscription);

  if (hasActivePayment) {
    return {
      case: 'active',
      badge: {
        text: 'Активен',
        className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100',
      },
      tooltip: hasSubscription
        ? 'Активная подписка. Средства будут снята автоматически в дату следующего платежа.'
        : 'Предмет оплачен и доступен.',
      disabled: isLoading || false,
      showCancelButton: hasSubscription || false,
    };
  }

  if (
    paymentStatus === 'overdue' ||
    (paymentStatus === 'paid' && !isNextPaymentInFuture)
  ) {
    return {
      case: 'overdue',
      badge: {
        text: 'Требуется оплата',
        className:
          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
      },
      button: {
        text: 'Оплатить предмет',
        variant: 'destructive',
        icon: <CreditCard className="w-4 h-4" />,
      },
      tooltip: 'Срок оплаты истёк. Нужна новая оплата для продолжения обучения.',
      disabled: isLoading || false,
      showCancelButton: false,
    };
  }

  return {
    case: 'waiting',
    badge: {
      text: 'Не подключен',
      className:
        'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
    },
    button: {
      text: 'Подключить предмет',
      variant: 'default',
      icon: <CreditCard className="w-4 h-4" />,
    },
    tooltip: 'Нажмите для подключения предмета.',
    disabled: isLoading || false,
    showCancelButton: false,
  };
};

export const PayButton = React.forwardRef<HTMLDivElement, PayButtonProps>(
  (props, ref) => {
    const {
      onPayClick,
      onCancelClick,
      isLoading = false,
      className,
    } = props;

    const state = getPayButtonState(props);

    const expiresAtText = props.expiresAt
      ? new Date(props.expiresAt).toLocaleString('ru-RU', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        })
      : null;

    return (
      <TooltipProvider>
        <div
          ref={ref}
          className={cn(
            'flex flex-col items-end gap-2',
            className
          )}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 cursor-help">
                {state.case === 'cancelled' && (
                  <AlertCircle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                )}
                <Badge
                  variant="secondary"
                  className={cn('text-xs', state.badge.className)}
                >
                  {state.badge.text}
                </Badge>
              </div>
            </TooltipTrigger>
            <TooltipContent>{state.tooltip}</TooltipContent>
          </Tooltip>

          {state.case === 'cancelled' && expiresAtText && (
            <div className="text-xs text-orange-600 dark:text-orange-400 text-right">
              До: {expiresAtText}
            </div>
          )}

          {state.button && (
            <Button
              type="button"
              size="sm"
              variant={state.button.variant}
              onClick={onPayClick}
              disabled={state.disabled}
              className="gap-2"
            >
              {state.button.icon}
              {state.button.text}
            </Button>
          )}

          {state.showCancelButton && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onCancelClick}
              disabled={isLoading}
              className="gap-2 whitespace-nowrap"
            >
              <Repeat className="w-4 h-4" />
              Отключить автосписание
            </Button>
          )}
        </div>
      </TooltipProvider>
    );
  }
);

PayButton.displayName = 'PayButton';
