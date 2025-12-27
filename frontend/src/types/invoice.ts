/**
 * TypeScript типы для системы выставления счетов.
 *
 * Используется в:
 * - frontend/src/integrations/api/invoiceAPI.ts
 * - frontend/src/hooks/useInvoicesList.ts
 * - frontend/src/hooks/useParentInvoices.ts
 * - frontend/src/pages/dashboard/TutorInvoicesPage.tsx
 * - frontend/src/pages/dashboard/ParentInvoicesPage.tsx
 */

// ============================================================================
// БАЗОВЫЕ ТИПЫ
// ============================================================================

/**
 * Статусы счета.
 *
 * Жизненный цикл:
 * draft → sent → viewed → paid
 *         ↓
 *      cancelled
 *         ↓
 *      overdue (автоматически если due_date < today)
 */
export type InvoiceStatus = 'draft' | 'sent' | 'viewed' | 'paid' | 'cancelled' | 'overdue';

/**
 * Основная модель счета.
 * Соответствует backend/invoices/models.py::Invoice
 */
export interface Invoice {
  id: number;
  tutor_id: number;
  student_id: number;
  parent_id: number;

  // Финансовые данные
  amount: string; // Decimal в виде строки для точности
  description: string;
  status: InvoiceStatus;
  due_date: string; // ISO date: YYYY-MM-DD

  // Временные метки
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
  sent_at?: string; // ISO datetime
  viewed_at?: string; // ISO datetime
  paid_at?: string; // ISO datetime
  cancelled_at?: string; // ISO datetime

  // Связи
  student: {
    id: number;
    full_name: string;
    avatar?: string;
  };
  enrollment?: {
    id: number;
    subject_name: string;
  };

  // Интеграции
  telegram_message_id?: string;
  payment_id?: number;
}

/**
 * Краткая информация о студенте тьютора.
 * Используется при создании счета для выбора студента.
 */
export interface TutorStudent {
  id: number;
  full_name: string;
  avatar?: string;
  enrollments: Array<{
    id: number;
    subject: {
      id: number;
      name: string;
    };
  }>;
}

// ============================================================================
// API REQUEST/RESPONSE ТИПЫ
// ============================================================================

/**
 * Запрос на создание счета.
 * POST /api/invoices/tutor/
 */
export interface CreateInvoiceRequest {
  student_id: number;
  amount: string; // Decimal как строка
  description: string;
  due_date: string; // ISO date: YYYY-MM-DD
  enrollment_id?: number; // Опционально, для привязки к предмету
}

/**
 * Запрос на обновление счета (только draft).
 * PATCH /api/invoices/tutor/{id}/
 */
export interface UpdateInvoiceRequest {
  amount?: string;
  description?: string;
  due_date?: string;
}

/**
 * Фильтры для списка счетов.
 * Используется как в tutor, так и в parent endpoints.
 */
export interface InvoiceFilters {
  status?: InvoiceStatus | InvoiceStatus[];
  student_id?: number;
  date_from?: string; // ISO date: YYYY-MM-DD
  date_to?: string; // ISO date: YYYY-MM-DD
  ordering?: string; // Например: '-created_at', 'amount', 'due_date'
  limit?: number;
  offset?: number;
}

/**
 * Ответ со списком счетов (paginated).
 * Backend использует Django REST Framework pagination.
 */
export interface InvoicesListResponse {
  count: number; // Общее количество
  results: Invoice[];
  next?: string; // URL следующей страницы
  previous?: string; // URL предыдущей страницы
}

/**
 * Ответ от endpoint инициации платежа.
 * POST /api/invoices/parent/{id}/pay/
 */
export interface InitiatePaymentResponse {
  payment_url: string;
  confirmation_url?: string;
  payment_id: string;
}

/**
 * Сводная статистика по счетам (для родителя).
 * GET /api/invoices/parent/summary/
 */
export interface InvoiceSummary {
  total_unpaid_amount: number;
  overdue_count: number;
  upcoming_count: number;
}

/**
 * Ответ с количеством неоплаченных счетов.
 * GET /api/invoices/parent/unpaid-count/
 */
export interface UnpaidCountResponse {
  count: number;
}

// ============================================================================
// КОМПОНЕНТНЫЕ ТИПЫ (для UI)
// ============================================================================

/**
 * Локальные фильтры для UI компонента (tutor).
 * Используется в useInvoicesList hook.
 */
export interface TutorInvoiceFilters {
  status: InvoiceStatus[];
  dateFrom?: string;
  dateTo?: string;
  ordering: string;
}

/**
 * Локальные фильтры для UI компонента (parent).
 * Используется в useParentInvoices hook.
 */
export interface ParentInvoiceFilters {
  status?: InvoiceStatus[];
  childId?: number;
  overdue?: boolean;
  page: number;
}

// ============================================================================
// УТИЛИТАРНЫЕ ТИПЫ
// ============================================================================

/**
 * Результат мутации с оптимистичным обновлением.
 * Используется в onMutate для сохранения предыдущего состояния.
 */
export interface OptimisticUpdateContext {
  previousInvoices?: InvoicesListResponse;
  previousInvoice?: Invoice;
}

/**
 * Варианты сортировки для UI.
 */
export const INVOICE_SORT_OPTIONS = {
  NEWEST_FIRST: '-created_at',
  OLDEST_FIRST: 'created_at',
  AMOUNT_HIGH: '-amount',
  AMOUNT_LOW: 'amount',
  DUE_DATE_SOON: 'due_date',
  DUE_DATE_LATE: '-due_date',
} as const;

export type InvoiceSortOption = typeof INVOICE_SORT_OPTIONS[keyof typeof INVOICE_SORT_OPTIONS];

/**
 * Цвета статусов для UI.
 */
export const INVOICE_STATUS_COLORS: Record<InvoiceStatus, string> = {
  draft: 'bg-gray-100 text-gray-800',
  sent: 'bg-blue-100 text-blue-800',
  viewed: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  overdue: 'bg-orange-100 text-orange-800',
};

/**
 * Текстовые метки статусов.
 */
export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: 'Черновик',
  sent: 'Отправлен',
  viewed: 'Просмотрен',
  paid: 'Оплачен',
  cancelled: 'Отменён',
  overdue: 'Просрочен',
};
