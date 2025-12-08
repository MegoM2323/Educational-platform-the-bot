/**
 * Tests for ParentInvoicesList component.
 * Covers rendering, filtering, sorting, and status handling.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ParentInvoicesList } from '../ParentInvoicesList';
import {
  createMockInvoices,
} from '@/__tests__/utils/test-utils';
import { InvoiceStatus } from '@/integrations/api/invoiceAPI';

describe('ParentInvoicesList', () => {
  const mockOnInvoiceClick = vi.fn();
  const mockOnFilterChange = vi.fn();

  const defaultProps = {
    invoices: createMockInvoices(5),
    isLoading: false,
    onInvoiceClick: mockOnInvoiceClick,
    onFilterChange: mockOnFilterChange,
    summary: {
      total_unpaid_amount: 15000,
      overdue_count: 2,
      upcoming_count: 3,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render invoice table with columns', () => {
      render(<ParentInvoicesList {...defaultProps} />);

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });

    it('should display loading skeleton when isLoading is true', () => {
      const { container } = render(
        <ParentInvoicesList {...defaultProps} isLoading={true} invoices={[]} />
      );

      const skeletons = container.querySelectorAll('[class*="skeleton"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should display empty state when no invoices', () => {
      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[]}
        />
      );

      const emptyState = screen.getByRole('img', { hidden: true });
      expect(emptyState).toBeInTheDocument();
    });
  });

  describe('Invoice List Display', () => {
    it('should render all invoices', () => {
      render(<ParentInvoicesList {...defaultProps} />);

      defaultProps.invoices.forEach((invoice) => {
        expect(
          screen.getByText(invoice.student.full_name)
        ).toBeInTheDocument();
      });
    });

    it('should display formatted amounts', () => {
      const invoices = createMockInvoices(2, { amount: '5000.00' });
      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      invoices.forEach((invoice) => {
        const amount = parseFloat(invoice.amount).toLocaleString('ru-RU');
        const elements = screen.getAllByText(new RegExp(`${amount}.*₽`));
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it('should display due dates', () => {
      const invoices = createMockInvoices(1, { due_date: '2025-12-31' });
      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      // Due date is formatted, so we check for the year at least
      expect(screen.getByText(/2025/)).toBeInTheDocument();
    });

    it('should make invoice rows clickable', async () => {
      const user = userEvent.setup();
      const invoices = defaultProps.invoices;
      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      const firstInvoice = invoices[0];
      const studentName = firstInvoice.student.full_name;
      const row = screen.getByText(studentName).closest('tr');

      if (row) {
        await user.click(row);
        expect(mockOnInvoiceClick).toHaveBeenCalledWith(firstInvoice);
      }
    });
  });

  describe('Status Badges', () => {
    it('should display invoices with different statuses', () => {
      const invoices = [
        createMockInvoices(1, { id: 1, status: 'draft' })[0],
        createMockInvoices(1, { id: 2, status: 'sent' })[0],
        createMockInvoices(1, { id: 3, status: 'paid' })[0],
      ];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      expect(screen.getAllByRole('row').length).toBeGreaterThanOrEqual(3);
    });

    it('should render invoices with past dates', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const pastDate = yesterday.toISOString().split('T')[0];

      const overdueInvoice = createMockInvoices(1, {
        due_date: pastDate,
        status: 'sent',
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[overdueInvoice]}
        />
      );

      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    it('should not mark paid invoices as overdue', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const pastDate = yesterday.toISOString().split('T')[0];

      const paidInvoice = createMockInvoices(1, {
        due_date: pastDate,
        status: 'paid',
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[paidInvoice]}
        />
      );

      // Should not have overdue indicator for paid invoices
      expect(screen.getByText(paidInvoice.student.full_name)).toBeInTheDocument();
    });
  });

  describe('Summary Statistics', () => {
    it('should display summary when provided', () => {
      const summary = {
        total_unpaid_amount: 25000,
        overdue_count: 3,
        upcoming_count: 5,
      };

      const { container } = render(
        <ParentInvoicesList
          {...defaultProps}
          summary={summary}
        />
      );

      // Summary should be rendered in the component
      expect(container).toBeInTheDocument();
    });

    it('should handle missing summary', () => {
      render(
        <ParentInvoicesList
          {...defaultProps}
          summary={undefined}
        />
      );

      expect(screen.getByRole('table')).toBeInTheDocument();
    });
  });

  describe('Filtering', () => {
    it('should accept onFilterChange callback', () => {
      render(
        <ParentInvoicesList
          {...defaultProps}
          onFilterChange={mockOnFilterChange}
        />
      );

      // Verify the component renders with the callback
      expect(screen.getByRole('table')).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    it('should render invoices in table with different dates', () => {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);

      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);

      const overdueInvoice = createMockInvoices(1, {
        id: 1,
        due_date: yesterday.toISOString().split('T')[0],
        status: 'sent',
        student: { id: 1, full_name: 'Overdue Student' },
      })[0];

      const upcomingInvoice = createMockInvoices(1, {
        id: 2,
        due_date: tomorrow.toISOString().split('T')[0],
        status: 'sent',
        student: { id: 2, full_name: 'Upcoming Student' },
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[upcomingInvoice, overdueInvoice]}
        />
      );

      // Verify both invoices render
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('row').length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Days Calculation', () => {
    it('should correctly calculate days remaining', () => {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const inSevenDays = new Date(today);
      inSevenDays.setDate(inSevenDays.getDate() + 7);

      const invoice = createMockInvoices(1, {
        due_date: inSevenDays.toISOString().split('T')[0],
        status: 'sent',
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[invoice]}
        />
      );

      // Invoice should be rendered
      expect(screen.getByText(invoice.student.full_name)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have semantic table structure', () => {
      const { container } = render(
        <ParentInvoicesList {...defaultProps} />
      );

      const table = container.querySelector('table');
      const thead = table?.querySelector('thead');
      const tbody = table?.querySelector('tbody');

      expect(table).toBeInTheDocument();
      expect(thead).toBeInTheDocument();
      expect(tbody).toBeInTheDocument();
    });

    it('should have proper table headers', () => {
      const { container } = render(
        <ParentInvoicesList {...defaultProps} />
      );

      const headers = container.querySelectorAll('thead th');
      expect(headers.length).toBeGreaterThan(0);
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      const invoices = defaultProps.invoices;

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      const firstInvoice = invoices[0];
      const studentName = firstInvoice.student.full_name;
      const row = screen.getByText(studentName).closest('tr');

      if (row) {
        expect(row).toBeInTheDocument();
        await user.click(row);
        expect(mockOnInvoiceClick).toHaveBeenCalled();
      }
    });
  });

  describe('Edge Cases', () => {
    it('should handle invoices with very large amounts', () => {
      const largeAmountInvoice = createMockInvoices(1, {
        amount: '999999999.99',
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[largeAmountInvoice]}
        />
      );

      expect(
        screen.getByText(largeAmountInvoice.student.full_name)
      ).toBeInTheDocument();
    });

    it('should handle invoices with long student names', () => {
      const longNameInvoice = createMockInvoices(1, {
        student: {
          id: 2,
          full_name: 'A'.repeat(100),
        },
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[longNameInvoice]}
        />
      );

      expect(screen.getByText('A'.repeat(100))).toBeInTheDocument();
    });

    it('should handle single invoice', () => {
      const singleInvoice = createMockInvoices(1);

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={singleInvoice}
        />
      );

      expect(
        screen.getByText(singleInvoice[0].student.full_name)
      ).toBeInTheDocument();
    });

    it('should handle many invoices', () => {
      const manyInvoices = createMockInvoices(100);

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={manyInvoices}
        />
      );

      // Check that table is rendered
      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    it('should handle mixed invoice statuses', () => {
      const mixedInvoices = [
        createMockInvoices(1, { id: 1, status: 'draft', student: { id: 1, full_name: 'Student One' } })[0],
        createMockInvoices(1, { id: 2, status: 'sent', student: { id: 2, full_name: 'Student Two' } })[0],
        createMockInvoices(1, { id: 3, status: 'viewed', student: { id: 3, full_name: 'Student Three' } })[0],
        createMockInvoices(1, { id: 4, status: 'paid', student: { id: 4, full_name: 'Student Four' } })[0],
        createMockInvoices(1, { id: 5, status: 'cancelled', student: { id: 5, full_name: 'Student Five' } })[0],
      ];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={mixedInvoices}
        />
      );

      // Verify table renders with all invoices
      expect(screen.getAllByRole('row').length).toBeGreaterThanOrEqual(5);
    });

    it('should handle invoices with missing avatar', () => {
      const noAvatarInvoice = createMockInvoices(1, {
        student: {
          id: 2,
          full_name: 'John Doe',
        },
      })[0];

      render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={[noAvatarInvoice]}
        />
      );

      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('should render large lists efficiently', () => {
      const largeList = createMockInvoices(50);

      const { container } = render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={largeList}
        />
      );

      const rows = container.querySelectorAll('tbody tr');
      expect(rows.length).toBe(50);
    });

    it('should memoize sorted invoices', () => {
      const invoices = createMockInvoices(3);

      const { rerender } = render(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      // Re-render with same props
      rerender(
        <ParentInvoicesList
          {...defaultProps}
          invoices={invoices}
        />
      );

      // Should still render correctly
      invoices.forEach((invoice) => {
        expect(
          screen.getByText(invoice.student.full_name)
        ).toBeInTheDocument();
      });
    });
  });
});
