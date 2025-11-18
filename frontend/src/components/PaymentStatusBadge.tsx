import { Badge } from "@/components/ui/badge";
import { 
  CheckCircle2, 
  Clock, 
  XCircle, 
  AlertCircle,
  CreditCard,
  LucideIcon
} from "lucide-react";
import { cn } from "@/lib/utils";

export type PaymentStatus = 'pending' | 'waiting_for_payment' | 'paid' | 'expired' | 'refunded' | 'overdue' | 'no_payment';

interface PaymentStatusConfig {
  label: string;
  icon: LucideIcon;
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  className: string;
}

const statusConfig: Record<PaymentStatus, PaymentStatusConfig> = {
  pending: {
    label: 'Ожидает оплаты',
    icon: Clock,
    variant: 'secondary',
    className: 'bg-amber-50/80 text-amber-700 border-amber-300/50 hover:bg-amber-100/80 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800/50',
  },
  waiting_for_payment: {
    label: 'Ожидание платежа',
    icon: CreditCard,
    variant: 'default',
    className: 'bg-blue-50/80 text-blue-700 border-blue-300/50 hover:bg-blue-100/80 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-800/50',
  },
  paid: {
    label: 'Оплачен',
    icon: CheckCircle2,
    variant: 'default',
    className: 'bg-green-50/80 text-green-700 border-green-300/50 hover:bg-green-100/80 dark:bg-green-950/30 dark:text-green-400 dark:border-green-800/50',
  },
  expired: {
    label: 'Просрочен',
    icon: XCircle,
    variant: 'destructive',
    className: 'bg-red-50/80 text-red-700 border-red-300/50 hover:bg-red-100/80 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800/50',
  },
  refunded: {
    label: 'Возвращен',
    icon: AlertCircle,
    variant: 'outline',
    className: 'bg-slate-50/80 text-slate-700 border-slate-300/50 hover:bg-slate-100/80 dark:bg-slate-950/30 dark:text-slate-400 dark:border-slate-800/50',
  },
  overdue: {
    label: 'Просрочен',
    icon: XCircle,
    variant: 'destructive',
    className: 'bg-red-50/80 text-red-700 border-red-300/50 hover:bg-red-100/80 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800/50',
  },
  no_payment: {
    label: 'Требуется оплата',
    icon: AlertCircle,
    variant: 'destructive',
    className: 'bg-orange-50/80 text-orange-700 border-orange-400/50 hover:bg-orange-100/80 dark:bg-orange-950/30 dark:text-orange-400 dark:border-orange-800/50 animate-pulse',
  },
};

interface PaymentStatusBadgeProps {
  status: PaymentStatus;
  size?: 'sm' | 'default' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const PaymentStatusBadge = ({
  status,
  size = 'default',
  showIcon = true,
  className
}: PaymentStatusBadgeProps) => {
  const config = statusConfig[status] || statusConfig.no_payment;
  const StatusIcon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    default: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  const iconSizeClasses = {
    sm: 'h-3 w-3',
    default: 'h-3.5 w-3.5',
    lg: 'h-4 w-4',
  };

  return (
    <Badge
      variant={config.variant}
      className={cn(
        'inline-flex items-center gap-1.5 font-medium transition-all duration-200 border',
        config.className,
        sizeClasses[size],
        className
      )}
    >
      {showIcon && (
        <StatusIcon className={cn(iconSizeClasses[size], 'shrink-0')} />
      )}
      <span className="whitespace-nowrap">{config.label}</span>
    </Badge>
  );
};

