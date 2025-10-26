import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { 
  CreditCard, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  AlertCircle,
  Loader2,
  ExternalLink,
  Calendar,
  DollarSign
} from "lucide-react";
import { toast } from "sonner";
import { unifiedAPI as djangoAPI, Payment } from "@/integrations/api/unifiedClient";

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
  payment?: Payment;
  amount: number;
  status: 'pending' | 'paid' | 'expired' | 'refunded';
  due_date: string;
  paid_at?: string;
  created_at: string;
}

interface PaymentButtonProps {
  subjectPayment: SubjectPayment;
  onPaymentSuccess?: (payment: Payment) => void;
  onPaymentError?: (error: string) => void;
  className?: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
  showDetails?: boolean;
}

const statusConfig = {
  pending: {
    label: 'Ожидает оплаты',
    color: 'bg-yellow-100 text-yellow-800',
    icon: Clock,
    buttonText: 'Оплатить',
    buttonVariant: 'default' as const,
  },
  paid: {
    label: 'Оплачен',
    color: 'bg-green-100 text-green-800',
    icon: CheckCircle2,
    buttonText: 'Оплачено',
    buttonVariant: 'outline' as const,
  },
  expired: {
    label: 'Просрочен',
    color: 'bg-red-100 text-red-800',
    icon: XCircle,
    buttonText: 'Просрочен',
    buttonVariant: 'outline' as const,
  },
  refunded: {
    label: 'Возвращен',
    color: 'bg-gray-100 text-gray-800',
    icon: AlertCircle,
    buttonText: 'Возвращен',
    buttonVariant: 'outline' as const,
  },
};

export const PaymentButton = ({
  subjectPayment,
  onPaymentSuccess,
  onPaymentError,
  className = "",
  variant = "default",
  size = "default",
  showDetails = false
}: PaymentButtonProps) => {
  const [isLoading, setIsLoading] = useState(false);
  const [payment, setPayment] = useState<Payment | null>(subjectPayment.payment || null);
  const [paymentStatus, setPaymentStatus] = useState(subjectPayment.status);

  const config = statusConfig[paymentStatus];
  const StatusIcon = config.icon;

  // Проверяем статус платежа периодически
  useEffect(() => {
    if (payment && payment.status === 'pending') {
      let attempts = 0;
      const maxAttempts = 24; // 2 минуты при интервале 5 секунд
      
      const interval = setInterval(async () => {
        attempts++;
        
        try {
          const updatedPayment = await djangoAPI.getPaymentStatus(payment.id);
          setPayment(updatedPayment);
          
          if (updatedPayment.status === 'succeeded') {
            setPaymentStatus('paid');
            onPaymentSuccess?.(updatedPayment);
            toast.success("Платеж успешно обработан!");
            clearInterval(interval);
          } else if (updatedPayment.status === 'canceled') {
            setPaymentStatus('pending');
            onPaymentError?.("Платеж был отменен");
            clearInterval(interval);
          } else if (attempts >= maxAttempts) {
            // Прекращаем проверку после 2 минут
            clearInterval(interval);
            toast.info("Проверка статуса платежа завершена. Обновите страницу для актуального статуса.");
          }
        } catch (error) {
          console.error("Error checking payment status:", error);
          
          // После 3 неудачных попыток останавливаем проверку
          if (attempts >= 3) {
            clearInterval(interval);
            toast.error("Не удалось проверить статус платежа. Пожалуйста, обновите страницу.");
          }
        }
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [payment, onPaymentSuccess, onPaymentError]);

  const handlePayment = async () => {
    if (paymentStatus !== 'pending') return;

    setIsLoading(true);
    toast.info("Создание платежа...", { duration: 2000 });
    
    try {
      // Создаем платеж через API
      const paymentData = {
        amount: subjectPayment.amount.toString(),
        service_name: `Оплата за предмет: ${subjectPayment.enrollment.subject.name}`,
        customer_fio: `${subjectPayment.enrollment.student.first_name} ${subjectPayment.enrollment.student.last_name}`,
        description: `Оплата за предмет "${subjectPayment.enrollment.subject.name}" для ученика ${subjectPayment.enrollment.student.first_name} ${subjectPayment.enrollment.student.last_name}`,
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
    if (paymentStatus !== 'pending') return false;
    return new Date(subjectPayment.due_date) < new Date();
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
              <span className="font-medium">{subjectPayment.enrollment.subject.name}</span>
            </div>
            <Badge className={config.color}>
              <StatusIcon className="h-3 w-3 mr-1" />
              {config.label}
            </Badge>
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
          </div>

          <Button
            onClick={handlePayment}
            disabled={paymentStatus !== 'pending' || isLoading}
            variant={paymentStatus === 'pending' ? 'default' : 'outline'}
            size={size}
            className={`w-full ${paymentStatus === 'pending' ? 'gradient-primary shadow-glow hover:opacity-90 transition-opacity' : ''}`}
          >
            {getButtonContent()}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Button
      onClick={handlePayment}
      disabled={paymentStatus !== 'pending' || isLoading}
      variant={paymentStatus === 'pending' ? variant : 'outline'}
      size={size}
      className={`${className} ${paymentStatus === 'pending' ? 'gradient-primary shadow-glow hover:opacity-90 transition-opacity' : ''}`}
    >
      {getButtonContent()}
    </Button>
  );
};
