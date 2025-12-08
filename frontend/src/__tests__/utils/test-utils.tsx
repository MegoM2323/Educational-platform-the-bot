/**
 * Test utilities for invoice components.
 * Provides custom render function with providers and mock data factories.
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '@/components/ui/toaster';
import {
  Invoice,
  TutorStudent,
  InvoicesListResponse,
  InvoiceStatus,
} from '@/integrations/api/invoiceAPI';

/**
 * Create a test QueryClient with disabled retries.
 */
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

/**
 * Custom render function with all providers.
 */
export const renderWithProviders = (
  ui: React.ReactElement,
  {
    queryClient = createTestQueryClient(),
    ...renderOptions
  }: RenderOptions & { queryClient?: QueryClient } = {}
) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          {children}
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }), queryClient };
};

/**
 * Factory: Create mock invoice with optional overrides.
 */
export const createMockInvoice = (
  overrides: Partial<Invoice> = {}
): Invoice => ({
  id: 1,
  tutor_id: 100,
  student_id: 2,
  parent_id: 3,
  amount: '5000.00',
  description: 'Test invoice for mathematics',
  status: 'draft',
  due_date: '2025-12-31',
  created_at: '2025-12-08T10:00:00Z',
  updated_at: '2025-12-08T10:00:00Z',
  student: {
    id: 2,
    full_name: 'John Doe',
    avatar: 'https://example.com/avatar.jpg',
  },
  enrollment: {
    id: 10,
    subject_name: 'Mathematics',
  },
  ...overrides,
});

/**
 * Factory: Create mock tutor student with optional overrides.
 */
export const createMockTutorStudent = (
  overrides: Partial<TutorStudent> = {}
): TutorStudent => ({
  id: 2,
  full_name: 'John Doe',
  avatar: 'https://example.com/avatar.jpg',
  enrollments: [
    {
      id: 10,
      subject: {
        id: 20,
        name: 'Mathematics',
      },
    },
    {
      id: 11,
      subject: {
        id: 21,
        name: 'Physics',
      },
    },
  ],
  ...overrides,
});

/**
 * Factory: Create mock invoices list response.
 */
export const createMockInvoicesListResponse = (
  invoices: Invoice[] = [],
  overrides: Partial<InvoicesListResponse> = {}
): InvoicesListResponse => ({
  count: invoices.length,
  results: invoices.length > 0 ? invoices : [createMockInvoice()],
  ...overrides,
});

/**
 * Factory: Create multiple mock invoices.
 */
export const createMockInvoices = (
  count: number = 5,
  overrides: Partial<Invoice> = {}
): Invoice[] => {
  return Array.from({ length: count }, (_, i) =>
    createMockInvoice({
      id: i + 1,
      student_id: i + 2,
      student: {
        id: i + 2,
        full_name: `Student ${i + 1}`,
      },
      amount: String((i + 1) * 1000),
      status: ['draft', 'sent', 'viewed', 'paid'][i % 4] as InvoiceStatus,
      ...overrides,
    })
  );
};

/**
 * Factory: Create multiple mock tutor students.
 */
export const createMockTutorStudents = (count: number = 3): TutorStudent[] => {
  return Array.from({ length: count }, (_, i) =>
    createMockTutorStudent({
      id: i + 2,
      full_name: `Student ${i + 1}`,
      enrollments: [
        {
          id: i * 2 + 10,
          subject: {
            id: i * 2 + 20,
            name: 'Mathematics',
          },
        },
        {
          id: i * 2 + 11,
          subject: {
            id: i * 2 + 21,
            name: 'Physics',
          },
        },
      ],
    })
  );
};

/**
 * Wait for element with longer timeout for slower operations.
 */
export const waitForElementWithTimeout = async (
  callback: () => HTMLElement,
  options: { timeout?: number } = {}
) => {
  const timeout = options.timeout || 3000;
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      return callback();
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
  }

  throw new Error('Element not found within timeout');
};

/**
 * Wait for mutations to complete.
 */
export const waitForMutation = async (options: { timeout?: number } = {}) => {
  await new Promise((resolve) =>
    setTimeout(resolve, options.timeout || 100)
  );
};
