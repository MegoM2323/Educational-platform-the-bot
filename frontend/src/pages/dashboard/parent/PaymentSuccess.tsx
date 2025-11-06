import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { CheckCircle, XCircle, Loader2, ArrowLeft } from "lucide-react";
import { unifiedAPI } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [paymentStatus, setPaymentStatus] = useState<'loading' | 'success' | 'failed' | 'pending'>('loading');
  const [paymentData, setPaymentData] = useState<any>(null);

  useEffect(() => {
    const paymentId = searchParams.get('payment_id');
    
    if (!paymentId) {
      setPaymentStatus('failed');
      return;
    }

    // Проверяем статус платежа
    const checkPayment = async () => {
      try {
        const response = await unifiedAPI.request(`/api/check-payment/?payment_id=${paymentId}`);
        
        if (response.data) {
          const status = response.data.status;
          setPaymentData(response.data);
          
          if (status === 'succeeded' || status === 'SUCCEEDED') {
            setPaymentStatus('success');
            toast({
              title: "Платеж успешно обработан",
              description: "Ваш платеж был успешно завершен",
              variant: "default",
            });
          } else if (status === 'canceled' || status === 'CANCELED') {
            setPaymentStatus('failed');
            toast({
              title: "Платеж отменен",
              description: "Платеж был отменен",
              variant: "destructive",
            });
          } else {
            setPaymentStatus('pending');
          }
        } else {
          setPaymentStatus('failed');
        }
      } catch (error: any) {
        console.error('Error checking payment status:', error);
        setPaymentStatus('failed');
        toast({
          title: "Ошибка проверки платежа",
          description: error.message || "Не удалось проверить статус платежа",
          variant: "destructive",
        });
      }
    };

    checkPayment();
  }, [searchParams, toast]);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold">Статус платежа</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-6">
            <Card className="p-8 max-w-2xl mx-auto">
              {paymentStatus === 'loading' && (
                <div className="text-center">
                  <Loader2 className="h-16 w-16 mx-auto mb-4 animate-spin text-primary" />
                  <h2 className="text-2xl font-bold mb-2">Проверка платежа...</h2>
                  <p className="text-muted-foreground">Пожалуйста, подождите</p>
                </div>
              )}

              {paymentStatus === 'success' && (
                <div className="text-center">
                  <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
                  <h2 className="text-2xl font-bold mb-2">Платеж успешно завершен!</h2>
                  <p className="text-muted-foreground mb-6">
                    Ваш платеж был успешно обработан
                  </p>
                  {paymentData && (
                    <div className="space-y-2 mb-6 text-left bg-muted p-4 rounded-lg">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Сумма:</span>
                        <span className="font-semibold">{paymentData.amount} ₽</span>
                      </div>
                      {paymentData.description && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Описание:</span>
                          <span className="font-medium">{paymentData.description}</span>
                        </div>
                      )}
                      {paymentData.paid_at && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Дата оплаты:</span>
                          <span>{new Date(paymentData.paid_at).toLocaleString('ru-RU')}</span>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="flex gap-4 justify-center">
                    <Button onClick={() => navigate('/dashboard/parent')}>
                      Вернуться в личный кабинет
                    </Button>
                    <Button variant="outline" onClick={() => navigate('/dashboard/parent/payment-history')}>
                      История платежей
                    </Button>
                  </div>
                </div>
              )}

              {paymentStatus === 'pending' && (
                <div className="text-center">
                  <Loader2 className="h-16 w-16 mx-auto mb-4 animate-spin text-yellow-500" />
                  <h2 className="text-2xl font-bold mb-2">Платеж обрабатывается</h2>
                  <p className="text-muted-foreground mb-6">
                    Ваш платеж находится в обработке. Пожалуйста, подождите.
                  </p>
                  <Button onClick={() => navigate('/dashboard/parent')}>
                    Вернуться в личный кабинет
                  </Button>
                </div>
              )}

              {paymentStatus === 'failed' && (
                <div className="text-center">
                  <XCircle className="h-16 w-16 mx-auto mb-4 text-red-500" />
                  <h2 className="text-2xl font-bold mb-2">Ошибка платежа</h2>
                  <p className="text-muted-foreground mb-6">
                    Произошла ошибка при обработке платежа. Пожалуйста, попробуйте еще раз.
                  </p>
                  <div className="flex gap-4 justify-center">
                    <Button onClick={() => navigate('/dashboard/parent')}>
                      Вернуться в личный кабинет
                    </Button>
                    <Button variant="outline" onClick={() => window.history.back()}>
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Назад
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default PaymentSuccess;

