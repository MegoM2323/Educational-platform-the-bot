import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  CreditCard,
  CheckCircle2,
  Clock,
  Loader2,
  ExternalLink,
  Calendar,
  DollarSign,
  XCircle,
  AlertCircle,
  X,
  Repeat,
  RefreshCw
} from "lucide-react";
import { toast } from "sonner";
import { unifiedAPI as djangoAPI, Payment } from "@/integrations/api/unifiedClient";
import { PaymentStatusBadge, PaymentStatus } from "@/components/PaymentStatusBadge";
import { parentDashboardAPI } from "@/integrations/api/dashboard";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export interface SubjectPayment {
  id: number;
  enrollment: {
    id: number;
    student: {
      id: number;
      first_name: string;
      last_name: string;
    };
    subject: {
      id: number;
      name: string;
      color: string;
    };
    teacher: {
      id: number;
      first_name: string;
      last_name: string;
    };
  };
  subject_name?: string; // Кастомное название предмета из API
  payment?: Payment;
  amount: number;
  status: PaymentStatus;
  due_date: string;
  paid_at?: string;
  created_at: string;
  next_payment_date?: string;
  has_subscription?: boolean;
}

interface PaymentButtonProps {
  subjectPayment: SubjectPayment;
  onPaymentSuccess?: (payment: Payment) => void;
  onPaymentError?: (error: string) => void;
  onCancelSubscription?: () => void | Promise<void>;
  childId?: number;
  enrollmentId?: number;
  className?: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
  showDetails?: boolean;
}

const statusConfig = {
  pending: {
    label: 'Ожидает оплаты',
    icon: Clock,
    buttonText: 'Подключить предмет',
    buttonVariant: 'default' as const,
  },
  waiting_for_payment: {
    label: 'Ожидание платежа',
    icon: Clock,
    buttonText: 'Перейти к оплате',
    buttonVariant: 'default' as const,
  },
  paid: {
    label: 'Оплачен',
    icon: CheckCircle2,
    buttonText: 'Оплачено',
    buttonVariant: 'outline' as const,
  },
  expired: {
    label: 'Просрочен',
    icon: XCircle,
    buttonText: 'Просрочен',
    buttonVariant: 'outline' as const,
  },
  refunded: {
    label: 'Возвращен',
    icon: AlertCircle,
    buttonText: 'Возвращен',
    buttonVariant: 'outline' as const,
  },
  overdue: {
    label: 'Просрочен',
    icon: XCircle,
    buttonText: 'Просрочен',
    buttonVariant: 'outline' as const,
  },
  no_payment: {
    label: 'Без платежа',
    icon: AlertCircle,
    buttonText: 'Подключить предмет',
    buttonVariant: 'default' as const,
  },
};

export const PaymentButton = ({
  subjectPayment,
  onPaymentSuccess,
  onPaymentError,
  onCancelSubscription,
  childId,
  enrollmentId,
  className = "",
  variant = "default",
  size = "default",
  showDetails = false
}: PaymentButtonProps) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [payment, setPayment] = useState<Payment | null>(subjectPayment.payment || null);
  const [paymentStatus, setPaymentStatus] = useState(subjectPayment.status);
  const [hasSubscription, setHasSubscription] = useState(subjectPayment.has_subscription || false);
  const [pollingAttempt, setPollingAttempt] = useState(0);
  const [isPolling, setIsPolling] = useState(false);
  const [pollingTimedOut, setPollingTimedOut] = useState(false);

  const config = statusConfig[paymentStatus] || statusConfig.pending;
  const StatusIcon = config.icon;

  // Проверяем статус платежа периодически
  useEffect(() => {
    if (payment && (payment.status === 'pending' || payment.status === 'waiting_for_capture')) {
      let attempts = 0;
      const maxAttempts = 60; // 5 минут при интервале 5 секунд
      setIsPolling(true);
      setPollingTimedOut(false);

      const interval = setInterval(async () => {
        attempts++;
        setPollingAttempt(attempts);

        try {
          const updatedPayment = await djangoAPI.getPaymentStatus(payment.id);
          setPayment(updatedPayment);

          if (updatedPayment.status === 'succeeded') {
            setPaymentStatus('paid');
            // После успешной оплаты подписка должна быть активна
            setHasSubscription(true);
            setIsPolling(false);
            setPollingAttempt(0);
            onPaymentSuccess?.(updatedPayment);
            toast.success("Платеж успешно обработан! Автосписание подключено.");
            clearInterval(interval);
          } else if (updatedPayment.status === 'canceled') {
            setPaymentStatus('pending');
            setIsPolling(false);
            setPollingAttempt(0);
            onPaymentError?.("Платеж был отменен");
            clearInterval(interval);
          } else if (updatedPayment.status === 'waiting_for_capture') {
            setPaymentStatus('waiting_for_payment');
          } else if (attempts >= maxAttempts) {
            // Прекращаем проверку после 5 минут
            setIsPolling(false);
            setPollingTimedOut(true);
            clearInterval(interval);
            toast.info("Время проверки статуса платежа истекло. Используйте кнопку повтора или обновите страницу.");
          }
        } catch (error) {
          console.error("Error checking payment status:", error);

          // После 3 неудачных попыток останавливаем проверку
          if (attempts >= 3) {
            setIsPolling(false);
            setPollingTimedOut(true);
            clearInterval(interval);
            toast.error("Не удалось проверить статус платежа. Используйте кнопку повтора или обновите страницу.");
          }
        }
      }, 5000);

      return () => {
        clearInterval(interval);
        setIsPolling(false);
      };
    }
  }, [payment, onPaymentSuccess, onPaymentError]);

  const handlePayment = async () => {
    if (paymentStatus !== 'pending' && paymentStatus !== 'waiting_for_payment') return;

    // Если платеж уже создан и есть confirmation_url, просто открываем его
    if (payment && payment.confirmation_url && paymentStatus === 'waiting_for_payment') {
      window.open(payment.confirmation_url, '_blank');
      return;
    }

    setIsLoading(true);
    toast.info("Создание платежа...", { duration: 2000 });
    
    try {
      // Получаем название предмета (кастомное или стандартное)
      const subjectName = subjectPayment.subject_name || subjectPayment.enrollment.subject.name;
      
      // Создаем платеж через API
      const paymentData = {
        amount: subjectPayment.amount.toString(),
        service_name: `Оплата за предмет: ${subjectName}`,
        customer_fio: `${subjectPayment.enrollment.student.first_name} ${subjectPayment.enrollment.student.last_name}`,
        description: `Оплата за предмет "${subjectName}" для ученика ${subjectPayment.enrollment.student.first_name} ${subjectPayment.enrollment.student.last_name}`,
        return_url: window.location.href,
        metadata: {
          subject_payment_id: subjectPayment.id,
          enrollment_id: subjectPayment.enrollment.id,
          subject_id: subjectPayment.enrollment.subject.id,
          student_id: subjectPayment.enrollment.student.id,
        }
      };

      const newPayment = await djangoAPI.createPayment(paymentData);
      
      if (!newPayment) {
        throw new Error("Не удалось создать платеж. Пустой ответ от сервера.");
      }
      
      setPayment(newPayment);
      setPaymentStatus('waiting_for_payment');

      if (newPayment.confirmation_url) {
        toast.success("Перенаправление на страницу оплаты...", { duration: 3000 });
        
        // Открываем страницу оплаты в новом окне
        const paymentWindow = window.open(newPayment.confirmation_url, '_blank');
        
        if (!paymentWindow) {
          toast.error("Не удалось открыть окно оплаты. Проверьте настройки блокировки всплывающих окон.", { duration: 5000 });
        }
      } else {
        throw new Error("Не получена ссылка для оплаты от платежного сервиса");
      }
    } catch (error) {
      console.error("Error creating payment:", error);
      
      let errorMessage = "Ошибка при создании платежа";
      
      if (error instanceof Error) {
        errorMessage = error.message;
        
        // Добавляем более понятные сообщения для пользователя
        if (error.message.includes('network') || error.message.includes('Failed to fetch')) {
          errorMessage = "Нет подключения к серверу. Проверьте интернет-соединение.";
        } else if (error.message.includes('500')) {
          errorMessage = "Ошибка на сервере. Попробуйте позже.";
        } else if (error.message.includes('400')) {
          errorMessage = "Неверные данные для платежа. Проверьте введенную информацию.";
        }
      }
      
      onPaymentError?.(errorMessage);
      toast.error(errorMessage, { duration: 5000 });
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const isOverdue = () => {
    if (paymentStatus !== 'pending' && paymentStatus !== 'waiting_for_payment') return false;
    return new Date(subjectPayment.due_date) < new Date();
  };

  const handleCancelSubscription = async () => {
    if (!childId || !enrollmentId) {
      toast.error("Не указаны параметры для отмены подписки");
      return;
    }

    const subjectName = subjectPayment.subject_name || subjectPayment.enrollment.subject.name;
    const confirmed = window.confirm(
      `Отключить автосписание для предмета "${subjectName}"?`
    );

    if (!confirmed) return;

    setIsCancelling(true);
    try {
      if (onCancelSubscription) {
        await onCancelSubscription();
      } else {
        await parentDashboardAPI.cancelSubscription(childId, enrollmentId);
      }
      setHasSubscription(false);
      toast.success("Автосписание отключено");
      // Обновляем состояние без перезагрузки страницы
      if (onPaymentSuccess) {
        // Если есть колбэк, вызываем его для обновления родительского компонента
        const updatedPayment = payment || {} as Payment;
        onPaymentSuccess(updatedPayment);
      }
    } catch (error) {
      console.error('Cancel subscription error:', error);
      toast.error("Не удалось отключить автосписание. Попробуйте позже.");
    } finally {
      setIsCancelling(false);
    }
  };

  const handleRetryPolling = async () => {
    if (!payment) return;

    setPollingTimedOut(false);
    setPollingAttempt(0);

    try {
      const updatedPayment = await djangoAPI.getPaymentStatus(payment.id);
      setPayment(updatedPayment);

      if (updatedPayment.status === 'succeeded') {
        setPaymentStatus('paid');
        setHasSubscription(true);
        onPaymentSuccess?.(updatedPayment);
        toast.success("Платеж успешно обработан! Автосписание подключено.");
      } else if (updatedPayment.status === 'canceled') {
        setPaymentStatus('pending');
        onPaymentError?.("Платеж был отменен");
      } else {
        toast.info("Платеж все еще обрабатывается. Попробуйте позже.");
      }
    } catch (error) {
      console.error("Error retrying payment status check:", error);
      toast.error("Не удалось проверить статус платежа. Попробуйте позже.");
    }
  };

  const getButtonContent = () => {
    if (isLoading) {
      return (
        <>
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          <span>Обработка...</span>
        </>
      );
    }

    if (paymentStatus === 'paid') {
      return (
        <>
          <CheckCircle2 className="h-4 w-4 mr-2" />
          <span>Оплачено</span>
        </>
      );
    }

    if (paymentStatus === 'waiting_for_payment' && payment?.confirmation_url) {
      return (
        <>
          <ExternalLink className="h-4 w-4 mr-2" />
          <span>Перейти к оплате</span>
        </>
      );
    }

    if (paymentStatus === 'pending' && payment?.confirmation_url) {
      return (
        <>
          <ExternalLink className="h-4 w-4 mr-2" />
          <span>Перейти к оплате</span>
        </>
      );
    }

    return (
      <>
        <CreditCard className="h-4 w-4 mr-2" />
        <span>{config.buttonText}</span>
      </>
    );
  };

  if (showDetails) {
    return (
      <Card className={`${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: subjectPayment.enrollment.subject.color }}
              />
              <span className="font-medium">{subjectPayment.subject_name || subjectPayment.enrollment.subject.name}</span>
            </div>
            <PaymentStatusBadge status={paymentStatus as PaymentStatus} size="default" />
          </div>

          <div className="space-y-2 text-sm text-muted-foreground mb-4">
            <div className="flex justify-between">
              <span>Ученик:</span>
              <span className="font-medium">
                {subjectPayment.enrollment.student.first_name} {subjectPayment.enrollment.student.last_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Учитель:</span>
              <span className="font-medium">
                {subjectPayment.enrollment.teacher.first_name} {subjectPayment.enrollment.teacher.last_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Сумма:</span>
              <span className="font-medium text-lg">{formatAmount(subjectPayment.amount)}</span>
            </div>
            <div className="flex justify-between">
              <span>Срок оплаты:</span>
              <span className={`font-medium ${isOverdue() ? 'text-red-600' : ''}`}>
                {formatDate(subjectPayment.due_date)}
              </span>
            </div>
            {subjectPayment.paid_at && (
              <div className="flex justify-between">
                <span>Дата оплаты:</span>
                <span className="font-medium text-green-600">
                  {formatDate(subjectPayment.paid_at)}
                </span>
              </div>
            )}
            {subjectPayment.next_payment_date && (
              <div className="flex justify-between">
                <span>Следующий платеж:</span>
                <span className="font-medium text-blue-600">
                  {formatDate(subjectPayment.next_payment_date)}
                </span>
              </div>
            )}
            {hasSubscription && paymentStatus === 'paid' && (
              <div className="flex items-center justify-between pt-2 mt-2 border-t">
                <div className="flex items-center gap-2">
                  <Repeat className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium text-green-600">Автосписание подключено</span>
                </div>
                <Badge variant="secondary" className="text-xs">Активно</Badge>
              </div>
            )}
          </div>

          <div className="space-y-2">
            {isPolling && (
              <div className="space-y-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-md">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span className="text-blue-700 dark:text-blue-300">
                      Проверяем статус платежа... (попытка {pollingAttempt} из 60)
                    </span>
                  </div>
                </div>
                <Progress value={(pollingAttempt / 60) * 100} className="h-2" />
              </div>
            )}

            {pollingTimedOut && (
              <Button
                onClick={handleRetryPolling}
                variant="outline"
                size={size}
                className="w-full"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                <span>Проверить статус платежа</span>
              </Button>
            )}

            {hasSubscription && paymentStatus === 'paid' ? (
              <Button
                onClick={handleCancelSubscription}
                disabled={isCancelling}
                variant="outline"
                size={size}
                className="w-full"
              >
                {isCancelling ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    <span>Отключение...</span>
                  </>
                ) : (
                  <>
                    <X className="h-4 w-4 mr-2" />
                    <span>Отключить автосписание</span>
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={handlePayment}
                disabled={(paymentStatus !== 'pending' && paymentStatus !== 'waiting_for_payment') || isLoading}
                variant={(paymentStatus === 'pending' || paymentStatus === 'waiting_for_payment') ? 'default' : 'outline'}
                size={size}
                className={`w-full ${(paymentStatus === 'pending' || paymentStatus === 'waiting_for_payment') ? 'gradient-primary shadow-glow hover:opacity-90 transition-opacity' : ''}`}
              >
                {getButtonContent()}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Button
      onClick={handlePayment}
      disabled={(paymentStatus !== 'pending' && paymentStatus !== 'waiting_for_payment') || isLoading}
      variant={(paymentStatus === 'pending' || paymentStatus === 'waiting_for_payment') ? variant : 'outline'}
      size={size}
      className={`${className} ${(paymentStatus === 'pending' || paymentStatus === 'waiting_for_payment') ? 'gradient-primary shadow-glow hover:opacity-90 transition-opacity' : ''}`}
    >
      {getButtonContent()}
    </Button>
  );
};
