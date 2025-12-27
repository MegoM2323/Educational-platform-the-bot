/**
 * Хуки для управления счетами (Parent role).
 *
 * Включает:
 * - useParentInvoices - список счетов с фильтрами и статистикой
 * - useMarkInvoiceViewed - отметить счет как просмотренный
 * - useInitiateInvoicePayment - инициировать оплату
 * - WebSocket real-time обновления статусов счетов
 *
 * Используется в: frontend/src/pages/dashboard/ParentInvoicesPage.tsx
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useMemo, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { useToast } from '@/hooks/use-toast';
import {
  invoiceAPI,
  type Invoice,
  type InvoicesListResponse,
  type InvoiceStatus,
  type InvoiceFilters as APIInvoiceFilters,
} from '@/integrations/api/invoiceAPI';
import type { InvoiceSummary } from '@/types/invoice';
import { invoiceWebSocketService } from '@/services/invoiceWebSocketService';

/**
 * Локальные фильтры для UI.
 */
export interface ParentInvoiceFilters {
  status?: InvoiceStatus[];
  childId?: number;
  overdue?: boolean;
  page: number;
}

/**
 * Опции для хука.
 */
interface UseParentInvoicesOptions {
  initialPageSize?: number;
  refetchInterval?: number;
}

/**
 * Хук для списка счетов родителя.
 * Включает фильтры, пагинацию, статистику и количество неоплаченных.
 */
export const useParentInvoices = (options?: UseParentInvoicesOptions) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const pageSize = options?.initialPageSize || 20;

  // Фильтры и пагинация
  const [filters, setFilters] = useState<ParentInvoiceFilters>({
    page: 1,
  });

  // Построение параметров для API
  const buildAPIFilters = useCallback((): APIInvoiceFilters => {
    return {
      status: filters.status,
      ordering: '-created_at', // Новые первыми
      limit: pageSize,
      offset: (filters.page - 1) * pageSize,
    };
  }, [filters, pageSize]);

  // Запрос списка счетов
  const {
    data: invoicesData,
    isLoading,
    error,
    refetch,
  } = useQuery<InvoicesListResponse>({
    queryKey: ['invoices', 'parent', filters],
    queryFn: async () => {
      logger.debug('[useParentInvoices] Fetching invoices:', filters);
      const result = await invoiceAPI.getParentInvoices(buildAPIFilters());
      logger.debug('[useParentInvoices] Received:', result);
      return result;
    },
    staleTime: 60000, // 1 минута
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchInterval: options?.refetchInterval,
  });

  // Запрос статистики
  const { data: summary, isLoading: isSummaryLoading } = useQuery<InvoiceSummary>({
    queryKey: ['invoices', 'parent', 'summary'],
    queryFn: async () => {
      try {
        const result = await invoiceAPI.getInvoiceSummary();
        logger.debug('[useParentInvoices] Summary:', result);
        return result;
      } catch (err) {
        logger.error('[useParentInvoices] Failed to fetch summary:', err);
        return {
          total_unpaid_amount: 0,
          overdue_count: 0,
          upcoming_count: 0,
        };
      }
    },
    staleTime: 60000,
  });

  // Запрос количества неоплаченных (для бейджа)
  const { data: unpaidCount, isLoading: isUnpaidCountLoading } = useQuery<number>({
    queryKey: ['invoices', 'parent', 'unpaid-count'],
    queryFn: async () => {
      try {
        const result = await invoiceAPI.getUnpaidInvoiceCount();
        logger.debug('[useParentInvoices] Unpaid count:', result);
        return result;
      } catch (err) {
        logger.error('[useParentInvoices] Failed to fetch unpaid count:', err);
        return 0;
      }
    },
    staleTime: 60000,
  });

  // Мутации для действий родителя
  const markViewedMutation = useMarkInvoiceViewed();
  const paymentMutation = useInitiateInvoicePayment();

  // WebSocket real-time обновления
  useEffect(() => {
    logger.debug('[useParentInvoices] Connecting to invoice WebSocket');

    invoiceWebSocketService.connect({
      onInvoiceCreated: (data) => {
        logger.info('[useParentInvoices] New invoice created:', data.invoice_id);
        // Инвалидируем все запросы для обновления данных
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent'] });
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'summary'] });
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'unpaid-count'] });
      },
      onStatusUpdate: (data) => {
        logger.info(
          '[useParentInvoices] Invoice status updated:',
          data.invoice_id,
          data.old_status,
          '→',
          data.new_status
        );
        // Инвалидируем для обновления списка и статистики
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent'] });
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'summary'] });
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'unpaid-count'] });
      },
      onInvoicePaid: (data) => {
        logger.info('[useParentInvoices] Invoice paid:', data.invoice_id);
        // Инвалидируем для обновления
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent'] });
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'summary'] });
        queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'unpaid-count'] });

        toast({
          title: 'Счёт оплачен',
          description: 'Платёж успешно обработан',
        });
      },
      onError: (error) => {
        logger.error('[useParentInvoices] WebSocket error:', error);
      },
    });

    return () => {
      logger.debug('[useParentInvoices] Disconnecting from invoice WebSocket');
      invoiceWebSocketService.disconnect();
    };
  }, [queryClient, toast]);

  // Вычисляемые значения
  const invoices = useMemo(() => invoicesData?.results || [], [invoicesData]);
  const totalCount = invoicesData?.count || 0;
  const totalPages = Math.ceil(totalCount / pageSize);
  const hasNext = !!invoicesData?.next;
  const hasPrevious = !!invoicesData?.previous;

  // Методы управления фильтрами
  const setStatus = useCallback((status?: InvoiceStatus[]) => {
    setFilters((prev) => ({ ...prev, status, page: 1 }));
  }, []);

  const setChild = useCallback((childId?: number) => {
    setFilters((prev) => ({ ...prev, childId, page: 1 }));
  }, []);

  const setOverdueOnly = useCallback((overdue?: boolean) => {
    setFilters((prev) => ({ ...prev, overdue, page: 1 }));
  }, []);

  const setPage = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ page: 1 });
  }, []);

  return {
    // Данные
    invoices,
    totalCount,
    totalPages,
    currentPage: filters.page,
    hasNext,
    hasPrevious,
    summary,
    unpaidCount,

    // Состояние загрузки
    isLoading,
    isSummaryLoading,
    isUnpaidCountLoading,
    error: error?.message || null,

    // Фильтры
    activeFilters: filters,
    setStatus,
    setChild,
    setOverdueOnly,
    setPage,
    resetFilters,

    // Перезагрузка
    refetch,

    // Действия родителя
    markAsViewed: markViewedMutation.mutate,
    isMarkingViewed: markViewedMutation.isPending,
    initiatePayment: paymentMutation.mutate,
    isInitiatingPayment: paymentMutation.isPending,
  };
};

/**
 * Хук для отметки счета как просмотренного.
 * Обновляет viewed_at timestamp.
 */
export const useMarkInvoiceViewed = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (invoiceId: number) => {
      logger.debug('[useMarkInvoiceViewed] Marking invoice as viewed:', invoiceId);
      const result = await invoiceAPI.markInvoiceViewed(invoiceId);
      logger.debug('[useMarkInvoiceViewed] Marked:', result);
      return result;
    },
    onMutate: async (invoiceId) => {
      // Отменяем текущие запросы
      await queryClient.cancelQueries({ queryKey: ['invoices', 'parent'] });

      // Сохраняем предыдущее состояние
      const previousLists = queryClient.getQueriesData({ queryKey: ['invoices', 'parent'] });

      // Оптимистично обновляем viewed_at
      queryClient.setQueriesData<InvoicesListResponse>(
        { queryKey: ['invoices', 'parent'] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            results: old.results.map((inv) =>
              inv.id === invoiceId
                ? { ...inv, viewed_at: new Date().toISOString(), status: 'viewed' as const }
                : inv
            ),
          };
        }
      );

      return { previousLists };
    },
    onError: (error: Error, variables, context) => {
      // Откатываем изменения
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }

      logger.error('[useMarkInvoiceViewed] Error:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось отметить счёт как просмотренный',
        variant: 'destructive',
      });
    },
    onSuccess: () => {
      // Инвалидируем для синхронизации с сервером
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent'] });
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'summary'] });
    },
  });
};

/**
 * Хук для инициации оплаты счета.
 * При успехе выполняет редирект на страницу оплаты YooKassa.
 */
export const useInitiateInvoicePayment = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (invoiceId: number) => {
      logger.debug('[useInitiateInvoicePayment] Initiating payment:', invoiceId);
      const result = await invoiceAPI.initiateInvoicePayment(invoiceId);
      logger.debug('[useInitiateInvoicePayment] Payment initiated:', result);
      return result;
    },
    onSuccess: (response) => {
      // Перенаправляем на страницу оплаты
      const paymentUrl = response.confirmation_url || response.payment_url;
      if (paymentUrl) {
        logger.debug('[useInitiateInvoicePayment] Redirecting to:', paymentUrl);
        window.location.href = paymentUrl;
      } else {
        logger.error('[useInitiateInvoicePayment] No payment URL in response');
        toast({
          title: 'Ошибка',
          description: 'Не удалось получить ссылку на оплату',
          variant: 'destructive',
        });
      }

      // Инвалидируем для обновления статусов после возврата с оплаты
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent'] });
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'summary'] });
      queryClient.invalidateQueries({ queryKey: ['invoices', 'parent', 'unpaid-count'] });
    },
    onError: (error: Error) => {
      logger.error('[useInitiateInvoicePayment] Error:', error);
      toast({
        title: 'Ошибка оплаты',
        description: error.message || 'Не удалось инициировать оплату',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Хук для получения детальной информации о счете (parent).
 */
export const useParentInvoiceDetail = (id: number) => {
  return useQuery<Invoice>({
    queryKey: ['invoice', 'parent', id],
    queryFn: async () => {
      logger.debug('[useParentInvoiceDetail] Fetching invoice:', id);
      const result = await invoiceAPI.getParentInvoiceDetail(id);
      logger.debug('[useParentInvoiceDetail] Received:', result);
      return result;
    },
    enabled: !!id && id > 0,
    staleTime: 300000, // 5 минут
    refetchOnWindowFocus: false,
  });
};
