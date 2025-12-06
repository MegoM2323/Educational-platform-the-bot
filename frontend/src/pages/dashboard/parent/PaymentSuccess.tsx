import { useEffect, useState } from "react";
import { logger } from '@/utils/logger';
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { CheckCircle, XCircle, Loader2, ArrowLeft, Repeat } from "lucide-react";
import { unifiedAPI } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [paymentStatus, setPaymentStatus] = useState<'loading' | 'success' | 'failed' | 'pending'>('loading');
  const [paymentData, setPaymentData] = useState<any>(null);
  const [redirectCountdown, setRedirectCountdown] = useState<number | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Получаем payment_id из URL или из sessionStorage (на случай если потерялся в URL)
    let paymentId = searchParams.get('payment_id');
    
    // Если payment_id нет в URL, пытаемся получить из sessionStorage
    if (!paymentId) {
      paymentId = sessionStorage.getItem('pending_payment_id');
      if (paymentId) {
        // Обновляем URL с payment_id
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.set('payment_id', paymentId);
        window.history.replaceState({}, '', newUrl.toString());
      }
    }
    
    if (!paymentId) {
      setPaymentStatus('failed');
      toast({
        title: "Ошибка",
        description: "Не указан идентификатор платежа",
        variant: "destructive",
      });
      return;
    }
    
    // Очищаем сохраненный payment_id после использования
    sessionStorage.removeItem('pending_payment_id');

    // Проверяем статус платежа с polling
    let checkPaymentTimeout: NodeJS.Timeout;
    let pollCount = 0;

    const checkPayment = async (retryCount = 0) => {
      const MAX_RETRIES = 60; // Maximum 60 attempts = 180 seconds (3 minutes) at 3s interval
      const RETRY_DELAY = 3000; // 3 seconds between attempts (gives YooKassa webhook time to arrive)

      try {
        setChecking(true);
        pollCount++;
        logger.debug(`[Payment Check ${pollCount}] Retry ${retryCount + 1}/${MAX_RETRIES}`);

        const response = await unifiedAPI.request(`/payments/check-payment-status/?payment_id=${paymentId}`);

        if (response.data) {
          const status = response.data.status;
          setPaymentData(response.data);

          if (status === 'succeeded' || status === 'SUCCEEDED') {
            // Payment successful
            logger.debug('[Payment Check] Status: SUCCEEDED');
            setPaymentStatus('success');

            // CRITICAL: Invalidate and refetch ALL related dashboard data
            logger.debug('[Payment Success] Invalidating all parent dashboard caches...');

            // Invalidate first to mark queries as stale
            await queryClient.invalidateQueries({ queryKey: ['parent-dashboard'] });
            await queryClient.invalidateQueries({ queryKey: ['parent-children'] });
            // Добавляем инвалидацию для подписок и платежей (важно для немедленного обновления статуса)
            await queryClient.invalidateQueries({ queryKey: ['parent-payments'] });
            await queryClient.invalidateQueries({ queryKey: ['parent-subscriptions'] });

            // Then explicitly refetch to get fresh data
            logger.debug('[Payment Success] Refetching parent dashboard data...');
            await queryClient.refetchQueries({ queryKey: ['parent-dashboard'] });
            await queryClient.refetchQueries({ queryKey: ['parent-children'] });
            await queryClient.refetchQueries({ queryKey: ['parent-payments'] });
            logger.debug('[Payment Success] All caches refreshed successfully');

            toast({
              title: "Платеж успешно завершен!",
              description: "Доступ к предмету активирован.",
            });

            setRedirectCountdown(5);

          } else if (status === 'pending' || status === 'PENDING' || status === 'waiting_for_capture') {
            // Payment still processing
            logger.debug(`[Payment Check] Status: ${status} - continuing polling`);
            setPaymentStatus('pending');

            // Retry after 3 seconds (max 180 seconds = 3 minutes)
            if (retryCount < MAX_RETRIES) {
              // Логируем только каждый 5-й запрос чтобы не замусорить консоль
              if (retryCount % 5 === 0) {
                logger.debug(`Payment pending, retry ${retryCount + 1}/${MAX_RETRIES}`);
              }
              checkPaymentTimeout = setTimeout(() => checkPayment(retryCount + 1), RETRY_DELAY);
            } else {
              // Максимум попыток исчерпан (3 минуты прошло)
              logger.debug('[Payment Check] Max retries reached (3 minutes), stopping polling');
              setPaymentStatus('pending'); // Оставляем "pending" статус
              toast({
                title: "Платеж обрабатывается",
                description: "Обработка платежа занимает больше времени, чем обычно (более 3 минут). Платеж будет учтен автоматически, пожалуйста, вернитесь в личный кабинет.",
                variant: "default",
              });
            }

          } else if (status === 'canceled' || status === 'CANCELED') {
            logger.debug('[Payment Check] Status: CANCELED');
            setPaymentStatus('failed');
            toast({
              title: "Платеж отменен",
              description: "Платеж был отменен.",
              variant: "destructive",
            });
          }
        }
      } catch (error: any) {
        logger.error('[Payment Check] Error:', error);
        // При ошибке продолжаем polling, не прерываем
        setPaymentStatus('pending');
        if (retryCount < 30) {
          checkPaymentTimeout = setTimeout(() => checkPayment(retryCount + 1), 5000);
        }
      } finally {
        setChecking(false);
      }
    };

    // Запускаем проверку
    checkPayment();

    // Cleanup при размонтировании
    return () => {
      if (checkPaymentTimeout) {
        clearTimeout(checkPaymentTimeout);
      }
    };
  }, [searchParams, toast, queryClient]);

  // Эффект для обратного отсчета и автоматического редиректа
  useEffect(() => {
    if (redirectCountdown === null) return;

    if (redirectCountdown === 0) {
      navigate('/dashboard/parent', { replace: true });
      return;
    }

    const timer = setTimeout(() => {
      setRedirectCountdown(redirectCountdown - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [redirectCountdown, navigate]);

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
                  {/* Информация о подписке */}
                  <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <div className="flex items-center gap-2 justify-center">
                      <Repeat className="h-5 w-5 text-green-600 dark:text-green-400" />
                      <div>
                        <p className="font-semibold text-green-800 dark:text-green-200">Автосписание подключено</p>
                        <p className="text-sm text-green-700 dark:text-green-300">
                          Платежи будут списываться автоматически согласно расписанию
                        </p>
                      </div>
                    </div>
                  </div>
                  {redirectCountdown !== null && (
                    <p className="text-sm text-muted-foreground mb-4">
                      Автоматический переход в личный кабинет через {redirectCountdown} сек...
                    </p>
                  )}
                  <div className="flex gap-4 justify-center">
                    <Button type="button" onClick={() => navigate('/dashboard/parent')}>
                      Вернуться в личный кабинет
                    </Button>
                    <Button type="button" variant="outline" onClick={() => navigate('/dashboard/parent/payment-history')}>
                      История платежей
                    </Button>
                  </div>
                </div>
              )}

              {paymentStatus === 'pending' && (
                <div className="text-center">
                  <Loader2 className="h-16 w-16 mx-auto mb-4 animate-spin text-yellow-500" />
                  <h2 className="text-2xl font-bold mb-2">Платеж обрабатывается</h2>
                  <p className="text-muted-foreground mb-2">
                    Ваш платеж находится в обработке. Пожалуйста, подождите.
                  </p>
                  <p className="text-sm text-muted-foreground mb-6">
                    Обработка может занять до 3 минут
                  </p>
                  <Button type="button" onClick={() => navigate('/dashboard/parent')}>
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
                    <Button type="button" onClick={() => navigate('/dashboard/parent')}>
                      Вернуться в личный кабинет
                    </Button>
                    <Button type="button" variant="outline" onClick={() => window.history.back()}>
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

