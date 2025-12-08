/**
 * Tests for useInvoicesList hook.
 * Covers data fetching, filtering, pagination, sorting, and mutations.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import {
  useInvoicesList,
  useCreateInvoice,
  useUpdateInvoice,
  useDeleteInvoice,
  useSendInvoice,
  useCancelInvoice,
  useInvoiceDetail,
} from '../useInvoicesList';
import * as invoiceAPI from '@/integrations/api/invoiceAPI';
import {
  createMockInvoices,
  createMockInvoicesListResponse,
  createTestQueryClient,
} from '@/__tests__/utils/test-utils';

vi.mock('@/integrations/api/invoiceAPI');
vi.mock('@/hooks/use-toast');

const MockedInvoiceAPI = invoiceAPI as any;

describe('useInvoicesList', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  describe('Data Fetching', () => {
    it('should fetch and return invoices list', async () => {
      const mockInvoices = createMockInvoices(3);
      const mockResponse = createMockInvoicesListResponse(mockInvoices);
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.invoices).toEqual(mockInvoices);
      expect(result.current.totalCount).toBe(3);
    });

    it('should handle empty list', async () => {
      const mockResponse = createMockInvoicesListResponse([]);
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.invoices).toEqual([]);
      expect(result.current.totalCount).toBe(0);
    });

    it('should handle API error gracefully', async () => {
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockRejectedValue(
        new Error('API Error')
      );

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
    });
  });

  describe('Pagination', () => {
    it('should calculate total pages correctly', async () => {
      const mockResponse = {
        count: 50,
        results: createMockInvoices(20),
      };
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList({ initialPageSize: 20 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.totalPages).toBe(3);
    });

    it('should update current page', async () => {
      const mockResponse = createMockInvoicesListResponse(createMockInvoices(20));
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      expect(result.current.currentPage).toBe(0);

      result.current.setPage(1);

      await waitFor(() => {
        expect(result.current.currentPage).toBe(1);
      });
    });

    it('should include page offset in API call', async () => {
      const mockResponse = createMockInvoicesListResponse(createMockInvoices(20));
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList({ initialPageSize: 20 }), {
        wrapper: createWrapper(),
      });

      result.current.setPage(2);

      await waitFor(() => {
        expect(MockedInvoiceAPI.invoiceAPI.getTutorInvoices).toHaveBeenCalledWith(
          expect.objectContaining({
            offset: 40,
            limit: 20,
          })
        );
      });
    });

    it('should reset to page 0 when filters change', async () => {
      const mockResponse = createMockInvoicesListResponse(createMockInvoices(20));
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setPage(2);
      await waitFor(() => {
        expect(result.current.currentPage).toBe(2);
      });

      result.current.setStatus(['paid']);
      await waitFor(() => {
        expect(result.current.currentPage).toBe(0);
      });
    });
  });

  describe('Filtering', () => {
    it('should set status filters', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setStatus(['draft', 'sent']);

      await waitFor(() => {
        expect(result.current.filters.status).toEqual(['draft', 'sent']);
      });
    });

    it('should set date range filters', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setDateRange('2025-12-01', '2025-12-31');

      await waitFor(() => {
        expect(result.current.filters.dateFrom).toBe('2025-12-01');
        expect(result.current.filters.dateTo).toBe('2025-12-31');
      });
    });

    it('should include filters in API call', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setStatus(['paid']);
      result.current.setDateRange('2025-12-01', '2025-12-31');

      await waitFor(() => {
        expect(MockedInvoiceAPI.invoiceAPI.getTutorInvoices).toHaveBeenCalledWith(
          expect.objectContaining({
            status: ['paid'],
            date_from: '2025-12-01',
            date_to: '2025-12-31',
          })
        );
      });
    });

    it('should clear filters', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setStatus(['draft']);
      result.current.setDateRange('2025-12-01', '2025-12-31');

      await waitFor(() => {
        expect(result.current.filters.status).toEqual(['draft']);
        expect(result.current.filters.dateFrom).toBe('2025-12-01');
      });

      result.current.clearFilters();

      await waitFor(() => {
        expect(result.current.filters.status).toEqual([]);
        expect(result.current.filters.dateFrom).toBeUndefined();
        expect(result.current.filters.dateTo).toBeUndefined();
      });
    });
  });

  describe('Sorting', () => {
    it('should set sort order', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setSort('amount');

      await waitFor(() => {
        expect(result.current.filters.ordering).toBe('amount');
      });
    });

    it('should use default sort order', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.filters.ordering).toBe('-created_at');
    });

    it('should use custom initial ordering', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(
        () => useInvoicesList({ initialOrdering: 'amount' }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.filters.ordering).toBe('amount');
    });

    it('should include ordering in API call', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      result.current.setSort('-amount');

      await waitFor(() => {
        expect(MockedInvoiceAPI.invoiceAPI.getTutorInvoices).toHaveBeenCalledWith(
          expect.objectContaining({
            ordering: '-amount',
          })
        );
      });
    });
  });

  describe('Refetch', () => {
    it('should provide refetch method', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      expect(result.current.refetch).toBeDefined();
      expect(typeof result.current.refetch).toBe('function');
    });

    it('should refetch data', async () => {
      const mockResponse = createMockInvoicesListResponse();
      MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useInvoicesList(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const initialCallCount = MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mock.calls.length;

      result.current.refetch();

      await waitFor(() => {
        expect(
          MockedInvoiceAPI.invoiceAPI.getTutorInvoices.mock.calls.length
        ).toBeGreaterThan(initialCallCount);
      });
    });
  });
});

describe('useCreateInvoice', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should create invoice successfully', async () => {
    const mockInvoice = createMockInvoices(1)[0];
    MockedInvoiceAPI.invoiceAPI.createInvoice.mockResolvedValue(mockInvoice);

    const { result } = renderHook(() => useCreateInvoice(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      student_id: 2,
      amount: '5000',
      description: 'Test',
      due_date: '2025-12-31',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockInvoice);
  });

  it('should handle creation error', async () => {
    MockedInvoiceAPI.invoiceAPI.createInvoice.mockRejectedValue(
      new Error('Creation failed')
    );

    const { result } = renderHook(() => useCreateInvoice(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      student_id: 2,
      amount: '5000',
      description: 'Test',
      due_date: '2025-12-31',
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useUpdateInvoice', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should update invoice successfully', async () => {
    const mockInvoice = createMockInvoices(1)[0];
    MockedInvoiceAPI.invoiceAPI.updateInvoice.mockResolvedValue(mockInvoice);

    const { result } = renderHook(() => useUpdateInvoice(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      id: 1,
      data: { amount: '6000' },
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useDeleteInvoice', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should delete invoice successfully', async () => {
    MockedInvoiceAPI.invoiceAPI.deleteTutorInvoice.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteInvoice(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useSendInvoice', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should send invoice successfully', async () => {
    const mockInvoice = createMockInvoices(1, { status: 'sent' })[0];
    MockedInvoiceAPI.invoiceAPI.sendInvoice.mockResolvedValue(mockInvoice);

    const { result } = renderHook(() => useSendInvoice(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.status).toBe('sent');
  });
});

describe('useCancelInvoice', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should cancel invoice successfully', async () => {
    const mockInvoice = createMockInvoices(1, { status: 'cancelled' })[0];
    MockedInvoiceAPI.invoiceAPI.cancelInvoice.mockResolvedValue(mockInvoice);

    const { result } = renderHook(() => useCancelInvoice(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.status).toBe('cancelled');
  });
});

describe('useInvoiceDetail', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should fetch invoice detail', async () => {
    const mockInvoice = createMockInvoices(1)[0];
    MockedInvoiceAPI.invoiceAPI.getTutorInvoiceDetail.mockResolvedValue(
      mockInvoice
    );

    const { result } = renderHook(() => useInvoiceDetail(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockInvoice);
  });

  it('should not fetch when id is invalid', async () => {
    const { result } = renderHook(() => useInvoiceDetail(0), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(MockedInvoiceAPI.invoiceAPI.getTutorInvoiceDetail).not.toHaveBeenCalled();
  });
});
