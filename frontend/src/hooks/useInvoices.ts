/**
 * Унифицированный экспорт хуков для работы со счетами.
 *
 * Упрощает импорты в компонентах:
 * ```typescript
 * // Вместо:
 * import { useInvoicesList } from '@/hooks/useInvoicesList';
 * import { useParentInvoices } from '@/hooks/useParentInvoices';
 *
 * // Используйте:
 * import { useInvoicesList, useParentInvoices } from '@/hooks/useInvoices';
 * ```
 */

// ============================================================================
// TUTOR HOOKS
// ============================================================================

export {
  useInvoicesList,
  useCreateInvoice,
  useUpdateInvoice,
  useDeleteInvoice,
  useSendInvoice,
  useCancelInvoice,
  useInvoiceDetail,
} from './useInvoicesList';

export type { InvoiceFilters as TutorInvoiceFilters } from './useInvoicesList';

// ============================================================================
// PARENT HOOKS
// ============================================================================

export {
  useParentInvoices,
  useMarkInvoiceViewed,
  useInitiateInvoicePayment,
  useParentInvoiceDetail,
} from './useParentInvoices';

export type { ParentInvoiceFilters } from './useParentInvoices';

// ============================================================================
// SHARED TYPES
// ============================================================================

export type {
  Invoice,
  InvoiceStatus,
  CreateInvoiceRequest,
  UpdateInvoiceRequest,
  InvoicesListResponse,
  TutorStudent,
  InitiatePaymentResponse,
  InvoiceSummary,
} from '@/integrations/api/invoiceAPI';
