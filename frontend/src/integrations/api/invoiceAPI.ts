/**
 * API клиент для работы со счетами.
 *
 * Endpoints:
 * - Tutor: /api/invoices/tutor/
 * - Parent: /api/invoices/parent/
 *
 * Backend: backend/invoices/views.py
 */

import { unifiedAPI } from './unifiedClient';
import type {
  Invoice,
  InvoicesListResponse,
  CreateInvoiceRequest,
  UpdateInvoiceRequest,
  InvoiceFilters,
  TutorStudent,
  InitiatePaymentResponse,
  InvoiceSummary,
} from '@/types/invoice';

// Реэкспорт типов для обратной совместимости
export type {
  Invoice,
  InvoicesListResponse,
  CreateInvoiceRequest,
  UpdateInvoiceRequest,
  InvoiceFilters,
  TutorStudent,
  InitiatePaymentResponse,
  InvoiceSummary,
};

export type { InvoiceStatus } from '@/types/invoice';

/**
 * Вспомогательная функция для построения query params.
 */
const buildQueryParams = (filters?: InvoiceFilters): string => {
  if (!filters) return '';

  const params = new URLSearchParams();

  if (filters.status) {
    const statuses = Array.isArray(filters.status) ? filters.status : [filters.status];
    statuses.forEach(s => params.append('status', s));
  }
  if (filters.student_id) {
    params.append('student_id', String(filters.student_id));
  }
  if (filters.date_from) {
    params.append('date_from', filters.date_from);
  }
  if (filters.date_to) {
    params.append('date_to', filters.date_to);
  }
  if (filters.ordering) {
    params.append('ordering', filters.ordering);
  }
  if (filters.limit !== undefined) {
    params.append('limit', String(filters.limit));
  }
  if (filters.offset !== undefined) {
    params.append('offset', String(filters.offset));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
};

export const invoiceAPI = {
  // ============================================================================
  // TUTOR ENDPOINTS
  // ============================================================================

  /**
   * Получить список счетов тьютора с фильтрацией и пагинацией.
   * GET /api/invoices/tutor/
   */
  getTutorInvoices: async (filters?: InvoiceFilters): Promise<InvoicesListResponse> => {
    const url = `/invoices/tutor/${buildQueryParams(filters)}`;
    const response = await unifiedAPI.request<{ success: boolean; data: InvoicesListResponse }>(url);

    if (response.error) {
      throw new Error(response.error);
    }

    // Backend возвращает { success, data: { results, count, page, ... } }
    return response.data?.data || { count: 0, results: [] };
  },

  /**
   * Получить детали конкретного счёта (tutor).
   * GET /api/invoices/tutor/{id}/
   */
  getTutorInvoiceDetail: async (id: number): Promise<Invoice> => {
    const response = await unifiedAPI.request<{ success: boolean; data: Invoice }>(
      `/invoices/tutor/${id}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data?.data) {
      throw new Error('Invoice not found');
    }

    return response.data.data;
  },

  /**
   * Создать новый счёт (статус draft).
   * POST /api/invoices/tutor/
   */
  createInvoice: async (data: CreateInvoiceRequest): Promise<Invoice> => {
    const response = await unifiedAPI.request<{ success: boolean; data: Invoice }>(
      '/invoices/tutor/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data?.data) {
      throw new Error('Failed to create invoice');
    }

    return response.data.data;
  },

  /**
   * Обновить счёт (только в статусе draft).
   * PATCH /api/invoices/tutor/{id}/
   */
  updateInvoice: async (id: number, data: UpdateInvoiceRequest): Promise<Invoice> => {
    const response = await unifiedAPI.request<{ success: boolean; data: Invoice }>(
      `/invoices/tutor/${id}/`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data?.data) {
      throw new Error('Failed to update invoice');
    }

    return response.data.data;
  },

  /**
   * Удалить счёт (только в статусе draft).
   * DELETE /api/invoices/tutor/{id}/
   */
  deleteTutorInvoice: async (id: number): Promise<void> => {
    const response = await unifiedAPI.request<{ success: boolean }>(
      `/invoices/tutor/${id}/`,
      {
        method: 'DELETE',
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }
  },

  /**
   * Отправить счёт родителю (draft → sent).
   * POST /api/invoices/tutor/{id}/send/
   */
  sendInvoice: async (id: number): Promise<Invoice> => {
    const response = await unifiedAPI.request<{ success: boolean; data: Invoice }>(
      `/invoices/tutor/${id}/send/`,
      {
        method: 'POST',
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data?.data) {
      throw new Error('Failed to send invoice');
    }

    return response.data.data;
  },

  /**
   * Отменить счёт.
   * POST /api/invoices/tutor/{id}/cancel/ (DELETE также работает)
   */
  cancelInvoice: async (id: number): Promise<Invoice> => {
    const response = await unifiedAPI.request<{ success: boolean; data: Invoice }>(
      `/invoices/tutor/${id}/`,
      {
        method: 'DELETE', // Backend использует DELETE для отмены
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data?.data) {
      throw new Error('Failed to cancel invoice');
    }

    return response.data.data;
  },

  /**
   * Получить список студентов тьютора для выбора при создании счёта.
   * GET /api/tutor/students/
   */
  getTutorStudents: async (): Promise<TutorStudent[]> => {
    const response = await unifiedAPI.request<{ results: TutorStudent[] }>(
      '/tutor/students/'
    );

    if (response.error) {
      throw new Error(response.error);
    }

    // Backend может вернуть массив или объект с results
    if (Array.isArray(response.data)) {
      return response.data;
    }

    return response.data?.results || [];
  },

  // ============================================================================
  // PARENT ENDPOINTS
  // ============================================================================

  /**
   * Получить список счетов родителя.
   * GET /api/invoices/parent/
   */
  getParentInvoices: async (filters?: InvoiceFilters): Promise<InvoicesListResponse> => {
    const url = `/invoices/parent/${buildQueryParams(filters)}`;
    const response = await unifiedAPI.request<InvoicesListResponse>(url);

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data || { count: 0, results: [] };
  },

  /**
   * Получить детали конкретного счёта (parent).
   * GET /api/invoices/parent/{id}/
   */
  getParentInvoiceDetail: async (id: number): Promise<Invoice> => {
    const response = await unifiedAPI.request<Invoice>(`/invoices/parent/${id}/`);

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data) {
      throw new Error('Invoice not found');
    }

    return response.data;
  },

  /**
   * Отметить счёт как просмотренный (viewed_at timestamp).
   * POST /api/invoices/parent/{id}/mark_viewed/
   */
  markInvoiceViewed: async (id: number): Promise<Invoice> => {
    const response = await unifiedAPI.request<Invoice>(
      `/invoices/parent/${id}/mark_viewed/`,
      {
        method: 'POST',
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data) {
      throw new Error('Failed to mark invoice as viewed');
    }

    return response.data;
  },

  /**
   * Инициировать оплату счёта через YooKassa.
   * POST /api/invoices/parent/{id}/pay/
   *
   * Возвращает URL для редиректа на страницу оплаты.
   */
  initiateInvoicePayment: async (id: number): Promise<InitiatePaymentResponse> => {
    const response = await unifiedAPI.request<InitiatePaymentResponse>(
      `/invoices/parent/${id}/pay/`,
      {
        method: 'POST',
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data) {
      throw new Error('Failed to initiate payment');
    }

    return response.data;
  },

  /**
   * Получить количество неоплаченных счетов (для бейджа).
   * GET /api/invoices/parent/unpaid-count/
   */
  getUnpaidInvoiceCount: async (): Promise<number> => {
    const response = await unifiedAPI.request<{ count: number }>(
      '/invoices/parent/unpaid-count/'
    );

    if (response.error) {
      // Не критичная ошибка, возвращаем 0
      return 0;
    }

    return response.data?.count || 0;
  },

  /**
   * Получить сводную статистику по счетам родителя.
   * GET /api/invoices/parent/summary/
   */
  getInvoiceSummary: async (): Promise<InvoiceSummary> => {
    const response = await unifiedAPI.request<InvoiceSummary>('/invoices/parent/summary/');

    if (response.error) {
      // Не критичная ошибка, возвращаем пустую статистику
      return {
        total_unpaid_amount: 0,
        overdue_count: 0,
        upcoming_count: 0,
      };
    }

    return (
      response.data || {
        total_unpaid_amount: 0,
        overdue_count: 0,
        upcoming_count: 0,
      }
    );
  },
};

// Алиасы для обратной совместимости
export const {
  getTutorInvoices: getInvoices,
  getTutorInvoiceDetail: getInvoice,
  deleteTutorInvoice: deleteInvoice,
  markInvoiceViewed: markAsViewed,
  getUnpaidInvoiceCount: getUnpaidCount,
} = invoiceAPI;
