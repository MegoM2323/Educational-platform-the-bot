/**
 * Хуки для управления счетами (Tutor role).
 *
 * Включает:
 * - useInvoicesList - список счетов с фильтрами и пагинацией
 * - useCreateInvoice - создание нового счета
 * - useUpdateInvoice - редактирование черновика
 * - useDeleteInvoice - удаление черновика
 * - useSendInvoice - отправка счета родителю
 * - useCancelInvoice - отмена счета
 * - useInvoiceDetail - детальная информация о счете
 *
 * Используется в: frontend/src/pages/dashboard/TutorInvoicesPage.tsx
 */

import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  invoiceAPI,
  type InvoiceStatus,
  type Invoice,
  type CreateInvoiceRequest,
  type UpdateInvoiceRequest,
} from '@/integrations/api/invoiceAPI';
import type { InvoicesListResponse } from '@/types/invoice';
import { useToast } from '@/hooks/use-toast';
import { logger } from '@/utils/logger';

/**
 * Локальные фильтры для UI.
 */
export interface InvoiceFilters {
  status: InvoiceStatus[];
  dateFrom?: string;
  dateTo?: string;
  ordering: string;
}

/**
 * Опции для hooks.
 */
interface UseInvoicesListOptions {
  initialPageSize?: number;
  initialOrdering?: string;
  refetchInterval?: number;
}

/**
 * Хук для списка счетов тьютора с фильтрами и пагинацией.
 */
export const useInvoicesList = (options?: UseInvoicesListOptions) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const itemsPerPage = options?.initialPageSize || 20;
  const initialOrdering = options?.initialOrdering || '-created_at';

  const [filters, setFilters] = useState<InvoiceFilters>({
    status: [],
    dateFrom: undefined,
    dateTo: undefined,
    ordering: initialOrdering,
  });

  const [page, setPage] = useState(0);

  // Запрос списка счетов
  const {
    data: invoicesResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<InvoicesListResponse>({
    queryKey: ['invoices', 'tutor', filters, page],
    queryFn: async () => {
      logger.debug('[useInvoicesList] Fetching invoices:', { filters, page });

      const result = await invoiceAPI.getTutorInvoices({
        status: filters.status.length > 0 ? filters.status : undefined,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        ordering: filters.ordering,
        limit: itemsPerPage,
        offset: page * itemsPerPage,
      });

      logger.debug('[useInvoicesList] Received:', result);
      return result;
    },
    staleTime: 60000, // 1 минута
    refetchOnWindowFocus: false,
    refetchOnMount: true,
    refetchInterval: options?.refetchInterval,
  });

  const invoices = useMemo(() => invoicesResponse?.results || [], [invoicesResponse]);
  const totalCount = invoicesResponse?.count || 0;
  const totalPages = Math.ceil(totalCount / itemsPerPage);

  // Методы управления фильтрами
  const setStatus = useCallback((status: InvoiceStatus[]) => {
    setFilters((prev) => ({ ...prev, status }));
    setPage(0);
  }, []);

  const setDateRange = useCallback((from?: string, to?: string) => {
    setFilters((prev) => ({ ...prev, dateFrom: from, dateTo: to }));
    setPage(0);
  }, []);

  const setSort = useCallback((ordering: string) => {
    setFilters((prev) => ({ ...prev, ordering }));
    setPage(0);
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({
      status: [],
      dateFrom: undefined,
      dateTo: undefined,
      ordering: initialOrdering,
    });
    setPage(0);
  }, [initialOrdering]);

  return {
    // Данные
    invoices,
    totalCount,
    totalPages,
    currentPage: page,

    // Состояние загрузки
    isLoading,
    error: error?.message || null,

    // Фильтры
    filters,
    setStatus,
    setDateRange,
    setSort,
    clearFilters,

    // Пагинация
    setPage,
    itemsPerPage,

    // Перезагрузка
    refetch,
  };
};

/**
 * Хук для создания счета.
 * Включает optimistic update.
 */
export const useCreateInvoice = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: CreateInvoiceRequest) => {
      logger.debug('[useCreateInvoice] Creating invoice:', data);
      const result = await invoiceAPI.createInvoice(data);
      logger.debug('[useCreateInvoice] Created:', result);
      return result;
    },
    onSuccess: () => {
      // Инвалидируем все списки счетов
      queryClient.invalidateQueries({ queryKey: ['invoices', 'tutor'] });

      toast({
        title: 'Успешно',
        description: 'Счёт создан',
      });
    },
    onError: (error: Error) => {
      logger.error('[useCreateInvoice] Error:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось создать счёт',
        variant: 'destructive',
      });
    },
  });
};

/**
 * Хук для обновления счета (только draft).
 */
export const useUpdateInvoice = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UpdateInvoiceRequest }) => {
      logger.debug('[useUpdateInvoice] Updating invoice:', id, data);
      const result = await invoiceAPI.updateInvoice(id, data);
      logger.debug('[useUpdateInvoice] Updated:', result);
      return result;
    },
    onMutate: async ({ id, data }) => {
      // Отменяем текущие запросы
      await queryClient.cancelQueries({ queryKey: ['invoices', 'tutor'] });
      await queryClient.cancelQueries({ queryKey: ['invoice', 'tutor', id] });

      // Сохраняем предыдущее состояние
      const previousLists = queryClient.getQueriesData({ queryKey: ['invoices', 'tutor'] });
      const previousDetail = queryClient.getQueryData<Invoice>(['invoice', 'tutor', id]);

      // Оптимистично обновляем detail
      if (previousDetail) {
        queryClient.setQueryData<Invoice>(['invoice', 'tutor', id], {
          ...previousDetail,
          ...data,
        });
      }

      return { previousLists, previousDetail };
    },
    onError: (error: Error, variables, context) => {
      // Откатываем изменения
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(['invoice', 'tutor', variables.id], context.previousDetail);
      }

      logger.error('[useUpdateInvoice] Error:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось обновить счёт',
        variant: 'destructive',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', 'tutor'] });

      toast({
        title: 'Успешно',
        description: 'Счёт обновлён',
      });
    },
  });
};

/**
 * Хук для удаления счета (только draft).
 */
export const useDeleteInvoice = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      logger.debug('[useDeleteInvoice] Deleting invoice:', id);
      await invoiceAPI.deleteTutorInvoice(id);
      logger.debug('[useDeleteInvoice] Deleted');
    },
    onMutate: async (id) => {
      // Отменяем текущие запросы
      await queryClient.cancelQueries({ queryKey: ['invoices', 'tutor'] });

      // Сохраняем предыдущее состояние
      const previousLists = queryClient.getQueriesData({ queryKey: ['invoices', 'tutor'] });

      // Оптимистично удаляем из всех списков
      queryClient.setQueriesData<InvoicesListResponse>(
        { queryKey: ['invoices', 'tutor'] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            results: old.results.filter((inv) => inv.id !== id),
            count: old.count - 1,
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

      logger.error('[useDeleteInvoice] Error:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось удалить счёт',
        variant: 'destructive',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', 'tutor'] });

      toast({
        title: 'Успешно',
        description: 'Счёт удалён',
      });
    },
  });
};

/**
 * Хук для отправки счета (draft → sent).
 */
export const useSendInvoice = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      logger.debug('[useSendInvoice] Sending invoice:', id);
      const result = await invoiceAPI.sendInvoice(id);
      logger.debug('[useSendInvoice] Sent:', result);
      return result;
    },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['invoices', 'tutor'] });
      await queryClient.cancelQueries({ queryKey: ['invoice', 'tutor', id] });

      const previousLists = queryClient.getQueriesData({ queryKey: ['invoices', 'tutor'] });
      const previousDetail = queryClient.getQueryData<Invoice>(['invoice', 'tutor', id]);

      // Оптимистично обновляем статус
      queryClient.setQueriesData<InvoicesListResponse>(
        { queryKey: ['invoices', 'tutor'] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            results: old.results.map((inv) =>
              inv.id === id
                ? { ...inv, status: 'sent' as const, sent_at: new Date().toISOString() }
                : inv
            ),
          };
        }
      );

      if (previousDetail) {
        queryClient.setQueryData<Invoice>(['invoice', 'tutor', id], {
          ...previousDetail,
          status: 'sent',
          sent_at: new Date().toISOString(),
        });
      }

      return { previousLists, previousDetail };
    },
    onError: (error: Error, variables, context) => {
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(['invoice', 'tutor', variables], context.previousDetail);
      }

      logger.error('[useSendInvoice] Error:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось отправить счёт',
        variant: 'destructive',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', 'tutor'] });

      toast({
        title: 'Успешно',
        description: 'Счёт отправлен студенту',
      });
    },
  });
};

/**
 * Хук для отмены счета.
 */
export const useCancelInvoice = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      logger.debug('[useCancelInvoice] Cancelling invoice:', id);
      const result = await invoiceAPI.cancelInvoice(id);
      logger.debug('[useCancelInvoice] Cancelled:', result);
      return result;
    },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['invoices', 'tutor'] });
      await queryClient.cancelQueries({ queryKey: ['invoice', 'tutor', id] });

      const previousLists = queryClient.getQueriesData({ queryKey: ['invoices', 'tutor'] });
      const previousDetail = queryClient.getQueryData<Invoice>(['invoice', 'tutor', id]);

      // Оптимистично обновляем статус
      queryClient.setQueriesData<InvoicesListResponse>(
        { queryKey: ['invoices', 'tutor'] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            results: old.results.map((inv) =>
              inv.id === id
                ? { ...inv, status: 'cancelled' as const, cancelled_at: new Date().toISOString() }
                : inv
            ),
          };
        }
      );

      if (previousDetail) {
        queryClient.setQueryData<Invoice>(['invoice', 'tutor', id], {
          ...previousDetail,
          status: 'cancelled',
          cancelled_at: new Date().toISOString(),
        });
      }

      return { previousLists, previousDetail };
    },
    onError: (error: Error, variables, context) => {
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(['invoice', 'tutor', variables], context.previousDetail);
      }

      logger.error('[useCancelInvoice] Error:', error);
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось отменить счёт',
        variant: 'destructive',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', 'tutor'] });

      toast({
        title: 'Успешно',
        description: 'Счёт отменён',
      });
    },
  });
};

/**
 * Хук для получения детальной информации о счете.
 */
export const useInvoiceDetail = (id: number) => {
  return useQuery<Invoice>({
    queryKey: ['invoice', 'tutor', id],
    queryFn: async () => {
      logger.debug('[useInvoiceDetail] Fetching invoice:', id);
      const result = await invoiceAPI.getTutorInvoiceDetail(id);
      logger.debug('[useInvoiceDetail] Received:', result);
      return result;
    },
    enabled: !!id && id > 0,
    staleTime: 300000, // 5 минут
    refetchOnWindowFocus: false,
  });
};
