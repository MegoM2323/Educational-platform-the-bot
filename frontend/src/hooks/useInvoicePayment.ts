/**
 * Hook для инициации оплаты счета через YooKassa.
 *
 * Используется для оплаты счетов родителями в личном кабинете.
 * При успешной инициации выполняет редирект на страницу оплаты YooKassa.
 * После оплаты пользователь вернется на /dashboard/parent/payment-success.
 *
 * Используется в:
 * - frontend/src/components/invoices/ParentInvoiceDetail.tsx
 * - frontend/src/pages/dashboard/parent/InvoicesPage.tsx
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { invoiceAPI } from '@/integrations/api/invoiceAPI';
import { useToast } from '@/hooks/use-toast';
import { logger } from '@/utils/logger';

interface UseInvoicePaymentOptions {
  onSuccess?: (paymentUrl: string) => void;
  onError?: (error: Error) => void;
}

/**
 * Hook для инициации оплаты счета через YooKassa.
 *
 * @example
 * const { initiatePayment, isLoading } = useInvoicePayment();
 *
 * <Button onClick={() => initiatePayment(invoiceId)} disabled={isLoading}>
 *   Оплатить
 * </Button>
 */
export const useInvoicePayment = (options?: UseInvoicePaymentOptions) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const mutation = useMutation({
    mutationFn: async (invoiceId: number) => {
      logger.debug('[useInvoicePayment] Initiating payment for invoice:', invoiceId);

      // Вызываем API для создания платежа в YooKassa
      const response = await invoiceAPI.initiateInvoicePayment(invoiceId);

      logger.debug('[useInvoicePayment] Payment initiated:', {
        paymentId: response.payment_id,
        invoiceId,
      });

      return response;
    },

    onSuccess: (response) => {
      // Получаем URL для редиректа на страницу оплаты YooKassa
      const paymentUrl = response.confirmation_url || response.payment_url;

      if (!paymentUrl) {
        logger.error('[useInvoicePayment] No payment URL in response:', response);
        toast({
          title: 'Ошибка',
          description: 'Не удалось получить ссылку на оплату',
          variant: 'destructive',
        });
        return;
      }

      logger.info('[useInvoicePayment] Redirecting to YooKassa:', paymentUrl);

      // Вызываем callback если передан
      if (options?.onSuccess) {
        options.onSuccess(paymentUrl);
      }

      // Инвалидируем кеш счетов для обновления после возврата
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent'] });
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'summary'] });
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'unpaid-count'] });

      // Редирект на страницу оплаты YooKassa
      window.location.href = paymentUrl;
    },

    onError: (error: Error) => {
      logger.error('[useInvoicePayment] Payment initiation failed:', error);

      toast({
        title: 'Ошибка оплаты',
        description: error.message || 'Не удалось инициировать оплату. Попробуйте позже.',
        variant: 'destructive',
      });

      // Вызываем callback если передан
      if (options?.onError) {
        options.onError(error);
      }
    },
  });

  return {
    /**
     * Инициирует оплату счета через YooKassa.
     * При успехе редиректит на страницу оплаты.
     *
     * @param invoiceId ID счета для оплаты
     */
    initiatePayment: mutation.mutate,

    /**
     * Асинхронная версия initiatePayment (возвращает Promise).
     */
    initiatePaymentAsync: mutation.mutateAsync,

    /**
     * Флаг загрузки (true во время создания платежа).
     */
    isLoading: mutation.isPending,

    /**
     * Ошибка если произошла.
     */
    error: mutation.error,

    /**
     * Сброс состояния мутации.
     */
    reset: mutation.reset,
  };
};
